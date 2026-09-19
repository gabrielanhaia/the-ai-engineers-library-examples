# ch06/test.sh
# Asserts invariants of the break-even, never a price: break-even
# U is the ratio of the two per-request prices, halving the API
# price doubles it, and every added cost moves it up.
. /lab/lib/lab.sh

bash run.sh

step "assertions"
jq -e '.numbers | length > 0' "$MEASURED/derived.json" >/dev/null \
  || die "derived.json has no numbers"
echo "ok  derived.json recorded"

python3 - <<'PY' || die "an invariant failed"
import math
from breakeven import HOURS, api_request, breakeven, load
from breakeven import per_million

ex = load()
n_in = ex["shape"]["input_tokens"]
n_out = ex["shape"]["output_tokens"]
node_h = ex["nebius"]["B200"] * ex["node"]["gpus"]
node_req = ex["node"]["server"] * 3600 * HOURS / n_out
month = node_h * HOURS
api = api_request(ex["together"], n_in, n_out)
self_req = n_out * per_million(node_h, ex["node"]["server"]) / 1e6
u, req = breakeven(month, node_req, api)
assert math.isclose(u, self_req / api) and 0 < u < 1
print("ok  break-even U = self-host / API price per request, < 1")
assert math.isclose(req * api, month)
print("ok  break-even requests x API price = the fleet's month")
u2, req2 = breakeven(month, node_req, api / 2)
assert math.isclose(u2, 2 * u) and math.isclose(req2, 2 * req)
print("ok  halving the API price doubles the break-even")
u3, _ = breakeven(2 * month + 5000, node_req, api)
assert u3 > 2 * u
print("ok  a second node and staff time move it further up")
PY
