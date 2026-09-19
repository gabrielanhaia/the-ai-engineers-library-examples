# measured/ch15

The ch15 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-engineering-in-practice ch15
```

- `output.txt`: the lab's stdout, which `ch15/README.md` prints.
- `machine.json`: the Docker host, image digests and model revisions.
- `promtool.txt`: `promtool test rules rules-test.yml`.
- `metrics.txt`: one live scrape of vLLM's `/metrics` after the
  traffic; every metric name in the rules is checked against it.
- `recorded.txt`: every recorded series' value after the traffic.
- `alerts.json`: Prometheus's `/api/v1/alerts`.
- `panels.json`: every panel of vLLM's three dashboards, and whether
  its queries returned data.
- `spans.jsonl`: what the OpenTelemetry Collector's file exporter
  wrote (OTLP JSON).
