# measured/ch12

The ch12 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-engineering-in-practice ch12
```

Recorded at 22:53 UTC with no other lab or engine running: load
average 0.82 / 4.57 / 5.49 inside the Docker VM (1 / 5 / 15 min,
the longer averages still falling from the previous lab) and
2.87 / 5.83 / 6.65 on the Mac, where macOS background work held
about one core. Every acceptance figure came back identical to
the earlier recording under load, drafted and accepted token
counts included: the sweep is greedy or seeded, so the machine
does not enter into it. Only the wall clock moved, from 0.71x to
0.74x.

- `output.txt`: the lab's stdout; `../../ch12/README.md` shows it.
- `acceptance.jsonl`: one row per task type and temperature, from `/metrics` deltas.
- `spec-<task>-t<T>.json`: every request's text and timings, including the server's `draft_n` and `draft_n_accepted`.
- `wallclock.json`: plain and speculative wall-clock time at temperature 0 (CPU, not representative).
- `machine.json`: the Docker host, image digests and model revisions.
