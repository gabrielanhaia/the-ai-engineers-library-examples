# measured/ch01

The ch01 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-engineering-in-practice ch01
```

Recorded at 22:03 UTC with no other lab or engine running: load
average 0.21 / 0.82 / 2.25 inside the Docker VM (1 / 5 / 15 min)
and 1.94 / 2.67 / 3.90 on the Mac, where macOS background work
(Spotlight, earlier XProtect and media analysis) held about one
core. It is one request, so it is one sample: six more runs on the
same quiet machine read the prompt in 21 to 79 ms (`prompt_ms`) and
wrote 2.7 to 6.4 ms per token; in every run the prompt was read
faster per token than the answer was written.

- `output.txt`: the lab's stdout; `../../ch01/README.md` shows it.
- `stream.sse`: the raw server-sent events, as received.
- `chunks.jsonl`: one JSON chunk per line, `data: ` stripped.
- `timings.json`: the `timings` object from the last chunk.
- `ttft.json`: client-side TTFT (to the first chunk with text) beside the server's `prompt_ms`.
- `machine.json`: the Docker host, image digests and model revisions.
