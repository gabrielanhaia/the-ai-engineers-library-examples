# ch02/run.sh
# Predict, then measure. Single-stream decode reads every weight once
# per token, so tokens/s <= memory bandwidth / weight bytes. Measure
# the bandwidth, predict, then time llama.cpp at three precisions of
# one model: SmolLM2-360M-Instruct as F16, Q8_0 and Q4_K_M GGUF.
. /lab/lib/lab.sh

step "model: one model, three GGUF files"
need_models smollm2-360m-gguf
G=/models/gguf/SmolLM2-360M-Instruct
FORMATS=(f16 Q8_0 Q4_K_M)

step "CPU instruction set"
grep -m1 -E '^(Features|flags)' /proc/cpuinfo \
  > "$MEASURED/cpuinfo.txt"
echo "arch: $(uname -m), $(nproc) CPUs"
# The SIMD and matrix extensions that decide which formats run
# natively: fp16/bf16 arithmetic, int8 dot products, AVX-512, AMX.
KEEP='asimd|asimddp|fphp|asimdhp|bf16|i8mm|sve|sve2|sme|avx2|fma'
KEEP+='|f16c|avx512f|avx512_bf16|avx512_vnni|avx512_fp16|avx_vnni'
KEEP+='|amx_bf16|amx_int8'
features=$(tr -s '[:blank:]' '\n' < "$MEASURED/cpuinfo.txt" \
           | { grep -xE "$KEEP" || true; } | tr '\n' ' ')
echo "features: ${features% }"

step "memory bandwidth (STREAM-style copy)"
python3 bandwidth.py | tee "$MEASURED/bandwidth.json"
BW=$(jq .copy_gb_s "$MEASURED/bandwidth.json")

step "prediction: $BW GB/s / weight bytes"
printf '%-7s %13s %13s\n' format "weight bytes" "tok/s <="
for f in "${FORMATS[@]}"; do
  bytes=$(stat -c %s "$G-$f.gguf")
  jq -n --arg f "$f" --argjson b "$bytes" --argjson bw "$BW" \
    '{format: $f, bytes: $b, predicted_tok_s: ($bw * 1e9 / $b)}'
done | jq -s . > "$MEASURED/predicted.json"
jq -r '.[] | [.format, .bytes, .predicted_tok_s] | @tsv' \
  "$MEASURED/predicted.json" \
  | while IFS=$'\t' read -r f b p; do
      printf '%-7s %13s %13.0f\n' "$f" "$b" "$p"
    done

# llama.cpp splits every step evenly over its threads and waits for
# the slowest. Using every CPU is not always fastest (efficiency
# cores, a busy host), so llama bench tries several thread counts;
# the lab keeps each format's fastest, by the median of 5 runs.
T=$(seq -s, 2 2 "$(nproc)")
step "measurement: llama bench, 64 tokens, 5 runs, threads ${T:-1}"
run_tool "$LLAMA_CPP_IMAGE" --entrypoint /app/llama -- bench \
  -m "$G-f16.gguf" -m "$G-Q8_0.gguf" -m "$G-Q4_K_M.gguf" \
  -p 0 -n 64 -r 5 -t "${T:-1}" -o json \
  > "$MEASURED/bench.json" 2> "$WORK/bench.err"
grep -m1 'CPU backend' "$WORK/bench.err" || true
jq -r '.[0] | "llama.cpp build b\(.build_number),"
  + " commit \(.build_commit)"' "$MEASURED/bench.json"

step "measured / predicted"
jq -s '.[1] as $bench | .[0] | map(.format as $f | . + ($bench
    | map(select(.model_filename | endswith("-" + $f + ".gguf"))
          | . + {median_ts: (.samples_ts | sort | .[length / 2])})
    | max_by(.median_ts)
    | {file: .model_filename, threads: .n_threads,
       measured_tok_s: .median_ts, runs_tok_s: .samples_ts}))
    | map(. + {ratio: (.measured_tok_s / .predicted_tok_s)})' \
  "$MEASURED/predicted.json" "$MEASURED/bench.json" \
  > "$MEASURED/results.json"
printf '%-7s %10s %10s %8s %8s\n' \
  format predicted measured threads ratio
jq -r '.[] | [.format, .predicted_tok_s, .measured_tok_s, .threads,
              .ratio] | @tsv' "$MEASURED/results.json" \
  | while IFS=$'\t' read -r f p m t r; do
      printf '%-7s %10.0f %10.1f %8s %8.2f\n' "$f" "$p" "$m" "$t" "$r"
    done

step "done"
write_manifest
