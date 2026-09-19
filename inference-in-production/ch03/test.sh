# ch03/test.sh
# Runs the lab with a smaller workload, then asserts invariants,
# never numbers: every stream arrived in chunks, server-side TTFT
# never exceeds client-side TTFT for the same request, the report
# and the goodput curve exist, the scraped counter carries _total,
# the recorded ramp replays and both queries return data, and the
# simulated run reports request goodput.
. /lab/lib/lab.sh

export CH03_RATES="1 2" CH03_N=12
export CH03_RAMP=0.2,0.4 CH03_STEP_S=20
export CH03_SIM_RATES=8
bash run.sh

step "assertions"
L=("$MEASURED"/llama/rate-*.jsonl)
jq -se 'all(.[]; .error == null and .chunks >= 2
       and (.text_chunk_times | length) >= 1)' "${L[@]}" >/dev/null \
  || die "a llama.cpp request failed or did not stream"
echo "ok  every request streamed, in chunks, without error"

jq -se 'all(.[]; (.text_chunk_times[0] - .sent) * 1000
                 >= .timings.prompt_ms)' "${L[@]}" >/dev/null \
  || die "server-side TTFT exceeded client-side TTFT"
echo "ok  server-side TTFT <= client-side TTFT, every request"

jq -e '.summary | .ttft.n > 0 and .tpot.n > 0 and .itl.n > 0
       and .server_ttft.n > 0' "$MEASURED/report.json" >/dev/null \
  || die "the SLO report is missing a quantity"
echo "ok  report has client TTFT, server TTFT, TPOT and ITL"

jq -e --argjson n "${#L[@]}" '(.curve | length) == $n
       and all(.curve[]; .attainment >= 0 and .attainment <= 1)' \
  "$MEASURED/goodput.json" >/dev/null \
  || die "goodput curve lacks a point per offered rate"
echo "ok  goodput curve: one attainment per offered rate"

grep -q '^vllm:generation_tokens_total{' "$MEASURED/vllm-scrape.txt" \
  || die "scraped counter vllm:generation_tokens_total not found"
grep -q '^vllm:time_to_first_token_seconds_bucket{' \
  "$MEASURED/vllm-scrape.txt" || die "no TTFT histogram buckets"
echo "ok  scrape: TTFT buckets, and the counter carries _total"

gzip -dc "$MEASURED/vllm-ramp.om.gz" | tail -n 1 | grep -qx '# EOF' \
  || die "the ramp recording is not closed with # EOF"
jq -e 'length == 2 and all(.[]; .status == "success"
       and ([.data.result[0].values[] | select(.[1] != "NaN")]
            | length) > 0)' "$MEASURED/promql.json" >/dev/null \
  || die "a query returned no data on the replayed ramp"
echo "ok  ramp replays; both queries return data"

for f in "$MEASURED"/simulated-*.json; do
  jq -e '.simulated == "true" and .request_goodput >= 0' "$f" \
    >/dev/null || die "$f: not labeled simulated, or no goodput"
done
echo "ok  simulated run labeled simulated, reports request goodput"
