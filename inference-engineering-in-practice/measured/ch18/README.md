# measured/ch18

The ch18 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-engineering-in-practice ch18
```

Recorded from 23:19 UTC with no other lab running: load average
4.85 / 6.11 / 6.55 inside the Docker VM (1 / 5 / 15 min, still
falling from the previous lab) and 3.83 / 5.78 / 6.58 on the Mac.
The gates' verdicts do not depend on the machine, and the
simulated benchmark's latencies are the simulator's configuration.

Both gates are wired to the labs they borrow from: the quality
gate runs chapter 11's eval and chapter 17's verifier against the
same llama.cpp server (chapter 17's stack: the F16 GGUF and
`ch17/template.jinja`), and the performance gate reads what
`vllm bench serve` reported, the harness chapter 4 uses.

- `gates.json`: every gate's verdict on every candidate, and how
  many contract replies the broken template changed.
- `eval-baseline.json`, `eval-rerun.json`,
  `eval-broken-template.json`: chapter 11's task eval (llama.cpp,
  SmolLM2-360M-Instruct F16), every reply included.
- `verify-rerun/llama.cpp.jsonl`,
  `verify-broken-template/llama.cpp.jsonl`: chapter 17's 40
  contract requests against the same server, one row per request,
  the whole message included. The broken template changed 24 of
  the 40 replies (each gains a stray `assistant` line) and not one
  schema-valid rate: the engine's grammar still yields a valid
  call, so chapter 17's floors cannot see this regression and the
  eval's unchanged-replies check is what catches it.
- `bench-baseline.json`, `bench-rerun.json`,
  `bench-slower-config.json`: `vllm bench serve` results against the
  simulator (**simulated**: its timings are its configuration);
  `perf-*.json`: the goodput, throughput and median TPOT the
  performance gate reads from each.
- `machine.json`: the Docker host, image digests and model
  revisions.
