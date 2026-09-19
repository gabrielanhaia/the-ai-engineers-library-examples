# ch01/run.sh
# The first token: one streamed request to llama.cpp, the moment the
# first text reached the client, and the server's own timings.
. /lab/lib/lab.sh

step "model"
need_models smoke
MODEL=/models/gguf/SmolLM2-135M-Instruct-Q8_0.gguf

step "llama.cpp server (build b10964)"
# Half the CPUs. llama.cpp's default takes them all, and a step waits
# for its slowest thread: on a laptop with efficiency cores, or a
# busy one, fewer threads decode faster.
THREADS=$(( ($(nproc) + 1) / 2 ))
start_llama llama -m "$MODEL" --ctx-size 2048 --metrics \
  --threads "$THREADS"
wait_ready llama http://llama:8080/health

step "one streamed request"
BODY='{"messages": [{"role": "user",
        "content": "What is a token, in one sentence?"}],
       "max_tokens": 32, "temperature": 0, "stream": true}'
# Stamp every line of the stream with the client's clock as it
# arrives. t0 is taken just before the request goes out.
t0=$EPOCHREALTIME
curl -sN http://llama:8080/v1/chat/completions \
  -H 'Content-Type: application/json' -d "$BODY" \
  | while IFS= read -r line; do
      printf '%s\t%s\n' "$EPOCHREALTIME" "$line"
    done > "$WORK/stamped.tsv"

cut -f2- "$WORK/stamped.tsv" > "$MEASURED/stream.sse"
grep '^data: {' "$MEASURED/stream.sse" | sed 's/^data: //' \
  > "$MEASURED/chunks.jsonl"
jq -j '.choices[0].delta.content // empty' "$MEASURED/chunks.jsonl"
echo

# Client-side TTFT: to the first chunk that carries text. The first
# chunk of the stream only announces the role, and holds no token.
t1=
while IFS=$'\t' read -r t line; do
  [[ $line == 'data: {'* ]] || continue
  text=$(jq -r '.choices[0].delta.content // empty' \
         <<< "${line#data: }")
  if [ -n "$text" ]; then t1=$t; break; fi
done < "$WORK/stamped.tsv"
[ -n "$t1" ] || die "no chunk in the stream carried text"

step "server timings (last chunk)"
jq -s 'map(select(.timings)) | last | .timings' \
  "$MEASURED/chunks.jsonl" | tee "$MEASURED/timings.json"

step "first token at the client"
jq -n --argjson t0 "$t0" --argjson t1 "$t1" \
  --slurpfile s "$MEASURED/timings.json" \
  '{client_ttft_ms: ((($t1 - $t0) * 1e6 | round) / 1000),
    server_prompt_ms: $s[0].prompt_ms}' \
  | tee "$MEASURED/ttft.json"

step "done"
write_manifest
echo "chunks: $(wc -l < "$MEASURED/chunks.jsonl")"
echo "raw stream: measured/ch01/stream.sse"
