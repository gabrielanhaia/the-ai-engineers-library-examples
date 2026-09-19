# ch08/run.sh
# Continuous batching, bounded and measured. First the roofline
# model's upper bound for an 8B model on an H100 (arithmetic on
# cited inputs). Then the laptop's own curve: a closed-loop sweep
# of concurrency 1 -> 128 on the vLLM CPU backend. Then the offline
# corner: the same requests as one batch file, nobody waiting.
. /lab/lib/lab.sh

CONCS=${CONCS:-1 2 4 8 16 32 64 128}
BATCH=${BATCH:-256}
MODEL=/models/hf/SmolLM2-360M-Instruct
URL=http://ch08-vllm:8000

step "the bound (DERIVED from inputs/, not measured)"
python3 bound.py
python3 derived.py > "$MEASURED/derived.json"

step "the laptop: vLLM CPU backend, 64 tokens in, 64 out"
need_models smollm2-360m-hf
start_vllm ch08-vllm "$MODEL" --served-model-name smollm2-360m \
  --dtype float16 --max-model-len 2048
wait_ready ch08-vllm "$URL/health" 600
mkdir -p /scratch/ch08
rm -f "$MEASURED"/bench-c*.json
for c in $CONCS; do
  n=$((c < 4 ? 16 : 4 * c))
  run_tool "$VLLM_CPU_IMAGE" --entrypoint vllm -- bench serve \
    --backend vllm --base-url "$URL" --model smollm2-360m \
    --tokenizer "$MODEL" --dataset-name random \
    --random-input-len 64 --random-output-len 64 --ignore-eos \
    --seed "$c" --num-prompts "$n" --max-concurrency "$c" \
    --num-warmups 4 \
    --request-rate inf --percentile-metrics ttft,tpot,itl \
    --metric-percentiles 50,99 --save-result \
    --result-dir /scratch/ch08 --result-filename "c$c.json" \
    > "$WORK/bench-c$c.log" 2>&1 \
    || { tail -n 20 "$WORK/bench-c$c.log"; die "bench at $c"; }
  cp "/scratch/ch08/c$c.json" "$MEASURED/bench-c$c.json"
done
python3 sweep.py "$MEASURED"
echo "preemptions during the sweep: $(python3 /lab/lib/metrics.py \
  get "$URL" vllm:num_preemptions_total)" \
  | tee "$MEASURED/preemptions.txt"
stop_server ch08-vllm

step "the offline corner: $BATCH requests in one file, run-batch"
python3 batch.py make "$BATCH" > /scratch/ch08/batch-in.jsonl
run_tool "$VLLM_CPU_IMAGE" --entrypoint vllm --shm-size 1g \
  -e VLLM_CPU_KVCACHE_SPACE=1 -- run-batch \
  -i /scratch/ch08/batch-in.jsonl -o /scratch/ch08/batch-out.jsonl \
  --model "$MODEL" --served-model-name smollm2-360m \
  --dtype float16 --max-model-len 2048 > "$WORK/run-batch.log" 2>&1 \
  || { tail -n 20 "$WORK/run-batch.log"; die "run-batch failed"; }
cp /scratch/ch08/batch-out.jsonl "$MEASURED/batch-out.jsonl"
grep -o 'Running batch: 100%.*' "$WORK/run-batch.log" | tail -n 1
python3 batch.py read "$MEASURED/batch-out.jsonl" \
  "$WORK/run-batch.log" "$MEASURED/offline.json"

step "done"
write_manifest
