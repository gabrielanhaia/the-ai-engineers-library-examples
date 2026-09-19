# measured/ch04

The ch04 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-in-production ch04
```

- `output.txt`: the lab's stdout, which `ch04/README.md` prints.
- `machine.json`: the Docker host, image digests and model revisions.
- `guidellm.json`, `guidellm.html`, `guidellm-console.txt`: GuideLLM
  0.7.4's sweep, as it wrote it (the HTML is the chapter's
  screenshot S10).
- `closed.json`, `open.json`: `vllm bench serve` results, closed loop
  at concurrency 4 and open loop (Poisson) at the rate it achieved.
- `cache-first.json`, `cache-again.json`, `cache-new-seed.json`: the
  three cache runs; `cache.tsv`: `vllm:prefix_cache_hits_total` and
  `vllm:prefix_cache_queries_total` before and after each.
- `runs.tsv`: the start and end of every `vllm bench serve` run.
- `metrics.om.gz`: the engine's series, one scrape a second, as
  OpenMetrics text (`promtool tsdb create-blocks-from openmetrics`).
