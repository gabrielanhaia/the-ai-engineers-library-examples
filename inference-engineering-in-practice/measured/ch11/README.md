# measured/ch11

The ch11 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-engineering-in-practice ch11
```

Recorded from 22:34 UTC with no other lab or engine running: load
average 1.35 / 2.54 / 3.23 inside the Docker VM (1 / 5 / 15 min,
the longer averages still carrying the previous lab) and
4.23 / 4.70 / 5.02 on the Mac, where macOS background work
held about one core. Everything the algorithm sets came back
identical to the earlier recording under load (perplexity, KL
divergence, same-top share, the eval's 39/40, 38/40, 38/40); only
the decode rates moved, by about 1% to 4%.

- `output.txt`: the lab's stdout; `../../ch11/README.md` shows it.
- `ppl-f16.log`, `kld-Q8_0.log`, `kld-Q4_K_M.log`: `llama perplexity`, as written.
- `eval-*.json`: the task eval, every reply and its score.
- `sizes.json`: the GGUF file sizes; `bench.json`: `llama bench` at every thread count.
- `results.json`: the summary behind the printed table.
- `machine.json`: the Docker host, image digests and model revisions.
