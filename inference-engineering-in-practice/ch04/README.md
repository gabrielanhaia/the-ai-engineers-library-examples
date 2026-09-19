# ch04: the sweep, the loops and the cache

Chapter 4's lab: three ways to benchmark the same vLLM CPU server,
and one way to fool yourself on purpose. Every number it prints is
the laptop's, and the laptop's curve is a laptop's curve.

## What it does

1. Starts vLLM 0.29.0's CPU backend with SmolLM2-360M-Instruct in
   FP16 (why not BF16: `ch09/README.md`).
2. **sweep.** GuideLLM 0.7.4 (`guidellm run`, profile `sweep`,
   Poisson): a synchronous run (one request at a time), a
   throughput run (as many at once as it can, up to 32), then four
   Poisson rates spaced between the two, 60 seconds each, 128
   tokens in and 64 out. The cap of 32 also bounds the Poisson
   points; without it GuideLLM's throughput run sends 512 at once,
   and on a CPU none of them finishes inside a 60-second point.
   `report.py sweep` prints one row per point: achieved request
   rate, mean requests in flight, TTFT p50 and p99, TPOT p50.
   GuideLLM also writes its JSON and its HTML report.
3. **loops.** `vllm bench serve`, 64 requests of 128 in and 64 out.
   First a closed loop at concurrency 4 (`--max-concurrency 4
   --request-rate inf`): a new request goes out only when one comes
   back. Then an open loop (`--request-rate R --burstiness 1.0`,
   Poisson arrivals) at R, the request rate the closed loop
   achieved: the same mean load, sent the way users send it.
   `report.py loops` prints both, with the most requests the
   client ever had in flight.
4. **cache.** `vllm bench serve` with its random dataset, 16
   requests of 1,024 tokens in and 32 out, concurrency 4, run
   three times: without `--seed` (it defaults to 0), the same
   command again, then with `--seed 1`. Before and after each run
   the lab reads `vllm:prefix_cache_hits_total` and
   `vllm:prefix_cache_queries_total`. The second run's prompts are
   the first run's, still in the prefix cache.

`PARTS` picks the parts (default `sweep loops cache`). A watcher
scrapes `/metrics` once a second throughout, so the loops table can
show the most requests the server itself ran at once, and every
table is printed at the end.

Two things the sweep's table shows that a single number hides:
GuideLLM's achieved request rate is not the Poisson rate it was
asked for, and the p99 TTFT climbs long before the median does.
`vllm bench serve --num-warmups N` sends the dataset's first
request N times before the run, so with prefix caching on, the
first measured request can be a cache hit (the warm-up reuses its
prompt, `vllm/benchmarks/serve.py` at v0.29.0); this lab uses no
warm-ups in the cache part for that reason.

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch04
```

It downloads the `smollm2-360m-hf` model (693 MiB) once. vLLM takes
about a minute to start; the whole lab takes about 12 minutes on the
reference laptop (the sweep alone about 7).

## Expected output

The hit rates are set by the seeds; the rates and milliseconds are
the laptop's. Recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack, linux/arm64, CPU only). This block is
[`../measured/ch04/output.txt`](../measured/ch04/output.txt):

```text

== vLLM CPU backend
models: 8 file(s), 693 MiB, into /models
  ok      hf/SmolLM2-360M-Instruct/config.json
  ok      hf/SmolLM2-360M-Instruct/generation_config.json
  ok      hf/SmolLM2-360M-Instruct/merges.txt
  ok      hf/SmolLM2-360M-Instruct/model.safetensors
  ok      hf/SmolLM2-360M-Instruct/special_tokens_map.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer_config.json
  ok      hf/SmolLM2-360M-Instruct/vocab.json
ch04-vllm ready after ~61s

== sweep: GuideLLM, 128 tokens in, 64 out, 60 s a point
GuideLLM's report: measured/ch04/guidellm.html

== loops: closed at concurrency 4, then open at its rate
closed loop: 1.10 req/s; open loop sent at that rate

== cache: one command twice, then a new seed

== results
 strategy      req/s  in flight  TTFT p50  TTFT p99  TPOT p50
 synchronous    0.37        1.0    294 ms   1474 ms     34 ms
 throughput     1.60       28.0   4451 ms   7394 ms    253 ms
 poisson 0.68   0.97       10.6    418 ms   3085 ms    218 ms
 poisson 0.98   1.15       12.7    766 ms   3637 ms    150 ms
 poisson 1.29   1.18       13.6    721 ms   4215 ms    206 ms
 poisson 1.60   1.68       24.0   1947 ms   4865 ms    232 ms

 loop     rate req/s  peak running  TTFT p50  TTFT p99
 closed         1.10             4    811 ms   1218 ms
 open           1.02            16    328 ms   2098 ms

 run       seed  hit rate  TTFT p50  total tok/s
 first        0      0.00   4557 ms        571.5
 again        0      0.88    935 ms       1207.2
 new-seed     1      0.00   3188 ms        526.6


== done
manifest: measured/ch04/machine.json
```

## What the test asserts

`test ch04` runs only the cache part (`PARTS=cache`), then asserts
what the seeds set: the first run's hit rate is below 0.1, the
repeated command's is above 0.8, the new seed's is below 0.1, and
the repeated command's total tok/s is higher than the first's.

## Files

- `report.py`: the three tables, from the recorded files.
- In `measured/ch04/`: `guidellm.json` and `guidellm.html`
  (GuideLLM's own report, the chapter's screenshot),
  `guidellm-console.txt`, `closed.json`, `open.json`,
  `cache-first.json`, `cache-again.json`, `cache-new-seed.json`
  (each `vllm bench serve` result) and `cache.tsv` (the counters
  before and after each cache run).
