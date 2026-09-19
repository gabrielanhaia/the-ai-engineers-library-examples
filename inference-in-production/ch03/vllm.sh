# ch03/vllm.sh
# Part 2 of the ch03 lab: a request-rate ramp on vLLM's CPU backend.
# /metrics is recorded every 5 s for replay into Prometheus and
# Grafana (screenshot S3); one scrape is kept as the chapter prints
# it; and the two queries in queries.promql run on the replay.
. /lab/lib/lab.sh
RAMP=${CH03_RAMP:-0.2,0.4,0.6,0.8,1.0}   # requests/s, one step each
STEP_S=${CH03_STEP_S:-60}                # seconds per step

step "vLLM 0.29.0 (CPU): SmolLM2-360M-Instruct, BF16"
need_models smollm2-360m-hf
start_vllm vllm /models/hf/SmolLM2-360M-Instruct \
  --served-model-name smollm2-360m --max-model-len 2048
wait_ready vllm http://vllm:8000/health 600

step "ramp: $RAMP requests/s, $STEP_S s per step"
python3 /lab/lib/metrics.py watch http://vllm:8000 \
  "$MEASURED/vllm-ramp.om.gz" 5 &
WATCH=$!
python3 load.py http://vllm:8000 --model smollm2-360m \
  --ramp "$RAMP" --step-s "$STEP_S" > "$MEASURED/vllm-ramp.jsonl"
sleep 10                      # two more scrapes after the last token
kill -TERM "$WATCH"
wait "$WATCH"
jq -rs '"\(length) requests, \(map(select(.error)) | length)"
  + " errors"' "$MEASURED/vllm-ramp.jsonl"

step "one scrape, filtered to the TTFT histogram and one counter"
curl -s http://vllm:8000/metrics \
  | grep -E '^vllm:(time_to_first_token_seconds|generation_tokens)' \
  | tee "$MEASURED/vllm-scrape.txt"

step "replay: the recording into Prometheus, and the two queries"
R=/scratch/ch03/replay
rm -rf "$R"
mkdir -p "$R"
gzip -dc "$MEASURED/vllm-ramp.om.gz" > "$R/vllm-ramp.om"
chmod -R a+rwX "$R"           # Prometheus runs as nobody
run_tool "$PROMETHEUS_IMAGE" --entrypoint promtool -- tsdb \
  create-blocks-from openmetrics "$R/vllm-ramp.om" "$R/tsdb" \
  > "$WORK/promtool.txt"
start_server prom "$PROMETHEUS_IMAGE" -- \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path="$R/tsdb" --storage.tsdb.retention.time=10y
wait_ready prom http://prom:9090/-/ready 60
read -r T0 T1 < <(awk '!/^#/ { t = $NF; if (!a || t < a) a = t
  if (t > b) b = t } END { print a, b }' "$R/vllm-ramp.om")
awk -v RS= -v ORS='\0' 'NR > 1' queries.promql \
  | while IFS= read -r -d '' q; do
      curl -sG http://prom:9090/api/v1/query_range \
        --data-urlencode "query=$q" --data-urlencode "start=$T0" \
        --data-urlencode "end=$T1" --data-urlencode step=15
      echo
    done | jq -s . > "$MEASURED/promql.json"
jq -r '.[] | .data.result[0].values | map(.[1] | select(. != "NaN")
  | tonumber) | "\(length) points, max \(max * 1000 | round) ms"' \
  "$MEASURED/promql.json"
