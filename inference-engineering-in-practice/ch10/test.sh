# ch10/test.sh
# Asserts what the workload sets, not the hardware: the shared-
# prefix layout hits the prefix cache (> 0.8 of prompt tokens), the
# variable-first layout does not (< 0.1), and cached prompts start
# answering sooner.
. /lab/lib/lab.sh

bash run.sh

step "assertions"
W=$MEASURED/workloads.json
pick() {  # pick WORKLOAD FIELD, rounded to 3 decimals
  jq -r --arg w "$1" --arg f "$2" '.[] | select(.workload == $w)
    | .[$f] * 1000 | round / 1000' "$W"
}
rate() { pick "$1" hit_rate; }
ttft() { pick "$1" ttft_p50_ms; }
awk -v r="$(rate shared)" 'BEGIN {exit !(r > 0.8)}' \
  || die "shared hit rate $(rate shared) is not above 0.8"
echo "ok  shared-prefix hit rate $(rate shared) > 0.8"
awk -v r="$(rate unique)" 'BEGIN {exit !(r < 0.1)}' \
  || die "unique hit rate $(rate unique) is not below 0.1"
echo "ok  variable-first hit rate $(rate unique) < 0.1"
awk -v s="$(ttft shared)" -v u="$(ttft unique)" \
  'BEGIN {exit !(s < u)}' || die "cached TTFT is not lower"
echo "ok  TTFT p50 shared < unique"
mkdir -p /scratch/ch10-om && rm -rf /scratch/ch10-om/data
gzip -dc "$MEASURED/metrics.om.gz" > /scratch/ch10-om/metrics.om
run_tool "$PROMETHEUS_IMAGE" --entrypoint promtool --user 0 -- tsdb \
  create-blocks-from openmetrics /scratch/ch10-om/metrics.om \
  /scratch/ch10-om/data > "$WORK/backfill.txt" 2>&1 \
  || die "metrics.om.gz does not load into Prometheus"
echo "ok  metrics.om.gz backfills into Prometheus"
