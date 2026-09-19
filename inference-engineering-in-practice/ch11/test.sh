# ch11/test.sh
# Runs the lab on fewer chunks of the text, then asserts invariants,
# never numbers. Robust orderings only: Q4_K_M moves further from
# F16 than Q8_0 does, on perplexity, KL divergence and top-token
# agreement. (Q8_0 and F16 perplexities differ by less than the
# noise of a short text, so their order is not asserted.) File sizes
# give F16 > Q8_0 > Q4_K_M bits per weight, with Q4_K_M above the
# 4.89 of its name's reference model.
. /lab/lib/lab.sh

CH11_CHUNKS=16 bash run.sh

step "assertions"
R=$MEASURED/results.json
jq -e 'length == 3' "$R" >/dev/null || die "results.json incomplete"

jq -e '.[2].ppl > .[1].ppl and .[2].ppl > .[0].ppl' "$R" \
  >/dev/null || die "Q4_K_M perplexity is not the highest"
echo "ok  perplexity: Q4_K_M > Q8_0 and Q4_K_M > F16"

jq -e '(.[1].ppl - .[0].ppl | fabs) < (.[2].ppl - .[0].ppl | fabs)' \
  "$R" >/dev/null || die "Q8_0 is not closer to F16 than Q4_K_M"
echo "ok  Q8_0 stays closer to F16 than Q4_K_M does"

jq -e '.[2].mean_kld > .[1].mean_kld
       and .[2].same_top_p_pct < .[1].same_top_p_pct' "$R" \
  >/dev/null || die "KL divergence does not grow from Q8_0 to Q4_K_M"
echo "ok  KL divergence Q4_K_M > Q8_0; same-top Q4_K_M < Q8_0"

jq -e 'all(.[]; .eval.n == 40 and .eval.correct >= 0
       and .eval_date_number.n == 20)' "$R" >/dev/null \
  || die "the task eval did not score every file"
echo "ok  task eval scored all 40 items on each file"

jq -e 'map(.bits_per_weight) | .[0] > .[1] and .[1] > .[2]
       and .[2] > 4.89' "$R" >/dev/null \
  || die "bits per weight out of order"
echo "ok  bits/weight F16 > Q8_0 > Q4_K_M > 4.89"
