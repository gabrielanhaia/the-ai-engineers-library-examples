# ch14/test.sh
# Runs the lab, then asserts invariants the routing policy, the
# priority classes and the adapter slots set, never a timing.
. /lab/lib/lab.sh

bash run.sh

step "assertions"
r=$MEASURED/routing.json
jq -e '."prefix-aware".hit_rate > ."round-robin".hit_rate + 0.1' \
  "$r" >/dev/null \
  || die "prefix-aware did not beat round-robin on hit rate"
echo "ok  prefix-aware hit rate beats round-robin by > 0.1"

jq -e '."prefix-aware".same_replica_as_last_turn >= 0.9
       and ."round-robin".same_replica_as_last_turn < 0.6' \
  "$r" >/dev/null || die "turns did not follow their conversation"
echo "ok  prefix-aware keeps a conversation on one replica"

p=$MEASURED/priority.json
jq -e '.interactive.probe.ttft_p50_s
       < 0.5 * .batch.probe.ttft_p50_s' "$p" >/dev/null \
  || die "priority 100 did not jump the queue"
echo "ok  under the flood, priority-100 probes wait far less"

jq -e '.batch.peak_batch_queue > 0' "$p" >/dev/null \
  || die "the flood never queued in the picker"
echo "ok  the flood queued in the endpoint picker"

jq -e '[.. | .errors? | numbers] | add == 0' "$p" >/dev/null \
  || die "requests failed"
echo "ok  no request failed"

l1=$MEASURED/lora-max1.json
l2=$MEASURED/lora-max2.json
jq -e '.same_prompt as $s | ($s.alpaca != $s["smollm2-360m"])
       and ($s.underdog != $s["smollm2-360m"])' "$l1" >/dev/null \
  || die "an adapter answered exactly like the base model"
echo "ok  each adapter changes the answer to the same prompt"

jq -e '.serialized' "$l1" >/dev/null \
  || die "with one adapter slot the adapters did not take turns"
jq -e '.serialized | not' "$l2" >/dev/null \
  || die "with two adapter slots the adapters did not share a batch"
echo "ok  one slot: adapters finish in turns; two: together"

om=$MEASURED/replicas.om
[ "$(tail -n 1 "$om")" = "# EOF" ] \
  && [ "$(grep -c '^vllm:prefix_cache_hits_total' "$om")" -gt 0 ] \
  || die "replicas.om is not OpenMetrics with samples"
echo "ok  per-replica counters exported (replicas.om)"
