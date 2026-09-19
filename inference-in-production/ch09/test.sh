# ch09/test.sh
# Asserts events, never timings: the prediction from the config
# agrees with the engine's own capacity line, preemptions stay at 0
# below the predicted concurrency and appear at and above it.
. /lab/lib/lab.sh

LEVELS=${LEVELS:-4 13} bash run.sh

step "assertions"
first=$(jq .first_preempting "$MEASURED/prediction.json")
fits=$(grep -o 'per request: [0-9.]*x' "$MEASURED/startup.txt" \
       | grep -o '[0-9.]*' | cut -d. -f1)
[ "$fits" -eq $((first - 1)) ] \
  || die "engine fits $fits requests, prediction says $((first - 1))"
echo "ok  engine fits $fits requests; preemption predicted at $first"
jq -c '.[]' "$MEASURED/levels.json" | while read -r row; do
  n=$(jq .concurrency <<< "$row")
  p=$(jq .preemptions <<< "$row")
  if [ "$n" -lt "$first" ]; then
    [ "$p" -eq 0 ] || die "$p preemptions at $n, below $first"
    echo "ok  concurrency $n: 0 preemptions"
  else
    [ "$p" -gt 0 ] || die "no preemption at $n (>= $first)"
    echo "ok  concurrency $n: $p preemption(s)"
  fi
done
mkdir -p /scratch/ch09-om && rm -rf /scratch/ch09-om/data
gzip -dc "$MEASURED/metrics.om.gz" > /scratch/ch09-om/metrics.om
run_tool "$PROMETHEUS_IMAGE" --entrypoint promtool --user 0 -- tsdb \
  create-blocks-from openmetrics /scratch/ch09-om/metrics.om \
  /scratch/ch09-om/data > "$WORK/backfill.txt" 2>&1 \
  || die "metrics.om.gz does not load into Prometheus"
echo "ok  metrics.om.gz backfills into Prometheus"
