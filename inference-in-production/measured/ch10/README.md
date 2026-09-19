# measured/ch10

The ch10 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-in-production ch10
```

- `output.txt`: the lab's stdout, which `ch10/README.md` prints.
- `machine.json`: the Docker host, image digests and model revisions.
- `workloads.json`: both workloads, every request's TTFT, the hit and
  query counts, the prompt size.
- `metrics.om.gz`: the engine's series, one scrape a second, as
  OpenMetrics text (`promtool tsdb create-blocks-from openmetrics`),
  for screenshot S4.
