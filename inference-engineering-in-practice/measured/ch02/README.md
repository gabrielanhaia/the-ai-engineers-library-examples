# measured/ch02

The ch02 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-engineering-in-practice ch02
```

Recorded at 22:04 UTC with no other lab or engine running: load
average 0.53 / 0.86 / 2.24 inside the Docker VM (1 / 5 / 15 min)
and 2.21 / 2.69 / 3.87 on the Mac, where macOS background work
(Spotlight, media analysis) held about one core. The earlier
recording of this lab shared the machine with other labs; this one
did not, and F16 moved from 113.2 to 132.3 tok/s while the
quantized files barely moved. The decode rate on this machine is
worth about +-10% between runs, and 10 threads stays pathological
(about 10 tok/s against 131 at 6 threads, `bench.json`).

- `output.txt`: the lab's stdout; `../../ch02/README.md` shows it.
- `cpuinfo.txt`: the CPU feature line from `/proc/cpuinfo`.
- `bandwidth.json`: the STREAM-style copy bandwidth.
- `predicted.json`: bandwidth / file bytes per format.
- `bench.json`: `llama bench` at every thread count, as written.
- `results.json`: per format, the fastest thread count by median, measured / predicted.
- `machine.json`: the Docker host, image digests and model revisions.
