# ch18/run.sh
# The release gates, each proven to fail. Every candidate either
# changes nothing (its gate must pass) or carries one injected
# regression (its gate must fail):
#   quality      ch11's task eval AND ch17's contract verifier on
#                llama.cpp; the regression is a chat template that
#                ignores add_generation_prompt
#   performance  `vllm bench serve` at 512 tokens in, 128 out,
#                against simulated replicas; the regression is a
#                slower simulator configuration (simulated)
# Then the canary route is validated by a Kubernetes API server and
# the alert rules by promtool.
. /lab/lib/lab.sh
. /lab/lib/kind.sh

S=/scratch/ch18
# The candidate stack is chapter 17's: the same F16 GGUF and the
# same chat template, so chapter 17's thresholds judge it.
GGUF=/models/gguf/SmolLM2-360M-Instruct-f16.gguf
HF=/models/hf/SmolLM2-360M-Instruct
mkdir -p "$S"
echo '{}' >"$MEASURED/gates.json"

# gate KIND CANDIDATE BASE FILE  run the gate on BASE vs CANDIDATE
# and record its verdict. A quality candidate must also clear
# chapter 17's endpoint contract, which is a floor, not a
# comparison: a stack that answers well and parses badly ships
# nothing.
gate() {
  local kind=$1 cand=$2 base=$3 file=$4 v=pass
  echo "$kind gate, candidate: $cand"
  python3 gate.py "$kind" "$MEASURED/$base" "$MEASURED/$file" \
    || v=fail
  if [ "$kind" = quality ]; then
    python3 /lab/ch17/gate.py "$WORK/thresholds.json" \
      "$MEASURED/verify-$cand" || v=fail
  fi
  jq --arg k "$kind" --arg c "$cand" --arg v "$v" \
    '.[$k][$c] = $v' "$MEASURED/gates.json" >"$WORK/g.json"
  mv "$WORK/g.json" "$MEASURED/gates.json"
}

step "quality gate: ch11's eval + ch17's verifier, llama.cpp F16"
need_models smollm2-360m-gguf hf >"$WORK/models.txt"
python3 broken_template.py /lab/ch17/template.jinja "$S"
# Chapter 17's floors, minus the engines this lab does not serve.
jq '{"llama.cpp": .["llama.cpp"]}' /lab/ch17/thresholds.json \
  >"$WORK/thresholds.json"
eval_with() {             # NAME TEMPLATE [verify]
  start_llama llama -m "$GGUF" --ctx-size 4096 --jinja \
    --chat-template-file "$S/$2.jinja"
  wait_ready llama http://llama:8080/health >/dev/null
  (cd /lab/ch11 && python3 eval.py http://llama:8080 "$1") \
    >"$MEASURED/eval-$1.json"
  if [ "${3:-}" = verify ]; then
    # The same 40 requests chapter 17 sends, against the same
    # server: the answers a caller has to parse.
    rm -rf "${MEASURED:?}/verify-$1"
    mkdir -p "$MEASURED/verify-$1"
    echo "contract check, $1 (chapter 17's requests):"
    echo " engine     kind         requests  valid   rate  right tool"
    (cd /lab/ch17 && python3 verify.py llama.cpp \
      http://llama:8080 "$MEASURED/verify-$1")
  fi
  stop_server llama
}
eval_with baseline good
eval_with rerun good verify
eval_with broken-template broken verify
jq -r '.items[0].reply | "first reply, broken template: \(@json)"' \
  "$MEASURED/eval-broken-template.json"
gate quality rerun eval-baseline.json eval-rerun.json
gate quality broken-template eval-baseline.json \
  eval-broken-template.json
# Chapter 17's floors do not move here: the engine's grammar still
# produces a valid tool call, whatever the prompt ended with. What
# moved is the replies themselves, which is why a gate needs both.
V=$MEASURED/verify
changed=$(paste <(jq -c .message "$V-rerun/llama.cpp.jsonl") \
                <(jq -c .message \
                  "$V-broken-template/llama.cpp.jsonl") \
          | awk -F'\t' '$1 != $2 {n++} END {print n + 0}')
n=$(wc -l < "$V-rerun/llama.cpp.jsonl")
echo "contract replies changed: $changed of $n, all still valid"
jq --argjson c "$changed" '.contract_replies_changed = $c' \
  "$MEASURED/gates.json" >"$WORK/g.json"
mv "$WORK/g.json" "$MEASURED/gates.json"

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
  # What the gate judges, kept on its own: goodput and median TPOT
  # from the harness chapter 4 uses, beside the run's shape.
  jq --arg run "$1" '{run: $run, request_rate, num_prompts,
      request_throughput, request_goodput, median_tpot_ms,
      p99_ttft_ms}' "$S/bench-$1.json" >"$MEASURED/perf-$1.json"
  stop_server sim
}
bench_with baseline 20ms
bench_with rerun 20ms
bench_with slower-config 26ms
gate performance rerun perf-baseline.json perf-rerun.json
gate performance slower-config perf-baseline.json \
  perf-slower-config.json

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
