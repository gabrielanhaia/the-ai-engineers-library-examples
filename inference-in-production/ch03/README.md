# ch03: SLOs for a token stream

Chapter 3's lab, in three parts that run one engine at a time:

1. `llama.sh`: an SLO report and goodput on llama.cpp. Client-side
   TTFT, server-side TTFT, TPOT and ITL at the mean, p50, p90 and
   p99, from a timestamp on every streamed chunk; then attainment
   and goodput at the SLO in `slo.toml`.
2. `vllm.sh`: a request-rate ramp on vLLM's CPU backend, with
   `/metrics` recorded every 5 s for replay into Prometheus and
   Grafana (the chapter's screenshot S3), one scrape kept as the
   chapter prints it, and the two queries in `queries.promql` run on
   the replayed recording.
3. `simulated.sh`: `vllm bench serve` against llm-d-inference-sim
   at rates no laptop could serve. **Simulated**: the simulator runs
   no model, so its latencies are its configuration.

## What it does

**llama.cpp.** SmolLM2-135M-Instruct (Q8_0 GGUF) on llama.cpp
v0.4.1 (build b10964) with 4 slots and half the CPUs (the load
generator runs on the same machine). `load.py` sends streamed chat
requests at Poisson arrivals, open loop, at 1, 2, 3, 4, 6 and 8
requests/s (40 requests per rate; 64 output tokens each, prompts
from `prompts.txt`, prompt caching off), and stamps each chunk with the
client's monotonic clock. `metrics.py` computes, per request:

- client-side TTFT = first chunk with text − send time;
- TPOT = (e2e − TTFT) / (output_tokens − 1), skipped for requests
  with one output token;
- ITL = every gap between consecutive chunks, pooled across
  requests.

Server-side TTFT is llama.cpp's `timings.prompt_ms`: its slot's
prompt work, from the moment a slot takes the request (it does not
include a wait for a free slot). `report.py` prints the table at the
lowest rate. `goodput.py` counts, per rate, the requests that met
BOTH targets in `slo.toml`, and walks the rates upward until the
share falls below the target.

**vLLM.** vLLM 0.29.0's CPU image serving SmolLM2-360M-Instruct
(BF16) with a 1 GiB KV cache; the same `load.py` ramps 0.2 → 1.0
requests/s, one minute per step, while `lib/metrics.py` records
`/metrics` to `vllm-ramp.om.gz`. The recording is rebuilt into a
fresh TSDB with `promtool tsdb create-blocks-from openmetrics`,
served by the pinned Prometheus, and both queries are evaluated
over the ramp.

**Simulated.** llm-d-inference-sim v0.11.2 configured for 80 ms to
the first token and 20 ms per token, up to 2x slower at its 16
concurrent requests, queueing beyond that. `vllm bench serve` sends
200 random requests (256 in, 64 out) at 4, 8 and 16 requests/s with
`--percentile-metrics ttft,tpot,itl,e2el`, `--metric-percentiles
50,90,99` and `--goodput ttft:200 tpot:50`.

## Run it

```sh
docker compose run --rm inference-in-production ch03
```

About 12 minutes on the reference laptop. vLLM's CPU engine uses
about 4 GiB of memory.

## Expected output

Recorded on the reference laptop (Apple M2 Pro, 16 GB, OrbStack,
linux/arm64, CPU only). This block is
[`../measured/ch03/output.txt`](../measured/ch03/output.txt), with
the scrape's bucket lines trimmed (marked):

```

== llama.cpp (build b10964): SmolLM2-135M-Instruct Q8_0, 4 slots
models: 1 file(s), 138 MiB, into /models
  ok      gguf/SmolLM2-135M-Instruct-Q8_0.gguf
llama ready after ~1s

== llama.cpp: 40 requests at 1 requests/s (Poisson)
errors: 0; last chunk at 42.8 s

== llama.cpp: 40 requests at 2 requests/s (Poisson)
errors: 0; last chunk at 21.5 s

== llama.cpp: 40 requests at 3 requests/s (Poisson)
errors: 0; last chunk at 14.4 s

== llama.cpp: 40 requests at 4 requests/s (Poisson)
errors: 0; last chunk at 11 s

== llama.cpp: 40 requests at 6 requests/s (Poisson)
errors: 0; last chunk at 7.4 s

== llama.cpp: 40 requests at 8 requests/s (Poisson)
errors: 0; last chunk at 5.7 s

== SLO report at 1 requests/s
llama.cpp b10964-b29c606e2, SmolLM2-135M Q8_0, 2026-09-19
Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)
ms                 n     mean      p50      p90      p99
TTFT, client      40     41.6     36.7     53.9    107.7
TTFT, server      40     33.6     27.1     47.3    102.9
TPOT              40      4.0      3.4      5.7      9.7
ITL (pooled)    2514      4.0      2.7      4.5     29.5
client - server TTFT: p50 7.0 ms, min 2.5 ms
requests with one token per chunk: 38 of 40

== goodput at the SLO in slo.toml
rate 1.0 req/s: attainment 100%
rate 2.0 req/s: attainment 100%
rate 3.0 req/s: attainment 100%
rate 4.0 req/s: attainment 100%
rate 6.0 req/s: attainment 100%
rate 8.0 req/s: attainment 75%
goodput: 6.0 req/s per replica, at TTFT <= 500 ms and TPOT <= 25 ms for 90% of requests

== vLLM 0.29.0 (CPU): SmolLM2-360M-Instruct, BF16
models: 8 file(s), 693 MiB, into /models
  ok      hf/SmolLM2-360M-Instruct/config.json
  ok      hf/SmolLM2-360M-Instruct/generation_config.json
  ok      hf/SmolLM2-360M-Instruct/merges.txt
  ok      hf/SmolLM2-360M-Instruct/model.safetensors
  ok      hf/SmolLM2-360M-Instruct/special_tokens_map.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer_config.json
  ok      hf/SmolLM2-360M-Instruct/vocab.json
vllm ready after ~55s

== ramp: 0.2,0.4,0.6,0.8,1.0 requests/s, 60 s per step
178 requests, 0 errors

== one scrape, filtered to the TTFT histogram and one counter
vllm:generation_tokens_total{engine="0",model_name="smollm2-360m"} 11392.0
vllm:generation_tokens_created{engine="0",model_name="smollm2-360m"} 1.7898432023697093e+09
[... trimmed ...]
vllm:time_to_first_token_seconds_bucket{engine="0",le="0.1",model_name="smollm2-360m"} 0.0
vllm:time_to_first_token_seconds_bucket{engine="0",le="0.25",model_name="smollm2-360m"} 102.0
vllm:time_to_first_token_seconds_bucket{engine="0",le="0.5",model_name="smollm2-360m"} 167.0
[... trimmed ...]
vllm:time_to_first_token_seconds_bucket{engine="0",le="1.0",model_name="smollm2-360m"} 175.0
vllm:time_to_first_token_seconds_bucket{engine="0",le="2.5",model_name="smollm2-360m"} 178.0
[... trimmed ...]
vllm:time_to_first_token_seconds_bucket{engine="0",le="+Inf",model_name="smollm2-360m"} 178.0
vllm:time_to_first_token_seconds_count{engine="0",model_name="smollm2-360m"} 178.0
vllm:time_to_first_token_seconds_sum{engine="0",model_name="smollm2-360m"} 50.003501176834106
vllm:time_to_first_token_seconds_created{engine="0",model_name="smollm2-360m"} 1.7898432023700442e+09

== replay: the recording into Prometheus, and the two queries
prom ready after ~1s
20 points, max 2250 ms
20 points, max 141 ms

== llm-d-inference-sim v0.11.2 (simulated)
models: 8 file(s), 693 MiB, into /models
  ok      hf/SmolLM2-360M-Instruct/config.json
  ok      hf/SmolLM2-360M-Instruct/generation_config.json
  ok      hf/SmolLM2-360M-Instruct/merges.txt
  ok      hf/SmolLM2-360M-Instruct/model.safetensors
  ok      hf/SmolLM2-360M-Instruct/special_tokens_map.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer_config.json
  ok      hf/SmolLM2-360M-Instruct/vocab.json
sim ready after ~1s

== simulated: vllm bench serve at 4 requests/s
# SIMULATED: llm-d-inference-sim v0.11.2; every latency
# below is the simulator's configuration, not a server.
============ Serving Benchmark Result ============
Successful requests:                     200       
Failed requests:                         0         
Request rate configured (RPS):           4.00      
Benchmark duration (s):                  52.07     
Total input tokens:                      37297     
Total generated tokens:                  12800     
Request throughput (req/s):              3.84      
Request goodput (req/s):                 3.78      
Output token throughput (tok/s):         245.84    
Peak output token throughput (tok/s):    376.00    
Peak concurrent requests:                21.00     
Total token throughput (tok/s):          962.17    
---------------Time to First Token----------------
Mean TTFT (ms):                          139.18    
Median TTFT (ms):                        131.50    
P50 TTFT (ms):                           131.50    
P90 TTFT (ms):                           155.39    
P99 TTFT (ms):                           406.27    
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          35.67     
Median TPOT (ms):                        35.61     
P50 TPOT (ms):                           35.61     
P90 TPOT (ms):                           40.80     
P99 TPOT (ms):                           42.01     
---------------Inter-token Latency----------------
Mean ITL (ms):                           34.57     
Median ITL (ms):                         35.25     
P50 ITL (ms):                            35.25     
P90 ITL (ms):                            42.21     
P99 ITL (ms):                            47.33     
----------------End-to-end Latency----------------
Mean E2EL (ms):                          2386.36   
Median E2EL (ms):                        2370.42   
P50 E2EL (ms):                           2370.42   
P90 E2EL (ms):                           2729.06   
P99 E2EL (ms):                           2857.94   
==================================================

== simulated: vllm bench serve at 8 requests/s
# SIMULATED: llm-d-inference-sim v0.11.2; every latency
# below is the simulator's configuration, not a server.
============ Serving Benchmark Result ============
Successful requests:                     200       
Failed requests:                         0         
Request rate configured (RPS):           8.00      
Benchmark duration (s):                  37.88     
Total input tokens:                      37297     
Total generated tokens:                  12800     
Request throughput (req/s):              5.28      
Request goodput (req/s):                 0.48      
Output token throughput (tok/s):         337.91    
Peak output token throughput (tok/s):    381.00    
Peak concurrent requests:                82.00     
Total token throughput (tok/s):          1322.53   
---------------Time to First Token----------------
Mean TTFT (ms):                          4851.22   
Median TTFT (ms):                        4840.73   
P50 TTFT (ms):                           4840.73   
P90 TTFT (ms):                           8977.80   
P99 TTFT (ms):                           10860.60  
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          42.72     
Median TPOT (ms):                        43.26     
P50 TPOT (ms):                           43.26     
P90 TPOT (ms):                           43.90     
P99 TPOT (ms):                           44.49     
---------------Inter-token Latency----------------
Mean ITL (ms):                           41.41     
Median ITL (ms):                         41.84     
P50 ITL (ms):                            41.84     
P90 ITL (ms):                            48.41     
P99 ITL (ms):                            51.20     
----------------End-to-end Latency----------------
Mean E2EL (ms):                          7542.65   
Median E2EL (ms):                        7561.94   
P50 E2EL (ms):                           7561.94   
P90 E2EL (ms):                           11730.24  
P99 E2EL (ms):                           12938.34  
==================================================

== simulated: vllm bench serve at 16 requests/s
# SIMULATED: llm-d-inference-sim v0.11.2; every latency
# below is the simulator's configuration, not a server.
============ Serving Benchmark Result ============
Successful requests:                     200       
Failed requests:                         0         
Request rate configured (RPS):           16.00     
Benchmark duration (s):                  37.79     
Total input tokens:                      37297     
Total generated tokens:                  12800     
Request throughput (req/s):              5.29      
Request goodput (req/s):                 0.42      
Output token throughput (tok/s):         338.73    
Peak output token throughput (tok/s):    384.00    
Peak concurrent requests:                144.00    
Total token throughput (tok/s):          1325.75   
---------------Time to First Token----------------
Mean TTFT (ms):                          10940.56  
Median TTFT (ms):                        11137.38  
P50 TTFT (ms):                           11137.38  
P90 TTFT (ms):                           20833.45  
P99 TTFT (ms):                           23247.03  
-----Time per Output Token (excl. 1st token)------
Mean TPOT (ms):                          43.39     
Median TPOT (ms):                        43.81     
P50 TPOT (ms):                           43.81     
P90 TPOT (ms):                           44.60     
P99 TPOT (ms):                           45.21     
---------------Inter-token Latency----------------
Mean ITL (ms):                           42.05     
Median ITL (ms):                         42.49     
P50 ITL (ms):                            42.49     
P90 ITL (ms):                            49.17     
P99 ITL (ms):                            51.39     
----------------End-to-end Latency----------------
Mean E2EL (ms):                          13673.89  
Median E2EL (ms):                        13905.48  
P50 E2EL (ms):                           13905.48  
P90 E2EL (ms):                           23620.10  
P99 E2EL (ms):                           25345.70  
==================================================

== simulated: attainment by offered rate (TTFT 200, TPOT 50 ms)
rate 4 req/s: goodput 3.78 of 3.84 completed/s = 99% (simulated)
rate 8 req/s: goodput 0.48 of 5.28 completed/s = 9% (simulated)
rate 16 req/s: goodput 0.42 of 5.29 completed/s = 8% (simulated)

== done
manifest: measured/ch03/machine.json
```

## What the test asserts

`test ch03` runs all three parts on a smaller workload, then checks
invariants, never latencies: every llama.cpp request streamed in
chunks without error; server-side TTFT never exceeds client-side
TTFT for the same request; the report has all four quantities; the
goodput curve has one attainment per offered rate; the scraped
counter carries `_total` and the TTFT histogram has buckets; the
recorded ramp replays and both queries return data; the simulated
results are labeled simulated and report request goodput.

## Files

- `run.sh` runs `llama.sh`, `vllm.sh` and `simulated.sh`.
  `load.py`: the load generator. `metrics.py`: TTFT, TPOT and ITL.
  `report.py`: the table. `goodput.py`: the goodput search.
  `slo.toml`: the SLO. `queries.promql`: the two queries.
  `prompts.txt`: the prompts. `test.sh`: runs, asserts.
- Output lands in `measured/ch03/`: `llama/rate-*.jsonl` (every
  request's chunk times and the server's timings), `report.json`,
  `goodput.json`, `vllm-ramp.jsonl`, `vllm-ramp.om.gz` (the
  recording S3 replays), `vllm-scrape.txt`, `promql.json`,
  `simulated-*.txt` and `simulated-*.json` (labeled simulated), and
  `machine.json`.
