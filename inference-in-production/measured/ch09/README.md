# measured/ch09

The ch09 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-in-production ch09
```

- `output.txt`: the lab's stdout, which `ch09/README.md` prints.
- `machine.json`: the Docker host, image digests and model revisions.
- `prediction.json`: `ch09/predict.py`'s arithmetic.
- `startup.txt`: the engine's capacity line and its block size.
- `levels.tsv`, `levels.json`: one row per concurrency.
- `bench-cN.json`: `vllm bench serve` at concurrency N.
- `metrics.om.gz`: the engine's scheduler, cache and latency series,
  one scrape a second, as OpenMetrics text (`promtool tsdb
  create-blocks-from openmetrics`), for screenshots S1 and S2.
