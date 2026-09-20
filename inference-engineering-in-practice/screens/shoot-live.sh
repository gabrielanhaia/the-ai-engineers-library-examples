#!/usr/bin/env bash
# screens/shoot-live.sh -- the two captures that need a live page.
#
# S11 photographs llama.cpp's web UI in the middle of an answer, and a
# 135M model on a laptop CPU finishes one in a few tenths of a second.
# A frame is kept only when the stop control was up on both sides of
# the screenshot AND the prompt's own token count has rendered, so an
# attempt can legitimately come back empty. Each retry starts a fresh
# llama-server, because llama.cpp caches the prompt and a second run of
# the same question reports a one-token prefill.
#
#   bash screens/shoot-live.sh          # S11 and S10
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
PY=${PY:-$ROOT/.work/screens/venv/bin/python}
OUT=${OUT:-$HOME/WebstormProjects/book-inference-engineering/en/content/chapters/images}
TRIES=${TRIES:-8}

png=$OUT/S11-llama-cpp-webui.png
rm -f "$png"
for i in $(seq 1 "$TRIES"); do
  echo "== S11 attempt $i"
  bash screens/live-servers.sh llama >/dev/null
  "$PY" screens/capture.py S11-llama-cpp-webui --out "$OUT" || true
  if [ -f "$png" ]; then
    echo "S11 captured on attempt $i"
    break
  fi
done
bash screens/live-servers.sh down >/dev/null
[ -f "$png" ] || { echo "S11: no mid-stream frame in $TRIES attempts" >&2; exit 1; }

"$PY" screens/capture.py S10-guidellm-report --out "$OUT"
