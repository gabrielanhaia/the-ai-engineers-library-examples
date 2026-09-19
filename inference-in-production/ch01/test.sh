# ch01/test.sh
# Asserts invariants, never numbers: the stream arrived in chunks and
# ended with [DONE], the first chunk held no text, the client saw the
# first text after the server finished the prompt, and the prompt
# was read faster per token than the answer was written.
. /lab/lib/lab.sh

bash run.sh

step "assertions"
n=$(wc -l < "$MEASURED/chunks.jsonl")
[ "$n" -ge 2 ] || die "expected a stream of chunks, got $n"
echo "ok  stream arrived in $n chunks"

grep -v '^$' "$MEASURED/stream.sse" | tail -n 1 \
  | grep -qx 'data: \[DONE\]' \
  || die "stream did not end with data: [DONE]"
echo "ok  stream ended with [DONE]"

jq -e '.object == "chat.completion.chunk"
       and (.choices[0].delta.content // "") == ""' \
  < <(head -n 1 "$MEASURED/chunks.jsonl") >/dev/null \
  || die "first chunk is not a role-only chat.completion.chunk"
echo "ok  first chunk is role-only; TTFT waits for the first text"

for k in prompt_n prompt_ms predicted_n predicted_ms; do
  jq -e --arg k "$k" '.[$k] > 0' "$MEASURED/timings.json" >/dev/null \
    || die "timings.$k missing or not positive"
done
echo "ok  timings has prompt_n, prompt_ms, predicted_n, predicted_ms"

jq -e '.client_ttft_ms > .server_prompt_ms' "$MEASURED/ttft.json" \
  >/dev/null || die "client TTFT is not above the server's prompt_ms"
echo "ok  client-side TTFT > server prompt_ms"

jq -e '.prompt_per_second > .predicted_per_second' \
  "$MEASURED/timings.json" >/dev/null \
  || die "prompt tokens were not faster per token than generation"
echo "ok  prompt_per_second > predicted_per_second"
