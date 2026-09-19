# ch05: the cost calculator

Chapter 5's one division, with its three labels. It reproduces worked
example A from MLPerf's published row and Nebius's dated list price,
and prices your own request shape the same way. It takes no
throughput as a number: rates come only from MLPerf's table in
`inputs/`, so a laptop's tokens per second never meet a GPU's price.

## What it does

1. Reads the MLPerf Inference v6.1 row for Nebius's 8 x B200 node on
   gpt-oss-120b, Server scenario, from `inputs/mlperf-v6.1-summary.csv`
   (copied verbatim from MLPerf's `summary.csv`), its p99 latency bound
   from `inputs/mlperf-rules.toml` and the B200 list price from
   `inputs/example-a.toml`.
2. Divides the unit's price per hour by the tokens the same unit makes
   in an hour, twice: per 8-GPU node and per GPU. The two must agree
   (the unit check), or it stops.
3. Prints the price per million output tokens with its token type,
   latency bound and utilization beside it, and the price of one
   request of the benchmark's shape.
4. Prices a second shape (20,000 in / 500 out at 41.2% utilization)
   and warns that the row was not measured at that shape.
5. Recomputes every DERIVED number chapter 5 prints into
   `measured/ch05/derived.json` (`derived.py`).

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch05
```

Pure Python on the runner: no model, no engine, a few seconds. Price
your own shape with arguments (they replace the default run):

```sh
docker compose run --rm inference-engineering-in-practice ch05 \
  --row Nebius/B300-SXM-270GBx8_TRT/gpt-oss-120b/Server \
  --price nebius.B300 --input 2000 --output 500 --utilization 0.4
```

- `--row` is an MLPerf row, `Organization/Platform/Model/Scenario`;
  add rows to the CSV from MLPerf's own `summary.csv`, header intact.
- `--price` is `table.GPU` in `inputs/example-a.toml` or
  `inputs/prices.toml`, per GPU-hour (a table with `gpus = 4` prices
  a 4-GPU instance). A price for a GPU the row was not measured on is
  refused.
- `--input`, `--output`: your mean request shape; `--utilization`:
  tokens you serve over tokens the fleet could serve at the SLO.

## Expected output

Recorded on the reference laptop (Apple M2 Pro, 16 GB, OrbStack,
linux/arm64). This block is
[`../measured/ch05/output.txt`](../measured/ch05/output.txt):

```

== worked example A
gpt-oss-120b, MLPerf v6.1 closed, Server
  system   Nebius B200 n1 (8x B200-SXM-180GB, TensorRT)
  unit     8 x $7.15 = $57.20 an hour
  tokens   89,856.3/s x 3,600 = 323.48 million an hour
  per unit $57.20 / 323.48 = $0.1768 per million
  per GPU  $7.15 / 40.44 = $0.1768 per million (unit check)

$0.177 per million output tokens
  tokens   output only; each request's prefill is included
  latency  p99 TTFT <= 3,000 ms, p99 TPOT <= 80 ms
           (a floor of 12.5 tokens/s per user)
  load     100% utilization; divide by your average
  request  5,000 in / 1,250 out: $0.00022
  inputs   MLPerf v6.1 summary.csv; nebius.B200, 2026-09-19

== another shape: 20,000 in / 500 out at 41.2% utilization
gpt-oss-120b, MLPerf v6.1 closed, Server
  system   Nebius B200 n1 (8x B200-SXM-180GB, TensorRT)
  unit     8 x $7.15 = $57.20 an hour
  tokens   89,856.3/s x 3,600 = 323.48 million an hour
  per unit $57.20 / 323.48 = $0.1768 per million
  per GPU  $7.15 / 40.44 = $0.1768 per million (unit check)

$0.429 per million output tokens
  tokens   output only; each request's prefill is included
  latency  p99 TTFT <= 3,000 ms, p99 TPOT <= 80 ms
           (a floor of 12.5 tokens/s per user)
  load     41.2% utilization: $0.1768 / 0.412
  request  20,000 in / 500 out: $0.00021
  WARNING  measured on MLPerf's gpt-oss-120b set, not your shape:
           measure yours before you price it (chapter 4)
  inputs   MLPerf v6.1 summary.csv; nebius.B200, 2026-09-19

== every DERIVED number in chapter 5
59 numbers, recomputed from inputs/: measured/ch05/derived.json

== done
manifest: measured/ch05/machine.json
```

## What the test asserts

`test ch05` runs the lab, then checks invariants, never a price: the
per-unit and per-GPU answers agree for every row it prices; the
orderings chapter 5 argues from (on one provider's list the cheapest
GPU-hour gives the dearest token, B300 < B200 < RTX PRO 6000; a
tighter latency bound costs more per token on the GB200 pair); cost at
utilization U is cost at 100% divided by U; a price for another GPU is
refused; no argument takes a typed-in throughput; a shape other than
the row's draws a warning. The numbers themselves are checked by the
`derived-data` CI job (`scripts/check_derived.py`), which recomputes
them from `inputs/` and fails on any difference from
`measured/ch05/derived.json`.

## Files

- `cost.py`: the calculator (printed in chapter 5).
- `derived.py`: every DERIVED number chapter 5 prints, as JSON.
- `run.sh`, `test.sh`: the lab and its test.
- Inputs: `../inputs/` (see its README). Output: `../measured/ch05/`.
