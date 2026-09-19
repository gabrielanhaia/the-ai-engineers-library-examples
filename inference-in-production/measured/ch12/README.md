# measured/ch12

The ch12 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-in-production ch12
```

- `output.txt`: the lab's stdout; `../../ch12/README.md` shows it.
- `acceptance.jsonl`: one row per task type and temperature, from `/metrics` deltas.
- `spec-<task>-t<T>.json`: every request's text and timings, including the server's `draft_n` and `draft_n_accepted`.
- `wallclock.json`: plain and speculative wall-clock time at temperature 0 (CPU, not representative).
- `machine.json`: the Docker host, image digests and model revisions.
