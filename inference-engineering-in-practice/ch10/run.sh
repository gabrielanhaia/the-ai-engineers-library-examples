# ch10/run.sh
# Prefix caching on the vLLM CPU backend: the same long system
# prompt sent with its stable part first (shared) and with a
# per-request line in front of it (unique). The hit rate is
# hits / queries from the server's own counters.
. /lab/lib/lab.sh

N=${N:-20}
MODEL=/models/hf/SmolLM2-360M-Instruct
URL=http://ch10-vllm:8000

step "vLLM CPU backend (prefix caching is on by default)"
need_models smollm2-360m-hf
start_vllm ch10-vllm "$MODEL" --served-model-name smollm2-360m \
  --dtype float16 --max-model-len 2048
wait_ready ch10-vllm "$URL/health" 600
curl -s "$URL/metrics" | grep -o '^vllm:prefix_cache_[a-z]*_total' \
  | sort -u

step "$N requests per workload, one at a time"
OM=$MEASURED/metrics.om.gz
python3 /lab/lib/metrics.py watch "$URL" "$OM" \
  > "$WORK/watch.log" 2>&1 &
WATCH=$!
python3 prompts.py "$URL" "$N" "$MEASURED"
kill -TERM "$WATCH"
wait "$WATCH"

step "done"
write_manifest
