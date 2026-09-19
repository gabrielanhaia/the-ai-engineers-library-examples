# ch08/test.sh
# Shapes, never speeds: throughput rises with concurrency and the
# gain per doubling shrinks at the top; TPOT rises; nothing was
# preempted; the batch file came back whole; the bound's ceiling is
# the chapter's.
. /lab/lib/lab.sh

CONCS=${CONCS:-1 2 16 64}
BATCH=${BATCH:-64}
CONCS=$CONCS BATCH=$BATCH bash run.sh

step "assertions"
col() {  # col CONCURRENCY FIELD, from sweep.csv
  awk -F, -v c="$1" -v f="$2" 'NR == 1 {for (i = 1; i <= NF; i++)
    if ($i == f) k = i} $1 == c {printf "%.1f\n", $k}' \
    "$MEASURED/sweep.csv"
}
t1=$(col 1 output_tok_s) t2=$(col 2 output_tok_s)
t16=$(col 16 output_tok_s) t64=$(col 64 output_tok_s)
awk -v a="$t1" -v b="$t64" 'BEGIN {exit !(b > 2 * a)}' \
  || die "throughput did not rise: $t1 -> $t64 tok/s"
echo "ok  output tok/s rises: $t1 at 1, $t64 at 64"
awk -v a="$t1" -v b="$t2" -v c="$t16" -v d="$t64" \
  'BEGIN {exit !(sqrt(d / c) < b / a)}' \
  || die "no flattening: 16->64 gains as much as 1->2"
echo "ok  it flattens: gain per doubling 16->64 < 1->2"
awk -v a="$(col 1 tpot_mean_ms)" -v b="$(col 64 tpot_mean_ms)" \
  'BEGIN {exit !(b > a)}' || die "TPOT did not rise"
echo "ok  mean TPOT rises from concurrency 1 to 64"
grep -q 'sweep: 0$' "$MEASURED/preemptions.txt" \
  || die "the sweep preempted: $(cat "$MEASURED/preemptions.txt")"
echo "ok  no preemption during the sweep"
jq -e --argjson n "$BATCH" '.requests == $n
  and .output_tokens == 64 * $n' "$MEASURED/offline.json" \
  > /dev/null || die "run-batch lost requests or tokens"
echo "ok  run-batch returned all $BATCH requests, 64 tokens each"
jq -e '.numbers[] | select(.key == "ceiling") | .shown == "6,240"' \
  "$MEASURED/derived.json" > /dev/null || die "ceiling moved"
echo "ok  bound ceiling 6,240 tok/s"
