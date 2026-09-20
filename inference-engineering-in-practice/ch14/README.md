# ch14: routing for the cache, the tenant and the adapter

Chapter 14's lab, on a Kubernetes cluster (kind) that the runner
creates and deletes itself. The serving path is the one the chapter
draws: a Gateway (Istio 1.30.4) routes to an `InferencePool`
(Gateway API Inference Extension v1.6.2), whose endpoint picker
(llm-d-router v0.10.0) chooses a replica for every request. The
replicas are three llm-d-inference-sim v0.11.2 simulators, so every
routing number here is **simulated**: the simulator's timings are
its configuration (`sim.yaml`), and only the hit rates and the
ordering of latencies carry over. The multi-LoRA step uses the real
vLLM CPU engine.

## What it does

1. **Multi-LoRA (real engine), first**, while the machine holds
   nothing else: serves SmolLM2-360M-Instruct with two public LoRA
   adapters on vLLM 0.29.0's CPU backend (`lora.py`): the same
   prompt to the base model and each adapter, then four requests
   per adapter at once, with `--max-loras 1` and again with
   `--max-loras 2`.
2. **Cluster.** kind v0.33.0 (Kubernetes 1.36.4); the Gateway API,
   `InferencePool` and llm-d-router CRDs; Istio with the inference
   extension on; the simulators (`sim.yaml`), the endpoint picker
   (`epp.yaml`, configured by `epp-config.yaml`), the pool
   (`inferencepool.yaml`), the Gateway (`gateway.yaml`) and two
   traffic classes (`objectives.yaml`).
3. **Round-robin vs prefix-aware.** The same multi-turn traffic
   (`traffic.py conversations`: 12 conversations, each with its own
   400-word context, 6 turns, 6 at a time) twice through the
   gateway: first with `route-rr.yaml` (the route's backend is a
   plain Service, round-robin), then with `route.yaml` (the backend
   is the pool). The replicas restart in between, so each policy
   starts with empty caches. Records each replica's prefix-cache
   hits and queries, which replica served each turn, and TTFT.
4. **Priority under a flood.** 36 concurrent requests in the
   `batch` class (priority -10) keep the pool saturated while a
   probe arrives every second; once with the probes in the
   `interactive` class (priority 100), once in `batch`. The
   endpoint picker's flow control holds the overflow and dispatches
   by priority. Records every request's TTFT and the picker's
   queue depth.

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch14
```

Nothing to install on the host: the runner downloads kind, kubectl
and istioctl once (pinned by SHA-256 in `../tools.env`). The first
run also pulls the kind node image and the cluster's images (about
1 GB) and the lab models; after that it takes about 7 minutes. It
needs about 4 GB of free memory for the vLLM step, which runs
before the cluster exists. `PARTS=lora` (or `PARTS=routing`) runs
one part of the lab: the real-engine multi-LoRA step, or the
simulated routing and priority steps on the cluster. A part run on
its own writes only its own files, so the multi-LoRA step can be
re-recorded on a quiet machine without disturbing the simulated
records; `PARTS=lora` writes its manifest to `machine-lora.json`.

## Expected output

Your numbers will differ; the shape will not. Recorded on the
reference laptop (Apple M2 Pro, 16 GB, OrbStack, linux/arm64, CPU
only). This block is
[`../measured/ch14/output.txt`](../measured/ch14/output.txt):

```

== multi-LoRA on vLLM CPU (real engine, not simulated)
models: 20 file(s), 973 MiB, into /models
vllm ready after ~24s
vllm ready after ~23s
same prompt, temperature 0:
smollm2-360m: One tip for staying focused is to eliminate
  distractions. This can be achieved by turning off notifications on
  your phone, closing unnecessary
alpaca: One tip for staying focused is to eliminate distractions and
  create a conducive environment for concentration. This can be
  achieved by turning off
underdog: Avoid multitasking, as it can decrease productivity and
  increase distractions.
burst: 8 requests, 64 tokens each; seconds to finish
--max-loras 1: alpaca 10.2-10.4  underdog 20.5-20.6
--max-loras 2: alpaca 12.2-12.3  underdog 12.2-12.3

== cluster
tools: kind v0.33.0, kubectl v1.36.4, istioctl 1.30.4
cluster ch14: Kubernetes v1.36.4, node ch14-control-plane
inference-gateway-istio-846748678b-kpgvd 0/1 Running
smollm2-epp-8696f7d6b9-9lzvs 1/1 Running
smollm2-sim-78675cbcbb-bxnlm 1/1 Running
smollm2-sim-78675cbcbb-nn9zc 1/1 Running
smollm2-sim-78675cbcbb-wxddg 1/1 Running

== round-robin (route-rr.yaml), simulated

== prefix-aware (route.yaml), simulated
simulated: timings are the simulator's configuration
policy        replica hit rates        all   same  TTFT p50
round-robin   0.56 0.53 0.51          0.53   0.40    0.185s
prefix-aware  0.77 0.77 0.77          0.77   1.00    0.110s

== priority classes under a flood, simulated
simulated: timings are the simulator's configuration
run                   class      n  TTFT p50     p95  errors
no flood              probe     10    0.062s  0.071s       0
flood, probes 100     probe     20    1.212s  2.064s       0
flood, probes 100     flood    121    8.504s 10.725s       0
flood, probes -10     probe     20    7.715s  9.621s       0
flood, probes -10     flood    163    6.425s 10.516s       0
peak EPP queue, priority -10: 28 and 37

== done
manifest: measured/ch14/machine.json
```

## What the test asserts

`test ch14` runs the lab, then checks what the routing policy, the
priority classes and the adapter slots decide, never a timing:
prefix-aware routing beats round-robin on the replicas' aggregate
prefix-cache hit rate by more than 0.1; it keeps at least 90% of
turns on the replica that served the conversation's previous turn,
where round-robin keeps fewer than 60%; under the flood, the
priority-100 probes' median TTFT is less than half the priority -10
probes'; the flood queued in the endpoint picker; no request
failed; each adapter answers the same prompt differently from the
base model; and with one adapter slot the two adapters' requests
finish in two separate groups, with two slots together. It also
checks that `replicas.om` holds samples.

## Files

- `sim.yaml`, `epp.yaml`, `epp-config.yaml`, `inferencepool.yaml`,
  `gateway.yaml`, `route.yaml`, `route-rr.yaml`, `objectives.yaml`:
  the manifests, which name images by tag; `run.sh` applies them
  with the digests in `../images.env`.
- `traffic.py`: the conversations and the priority flood.
- `lora.py`: the multi-LoRA step.
- `report.py`: the tables, and `replicas.om` (the replicas'
  counters every 2 s, OpenMetrics, for the per-replica hit-rate
  panel).
- Output lands in `measured/ch14/`: `routing.json`,
  `priority.json`, `lora.json` and the raw records they come from.
