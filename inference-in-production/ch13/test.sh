# ch13/test.sh
# Asserts what must stay true of the three formulas, never their
# numbers: copies never fall below one, TP=2 holds exactly one more
# copy of the weights as KV than two replicas, and the P:D ratio
# does not move when the arrival rate doubles.
. /lab/lib/lab.sh

bash run.sh

step "assertions"
jq -e '.numbers | length > 0' "$MEASURED/derived.json" >/dev/null \
  || die "derived.json has no numbers"
echo "ok  derived.json recorded"

python3 - <<'PY' || die "an invariant failed"
import math
import layout as ly

models = ly.toml("models.toml")
for m in models.values():
    if "kv_heads" in m:
        for tp in (1, 2, 4, 8, 16):
            assert ly.kv_copies(tp, m["kv_heads"]) >= 1
print("ok  KV copies never fall below one")
w = models["llama-3_1-70b"]["params"]
two = ly.kv_budget_gb(80, 0.92, w, 1, 2)
tp2 = ly.kv_budget_gb(80, 0.92, w, 2, 1)
assert round((tp2 - two) * 1e9) == w
print("ok  TP=2 minus two replicas = one copy of the weights, "
      "to the byte")
sg = ly.toml("parallelism.toml")["sglang"]
args = (8, 1, sg["prefill_tok_s"], sg["decode_tok_s"])
assert math.isclose(ly.pd_ratio(*args, rate=1.0),
                    ly.pd_ratio(*args, rate=2.0))
print("ok  the P:D ratio does not move when the rate doubles")
PY
