# ch15/run.sh
# Wire the serving layer's signals: vLLM CPU -> Prometheus (with
# the recording and alert rules) -> Grafana (vLLM's own dashboards),
# and vLLM -> OTLP -> an OpenTelemetry Collector for the traces.
. /lab/lib/lab.sh
. /lab/tools.env

MODEL=/models/hf/SmolLM2-360M-Instruct
S=/scratch/ch15
PROM=http://ch15-prom:9090
GRAFANA=http://ch15-grafana:3000

# fetch NAME FILE: a file tools.env pins by URL and SHA-256.
fetch() {
  local spec=${!1}
  curl -fsSL --retry 5 -o "$2" "${spec%@sha256:*}"
  echo "${spec##*@sha256:}  $2" | sha256sum -c --quiet - \
    || die "SHA-256 mismatch: $1"
}

step "config into the shared volume"
rm -rf "$S" && mkdir -p "$S/grafana/dashboards" \
  "$S/grafana/provisioning/datasources" \
  "$S/grafana/provisioning/dashboards" && chmod 777 "$S"
cp prometheus.yml rules.yml alerts.yml cost.yml rules-test.yml \
  otel-collector.yml "$S/"
cp grafana/datasource.yml "$S/grafana/provisioning/datasources/"
cp grafana/dashboards.yml "$S/grafana/provisioning/dashboards/"
D=$S/grafana/dashboards
fetch VLLM_DASHBOARD "$D/grafana.json"
fetch VLLM_DASHBOARD_PERF "$D/performance_statistics.json"
fetch VLLM_DASHBOARD_QUERY "$D/query_statistics.json"
ls "$D"

step "promtool: check the config, then unit-test the rules"
promtool() {
  run_tool "$PROMETHEUS_IMAGE" --entrypoint promtool -w "$S" -- "$@"
}
promtool check config prometheus.yml
promtool check rules cost.yml
promtool test rules rules-test.yml | tee "$MEASURED/promtool.txt"

step "the collector, then vLLM with its traces pointed at it"
start_server ch15-otel "$OTEL_COLLECTOR_IMAGE" \
  -- --config=/scratch/ch15/otel-collector.yml
wait_ready ch15-otel http://ch15-otel:13133/ 120
need_models smollm2-360m-hf
start_server ch15-vllm "$VLLM_CPU_IMAGE" --shm-size 1g \
  -e VLLM_CPU_KVCACHE_SPACE=1 -e OTEL_SERVICE_NAME=vllm \
  -- "$MODEL" --served-model-name smollm2-360m --dtype float16 \
  --max-model-len 2048 --port 8000 \
  --otlp-traces-endpoint grpc://ch15-otel:4317
wait_ready ch15-vllm http://ch15-vllm:8000/health 600

step "Prometheus and Grafana"
start_server ch15-prom "$PROMETHEUS_IMAGE" \
  -- --config.file=/scratch/ch15/prometheus.yml
start_server ch15-grafana "$GRAFANA_IMAGE" \
  -e GF_PATHS_PROVISIONING=/scratch/ch15/grafana/provisioning \
  -e GF_AUTH_ANONYMOUS_ENABLED=true \
  -e GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer --
wait_ready ch15-prom "$PROM/-/ready" 120
wait_ready ch15-grafana "$GRAFANA/api/health" 180

step "traffic: 48 requests sharing a 256-token prefix"
run_tool "$VLLM_CPU_IMAGE" --entrypoint vllm -- bench serve \
  --backend vllm --base-url http://ch15-vllm:8000 \
  --model smollm2-360m --tokenizer "$MODEL" \
  --dataset-name random --random-prefix-len 256 \
  --random-input-len 128 --random-output-len 32 --ignore-eos \
  --num-prompts 48 --max-concurrency 4 --seed 15 \
  > "$WORK/bench.log" 2>&1 \
  || { tail -n 20 "$WORK/bench.log"; die "bench failed"; }
curl -s http://ch15-vllm:8000/metrics > "$MEASURED/metrics.txt"
sleep 15  # a few scrapes and rule evaluations after the last one

step "Prometheus: the target, the recorded series, the alerts"
q() {
  curl -s --get "$PROM/api/v1/query" --data-urlencode "query=$1"
}
q 'up{job="vllm"}' | jq -r '.data.result[] | "up \(.value[1])"'
grep -o 'record: .*' rules.yml | cut -d' ' -f2 | while read -r r; do
  q "$r" | jq -r --arg r "$r" '.data.result[] | "\($r) \(.value[1])"'
done | awk '{printf "%-36s %8.3f\n", $1, $2}' \
  | tee "$MEASURED/recorded.txt"
curl -s "$PROM/api/v1/alerts" | tee "$MEASURED/alerts.json" \
  | jq -r '.data.alerts[] | "\(.state)  \(.labels.alertname)"'

step "Grafana: vLLM's dashboards, panel by panel"
python3 panels.py "$GRAFANA" "$PROM" smollm2-360m \
  "$MEASURED/panels.json"

step "traces"
cp "$S/spans.jsonl" "$MEASURED/spans.jsonl"
python3 spans.py "$MEASURED/spans.jsonl"

step "done"
write_manifest
