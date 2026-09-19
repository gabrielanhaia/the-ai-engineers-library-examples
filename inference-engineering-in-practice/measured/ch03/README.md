# measured/ch03

The ch03 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-engineering-in-practice ch03
```

- `output.txt`: the lab's stdout; `../../ch03/README.md` shows it.
- `llama/rate-*.jsonl`: every llama.cpp request, with its send time, the arrival time of each chunk with text and the server's `timings`.
- `report.json`: the SLO report behind the printed table.
- `goodput.json`: attainment per offered rate, the SLO, and goodput.
- `vllm-ramp.jsonl`: every request of the vLLM CPU ramp.
- `vllm-ramp.om.gz`: `/metrics` every 5 s during the ramp, as OpenMetrics with timestamps (replay: `promtool tsdb create-blocks-from openmetrics`); the data behind screenshot S3.
- `vllm-scrape.txt`: one scrape, filtered to the TTFT histogram and `vllm:generation_tokens`.
- `promql.json`: the two queries in `ch03/queries.promql`, evaluated over the replayed ramp (15 s steps).
- `simulated-*.txt`, `simulated-*.json`: SIMULATED. `vllm bench serve` against llm-d-inference-sim v0.11.2, whose latencies are its configuration.
- `machine.json`: the Docker host, image digests and model revisions.
