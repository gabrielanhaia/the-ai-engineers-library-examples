# ch00/test.sh
# Asserts invariants, never numbers: a stream arrived in several
# chunks, it ended with [DONE], and the server reported timings.
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

jq -e '.object == "chat.completion.chunk"' \
  < <(head -n 1 "$MEASURED/chunks.jsonl") >/dev/null \
  || die "first chunk is not a chat.completion.chunk"
echo "ok  OpenAI chunk shape"

for k in prompt_n prompt_ms predicted_n predicted_ms; do
  jq -e --arg k "$k" '.[$k] > 0' "$MEASURED/timings.json" >/dev/null \
    || die "timings.$k missing or not positive"
done
echo "ok  timings has prompt_n, prompt_ms, predicted_n, predicted_ms"
