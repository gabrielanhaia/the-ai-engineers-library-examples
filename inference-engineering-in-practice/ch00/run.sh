# ch00/run.sh
# Smoke test for the whole path: model cache -> llama.cpp server ->
# one streamed OpenAI-compatible request -> the server's timings.
. /lab/lib/lab.sh

step "model"
need_models smoke
MODEL=/models/gguf/SmolLM2-135M-Instruct-Q8_0.gguf

step "llama.cpp server"
start_llama llama -m "$MODEL" --ctx-size 2048 --metrics
wait_ready llama http://llama:8080/health

step "one streamed request"
curl -sN http://llama:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages": [{"role": "user",
        "content": "Name three primary colors."}],
       "max_tokens": 32, "temperature": 0,
       "stream": true}' \
  > "$MEASURED/stream.sse"

# Each event is one "data: {json}" line; the last is "data: [DONE]".
grep '^data: {' "$MEASURED/stream.sse" | sed 's/^data: //' \
  > "$MEASURED/chunks.jsonl"
jq -j '.choices[0].delta.content // empty' "$MEASURED/chunks.jsonl"
echo

step "server timings (last chunk)"
jq -s 'map(select(.timings)) | last | .timings' \
  "$MEASURED/chunks.jsonl" | tee "$MEASURED/timings.json"

step "done"
write_manifest
echo "chunks: $(wc -l < "$MEASURED/chunks.jsonl")"
echo "raw stream: measured/ch00/stream.sse"
