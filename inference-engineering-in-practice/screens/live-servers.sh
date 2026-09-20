#!/usr/bin/env bash
# screens/live-servers.sh llama|down -- the servers the live captures need.
#
# S11 photographs llama.cpp's own web UI while it answers, so it needs a
# real llama-server. The server is started fresh every time: llama.cpp
# keeps a prompt cache between requests, and a second run of the same
# prompt reports a one-token prefill at two tokens a second, which is
# true and reads as nonsense in a book.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
. ./images.env

NET=${AIEL_NET:-aiel-inference}
C=aiel-screens-llama

case ${1:-llama} in
  down)
    docker rm -f "$C" >/dev/null 2>&1 || true
    echo "stopped"
    exit 0
    ;;
  llama) ;;
  *) echo "usage: live-servers.sh llama|down" >&2; exit 1 ;;
esac

docker rm -f "$C" >/dev/null 2>&1 || true
docker run -d --name "$C" --network "$NET" --network-alias llama \
  -p 127.0.0.1:8080:8080 -v aiel-models:/models:ro "$LLAMA_CPP_IMAGE" \
  --port 8080 --host 0.0.0.0 \
  -m /models/gguf/SmolLM2-135M-Instruct-Q8_0.gguf \
  --ctx-size 2048 --metrics --threads 5 >/dev/null

for _ in $(seq 1 90); do
  if curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
    echo "llama.cpp on http://127.0.0.1:8080 (fresh, no prompt cache)"
    exit 0
  fi
  sleep 1
done
echo "llama.cpp did not come up" >&2
exit 1
