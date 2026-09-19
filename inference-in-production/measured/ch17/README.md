# measured/ch17

The ch17 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-in-production ch17
```

- `output.txt`: the lab's stdout, which `ch17/README.md` prints.
- `machine.json`: the Docker host, image digests and model revisions.
- `llama.cpp.jsonl`, `vllm.jsonl`: every request's verdict, its
  problems, whether it named the right tool, and the engine's full
  message.
- `summary.txt`: the rates table.
