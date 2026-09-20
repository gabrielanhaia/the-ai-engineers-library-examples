# ch15/test.sh
# The wiring, not the numbers: the rules pass promtool's unit tests,
# every metric they read exists in a live scrape, the recorded
# series have values, vLLM's dashboards load and draw data, and the
# engine's spans reach the collector.
. /lab/lib/lab.sh

bash run.sh

step "assertions"
grep -q SUCCESS "$MEASURED/promtool.txt" || die "promtool test rules"
echo "ok  promtool test rules: SUCCESS"
names=$(grep -ohE 'vllm:[a-z_]+(:[a-z0-9_]+)?' rules.yml alerts.yml \
          cost.yml | grep -v ':.*:' | sort -u)
for n in $names; do
  grep -q "^${n}[{ ]" "$MEASURED/metrics.txt" \
    || die "$n is not in the live scrape"
done
echo "ok  all $(wc -w <<< "$names") metric names are in a live scrape"
grep -q '^vllm:prefix_cache_hit_ratio:rate5m ' \
  "$MEASURED/recorded.txt" || die "no recorded hit ratio"
echo "ok  recording rules produced series"
jq -e 'length == 3 and all(.[]; any(.panels[]; .data))' \
  "$MEASURED/panels.json" > /dev/null \
  || die "a vLLM dashboard is missing or draws nothing"
echo "ok  vLLM's three dashboards load and draw data"
# To a file, then grep the file: `python3 ... | grep -q` kills the
# writer with SIGPIPE on the first match, and pipefail fails the
# test for it.
python3 spans.py "$MEASURED/spans.jsonl" >"$WORK/spans.txt"
grep -q 'service.name vllm' "$WORK/spans.txt" \
  || die "no vLLM spans arrived"
echo "ok  vLLM's spans reached the collector"
