#!/usr/bin/env bash
# screens/cost-sim.sh [MINUTES] -- record the data behind screenshot S12.
#
# It starts llm-d-inference-sim v0.11.2, drives it at chapter 5's CITED
# per-node output-token rate with screens/cost_pacer.py, and writes the
# counter to measured/ch15/cost-sim.om. Nothing is measured here: the
# rate is a published figure and the tokens are a simulator's.
#
#   bash screens/cost-sim.sh 12
#
# screens/cost-replay.sh then rebuilds that file into a Prometheus,
# backfills ch15/cost.yml over it and captures the panel.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
. ./images.env

MINUTES=${1:-12}
OUT=$ROOT/measured/ch15/cost-sim.om
SIM=aiel-screens-sim
NET=${AIEL_NET:-aiel-inference}
PY=${PY:-$ROOT/.work/screens/venv/bin/python}
[ -x "$PY" ] || PY=python3

docker rm -f "$SIM" >/dev/null 2>&1 || true
docker run -d --name "$SIM" --network "$NET" --network-alias sim \
  -p 127.0.0.1:8011:8000 "$LLM_D_SIM_IMAGE" \
  --model gpt-oss --served-model-name gpt-oss --port 8000 \
  --max-model-len 65536 --max-num-seqs 256 \
  --max-waiting-queue-length 4096 \
  --inter-token-latency 0 --time-to-first-token 0 >/dev/null

for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8011/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

"$PY" screens/cost_pacer.py --url http://127.0.0.1:8011 --model gpt-oss \
  --minutes "$MINUTES" --out "$OUT"

docker rm -f "$SIM" >/dev/null
echo "sim stopped; data in $OUT"
