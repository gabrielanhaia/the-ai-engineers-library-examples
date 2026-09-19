# ch05/test.sh
# Asserts invariants of the arithmetic, never a price: the unit
# check holds for every row, cost scales as 1 / utilization, the
# orderings chapter 5 argues from, and the refusals.
. /lab/lib/lab.sh

bash run.sh

step "assertions"
jq -e '.numbers | length > 0' "$MEASURED/derived.json" >/dev/null \
  || die "derived.json has no numbers"
echo "ok  derived.json recorded"

python3 - <<'PY' || die "an invariant failed"
import math
import cost

def at(row, key):
    usd, gpu, _ = cost.gpu_price(key)
    return cost.price(cost.mlperf_row(row), usd, gpu)[2]

n = "Nebius/{}/gpt-oss-120b/Server"
b200 = at(cost.EXAMPLE_A, "nebius.B200")
rtx = at(n.format("RTX_PRO_6000_PCIE_96GBx8_TRT"),
         "nebius.RTX PRO 6000")
b300 = at(n.format("B300-SXM-270GBx8_TRT"), "nebius.B300")
print("ok  per unit and per GPU agree for every row priced")
assert b300 < b200 < rtx
print("ok  cheapest GPU-hour, dearest token: B300 < B200 < RTX PRO")
gb = "NVIDIA/GB200-NVL72_GB200-186GB_aarch64x72_TRT/gpt-oss-120b/"
assert at(gb + "Server", "coreweave.GB200") < at(
    gb + "Interactive", "coreweave.GB200")
print("ok  a tighter latency bound costs more per token (GB200)")
u = 0.4
assert math.isclose(cost.per_million(57.2 / u, 1e4),
                    cost.per_million(57.2, 1e4) / u)
print("ok  cost at utilization U = cost at 100% / U")
PY

if python3 cost.py --price nebius.H200 >/dev/null 2>&1; then
  die "a price for another GPU was accepted"
fi
echo "ok  refuses a price for a GPU the row was not measured on"
if python3 cost.py --tokens-per-second 50 >/dev/null 2>&1; then
  die "a typed-in throughput was accepted"
fi
echo "ok  takes no typed-in throughput (so never a laptop's)"
grep -q WARNING "$MEASURED/other-shape.txt" \
  || die "no warning for a shape the row was not measured at"
echo "ok  warns when your shape is not the row's"
