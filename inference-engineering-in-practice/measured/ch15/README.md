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
- `cost-sim.om`: SIMULATED, and not part of the lab run. The output-token
  counter of llm-d-inference-sim v0.11.2 paced to chapter 5's CITED
  per-node rate (MLPerf Inference v6.1 Server, 89,856.3 output tokens a
  second for one node of eight B200s), recorded on 2026-09-20 by
  `screens/cost-sim.sh`. It exists so screenshot S12 can show
  `cost.yml`'s dollars-per-million rule reading chapter 5's own figure
  without ever pricing a laptop's tokens; `screens/cost-replay.sh`
  rebuilds it and backfills the rule over it. Over the 780-second
  recording the counter tracked the cited rate to 89,844.3 tokens a
  second, 99.99% of it.
