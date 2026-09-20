# ch07/test.sh
# Asserts invariants of the capacity arithmetic, never a GPU
# count: Little's law is linear in the rate, a bigger model leaves
# less KV, and the refusals (a looser bound, a laptop's rate).
. /lab/lib/lab.sh

bash run.sh

step "assertions"
jq -e '.numbers | length > 0' "$MEASURED/derived.json" >/dev/null \
  || die "derived.json has no numbers"
echo "ok  derived.json recorded"

python3 - <<'PY' || die "an invariant failed"
import math
import capacity as c

hw = c.toml(c.INPUTS / "hardware.toml")
models = c.toml(c.INPUTS / "models.toml")
m = models["llama-3_1-70b"]
b = [c.kv_budget(hw["B200"], m["params"] * wb, 0.92) for wb in (1, 2)]
assert b[0] > b[1] > 0
print("ok  more weight bytes leave less KV (FP8 > BF16 on B200)")
one = c.running_batch(10, 1.0, 500, 0.04)
assert math.isclose(c.running_batch(20, 1.0, 500, 0.04), 2 * one)
print("ok  the running batch is linear in the arrival rate")
w = {"rate": "example-a", "gpu": "B200", "ttft_ms": 3000,
     "tpot_ms": 40}
try:
    c.cited_rate(w, hw)
    raise AssertionError("accepted a rate at a looser bound")
except SystemExit as e:
    assert "looser" in str(e)
print("ok  refuses a rate measured at a looser bound than the SLO")
real = c.toml
c.toml = lambda p: {"node": {"gpu": "M2 Pro", "tokens": "output",
                             "server": 60, "gpus": 1,
                             "ttft_ms": 1, "tpot_ms": 1}}
try:
    c.cited_rate(w | {"gpu": "M2 Pro", "tpot_ms": 80}, hw)
    raise AssertionError("accepted a laptop's rate")
except SystemExit as e:
    assert "not a GPU" in str(e)
c.toml = real
print("ok  refuses a rate from a machine that is not a GPU")
PY

python3 - <<'PY' || die "a fleet is smaller than a count"
import contextlib
import io
import capacity as c

hw = c.toml(c.INPUTS / "hardware.toml")
models = c.toml(c.INPUTS / "models.toml")
for w in c.toml(c.HERE / "examples.toml")["workload"]:
    with contextlib.redirect_stdout(io.StringIO()):
        memory, rate, fleet = c.plan(w, hw, models, 0.92)
    assert fleet >= max(memory, rate) and fleet % w["unit"] == 0
print("ok  every fleet covers both counts, in whole units")
PY

python3 - <<'PY' || die "the purchase unit multiplied a GPU count"
import contextlib
import io
import capacity as c

# The purchase unit rounds the memory count UP to a whole unit; it
# never multiplies it. A workload whose KV needs three GPUs is 8
# H100 when you buy 8 at a time, never 24, and the per-replica line
# says the same thing whatever the unit is.
hw = c.toml(c.INPUTS / "hardware.toml")
models = c.toml(c.INPUTS / "models.toml")
base = c.toml(c.HERE / "examples.toml")["workload"][0]


def memory_count(unit):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        need, _, _ = c.plan(dict(base, unit=unit), hw, models, 0.92)
    per = [ln for ln in out.getvalue().splitlines() if "seqs," in ln]
    return need, per


one, per_one = memory_count(1)
assert one > 1, "this workload must need more than one GPU"
for unit in (2, 8):
    need, per = memory_count(unit)
    assert need % unit == 0, f"{need} is not whole units of {unit}"
    assert one <= need < one + unit, f"unit {unit} gave {need}"
    assert per == per_one, "the per-replica line moved with the unit"
print("ok  the purchase unit rounds the count up, never multiplies")
PY
