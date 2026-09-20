#!/usr/bin/env bash
# screens/replay.sh NAME FILE[...] -- rebuild committed lab data into a
# fresh Prometheus and bring up Grafana on top of it, so a screenshot
# can be re-made from the repository alone.
#
#   bash screens/replay.sh ch09 measured/ch09/metrics.om.gz
#   bash screens/replay.sh ch14 measured/ch14/replicas.om
#
# Each FILE is OpenMetrics text with timestamps, gzipped or not, as
# written by the lab. `promtool tsdb create-blocks-from openmetrics`
# turns it into TSDB blocks; Prometheus serves them and scrapes
# nothing. Grafana gets vLLM 0.29.0's own dashboards (fetched by the
# URL+SHA-256 pins in tools.env) and screens/dashboards/*.json.
#
# Prometheus lands on 127.0.0.1:9090, Grafana on 127.0.0.1:3000, both
# also on the lab network as `prometheus` and `grafana`.
#
#   bash screens/replay.sh --down     stop both
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
. ./images.env
. ./tools.env

W=$ROOT/.work/screens
NET=${AIEL_NET:-aiel-inference}
PROM_C=aiel-screens-prom
GRAF_C=aiel-screens-grafana

down() { docker rm -f "$PROM_C" "$GRAF_C" >/dev/null 2>&1 || true; }
[ "${1:-}" = --down ] && { down; echo "stopped"; exit 0; }

NAME=${1:?usage: replay.sh NAME FILE...}
shift
[ $# -ge 1 ] || { echo "usage: replay.sh NAME FILE..." >&2; exit 1; }

# The vLLM dashboards, by the tools.env pins. Fetched once.
mkdir -p "$W/dashboards"
fetch_dash() {
  local spec=${!1} out=$W/dashboards/$2 url want got
  url=${spec%@sha256:*}; want=${spec##*@sha256:}
  [ -f "$out" ] && got=$(shasum -a 256 "$out" | cut -d' ' -f1) || got=
  [ "$got" = "$want" ] && return 0
  curl -fsSL --retry 5 -o "$out" "$url"
  got=$(shasum -a 256 "$out" | cut -d' ' -f1)
  [ "$got" = "$want" ] || { echo "SHA-256 mismatch: $1" >&2; exit 1; }
}
fetch_dash VLLM_DASHBOARD grafana.json
fetch_dash VLLM_DASHBOARD_PERF performance_statistics.json
fetch_dash VLLM_DASHBOARD_QUERY query_statistics.json

# The book's own panels, and the print patches the vLLM dashboards
# need (one line style per series, so a line survives black and white).
python3 "$ROOT/screens/patch_dashboards.py" "$W/dashboards"
cp "$ROOT"/screens/dashboards/*.json "$W/dashboards/"

# The data.
rm -rf "$W/data/$NAME" "$W/om/$NAME"
mkdir -p "$W/data/$NAME" "$W/om/$NAME"
i=0
for f in "$@"; do
  i=$((i + 1))
  case $f in
    *.gz) gzcat "$f" > "$W/om/$NAME/$i.om" ;;
    *)    cp "$f" "$W/om/$NAME/$i.om" ;;
  esac
done
for f in "$W/om/$NAME"/*.om; do
  docker run --rm --entrypoint promtool \
    -v "$W/om/$NAME:/in:ro" -v "$W/data/$NAME:/data" \
    "$PROMETHEUS_IMAGE" \
    tsdb create-blocks-from openmetrics "/in/$(basename "$f")" /data
done

# The datasource, with the lab's own scrape interval under it. Left at
# Grafana's 15 s default, a lab that scrapes every second is drawn at
# one point per fifteen and its peaks disappear.
SCRAPE=${SCRAPE:-5s}
mkdir -p "$W/provisioning"/{datasources,dashboards,plugins,alerting,notifiers}
sed "s/timeInterval: .*/timeInterval: $SCRAPE/" \
  "$ROOT/screens/grafana-datasource.yml" \
  > "$W/provisioning/datasources/prometheus.yml"
cp "$ROOT/screens/grafana-dashboards.yml" "$W/provisioning/dashboards/screens.yml"

# Anything else the caller wants: extra Prometheus flags, one per
# element, in EXTRA_PROM_ARGS (a space-separated string).
prom_args=(
  --config.file=/etc/prometheus/prometheus.yml
  --storage.tsdb.path=/prometheus
  --storage.tsdb.retention.time=10y
  --web.enable-admin-api
)
if [ -n "${EXTRA_PROM_ARGS:-}" ]; then
  read -r -a extra <<<"$EXTRA_PROM_ARGS"
  prom_args+=("${extra[@]}")
fi

down
docker run -d --name "$PROM_C" --network "$NET" --network-alias prometheus \
  -p 127.0.0.1:9090:9090 \
  -v "$ROOT/screens/prometheus-replay.yml:/etc/prometheus/prometheus.yml:ro" \
  -v "$ROOT/screens:/screens:ro" \
  -v "$W/data/$NAME:/prometheus" \
  "$PROMETHEUS_IMAGE" "${prom_args[@]}" >/dev/null

docker run -d --name "$GRAF_C" --network "$NET" --network-alias grafana \
  -p 127.0.0.1:3000:3000 \
  -e GF_AUTH_ANONYMOUS_ENABLED=true \
  -e GF_AUTH_ANONYMOUS_ORG_ROLE=Admin \
  -e GF_AUTH_BASIC_ENABLED=false \
  -e GF_USERS_DEFAULT_THEME=light \
  -e GF_NEWS_NEWS_FEED_ENABLED=false \
  -e GF_ANALYTICS_REPORTING_ENABLED=false \
  -e GF_ANALYTICS_CHECK_FOR_UPDATES=false \
  -v "$W/provisioning:/etc/grafana/provisioning-extra:ro" \
  -e GF_PATHS_PROVISIONING=/etc/grafana/provisioning-extra \
  -v "$W/dashboards:/var/lib/grafana/dashboards:ro" \
  "$GRAFANA_IMAGE" >/dev/null

# wait_for SECONDS DESCRIPTION COMMAND...: poll until it succeeds.
wait_for() {
  local secs=$1 what=$2 i
  shift 2
  for ((i = 0; i < secs; i++)); do
    if "$@" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "timed out waiting for $what" >&2
  return 1
}

wait_for 60 "prometheus" curl -sf http://127.0.0.1:9090/-/ready
wait_for 90 "grafana" curl -sf http://127.0.0.1:3000/api/health

# Grafana answers /api/health before the provisioned datasource can
# serve a query, and a panel that asks too early renders "No data" and
# stays that way. Wait until the datasource actually returns a series,
# so the capture never races provisioning.
datasource_provisioned() {
  curl -sf \
    "http://127.0.0.1:3000/api/datasources/proxy/uid/prometheus/api/v1/label/__name__/values" \
    | grep -q 'vllm:\|lab_\|fleet:'
}
# And the query path itself: Grafana's Prometheus datasource runs as a
# plugin process that can still be starting when the HTTP API is up,
# and a panel that asks then draws "Prometheus plugin failed" over a
# "No data". vector(1) answers whatever the data is, so this waits for
# the plugin and nothing else.
plugin_ready() {
  curl -sf -X POST http://127.0.0.1:3000/api/ds/query \
    -H 'Content-Type: application/json' \
    -d '{"queries":[{"refId":"A","datasource":{"type":"prometheus","uid":"prometheus"},"expr":"vector(1)","instant":true}],"from":"now-5m","to":"now"}' \
    | grep -q '"status":200'
}
wait_for 60 "the Prometheus datasource" datasource_provisioned
wait_for 60 "the Prometheus plugin" plugin_ready

echo "prometheus http://127.0.0.1:9090   grafana http://127.0.0.1:3000"
curl -s http://127.0.0.1:9090/api/v1/status/tsdb | python3 -c '
import json, sys
d = json.load(sys.stdin)["data"]
print("series in head:", d["headStats"]["numSeries"])
' 2>/dev/null || true
curl -s "http://127.0.0.1:9090/api/v1/label/__name__/values" | python3 -c '
import json, sys
print("metric names on disk:", len(json.load(sys.stdin)["data"]))
' 2>/dev/null || true
