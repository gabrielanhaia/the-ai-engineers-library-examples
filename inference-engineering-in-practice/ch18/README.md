# ch18: release gates, a canary route and alert rules

Chapter 18's listings, each one run. Every gate compares a
candidate serving stack with the current one (the baseline), and
every gate is shown both passing a candidate that changes nothing
and failing one that carries a single injected regression. A gate
that has never failed has not been tested.

## What it does

1. **Quality gate** (`gate.py quality`, then `../ch17/gate.py`).
   Runs chapter 11's task eval (`../ch11/eval.py`, 40 questions,
   greedy) against llama.cpp serving SmolLM2-360M-Instruct F16
   three times: the baseline with chapter 17's chat template, a
   rerun of the same, and a candidate whose template ignores
   `add_generation_prompt` (`broken_template.py`). Each judged
   candidate also answers chapter 17's 40 contract requests
   (`../ch17/verify.py`), and its schema-valid rates must clear
   the floors in `../ch17/thresholds.json`. The gate fails a
   candidate that loses more than 2 correct answers, changes more
   than 10% of the baseline's replies, or falls below a contract
   floor: at temperature 0 on the same weights, a changed reply is
   a changed output, whatever the score says — and an answer no
   caller can parse is not an answer.
2. **Performance gate** (`gate.py performance`). Runs
   `vllm bench serve` at one fixed shape (512 tokens in, 128 out,
   2 requests/s, 60 requests) against a simulated replica
   (llm-d-inference-sim v0.11.2) three times: the baseline (20 ms
   per output token), a rerun, and a slower configuration (26 ms).
   The harness is the one chapter 4 uses, `vllm bench serve`, with
   chapter 3's percentile flags; each run's `request_goodput` and
   `median_tpot_ms` are saved to `perf-<run>.json`, and the gate
   reads those. Goodput counts requests inside the SLO (TTFT under
   1 s, TPOT under 25 ms); the gate fails a candidate below 90% of
   the baseline's goodput, and prints the raw request throughput
   beside it, which is the number that hides the regression.
   **Simulated**: the simulator's timings are its configuration,
   so this proves the gate's logic, not a GPU's speed.
3. **Canary route** (`canary-route.yaml`, `pools.yaml`). A kind
   cluster with the Gateway API v1.5.1 and `InferencePool` v1 CRDs
   validates both files with a server-side dry run, and rejects a
   copy of the route with a negative weight.
4. **Alert rules** (`alerts.yaml`). `promtool check rules`, then
   `promtool test rules alerts-test.yaml`: an Xid 79 fires the
   restart-the-machine alert, an Xid 13 the restart-the-app alert,
   an Xid 43 fires nothing, and a TTFT p99 of about a second pages
   only after 5 minutes.

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch18
```

It needs chapter 11's eval (`../ch11/eval.py`, `../ch11/tasks.json`)
and chapter 17's verifier (`../ch17/verify.py`, `../ch17/cases.py`,
`../ch17/gate.py`, `../ch17/template.jinja`,
`../ch17/thresholds.json`), and the models `smollm2-360m-gguf` and
`hf`, which it downloads once. It took 11 minutes on the reference
laptop.

## Expected output

Recorded on the reference laptop (Apple M2 Pro, 16 GB, OrbStack,
linux/arm64, CPU only). This block is
[`../measured/ch18/output.txt`](../measured/ch18/output.txt):

```

== quality gate: ch11's eval + ch17's verifier, llama.cpp F16
contract check, rerun (chapter 17's requests):
 engine     kind         requests  valid   rate  right tool
 llama.cpp  tool call          20     12   0.60          11
 llama.cpp  json schema        20     20   1.00
contract check, broken-template (chapter 17's requests):
 engine     kind         requests  valid   rate  right tool
 llama.cpp  tool call          20     12   0.60          11
 llama.cpp  json schema        20     20   1.00
first reply, broken template: "assistant\nApollo 11 landed on the Moon on July 20, 1969"
quality gate, candidate: rerun
  ok   correct: 39/40 (baseline 39/40)
  ok   replies unchanged: 100% (need 90%)
  quality gate: PASS
 pass  llama.cpp  tool call     0.60 >= 0.45
 pass  llama.cpp  json schema   1.00 >= 0.90
quality gate, candidate: broken-template
  ok   correct: 38/40 (baseline 39/40)
  FAIL replies unchanged: 0% (need 90%)
  quality gate: FAIL, do not ship
 pass  llama.cpp  tool call     0.60 >= 0.45
 pass  llama.cpp  json schema   1.00 >= 0.90
contract replies changed: 24 of 40, all still valid

== performance gate: vllm bench serve, 512 in / 128 out, simulated
performance gate, candidate: rerun
  ok   goodput: 1.80 req/s, baseline 1.80 (100%, need 90%)
  ok   throughput: 1.80 req/s, baseline 1.80 (not a gate)
  ok   median TPOT: 23.7 ms, baseline 23.9 ms
  performance gate: PASS
performance gate, candidate: slower-config
  FAIL goodput: 0.00 req/s, baseline 1.80 (0%, need 90%)
  ok   throughput: 1.75 req/s, baseline 1.80 (not a gate)
  ok   median TPOT: 30.6 ms, baseline 23.9 ms
  performance gate: FAIL, do not ship

== canary route: validated by the API server (kind)
inferencepool.inference.networking.k8s.io/smollm2-stable created (server dry run)
inferencepool.inference.networking.k8s.io/smollm2-canary created (server dry run)
httproute.gateway.networking.k8s.io/smollm2 created (server dry run)
rejected, as it should be: a route with weight -5

== alert rules: promtool
Checking /scratch/ch18/alerts.yaml
  SUCCESS: 7 rules found

  SUCCESS


== done
{
  "quality": {
    "rerun": "pass",
    "broken-template": "fail"
  },
  "contract_replies_changed": 24,
  "performance": {
    "rerun": "pass",
    "slower-config": "fail"
  },
  "manifests": "valid",
  "alert_rules": "pass"
}
manifest: measured/ch18/machine.json
```

## What the test asserts

`test ch18` runs the lab, then checks each gate's verdicts in
`measured/ch18/gates.json`: the quality gate passes the rerun and
fails the broken template, and chapter 17's verifier ran for both; the performance gate passes the rerun
and fails the slower configuration; the canary route and the pools
validate; the alert rules pass `promtool`.

## Files

- `gate.py`: both gates.
- `broken_template.py`: a chat template, and the copy with its
  generation prompt deleted.
- `canary-route.yaml`, `pools.yaml`: the blue-green route and the
  two pools it splits between.
- `alerts.yaml`, `alerts-test.yaml`: the Xid and SLO alert rules
  and their unit tests.
- Output lands in `measured/ch18/`: `gates.json`, the three eval
  results (`eval-*.json`), the verifier's answers per judged
  candidate (`verify-*/llama.cpp.jsonl`), the three benchmark
  results (`bench-*.json`) and what the performance gate reads
  (`perf-*.json`).
