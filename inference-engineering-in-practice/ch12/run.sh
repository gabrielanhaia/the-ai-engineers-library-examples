# ch12/run.sh
# Speculative decoding on a laptop CPU: SmolLM2-135M-Instruct drafts
# for SmolLM2-360M-Instruct (both Q8_0 GGUF) in llama.cpp. Acceptance
# is measured per task type and temperature from the server's own
# counters. Then the same prompts run with and without a draft, for
# a wall-clock ratio that on a CPU says nothing about a GPU.
. /lab/lib/lab.sh
K=4                                    # tokens drafted per step
TEMPS=${CH12_TEMPS:-0 0.4 0.8 1.2}
THREADS=$(( ($(nproc) + 1) / 2 ))      # both servers: half the CPUs

step "models: target and draft"
need_models smollm2-360m-gguf:SmolLM2-360M-Instruct-Q8_0.gguf \
            smollm2-135m-gguf:SmolLM2-135M-Instruct-Q8_0.gguf
TARGET=/models/gguf/SmolLM2-360M-Instruct-Q8_0.gguf
DRAFT=/models/gguf/SmolLM2-135M-Instruct-Q8_0.gguf

step "llama.cpp (build b10964) with a draft model, k = $K"
start_llama llama -m "$TARGET" --ctx-size 2048 --metrics -np 1 \
  --threads "$THREADS" \
  --spec-type draft-simple --spec-draft-model "$DRAFT" \
  --spec-draft-n-max "$K" --spec-draft-n-min 0 \
  --spec-draft-p-min 0
wait_ready llama http://llama:8080/health

scrape() { curl -sf http://llama:8080/metrics > "$1"; }
: > "$MEASURED/acceptance.jsonl"
printf '%-6s %5s %8s %9s %11s %12s\n' \
  task temp drafted accepted acceptance tokens/step
for task in code prose; do
  for t in $TEMPS; do
    scrape "$WORK/before.prom"
    python3 generate.py http://llama:8080 "$task" "$t" \
      > "$MEASURED/spec-$task-t$t.json"
    scrape "$WORK/after.prom"
    python3 accept.py "$WORK/before.prom" "$WORK/after.prom" \
      | jq -c --arg task "$task" --argjson t "$t" --argjson k "$K" \
          '{task: $task, temperature: $t, k: $k} + .' \
      | tee -a "$MEASURED/acceptance.jsonl" \
      | jq -r '[.task, .temperature, .drafted, .accepted,
                .acceptance, .tokens_per_step] | @tsv' \
      | while IFS=$'\t' read -r a b c d e f; do
          printf '%-6s %5s %8.0f %9.0f %11.3f %12.2f\n' \
            "$a" "$b" "$c" "$d" "$e" "$f"
        done
  done
done

step "the same prompts at temperature 0, with and without a draft"
# A second server with no draft model; requests alternate between
# the two, so a busy moment on the machine hits both alike.
start_llama plain -m "$TARGET" --ctx-size 2048 --metrics -np 1 \
  --threads "$THREADS"
wait_ready plain http://plain:8080/health
python3 wallclock.py http://plain:8080 http://llama:8080 \
  | tee "$MEASURED/wallclock.json" \
  | jq -r '"plain \(.plain_s * 10 | round / 10) s, speculative "
    + "\(.speculative_s * 10 | round / 10) s: "
    + "\(.plain_over_speculative * 100 | round / 100)x "
    + "(CPU, not representative)"'

step "done"
write_manifest
