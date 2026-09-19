# measured/ch16

The ch16 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-in-production ch16
```

The scale-out is **simulated** (llm-d-inference-sim v0.11.2, KEDA
2.20.2, on kind): the simulator's timings, including its 20 s
start-up, are its configuration (`ch16/sim.yaml`). The cold starts
are the real vLLM 0.29.0 CPU container on this laptop, never a GPU.

Two things about this recording. The machine was shared with other
labs: runs 1 and 2 of the cold start had it nearly to themselves,
but another lab's vLLM engine started during run 3 (the VM's swap
grew from 0.4 to 2.7 GB), so run 3's warm-up (84.7 s) is inflated.
And one request of 555 failed with a 503, at t = 196 s, when the
scale-in removed a replica the Service was still sending traffic to.

- `timeline.csv`: every ~2 s, the queue and running requests (from
  Prometheus), the HPA's desired replicas, the Deployment's replicas
  and how many were ready; `timeline.om`, the same as OpenMetrics.
- `requests.jsonl`: one line per request: send time, load phase,
  status, TTFT, end-to-end.
- `hpa-events.txt`: the HPA's rescale events.
- `scaling.json`: when each step of the scale-out happened.
- `coldstart.jsonl`, `coldstart.json`: each run's phases (seconds)
  and their medians; `coldstart-N.log`: each run's vLLM log with
  timestamps, from which the weight-load and warm-up phases come.
- `machine.json`: the Docker host, image digests, model revisions,
  and the pinned downloads (`tools`).
