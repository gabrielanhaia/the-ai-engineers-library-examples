# ch04/run.sh
# Benchmarking the vLLM CPU backend three ways, all on the laptop:
#   sweep  GuideLLM maps latency against load: a synchronous run,
#          a throughput run (up to 32 in flight), then Poisson
#          (open-loop) rates between the two
#   loops  vllm bench serve, closed loop at concurrency 4, then
#          open loop (Poisson) at the request rate that achieved
#   cache  the same command twice (the default seed, 0), then with
#          a new seed: the second run reuses the prompts the first
#          left in the prefix cache
. /lab/lib/lab.sh

PARTS=${PARTS:-sweep loops cache}
MODEL=/models/hf/SmolLM2-360M-Instruct
URL=http://ch04-vllm:8000
S=/scratch/ch04
metric() { python3 /lab/lib/metrics.py get "$URL" "$@"; }

# bench NAME [vllm bench serve flags]: one run, its JSON kept, its
# start and end in runs.tsv.
bench() {
  local name=$1 t0=$EPOCHREALTIME
  shift
  run_tool "$VLLM_CPU_IMAGE" --entrypoint vllm -- bench serve \
    --backend vllm --base-url "$URL" --model smollm2-360m \
    --tokenizer "$MODEL" --dataset-name random \
    --percentile-metrics ttft,tpot,itl,e2el \
    --metric-percentiles 50,90,99 --save-result \
    --result-dir "$S" --result-filename "$name.json" "$@" \
    > "$WORK/$name.log" 2>&1 \
    || { tail -n 20 "$WORK/$name.log"; die "bench $name"; }
  cp "$S/$name.json" "$MEASURED/$name.json"
  echo "$name $t0 $EPOCHREALTIME" >> "$MEASURED/runs.tsv"
}

step "vLLM CPU backend"
need_models smollm2-360m-hf
start_vllm ch04-vllm "$MODEL" --served-model-name smollm2-360m \
  --dtype float16 --max-model-len 2048
wait_ready ch04-vllm "$URL/health" 600
mkdir -p "$S" && chmod 777 "$S"
: > "$MEASURED/runs.tsv"
OM=$MEASURED/metrics.om.gz
python3 /lab/lib/metrics.py watch "$URL" "$OM" \
  > "$WORK/watch.log" 2>&1 &
WATCH=$!

if [[ $PARTS == *sweep* ]]; then
  step "sweep: GuideLLM, 128 tokens in, 64 out, 60 s a point"
  poisson=strategy_type=poisson,max_concurrency=32
  run_tool "$GUIDELLM_IMAGE" --entrypoint guidellm \
    -e HF_HUB_OFFLINE=1 -- run \
    --backend kind=openai_http,target="$URL",model=smollm2-360m \
    --tokenizer kind=huggingface_auto,model="$MODEL" \
    --data kind=synthetic_text,prompt_tokens=128,output_tokens=64 \
    --profile "kind=sweep,sweep_size=6,$poisson" \
    --constraint kind=max_duration,seconds=60 \
    --output kind=json,path="$S/guidellm.json" \
    --output kind=html,path="$S/guidellm.html" \
    --disable-progress > "$MEASURED/guidellm-console.txt" 2>&1 \
    || { tail -n 30 "$MEASURED/guidellm-console.txt"; die guidellm; }
  cp "$S/guidellm.json" "$S/guidellm.html" "$MEASURED/"
  echo "GuideLLM's report: measured/ch04/guidellm.html"
fi

if [[ $PARTS == *loops* ]]; then
  step "loops: closed at concurrency 4, then open at its rate"
  shape=(--random-input-len 128 --random-output-len 64 --ignore-eos
         --num-prompts 64)
  bench closed "${shape[@]}" --seed 11 --max-concurrency 4 \
    --request-rate inf
  rate=$(jq -r .request_throughput "$MEASURED/closed.json")
  bench open "${shape[@]}" --seed 12 --request-rate "$rate" \
    --burstiness 1.0
  printf 'closed loop: %.2f req/s; open loop sent at that rate\n' \
    "$rate"
fi

if [[ $PARTS == *cache* ]]; then
  step "cache: one command twice, then a new seed"
  shape=(--random-input-len 1024 --random-output-len 32 --ignore-eos
         --num-prompts 16 --max-concurrency 4 --request-rate inf)
  : > "$MEASURED/cache.tsv"
  for run in first again new-seed; do
    seed=()
    [ "$run" = new-seed ] && seed=(--seed 1)
    h0=$(metric vllm:prefix_cache_hits_total)
    q0=$(metric vllm:prefix_cache_queries_total)
    bench "cache-$run" "${shape[@]}" "${seed[@]}"
    echo "$run $h0 $q0 $(metric vllm:prefix_cache_hits_total)" \
      "$(metric vllm:prefix_cache_queries_total)" \
      >> "$MEASURED/cache.tsv"
  done
fi

kill -TERM "$WATCH"
wait "$WATCH"

step "results"
for p in $PARTS; do
  case $p in
    sweep) python3 report.py sweep "$MEASURED/guidellm.json" ;;
    *) python3 report.py "$p" "$MEASURED" ;;
  esac
  echo
done

# Every number the chapter prints, from the files above, for the
# derived-data CI job (scripts/check_derived.py). A partial run
# (CI runs the cache part alone) has nothing to write it from.
if [[ $PARTS == *sweep*loops*cache* ]]; then
  python3 report.py derived "$MEASURED" > "$MEASURED/derived.json"
fi

step "done"
write_manifest
