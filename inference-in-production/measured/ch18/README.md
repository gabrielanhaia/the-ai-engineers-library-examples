# measured/ch18

The ch18 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-in-production ch18
```

- `gates.json`: every gate's verdict on every candidate.
- `eval-baseline.json`, `eval-rerun.json`,
  `eval-broken-template.json`: chapter 11's task eval (llama.cpp,
  SmolLM2-360M-Instruct Q8_0), every reply included.
- `bench-baseline.json`, `bench-rerun.json`,
  `bench-slower-config.json`: `vllm bench serve` results against the
  simulator (**simulated**: its timings are its configuration).
- `machine.json`: the Docker host, image digests and model
  revisions.
