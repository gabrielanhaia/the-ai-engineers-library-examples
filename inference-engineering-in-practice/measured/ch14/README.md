# measured/ch14

The ch14 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-engineering-in-practice ch14
```

Everything from the routing and priority steps is **simulated**
(llm-d-inference-sim v0.11.2 behind Istio 1.30.4 and llm-d-router
v0.10.0's endpoint picker, on kind): the simulator's timings are its
configuration (`ch14/sim.yaml`). The multi-LoRA step ran the real
vLLM 0.29.0 CPU engine, first, with the machine to itself; another
lab's vLLM engine shared the machine during the routing and
priority steps.

- `routing.json`: per-replica and aggregate prefix-cache hit rate,
  the share of turns served by the previous turn's replica, and
  TTFT, round-robin vs prefix-aware (simulated).
- `replicas-rr.json`, `replicas-pa.json`: each replica's
  `vllm:prefix_cache_hits_total` and `..._queries_total` at the end
  of each policy's run.
- `conversations-rr.jsonl`, `conversations-pa.jsonl`: one line per
  request: conversation, turn, serving replica, TTFT, end-to-end.
- `replicas.om`: the replicas' two counters every 2 s, both
  policies, as OpenMetrics (for the per-replica hit-rate panel).
- `priority.json`, `priority-{idle,interactive,batch}.jsonl`,
  `queue-{interactive,batch}.txt`: the probes and the flood, and the
  endpoint picker's flow-control queue every second (simulated).
- `lora.json`, `lora-max1.json`, `lora-max2.json`: the multi-LoRA
  step, and every `vllm:lora_requests_info` label pair it saw.
- `machine.json`: the Docker host, image digests, model revisions,
  and the pinned downloads (`tools`).
