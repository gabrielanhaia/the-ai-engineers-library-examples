# ch12/test.sh
# Runs the lab on fewer prompts, shorter answers and two
# temperatures, then asserts invariants, never numbers: every
# setting drafted tokens and accepted some, acceptance is a share,
# tokens per step is at least one, and the wall-clock ratio was
# recorded.
. /lab/lib/lab.sh

CH12_PROMPTS=2 CH12_MAX_TOKENS=48 CH12_TEMPS="0 1.2" bash run.sh

step "assertions"
A=$MEASURED/acceptance.jsonl
[ "$(wc -l < "$A")" -eq 4 ] || die "expected 2 tasks x 2 temperatures"
echo "ok  one row per task type and temperature"

jq -se 'all(.[]; .drafted > 0 and .accepted > 0 and .drafts > 0)' \
  "$A" >/dev/null || die "a setting drafted or accepted nothing"
echo "ok  every setting drafted tokens, and some were accepted"

jq -se 'all(.[]; .acceptance > 0 and .acceptance <= 1
         and .tokens_per_step >= 1 and .k == 4)' "$A" >/dev/null \
  || die "acceptance or tokens per step out of range"
echo "ok  0 < acceptance <= 1, tokens per step >= 1, k = 4"

jq -e '.speculative_s > 0 and .plain_s > 0' \
  "$MEASURED/wallclock.json" >/dev/null \
  || die "wall-clock ratio not recorded"
echo "ok  wall-clock ratio recorded (CPU, not representative)"
