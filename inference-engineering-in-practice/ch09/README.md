# ch09: predict the cliff, then watch it

Chapter 9's lab. It predicts, from nothing but the model's config
and the size of the KV cache, the concurrency at which the cache
must overflow, then drives the vLLM CPU backend below and above that
point and reads the engine's own preemption counter.

## What it does

1. `predict.py` reads SmolLM2-360M-Instruct's `config.json` (the
   pinned revision, from the model cache) and computes KV bytes per
   token: 2 × 32 layers × 5 KV heads × 64 (head_dim = 960 / 15) × 2
   bytes = 40,960 B. A 1 GiB cache holds 26,214 of them. Each
   request here is 1,792 tokens in and 256 out, 2,048 in all, so
   the cache fits 12.80 requests at once and preemption must start
   at 13.
2. Starts vLLM 0.29.0's CPU backend with `VLLM_CPU_KVCACHE_SPACE=1`
   and `--max-model-len 2048`, and prints its own capacity line
   (`GPU KV cache size: 26,112 tokens, Maximum concurrency for
   2,048 tokens per request: 12.75x`) and its block size. On the
   CPU backend the block is 128 tokens, not the GPU's 16, which is
   why the engine's figure is 26,112 (204 blocks of 128) and not
   26,214.
3. For each concurrency in `LEVELS` (default 4, 8, 12, 13, 16) sends
   that many requests at once with `vllm bench serve` (random
   tokens, `--ignore-eos`, a new seed per batch so no prefix is
   reused) and reads `vllm:num_preemptions_total` before and after.
   A watcher scrapes `/metrics` once a second the whole time.
4. `report.py` prints one row per concurrency: the prediction, the
   peak number of running requests, the peak of
   `vllm:kv_cache_usage_perc`, the preemptions during the batch,
   and `vllm:num_preemptions_total` itself after it.

Above 13 the engine does not run more requests at once. It admits
a request only when that request's prompt fits in the free blocks,
so at 16 three requests wait in the queue while 13 run, and the
overflow among those 13 is what preempts.

The model is served in FP16 (`--dtype float16`), not its native
BF16: both are 2 bytes per value, so the KV arithmetic is the same,
and on the reference laptop's vLLM CPU backend FP16 decoded about
twice as fast (a quick A/B, not recorded here: 128 tokens, median
of three requests, 8.7 s in BF16 and 4.6 s in FP16). The vLLM labs
of chapters 4, 8, 10, 15 and 17 use FP16 for the same reason.

Long prompts and short outputs would not show the cliff. The
engine admits a request only when its prompt fits, so a request
that does not fit waits in the queue instead. Preemption is what
happens when requests already running grow into memory that is not
there, so the output (256 tokens) has to outlast the time it takes
to admit the whole batch.

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch09
```

It downloads the `smollm2-360m-hf` model (693 MiB) once. vLLM takes
about a minute to start; the five batches take about 6 minutes on
the reference laptop. `LEVELS="12 13"` runs only the two that
matter.

## Expected output

The counts and the prediction are set by the model and the cache;
the seconds are the laptop's. Recorded on the reference laptop
(Apple M2 Pro, 16 GB, OrbStack, linux/arm64, CPU only). This block
is [`../measured/ch09/output.txt`](../measured/ch09/output.txt):

```text

== prediction, from the model's config
models: 8 file(s), 693 MiB, into /models
  ok      hf/SmolLM2-360M-Instruct/config.json
  ok      hf/SmolLM2-360M-Instruct/generation_config.json
  ok      hf/SmolLM2-360M-Instruct/merges.txt
  ok      hf/SmolLM2-360M-Instruct/model.safetensors
  ok      hf/SmolLM2-360M-Instruct/special_tokens_map.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer_config.json
  ok      hf/SmolLM2-360M-Instruct/vocab.json
KV per token  2 x 32 x 5 x 64 x 2 B = 40,960 B
cache         1 GiB / 40,960 B = 26,214 tokens
per request   1,792 in + 256 out = 2,048 tokens
fits          26,214 / 2,048 = 12.80 requests
prediction    preemption starts at 13 concurrent requests

== vLLM CPU backend, 1 GiB of KV cache
ch09-vllm ready after ~61s
GPU KV cache size: 26,112 tokens, Maximum concurrency for 2,048
  tokens per request: 12.75x
block_size="128" num_gpu_blocks="204"

== load: one batch of long requests per concurrency
concurrency 4: 40 s
concurrency 8: 56 s
concurrency 12: 73 s
concurrency 13: 84 s
concurrency 16: 96 s

== result
 conc  predicted  peak running  peak KV use  preemptions  counter
    4  fits                  4         0.32            0        0
    8  fits                  8         0.63            0        0
   12  fits                 12         0.95            0        0
   13  overflows            13         0.96            1        1
   16  overflows            13         0.97            1        2

== done
manifest: measured/ch09/machine.json
```

## What the test asserts

`test ch09` runs the lab at concurrency 4 and 13, then asserts
events, never timings: the engine's own "maximum concurrency"
figure rounds down to one less than the predicted first preempting
concurrency; there are no preemptions at 4; there is at least one
at 13; and `metrics.om.gz` loads into Prometheus with `promtool tsdb
create-blocks-from openmetrics`.

## Files

- `predict.py`: the prediction, from the config alone.
- `report.py`: the table, from what `run.sh` recorded.
- In `measured/ch09/`: `prediction.json`, `startup.txt` (the
  engine's capacity line and block size), `levels.tsv` and
  `levels.json` (one row per batch), `bench-cN.json` (each
  `vllm bench serve` result), and `metrics.om.gz`: the engine's
  scheduler, cache and latency series, one scrape a second, as
  OpenMetrics text that `promtool tsdb create-blocks-from
  openmetrics` loads into any Prometheus for the chapter's
  screenshots.
