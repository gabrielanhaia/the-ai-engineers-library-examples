# measured/ch07

The ch07 calculator as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-in-production ch07
```

Nothing here is a measurement of hardware: every number is DERIVED,
arithmetic on the cited inputs in `inputs/`, and the same on any
machine.

- `output.txt`: the lab's output; the README's *Expected output*.
- `derived.json`: every DERIVED number the chapter prints, with its
  full value and the string the chapter prints, and the calculator's
  default output. `scripts/check_derived.py` (CI job
  `derived-data`) recomputes it from `inputs/` and fails on any
  difference.
- `machine.json`: the Docker host, image digests and model revisions.
