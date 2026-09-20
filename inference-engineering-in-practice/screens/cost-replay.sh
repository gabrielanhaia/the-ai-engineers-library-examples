#!/usr/bin/env bash
# screens/cost-replay.sh -- the replay stack for screenshot S12.
#
# The other replayed shots only need their series rebuilt. This one
# also needs ch15/cost.yml evaluated over them, and a recording rule
# only fires on live scrapes -- so the rule is backfilled with
# `promtool tsdb create-blocks-from rules` into the same TSDB, and
# Prometheus is restarted to pick the new blocks up.
#
#   bash screens/cost-sim.sh 13      # record the data (once)
#   bash screens/cost-replay.sh      # rebuild it, backfill, capture
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
. ./images.env

OM=measured/ch15/cost-sim.om
DATA=$ROOT/.work/screens/data/cost
BACKFILL=$ROOT/.work/screens/backfill
NET=${AIEL_NET:-aiel-inference}
PY=${PY:-$ROOT/.work/screens/venv/bin/python}
OUT=${OUT:-$HOME/WebstormProjects/book-inference-engineering/en/content/chapters/images}

[ -f "$OM" ] || { echo "no $OM; run screens/cost-sim.sh first" >&2; exit 1; }

# The window the data covers, from the file itself.
read -r START END < <(awk '!/^#/ && NF { t = $NF + 0;
  if (a == 0 || t < a) a = t; if (t > b) b = t } END { printf "%d %d\n", a, b }' "$OM")
echo "data covers $START .. $END ($((END - START)) s)"

SCRAPE=5s bash screens/replay.sh cost "$OM" >/dev/null
echo "raw series replayed"

# Twice, because the second rule reads the first. promtool evaluates
# every rule against the Prometheus it is pointed at, and the series
# the first rule records does not exist there until its blocks have
# been loaded -- so pass one lands `fleet:usd_per_hour` and pass two,
# against a Prometheus that now has it, lands the dollars-per-million
# rule that divides by it. The rule file is used exactly as ch15 ships
# it; only the order is arranged.
backfill_pass() {
  local n=$1
  rm -rf "$BACKFILL" && mkdir -p "$BACKFILL"
  docker run --rm --network "$NET" --entrypoint promtool \
    -v "$ROOT:/repo:ro" -v "$BACKFILL:/out" \
    "$PROMETHEUS_IMAGE" tsdb create-blocks-from rules \
    --start "$START" --end "$END" --eval-interval 15s \
    --url http://prometheus:9090 --output-dir /out \
    /repo/ch15/cost.yml 2>&1 | grep "processing rule" || true
  # promtool writes its blocks under <output-dir>/data.
  find "$BACKFILL" -maxdepth 3 -name meta.json -exec dirname {} \; \
    | while read -r block; do cp -R "$block" "$DATA/"; done
  docker restart aiel-screens-prom >/dev/null
  for _ in $(seq 1 60); do
    if curl -sf http://127.0.0.1:9090/-/ready >/dev/null 2>&1; then break; fi
    sleep 1
  done
  echo "pass $n done"
}
backfill_pass 1
backfill_pass 2

echo "recorded series now in the replay:"
curl -s "http://127.0.0.1:9090/api/v1/label/__name__/values" \
  | tr ',' '\n' | grep fleet || echo "  (none -- the backfill produced nothing)"

"$PY" screens/capture.py S12-cost-panel --out "$OUT"
