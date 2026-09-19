# ch11/run.sh
# Fewer bytes, and the accuracy you must prove. SmolLM2-360M-Instruct
# as F16, Q8_0 and Q4_K_M GGUF, judged against F16 three ways on the
# same pinned text: perplexity, KL divergence, and a task eval. Then
# decode speed and bits per weight for each file.
. /lab/lib/lab.sh
CHUNKS=${CH11_CHUNKS:-100}   # 512-token chunks of the text

step "models and the pinned text"
need_models smollm2-360m-gguf
G=/models/gguf/SmolLM2-360M-Instruct
FORMATS=(f16 Q8_0 Q4_K_M)
# WikiText-2 (raw), test split, from ggml-org/ci at a fixed commit.
URL=https://huggingface.co/datasets/ggml-org/ci/resolve
URL+=/927b3642933080f1b0e811e2f916e14c292992f9/wikitext-2-raw-v1.zip
SHA=ef7edb566e3e2b2d31b29c1fdb0c89a4cc683597484c3dc2517919c615435a11
S=/scratch/ch11
mkdir -p "$S"
curl -sfL --retry 3 -o "$S/wikitext.zip" "$URL"
echo "$SHA  $S/wikitext.zip" | sha256sum -c
python3 -m zipfile -e "$S/wikitext.zip" "$S/"
TEXT=$S/wikitext-2-raw/wiki.test.raw
for f in "${FORMATS[@]}"; do
  jq -n --arg f "$f" --argjson b "$(stat -c %s "$G-$f.gguf")" \
    '{($f): $b}'
done | jq -s add > "$MEASURED/sizes.json"

ppl() {
  run_tool "$LLAMA_CPP_IMAGE" --entrypoint /app/llama -- \
    perplexity -c 512 --chunks "$CHUNKS" "$@"
}

step "F16: perplexity; its logits become the reference"
ppl -m "$G-f16.gguf" -f "$TEXT" --kl-divergence-base "$S/f16.kld" \
  > "$MEASURED/ppl-f16.log" 2>&1
grep -o 'Final estimate.*' "$MEASURED/ppl-f16.log"

for q in Q8_0 Q4_K_M; do
  step "$q: perplexity and KL divergence against F16"
  ppl -m "$G-$q.gguf" --kl-divergence-base "$S/f16.kld" \
    --kl-divergence > "$MEASURED/kld-$q.log" 2>&1
  grep -E '^(Mean PPL|Mean    KLD|99.0%   Δp| 1.0%   Δp|Same top)' \
    "$MEASURED/kld-$q.log"
done
rm -f "$S/f16.kld"           # the reference logits: gigabytes

ITEMS=$(jq '.items | length' tasks.json)
for f in "${FORMATS[@]}"; do
  step "task eval: $f (greedy, $ITEMS items)"
  start_llama llama -m "$G-$f.gguf" --ctx-size 2048
  wait_ready llama http://llama:8080/health
  python3 eval.py http://llama:8080 "$f" > "$MEASURED/eval-$f.json"
  stop_server llama
  jq -r '"\(.all.correct)/\(.all.n) correct; dates and numbers "
    + "\(.date_number.correct)/\(.date_number.n)"' \
    "$MEASURED/eval-$f.json"
done

# As in ch02: several thread counts, each format's fastest kept, by
# the median of 5 runs of 64 generated tokens.
T=$(seq -s, 2 2 "$(nproc)")
step "decode speed: llama bench, CPU, threads ${T:-1}"
run_tool "$LLAMA_CPP_IMAGE" --entrypoint /app/llama -- bench \
  -m "$G-f16.gguf" -m "$G-Q8_0.gguf" -m "$G-Q4_K_M.gguf" \
  -p 0 -n 64 -r 5 -t "${T:-1}" -o json \
  > "$MEASURED/bench.json" 2> "$WORK/bench.err"
jq -r '.[0] | "llama.cpp build b\(.build_number),"
  + " commit \(.build_commit)"' "$MEASURED/bench.json"

step "summary (perplexity and KLD on $CHUNKS chunks of 512 tokens)"
python3 summary.py "$MEASURED"

step "done"
write_manifest
