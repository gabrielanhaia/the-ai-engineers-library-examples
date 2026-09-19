# ch18/run.sh
# The release gates, each proven to fail. Every candidate either
# changes nothing (its gate must pass) or carries one injected
# regression (its gate must fail):
#   quality      ch11's task eval on llama.cpp; the regression is a
#                chat template that ignores add_generation_prompt
#   performance  `vllm bench serve` at 512 tokens in, 128 out,
#                against simulated replicas; the regression is a
#                slower simulator configuration (simulated)
# Then the canary route is validated by a Kubernetes API server and
# the alert rules by promtool.
. /lab/lib/lab.sh
. /lab/lib/kind.sh

S=/scratch/ch18
GGUF=/models/gguf/SmolLM2-360M-Instruct-Q8_0.gguf
HF=/models/hf/SmolLM2-360M-Instruct
mkdir -p "$S"
echo '{}' >"$MEASURED/gates.json"

# gate KIND CANDIDATE  run gate.py on BASE vs CANDIDATE, record it.
gate() {
  local kind=$1 cand=$2 base=$3 file=$4 v
  echo "$kind gate, candidate: $cand"
  if python3 gate.py "$kind" "$MEASURED/$base" "$MEASURED/$file"
  then v=pass; else v=fail; fi
  jq --arg k "$kind" --arg c "$cand" --arg v "$v" \
    '.[$k][$c] = $v' "$MEASURED/gates.json" >"$WORK/g.json"
  mv "$WORK/g.json" "$MEASURED/gates.json"
}

step "quality gate: ch11's task eval, llama.cpp, SmolLM2-360M Q8_0"
need_models smollm2-360m-gguf hf >"$WORK/models.txt"
python3 broken_template.py "$HF" "$S"
eval_with() {             # NAME TEMPLATE
  start_llama llama -m "$GGUF" --ctx-size 2048 --jinja \
    --chat-template-file "$S/$2.jinja"
  wait_ready llama http://llama:8080/health >/dev/null
  (cd /lab/ch11 && python3 eval.py http://llama:8080 "$1") \
    >"$MEASURED/eval-$1.json"
  stop_server llama
}
eval_with baseline good
eval_with rerun good
eval_with broken-template broken
jq -r '.items[0].reply | "first reply, broken template: \(@json)"' \
  "$MEASURED/eval-broken-template.json"
gate quality rerun eval-baseline.json eval-rerun.json
gate quality broken-template eval-baseline.json \
  eval-broken-template.json

step "performance gate: vllm bench serve, 512 in / 128 out, simulated"
bench_with() {            # NAME INTER_TOKEN_LATENCY
  _start sim "$LLM_D_SIM_IMAGE" -- --model=smollm2-360m --port=8000 \
    --mode=random --max-model-len=8192 --max-num-seqs=16 \
    --latency-calculator=per-token --prefill-overhead=20ms \
    --prefill-time-per-token=1ms --inter-token-latency="$2"
  wait_ready sim http://sim:8000/health >/dev/null
  run_tool "$VLLM_CPU_IMAGE" --entrypoint vllm -- bench serve \
    --base-url http://sim:8000 --model smollm2-360m \
    --tokenizer "$HF" --dataset-name random \
    --random-input-len 512 --random-output-len 128 \
    --num-prompts 60 --request-rate 2 --seed 18 --ignore-eos \
    --percentile-metrics ttft,tpot,itl --metric-percentiles 50,99 \
    --goodput ttft:1000 tpot:25 \
    --save-result --result-dir "$S" \
    --result-filename "bench-$1.json" \
    >"$WORK/bench-$1.log" 2>&1 \
    || { tail -n 20 "$WORK/bench-$1.log" >&2; die "bench $1"; }
  cp "$S/bench-$1.json" "$MEASURED/"
  stop_server sim
}
bench_with baseline 20ms
bench_with rerun 20ms
bench_with slower-config 26ms
gate performance rerun bench-baseline.json bench-rerun.json
gate performance slower-config bench-baseline.json \
  bench-slower-config.json

step "canary route: validated by the API server (kind)"
kind_tools >/dev/null
start_kind ch18 >/dev/null
apply_pinned GATEWAY_API_CRDS
apply_pinned GAIE_CRDS
kubectl apply --dry-run=server -f pools.yaml -f canary-route.yaml
sed 's/weight: 5$/weight: -5/' canary-route.yaml >"$WORK/bad.yaml"
if kubectl apply --dry-run=server -f "$WORK/bad.yaml" \
     >"$WORK/bad.log" 2>&1; then
  die "the API server accepted a negative weight"
fi
echo "rejected, as it should be: a route with weight -5"
jq '.manifests = "valid"' "$MEASURED/gates.json" >"$WORK/g.json"
mv "$WORK/g.json" "$MEASURED/gates.json"

step "alert rules: promtool"
cp alerts.yaml alerts-test.yaml "$S/"
run_tool "$PROMETHEUS_IMAGE" --entrypoint promtool -- \
  check rules "$S/alerts.yaml"
run_tool "$PROMETHEUS_IMAGE" --entrypoint promtool -- \
  test rules "$S/alerts-test.yaml"
jq '.alert_rules = "pass"' "$MEASURED/gates.json" >"$WORK/g.json"
mv "$WORK/g.json" "$MEASURED/gates.json"

step "done"
jq . "$MEASURED/gates.json"
kind_manifest
