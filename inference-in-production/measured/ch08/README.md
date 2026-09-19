# measured/ch08

The ch08 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-in-production ch08
```

- `output.txt`: the lab's stdout, which `ch08/README.md` prints.
- `machine.json`: the Docker host, image digests and model revisions.
- `derived.json`: every DERIVED number chapter 8 prints, with the
  string it prints (`ch08/derived.py`; `scripts/check_derived.py`
  recomputes it).
- `bench-cN.json`: `vllm bench serve` at concurrency N; `sweep.csv`:
  the sweep table's data, the figure's source.
- `preemptions.txt`: the preemption counter after the sweep.
- `batch-out.jsonl`: what `vllm run-batch` wrote; `offline.json`: its
  requests, output tokens and elapsed seconds.
