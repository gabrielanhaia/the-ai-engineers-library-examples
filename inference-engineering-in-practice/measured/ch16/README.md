# measured/ch16

The ch16 lab as recorded on the reference laptop (Apple M2 Pro,
16 GB, OrbStack 29.4.0, linux/arm64, CPU only) on 2026-09-19:

```sh
AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)" \
  docker compose run --rm inference-engineering-in-practice ch16
```

The scale-out is **simulated** (llm-d-inference-sim v0.11.2, KEDA
2.20.2, on kind): the simulator's timings, including its 20 s
start-up, are its configuration (`ch16/sim.yaml`). The cold starts
are the real vLLM 0.29.0 CPU container on this laptop, never a GPU.

The two halves were recorded separately. The scale-out is from
2026-09-19 at 18:27 UTC (`machine.json`); one request of 555
failed with a 503, at t = 196 s, when the scale-in removed a
replica the Service was still sending traffic to. The cold start
was re-recorded at 23:42 UTC with nothing else running
(`PARTS=coldstart`, manifest in `machine-coldstart.json`; VM load
average 1.92 at the start, 3.90 at the end, no other lab
container). The earlier cold start shared the machine with another
lab's vLLM engine during run 3, whose warm-up came out at 84.7 s
against 36.7 s for run 2; the three quiet runs agree within 5%
(106.6, 111.0 and 108.6 s in total), so that caveat is gone.

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
  and the pinned downloads (`tools`), for the scale-out;
  `machine-coldstart.json`: the same for the cold-start recording.
