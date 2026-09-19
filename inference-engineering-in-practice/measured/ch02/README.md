# measured/ch02

The ch02 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-engineering-in-practice ch02
```

- `output.txt`: the lab's stdout; `../../ch02/README.md` shows it.
- `cpuinfo.txt`: the CPU feature line from `/proc/cpuinfo`.
- `bandwidth.json`: the STREAM-style copy bandwidth.
- `predicted.json`: bandwidth / file bytes per format.
- `bench.json`: `llama bench` at every thread count, as written.
- `results.json`: per format, the fastest thread count by median, measured / predicted.
- `machine.json`: the Docker host, image digests and model revisions.
