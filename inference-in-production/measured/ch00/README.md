# measured/ch00

The ch00 smoke lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-in-production ch00
```

- `stream.sse`: the raw server-sent events, as received.
- `chunks.jsonl`: one JSON chunk per line, `data: ` stripped.
- `timings.json`: the `timings` object from the last chunk.
- `machine.json`: the Docker host, image digests and model revisions.
