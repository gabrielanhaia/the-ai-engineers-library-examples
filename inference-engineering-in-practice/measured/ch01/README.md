# measured/ch01

The ch01 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-engineering-in-practice ch01
```

- `output.txt`: the lab's stdout; `../../ch01/README.md` shows it.
- `stream.sse`: the raw server-sent events, as received.
- `chunks.jsonl`: one JSON chunk per line, `data: ` stripped.
- `timings.json`: the `timings` object from the last chunk.
- `ttft.json`: client-side TTFT (to the first chunk with text) beside the server's `prompt_ms`.
- `machine.json`: the Docker host, image digests and model revisions.
