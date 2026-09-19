# ch02: predict, then measure

Chapter 2's lab. Single-stream decode reads every weight once per
token, so its speed is bounded by memory bandwidth ÷ weight bytes.
The lab measures this machine's bandwidth, predicts the bound for
one model in three GGUF files, then times llama.cpp on each and
reports measured ÷ predicted.

## What it does

1. Fetches SmolLM2-360M-Instruct as F16, Q8_0 and Q4_K_M GGUF
   (1,319 MiB), pinned and checked by SHA-256.
2. Records the CPU's architecture and the SIMD and matrix features
   that decide which formats run natively (`/proc/cpuinfo`, kept
   whole in `measured/ch02/cpuinfo.txt`).
3. Measures copy bandwidth with `bandwidth.py`, a STREAM-style test
   in standard-library Python: one process per CPU copies its share
   of two 512 MiB arrays, far larger than any cache, all at once;
   a copied byte counts twice (read and written), and the best of 10
   trials is kept, as STREAM does.
4. Predicts tokens/s <= bandwidth ÷ file bytes for each format, and
   prints the prediction before measuring anything.
5. Runs `llama bench` (the multi-call `llama` binary's `bench`,
   which is `llama-bench`): 64 generated tokens, 5 runs, at 2, 4,
   6, ... threads up to the CPU count. llama.cpp splits each step
   evenly across its threads and waits for the slowest, so using
   every CPU is not always fastest (efficiency cores, a busy host);
   the lab keeps each format's fastest thread count, judged by the
   median of its 5 runs.
6. Prints predicted, measured, the thread count and the ratio.

F16 leads, not BF16: on a CPU without native BF16 arithmetic a BF16
matrix multiply turns compute-bound and stops measuring bandwidth.

## Run it

```sh
docker compose run --rm inference-in-production ch02
```

A few minutes after the first run, which downloads the models.

## Expected output

Recorded on the reference laptop (Apple M2 Pro, 16 GB, OrbStack,
linux/arm64, CPU only). This block is
[`../measured/ch02/output.txt`](../measured/ch02/output.txt):

```

== model: one model, three GGUF files
models: 3 file(s), 1,319 MiB, into /models
  ok      gguf/SmolLM2-360M-Instruct-f16.gguf
  ok      gguf/SmolLM2-360M-Instruct-Q8_0.gguf
  ok      gguf/SmolLM2-360M-Instruct-Q4_K_M.gguf

== CPU instruction set
arch: aarch64, 10 CPUs
features: asimd fphp asimdhp asimddp bf16

== memory bandwidth (STREAM-style copy)
{"copy_gb_s": 157.7, "median_gb_s": 151.8, "processes": 10, "array_mib": 512, "trials": 10, "counted": "2 bytes per byte copied"}

== prediction: 157.7 GB/s / weight bytes
format   weight bytes      tok/s <=
f16         725553792           217
Q8_0        386405280           408
Q4_K_M      270590880           583

== measurement: llama bench, 64 tokens, 5 runs, threads 2,4,6,8,10
load_backend: loaded CPU backend from /app/libggml-cpu-armv8.2_2.so
llama.cpp build b10964, commit b29c606e2

== measured / predicted
format   predicted   measured  threads    ratio
f16            217      113.2        4     0.52
Q8_0           408      207.5        6     0.51
Q4_K_M         583      225.1        6     0.39

== done
manifest: measured/ch02/machine.json
```

## What the test asserts

`test ch02` runs the lab, then checks invariants, never speeds: a
bandwidth was measured; each format has a prediction and a
measurement; file sizes order F16 > Q8_0 > Q4_K_M; and both
quantized files decode faster than F16. It does not assert Q4_K_M
against Q8_0: on a model this small their gap is narrow (8% in the
run above), and a busy machine can flip it.

## Files

- `run.sh`: the lab. `bandwidth.py`: the copy test. `test.sh`:
  runs the lab, then asserts.
- Output lands in `measured/ch02/`: `cpuinfo.txt`,
  `bandwidth.json`, `predicted.json`, `bench.json` (every thread
  count, as `llama bench` wrote it), `results.json` and
  `machine.json`.
