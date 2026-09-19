# ch16/test.sh
# Runs the lab with one cold start instead of three, then asserts
# events and orderings, never a timing.
. /lab/lib/lab.sh

RUNS=${RUNS:-1} bash run.sh

step "assertions"
s=$MEASURED/scaling.json
jq -e '.peak.replicas > 1' "$s" >/dev/null \
  || die "KEDA never scaled the pool out"
echo "ok  the pool scaled out on queue depth"

jq -e '.events_s as $e
       | $e.queue_reaches_threshold != null
       and $e.replicas_raised >= $e.queue_reaches_threshold
       and $e.second_replica_ready > $e.replicas_raised' "$s" \
  >/dev/null || die "scale-out events out of order"
echo "ok  queue crossed the threshold, then replicas, then ready"

jq -e '.events_s.replicas_lowered != null' "$s" >/dev/null \
  || die "the pool never scaled back in"
echo "ok  the pool scaled back in after the burst"

# A replica removed at scale-in can answer 503 to a request the
# Service still sent it: allowed there, and nowhere else.
down=$(jq '.events_s.replicas_lowered' "$s")
jq -se --argjson d "$down" \
  'all(.[]; .status == 200 or .t >= $d - 5)' \
  "$MEASURED/requests.jsonl" >/dev/null \
  || die "a request failed before the scale-in"
echo "ok  no request failed before the scale-in"

c=$MEASURED/coldstart.json
jq -e '.runs | length > 0 and all(.[];
         (.image_cached | not) and .pull_s > 0 and .weights_s > 0
         and .warmup_s > 0 and .rest_s >= 0)' "$c" >/dev/null \
  || die "a cold-start phase is missing"
echo "ok  every run pulled the image, loaded weights, warmed up"

jq -e 'all(.runs[]; .second_ttft_s <= .first_ttft_s)' "$c" \
  >/dev/null || die "the first request was not the slowest"
echo "ok  the first request after start-up is the slowest"
