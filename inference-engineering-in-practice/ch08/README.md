# ch08: the knee, bounded and measured

Chapter 8's lab, in three parts. The first is arithmetic, the
second is the laptop's own curve, the third is the same work with
nobody waiting for it.

## What it does

1. **The bound (DERIVED).** `bound.py` computes the roofline
   model's upper bound on decode throughput against batch size for
   Llama-3.1-8B in BF16 on an H100, at 4,096 tokens of context per
   sequence, from the cited inputs in `inputs/hardware.toml` (3.35
   TB/s) and `inputs/models.toml` (8,030,261,248 parameters; 32
   layers, 8 KV heads, head_dim 128). Each step reads the weights
   once and every sequence's KV, so aggregate tok/s ≤ B × BW ÷ (W +
   B × L × k). It prints the bound at nine batch sizes, the ceiling
   BW ÷ (L × k) it approaches and never passes, and the batch at
   which it is halfway there. `derived.py` records every number the
   chapter prints from it in `measured/ch08/derived.json`, which CI
   recomputes. It is a bound, not a prediction.
2. **The laptop's curve (MEASURED).** vLLM 0.29.0's CPU backend
   serving SmolLM2-360M-Instruct in FP16 (why not BF16:
   `ch09/README.md`), and `vllm bench serve` as a
   closed loop at concurrency 1, 2, 4, 8, 16, 32, 64 and 128
   (random prompts of 64 tokens, 64 output tokens, `--ignore-eos`,
   four warm-up requests, then four times as many requests as the
   concurrency, at least 16).
   `sweep.py` prints output tok/s, its multiple of concurrency 1,
   median TTFT, and mean and p99 TPOT. A 64 + 64 token request
   fits one 128-token KV block, so 128 of them fit the 1 GiB cache
   and the sweep never preempts (the run prints the counter): the
   flattening is the laptop's compute, not a full cache. 128 is
   also the CPU backend's default `max_num_seqs` for `vllm serve`.
3. **The offline corner (MEASURED).** The server is stopped and the
   same kind of request, 256 of them, goes into one batch file for
   `vllm run-batch` (OpenAI batch format, one request per line).
   The engine starts, takes the whole file at once, and writes the
   answers to another file. `batch.py` prints output tokens per
   second over the batch's own elapsed time (the `Running batch`
   line), engine start-up excluded. `run-batch` accepts
   `/v1/chat/completions` requests (not `/v1/completions`), and on
   the CPU backend it schedules with the same defaults as `vllm
   serve` (2,048 batched tokens, 128 sequences); only the Python
   `LLM` class gets the larger offline defaults (4,096 and 256).

The laptop's numbers describe the laptop: a CPU running a 360M
model, where the curve bends at a batch no GPU would recognise.
The shape is the point: throughput climbs and then flattens while
each user's tokens slow down.

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch08
```

It downloads the `smollm2-360m-hf` model (693 MiB) once. vLLM takes
about a minute to start twice (the server, then `run-batch`); the
whole lab takes about 11 minutes on the reference laptop.
`CONCS="1 4 16 64"` and `BATCH=64` make it shorter.

## Expected output

The bound is arithmetic and does not change. The sweep and the
batch are the laptop's. Recorded on the reference laptop (Apple M2
Pro, 16 GB, OrbStack, linux/arm64, CPU only). This block is
[`../measured/ch08/output.txt`](../measured/ch08/output.txt):

```text

== the bound (DERIVED from inputs/, not measured)
Llama-3.1-8B, 2 B/value, on H100 (3.35 TB/s), L = 4,096
W = 16.06 GB, KV = 131,072 B/token, 0.537 GB/sequence
DERIVED upper bounds (roofline model):
    B   step (ms)   aggregate tok/s   per-user tok/s
    1        4.95               202              202
    2        5.11               391              196
    4        5.44               736              184
    8        6.08             1,317              165
   16        7.36             2,174              136
   30        9.60             3,124              104
   64       15.05             4,252               66
  128       25.31             5,058               40
  256       45.82             5,587               22
ceiling BW / (L x k) = 6,240 tok/s; half of it at B = W / (L x k) = 30

== the laptop: vLLM CPU backend, 64 tokens in, 64 out
models: 8 file(s), 693 MiB, into /models
  ok      hf/SmolLM2-360M-Instruct/config.json
  ok      hf/SmolLM2-360M-Instruct/generation_config.json
  ok      hf/SmolLM2-360M-Instruct/merges.txt
  ok      hf/SmolLM2-360M-Instruct/model.safetensors
  ok      hf/SmolLM2-360M-Instruct/special_tokens_map.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer_config.json
  ok      hf/SmolLM2-360M-Instruct/vocab.json
ch08-vllm ready after ~59s
 conc  output tok/s  x conc 1  TTFT p50  TPOT mean  TPOT p99
    1          32.6       1.0    148 ms      29 ms     39 ms
    2          65.1       2.0    253 ms      28 ms     31 ms
    4          90.8       2.8    368 ms      39 ms     50 ms
    8         121.5       3.7    785 ms      55 ms     71 ms
   16         157.2       4.8   1410 ms      82 ms    124 ms
   32         183.2       5.6   2719 ms     136 ms    179 ms
   64         265.9       8.1   4431 ms     181 ms    253 ms
  128         272.9       8.4   5216 ms     391 ms    500 ms
preemptions during the sweep: 0

== the offline corner: 256 requests in one file, run-batch
Running batch: 100% Completed | 256/256 [01:10<00:00,  3.62req/s]
requests 256 of 256, prompt 73 tokens each, 16,384 output tokens
elapsed 70 s, output 234.1 tok/s

== done
manifest: measured/ch08/machine.json
```

## What the test asserts

`test ch08` runs a shorter sweep (concurrency 1, 2, 16, 64) and a
64-request batch, then asserts shapes, never speeds: output tok/s
rises with concurrency and the gain per doubling at the top is
smaller than at the bottom; mean TPOT at the highest concurrency is
above that at 1; the sweep never preempted; every request in the
batch file came back with its 64 tokens; and the bound's ceiling is
the chapter's 6,240 tok/s.

## Files

- `bound.py`: the roofline-model bound, from `inputs/`.
- `derived.py`: the DERIVED numbers the chapter prints, as JSON
  (`scripts/check_derived.py` recomputes it).
- `sweep.py`: the sweep table and `sweep.csv`.
- `batch.py`: the batch file, and what came back.
- In `measured/ch08/`: `derived.json`, `bench-cN.json` (each
  `vllm bench serve` result), `sweep.csv`, `batch-out.jsonl` and
  `offline.json`.
