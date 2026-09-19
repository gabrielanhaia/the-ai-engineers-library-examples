# ch10: measure your hit rate

Chapter 10's lab. The same words in two orders: a long system
prompt with the part that changes last, and the same prompt with
the part that changes first. vLLM's prefix cache sees the first as
one shared prefix and the second as twenty strangers.

## What it does

1. Starts vLLM 0.29.0's CPU backend with SmolLM2-360M-Instruct in
   FP16 (why not BF16: `ch09/README.md`).
   Prefix caching is on by default in 0.29.0, so no flag turns it
   on. The run prints the two counters it exports,
   `vllm:prefix_cache_queries_total` and
   `vllm:prefix_cache_hits_total`, both in prompt tokens.
2. `prompts.py` builds a 1,800-token system prompt (a hardware
   store's catalogue of 64 items) and sends 20 chat requests one at
   a time for each layout, streaming, 16 output tokens each:
   - **unique**: `Customer 007, visit 10.` on the first line of the
     system prompt, so every prompt differs from its first token;
   - **shared**: the catalogue first and the customer line in the
     user message, so every prompt shares its first 1,700-odd
     tokens.
3. For each workload it reads both counters before and after and
   prints the hit rate, hits ÷ queries, beside the client-side TTFT
   (request sent to the first chunk that carries text), median and
   90th percentile.

Requests go one at a time so that TTFT is the prefill and nothing
else: no queue, no neighbours. On a CPU prefill is slow, so a hit
saves more time here than the same hit saves on a GPU; the hit rate
is the number that carries over, since the workload sets it.

The hit rate stops short of 1.0 for two reasons the lab shows on
purpose: the first shared request finds nothing cached, and the
engine caches only full blocks (128 tokens on the CPU backend), so
the tail of the prefix and the user's question are computed every
time.

In PromQL, over the recorded series (names as scraped):

```promql
rate(vllm:prefix_cache_hits_total[5m])
  / rate(vllm:prefix_cache_queries_total[5m])
```

## Run it

```sh
docker compose run --rm inference-in-production ch10
```

It downloads the `smollm2-360m-hf` model (693 MiB) once. vLLM takes
about a minute to start; the 40 requests take about a minute and a
half on the reference laptop. `N=40` sends 40 per workload.

## Expected output

The hit rates are set by the workload; the milliseconds are the
laptop's. Recorded on the reference laptop (Apple M2 Pro, 16 GB,
OrbStack, linux/arm64, CPU only). This block is
[`../measured/ch10/output.txt`](../measured/ch10/output.txt):

```text

== vLLM CPU backend (prefix caching is on by default)
models: 8 file(s), 693 MiB, into /models
  ok      hf/SmolLM2-360M-Instruct/config.json
  ok      hf/SmolLM2-360M-Instruct/generation_config.json
  ok      hf/SmolLM2-360M-Instruct/merges.txt
  ok      hf/SmolLM2-360M-Instruct/model.safetensors
  ok      hf/SmolLM2-360M-Instruct/special_tokens_map.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer_config.json
  ok      hf/SmolLM2-360M-Instruct/vocab.json
ch10-vllm ready after ~61s
vllm:prefix_cache_hits_total
vllm:prefix_cache_queries_total

== 20 requests per workload, one at a time
 workload  requests  prompt tokens  hit rate  TTFT p50  TTFT p90
 unique          20          1,801      0.00   2754 ms   3195 ms
 shared          20          1,800      0.88    327 ms    486 ms

== done
manifest: measured/ch10/machine.json
```

## What the test asserts

`test ch10` runs the lab, then asserts what the workload sets: the
shared layout's hit rate is above 0.8, the variable-first layout's
is below 0.1, and the shared layout's median TTFT is lower. It also
loads `metrics.om.gz` into Prometheus with `promtool tsdb
create-blocks-from openmetrics`.

## Files

- `prompts.py`: both workloads, the client, the counters.
- In `measured/ch10/`: `workloads.json` (every request's TTFT, the
  hit and query counts, the prompt size) and `metrics.om.gz` (the
  engine's series, one scrape a second, as OpenMetrics text for
  `promtool tsdb create-blocks-from openmetrics`: the hit-rate and
  TTFT panels of the chapter's screenshot replay from it).
