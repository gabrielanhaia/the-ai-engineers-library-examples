# ch07: the capacity calculator

Chapter 7's answer to "how many GPUs": the larger of a memory count and
a throughput count, rounded up to the unit you can buy, then the
utilization and cost per million output tokens that fleet implies.
Rates come from `inputs/`, each with its latency bound and token type;
a rate measured at a looser bound than your SLO, or on a machine that
is not a GPU, is refused.

## What it does

1. The fit table: KV budget = HBM x 0.92 - total weight bytes, in
   decimal GB, for six model and GPU pairs. An upper bound: it leaves
   out activations and workspace. The engine's startup line is the
   authority.
2. The support assistant (memory count): the running batch by Little's
   law, with W the time in service (prefill + decode, not the queue);
   KV needed = running batch x (ISL + OSL/2); replicas = KV needed over
   one card's budget; the bandwidth floor on a step at that batch.
3. The gpt-oss-120b product (throughput count): peak output tokens
   over MLPerf's per-GPU Server rate at 70% of the rate; rounded up to
   8-GPU nodes; utilization and $ per million output tokens at the
   average and in the valley.
4. Recomputes every DERIVED number chapter 7 prints into
   `measured/ch07/derived.json` (`derived.py`).

The workloads are the chapter's assumptions, in `ch07/examples.toml`;
models, GPUs, rates, prices and traffic shapes are read from
`inputs/` by name.

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch07
```

Pure Python on the runner, a few seconds. For your own forecast, copy
`examples.toml`, put in your numbers, and pass it as the argument:

```sh
docker compose run --rm inference-engineering-in-practice ch07 my-forecast.toml
```

## Expected output

Recorded on the reference laptop (Apple M2 Pro, 16 GB, OrbStack,
linux/arm64). This block is
[`../measured/ch07/output.txt`](../measured/ch07/output.txt):

```

== fit, and the two worked examples
fit: KV budget <= HBM x 0.92 - weights (decimal GB),
an upper bound: activations and workspace are left out
model              GPU   HBMx0.92  weights  for KV  KV tokens
8B BF16            H100     73.60    16.06   57.54    438,991
70B FP8, FP8 KV    H100     73.60    70.55    3.05     18,593
70B FP8, FP8 KV    B200    165.60    70.55   95.05    580,116
70B BF16           B200    165.60   141.11   24.49     74,745
granite-8b BF16    L4       22.08    17.58    4.50     27,446
granite-8b BF16    L40S     44.16    17.58   26.58    162,212

support assistant: Llama-3.1-8B on H100
  peak       20 requests/s (the busiest hour)
  shape      2,000 in / 500 out; SLO TTFT <= 1,000 ms, TPOT <= 40 ms
  W          <= 1 + 499 x 0.04 = 20.96 s in service
  running    20 x 20.96 = 419.2 sequences
  KV needed  419.2 x (2,000 + 500 / 2) = 943,200 tokens
             x 131,072 B = 123.6 GB
  memory     943,200 / 438,991 = 2.15 -> 3 H100
             each 139.7 seqs, 314,400 tokens (72% of fit)
  step       >= (16.06 + 41.21) GB / 3.35 TB/s = 17.1 ms
  throughput no cited rate at this SLO: measure one
  fleet      3 H100, the memory count

a product: gpt-oss-120b on B200
  average    40 requests/s x 1.7 (conversation) = 68 at peak
  shape      5,000 in / 1,250 out; SLO TTFT <= 3,000 ms, TPOT <= 80 ms
  memory     no KV shape in inputs/: not counted
  rate       89,856.3 / 8 = 11,232.0 output tokens/s per GPU
             Nebius B200 n1 (8x B200-SXM-180GB, TensorRT)
             at p99 TTFT <= 3,000 ms, TPOT <= 80 ms
  throughput 85,000 / (0.70 x 11,232.0) = 10.81 -> 11 GPUs
  fleet      16 B200, bought 8 at a time
  load       40.0 requests/s: 50,000 / 179,712.6 = 27.8%
             16 x $7.15 = $114.40 / 180.00M = $0.636 per M out
  valley     20.6 requests/s: 25,758 / 179,712.6 = 14.3%
             16 x $7.15 = $114.40 / 92.73M = $1.23 per M out

== every DERIVED number in chapter 7
70 numbers, recomputed from inputs/: measured/ch07/derived.json

== done
manifest: measured/ch07/machine.json
```

## What the test asserts

`test ch07` runs the lab, then checks invariants, never a GPU count:
more weight bytes leave less KV; the running batch is linear in the
arrival rate; a rate measured at a looser bound than the SLO is
refused; a rate from a machine that is not a GPU is refused; every
fleet covers both counts, in whole units. The numbers themselves are
checked by the `derived-data` CI job (`scripts/check_derived.py`).

## Files

- `capacity.py`: the calculator (printed in chapter 7).
- `examples.toml`: the chapter's worked examples, as assumptions.
- `derived.py`: every DERIVED number chapter 7 prints, as JSON.
- `run.sh`, `test.sh`: the lab and its test.
