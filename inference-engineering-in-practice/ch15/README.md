# ch15: wire it

Chapter 15's lab: the serving layer's signals, end to end, on the
laptop. vLLM's CPU backend exports its metrics to Prometheus, which
records the series the chapter's panels read and evaluates the
alerts; Grafana draws vLLM's own dashboards; and the engine sends
its request spans over OTLP to an OpenTelemetry Collector, the
first hop of Vol. 1's trace stack.

## What it does

1. Copies the configs into the shared volume and fetches vLLM's
   three Grafana dashboards from the v0.29.0 tag, each pinned by
   SHA-256 in `tools.env`.
2. `promtool check config prometheus.yml`, then `promtool test rules
   rules-test.yml`: synthetic series in, expected values and alerts
   out, for `rules.yml`, `alerts.yml` and `cost.yml`.
3. Starts the collector (OpenTelemetry Collector contrib 0.161.0,
   `otel-collector.yml`: an OTLP gRPC receiver and a file exporter),
   then vLLM 0.29.0 with `--otlp-traces-endpoint
   grpc://ch15-otel:4317` and `OTEL_SERVICE_NAME=vllm`, then
   Prometheus 3.14.0 (scraping every 5 s, evaluating the rules as
   often) and Grafana 13.2.2 (vLLM's dashboards provisioned).
4. Sends 48 requests sharing a 256-token prefix (`vllm bench serve`,
   concurrency 4), so the hit-rate rule has something to count.
5. Prints the target's `up`, every recorded series' current value,
   and the state of every alert; runs every panel of vLLM's
   dashboards against Prometheus (`panels.py`) and counts the
   panels that draw data; counts the spans the collector wrote, by
   name, and prints the attributes of one request span
   (`spans.py`). vLLM sends one `llm_request` span per request,
   with its latencies and token counts as `gen_ai.*` attributes,
   and a span for each step of its own start-up.

The rules:

- `rules.yml`: TTFT and ITL p99 over 5 minutes, the prefix-cache hit
  ratio over 5 minutes and an hour, the preemption rate, the
  generation-token rate, and the SLIs the burn-rate alerts read
  (the share of first tokens over 1 s, of token gaps over 100 ms,
  both bucket bounds vLLM exports).
- `alerts.yml`: Vol. 1's multi-window burn rate on those SLIs (14.4
  times a 1% budget over both 1 h and 5 m), the KV cache full while
  the engine preempts, and a prefix hit rate at half of the last
  hour's.
- `cost.yml`: $ per million output tokens as a fleet quantity, the
  serving units' price per hour over the output tokens they made.
  Its unit test feeds it chapter 5's cited rate (89,856.3 output
  tok/s on one 8 × B200 node at $57.20 an hour) and expects
  chapter 5's $0.1768. It is deliberately not loaded into the
  laptop's Prometheus: a laptop's tokens times a GPU's price is not
  a number anyone should see.

In the recorded run the laptop missed a GPU-sized TTFT target of
1 s on 14.6% of requests, more than the 14.4% a 99% SLO's fast burn
allows, so the TTFT burn-rate alert fired. It proves the wiring,
not the laptop's speed: on a busier or quieter laptop the alert
may or may not fire, and the test does not assert either. vLLM's dashboards have
no panel for the prefix-cache hit rate or for preemptions, the two
serving signals chapters 9 and 10 lean on; `rules.yml` records
both.

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch15
```

It downloads the `smollm2-360m-hf` model (693 MiB) and pulls the
OpenTelemetry Collector image once. The run takes about 3 minutes
on the reference laptop.
With `AIEL_KEEP=1` the containers stay up afterwards; Grafana is
then at `http://ch15-grafana:3000` on the lab network.

## Expected output

Recorded on the reference laptop (Apple M2 Pro, 16 GB, OrbStack,
linux/arm64, CPU only). This block is
[`../measured/ch15/output.txt`](../measured/ch15/output.txt):

```text

== config into the shared volume
grafana.json
performance_statistics.json
query_statistics.json

== promtool: check the config, then unit-test the rules
Checking prometheus.yml
  SUCCESS: 2 rule files found
 SUCCESS: prometheus.yml is valid prometheus config file syntax

Checking rules.yml
  SUCCESS: 10 rules found

Checking alerts.yml
  SUCCESS: 4 rules found

Checking cost.yml
  SUCCESS: 2 rules found

  SUCCESS


== the collector, then vLLM with its traces pointed at it
ch15-otel ready after ~1s
models: 8 file(s), 693 MiB, into /models
  ok      hf/SmolLM2-360M-Instruct/config.json
  ok      hf/SmolLM2-360M-Instruct/generation_config.json
  ok      hf/SmolLM2-360M-Instruct/merges.txt
  ok      hf/SmolLM2-360M-Instruct/model.safetensors
  ok      hf/SmolLM2-360M-Instruct/special_tokens_map.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer_config.json
  ok      hf/SmolLM2-360M-Instruct/vocab.json
ch15-vllm ready after ~59s

== Prometheus and Grafana
ch15-prom ready after ~1s
ch15-grafana ready after ~7s

== traffic: 48 requests sharing a 256-token prefix

== Prometheus: the target, the recorded series, the alerts
up 1
vllm:ttft_seconds:p99_5m                2.397
vllm:itl_seconds:p99_5m                 0.277
vllm:prefix_cache_hit_ratio:rate5m      0.653
vllm:prefix_cache_hit_ratio:rate1h      0.653
vllm:preemptions:rate5m                 0.000
vllm:generation_tokens:rate5m           5.346
vllm:ttft_slow:ratio_rate5m             0.146
vllm:ttft_slow:ratio_rate1h             0.146
vllm:itl_slow:ratio_rate5m              0.036
vllm:itl_slow:ratio_rate1h              0.036
firing  TTFTBudgetBurn

== Grafana: vLLM's dashboards, panel by panel
 dashboard                 panels  with data
 Performance Statistics        16         16
 Query Statistics_New4         14         14
 vLLM                          12         12

== traces
spans received: 61, service.name vllm
    48  llm_request
     2  Worker init
     1  Initialize model
     1  Load weights
     1  Load model
     1  Loading (CPU)
     1  Executor init
     1  Prepare model
     1  AsyncMPClient init
     1  Overall Loading
     1  Warmup (CPU)
     1  Allocate KV cache
     1  EngineCoreProc init
one llm_request span:
  gen_ai.latency.e2e                       1.976
  gen_ai.latency.time_in_model_decode      0.654
  gen_ai.latency.time_in_model_inference   1.935
  gen_ai.latency.time_in_model_prefill     1.281
  gen_ai.latency.time_in_queue             0.001
  gen_ai.latency.time_to_first_token       1.325
  gen_ai.request.id                        cmpl-bench-00871b8e-0-0
  gen_ai.request.max_tokens                32
  gen_ai.request.n                         1
  gen_ai.request.temperature               1
  gen_ai.request.top_p                     1
  gen_ai.usage.completion_tokens           32
  gen_ai.usage.prompt_tokens               384

== done
manifest: measured/ch15/machine.json
```

## What the test asserts

`test ch15` runs the lab, then asserts the wiring: `promtool test
rules` reports SUCCESS; every raw metric name the three rule files
read is in the live scrape (`measured/ch15/metrics.txt`), so none
was copied from docs; the hit-ratio series was recorded; all three
of vLLM's dashboards load and each draws data; and spans from
`service.name` `vllm` reached the collector.

## Files

- `prometheus.yml`, `rules.yml`, `alerts.yml`, `cost.yml`,
  `rules-test.yml`: the Prometheus side.
- `grafana/datasource.yml`, `grafana/dashboards.yml`: Grafana's
  provisioning.
- `otel-collector.yml`: the trace bridge.
- `panels.py`, `spans.py`: the checks.
- In `measured/ch15/`: `promtool.txt`, `metrics.txt` (one live
  scrape), `recorded.txt`, `alerts.json`, `panels.json` and
  `spans.jsonl` (what the collector wrote, OTLP JSON).
