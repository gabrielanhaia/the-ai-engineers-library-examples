# ch03/simulated.sh
# Part 3 of the ch03 lab, SIMULATED: the same SLO method at rates no
# laptop could serve. llm-d-inference-sim runs no model; its latency
# is its configuration (80 ms to the first token, 20 ms per token,
# up to 2x slower with 16 requests in flight, queueing beyond that).
# Every number this part prints is simulated.
. /lab/lib/lab.sh
RATES=${CH03_SIM_RATES:-4 8 16}          # offered requests/s

step "llm-d-inference-sim v0.11.2 (simulated)"
need_models smollm2-360m-hf               # the tokenizer only
start_server sim "$LLM_D_SIM_IMAGE" -- --port 8000 \
  --model smollm2-360m --max-num-seqs 16 \
  --time-to-first-token 80ms --inter-token-latency 20ms \
  --time-factor-under-load 2.0
wait_ready sim http://sim:8000/health 60

mkdir -p /scratch/ch03
rm -f "$MEASURED"/simulated-*
for r in $RATES; do
  step "simulated: vllm bench serve at $r requests/s"
  run_tool "$VLLM_CPU_IMAGE" --entrypoint vllm -- bench serve \
    --backend openai-chat --endpoint /v1/chat/completions \
    --base-url http://sim:8000 --model smollm2-360m \
    --tokenizer /models/hf/SmolLM2-360M-Instruct \
    --dataset-name random --random-input-len 256 \
    --random-output-len 64 --ignore-eos \
    --num-prompts 200 --request-rate "$r" --seed 7 \
    --percentile-metrics ttft,tpot,itl,e2el \
    --metric-percentiles 50,90,99 \
    --goodput ttft:200 tpot:50 \
    --metadata simulated=true simulator=llm-d-inference-sim \
    --save-result --result-dir /scratch/ch03 \
    --result-filename "simulated-$r.json" --disable-tqdm \
    > "$WORK/bench.txt" 2>&1
  { echo "# SIMULATED: llm-d-inference-sim v0.11.2; every latency"
    echo "# below is the simulator's configuration, not a server."
    cat "$WORK/bench.txt"; } > "$MEASURED/simulated-$r.txt"
  sed -n '1,2p; /Serving Benchmark Result/,$p' \
    "$MEASURED/simulated-$r.txt"
  cp "/scratch/ch03/simulated-$r.json" "$MEASURED/"
done

step "simulated: attainment by offered rate (TTFT 200, TPOT 50 ms)"
for r in $RATES; do
  jq -r --arg r "$r" '"rate \($r) req/s: goodput "
    + "\(.request_goodput * 100 | round / 100) of "
    + "\(.request_throughput * 100 | round / 100) completed/s = "
    + "\(.request_goodput / .request_throughput * 100 | round)%"
    + " (simulated)"' "$MEASURED/simulated-$r.json"
done
