# ch09/run.sh
# KV-cache pressure on the vLLM CPU backend. Predict from the
# model's config the concurrency at which a 1 GiB cache overflows,
# then send batches of long requests at once, below and above that
# point, and read vllm:num_preemptions_total after each batch.
. /lab/lib/lab.sh

LEVELS=${LEVELS:-4 8 12 13 16}
IN=1792
OUT=256
MODEL=/models/hf/SmolLM2-360M-Instruct
URL=http://ch09-vllm:8000
metric() { python3 /lab/lib/metrics.py get "$URL" "$@"; }

step "prediction, from the model's config"
need_models smollm2-360m-hf
python3 predict.py --kv-gib 1 --prompt "$IN" --output "$OUT" \
  --json "$MEASURED/prediction.json"

step "vLLM CPU backend, 1 GiB of KV cache"
VLLM_CPU_KVCACHE_SPACE=1 start_vllm ch09-vllm "$MODEL" \
  --served-model-name smollm2-360m --dtype float16 \
  --max-model-len $((IN + OUT))
wait_ready ch09-vllm "$URL/health" 600
server_logs ch09-vllm > "$WORK/startup.log"
grep -o 'GPU KV cache size.*' "$WORK/startup.log" \
  | tee "$MEASURED/startup.txt" | fold -s -w 66 \
  | sed -e 's/ *$//' -e '2,$s/^/  /'
curl -s "$URL/metrics" | grep '^vllm:cache_config_info' \
  | grep -o 'block_size="[0-9]*"\|num_gpu_blocks="[0-9]*"' \
  | paste -sd ' ' - | tee -a "$MEASURED/startup.txt"

step "load: one batch of long requests per concurrency"
OM=$MEASURED/metrics.om.gz
python3 /lab/lib/metrics.py watch "$URL" "$OM" \
  > "$WORK/watch.log" 2>&1 &
WATCH=$!
: > "$MEASURED/levels.tsv"
rm -f "$MEASURED"/bench-c*.json
mkdir -p /scratch/ch09
for n in $LEVELS; do
  before=$(metric vllm:num_preemptions_total)
  t0=$EPOCHREALTIME
  run_tool "$VLLM_CPU_IMAGE" --entrypoint vllm -- bench serve \
    --backend vllm --base-url "$URL" --model smollm2-360m \
    --tokenizer "$MODEL" --dataset-name random \
    --random-input-len "$IN" --random-output-len "$OUT" \
    --ignore-eos --seed "$n" --num-prompts "$n" \
    --max-concurrency "$n" --request-rate inf \
    --save-result --result-dir /scratch/ch09 \
    --result-filename "c$n.json" > "$WORK/bench-c$n.log" 2>&1 \
    || { tail -n 20 "$WORK/bench-c$n.log"; die "bench at $n"; }
  t1=$EPOCHREALTIME
  after=$(metric vllm:num_preemptions_total)
  echo "$n $t0 $t1 $before $after" >> "$MEASURED/levels.tsv"
  cp "/scratch/ch09/c$n.json" "$MEASURED/bench-c$n.json"
  awk -v n="$n" -v a="$t0" -v b="$t1" \
    'BEGIN {printf "concurrency %d: %.0f s\n", n, b - a}'
done
kill -TERM "$WATCH"
wait "$WATCH"

step "result"
python3 report.py "$MEASURED"

step "done"
write_manifest
