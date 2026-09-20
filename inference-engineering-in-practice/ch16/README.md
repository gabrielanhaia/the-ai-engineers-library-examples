# ch16: autoscaling and a cold start

Chapter 16's lab, on a Kubernetes cluster (kind) that the runner
creates and deletes itself. Two halves (the run does the cold start
first, while the node holds nothing else):

- **Scale on the queue (simulated).** KEDA 2.20.2 scales a pool of
  llm-d-inference-sim v0.11.2 replicas on
  `sum(vllm:num_requests_waiting)`, one replica per 5 waiting
  requests, while open-loop load steps up and back down. The
  simulator's timings are its configuration (`sim.yaml`), including
  the 20 s a new replica takes to report ready, which stands in for
  loading weights; the control loop's steps and their order are
  what carries over.
- **A cold start (laptop).** The real vLLM 0.29.0 CPU container,
  started three times from nothing inside the cluster: the node
  pulls the image, vLLM loads SmolLM2-360M-Instruct and warms up.
  Each start is split into its phases. These are a laptop's CPU
  timings, never a GPU's.

## What it does

1. **Cluster.** kind v0.33.0 (Kubernetes 1.36.4). The weights of
   SmolLM2-360M-Instruct are copied onto the node, so the weight
   load reads a local disk.
2. **Cold start** (`coldstart.yaml`, `coldstart.py`), three times:
   remove the vLLM image from the node, apply the pod, wait for
   `/health`, then send two requests and time each one's first
   token. The phases come from the kubelet (image pull), from the
   container's first log line (start), and from vLLM's own log
   lines (weight load; warm-up, which includes `torch.compile`,
   shown on its own as compile); the rest is the remainder.
3. **Scale on the queue.** KEDA (its release manifest, images
   pinned by digest), a Prometheus that scrapes every ready replica
   every 5 s (`prometheus.yaml`), one simulated replica behind a
   NodePort (`sim.yaml`), and the `ScaledObject`
   (`scaledobject.yaml`). Then the load (`load.py`): 1 request/s
   for 30 s, 4 requests/s for 120 s, 0.5 requests/s for 90 s, each
   request 100 output tokens on a new connection, sent on schedule
   whatever the server does (an open loop). Every 2 s it records
   the queue and running requests (from Prometheus), the replicas
   the HPA wants, the Deployment's replicas, and how many are
   ready: `timeline.csv`, and `timeline.om` for the
   queue-vs-replicas panel. `report.py scaling` prints the timeline
   every 15 s and when each step happened.

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch16
```

Nothing to install on the host: the runner downloads kind and
kubectl once (pinned by SHA-256 in `../tools.env`). The run takes
about 15 minutes, most of it three pulls of the vLLM CPU image
(0.9 GB compressed on arm64, 1.8 GB on x64). It needs about 5 GB of
free memory while vLLM runs inside the cluster. `RUNS=1` in the
environment does one cold start instead of three, and
`PARTS=coldstart` (or `PARTS=scaling`) runs one half of the lab.

## Expected output

Your numbers will differ; the shape will not. Recorded on the
reference laptop (Apple M2 Pro, 16 GB, OrbStack, linux/arm64, CPU
only). This block is
[`../measured/ch16/output.txt`](../measured/ch16/output.txt):

```

== cluster
tools: kind v0.33.0, kubectl v1.36.4
cluster ch16: Kubernetes v1.36.4, node ch16-control-plane

== cold start: vLLM CPU container, 3 runs (laptop)
models: 16 file(s), 953 MiB, into /models
laptop, CPU container; not a GPU cold start (seconds)
run    pull   start weights warm-up compile    rest   total  TTFT 1  TTFT 2
  1   45.91    9.67    1.66   32.26   25.91   17.04  106.55    0.99    0.19
  2   47.92   10.35    2.11   33.66   27.31   17.00  111.03    1.27    0.20
  3   46.35   10.05    2.32   33.92   26.62   15.93  108.57    1.27    0.21
med   46.35   10.05    2.11   33.66   26.62   17.00  108.57    1.27    0.20

== scale on queue depth (load 1:30,4:120,0.5:90), simulated
default prometheus-595fdb8cb7-hd4vl Running
default smollm2-sim-7987dcc858-wxgbb Running
keda keda-admission-576868fbdb-k8bcl Running
keda keda-metrics-apiserver-8d65f7b65-k4mb4 Running
keda keda-operator-77bc47ccb8-xmtnm Running
local-path-storage local-path-provisioner-56c4685b7c-rqvrv Running
simulated: timings are the simulator's configuration
 t (s)  waiting  running  desired  replicas  ready
     0        0        0        0         1      1
    15        0        2        1         1      1
    32        0        2        1         1      1
    47       29        4        4         4      1
    63       61        4        4         4      1
    79       75       10        4         4      4
    94       53       13        4         4      4
   110       40        9        4         4      4
   125       24       11        4         4      4
   140       12       11        4         4      4
   155        0        3        4         4      4
   170        0        1        4         4      4
   188        0        1        3         3      3
   203        0        2        1         1      1
   218        0        1        1         1      1
   234        0        1        1         1      1
   249        0        0        1         1      1
   264        0        0        1         1      1
burst starts              30 s
queue reaches threshold   34 s
replicas raised           45 s
second replica ready      67 s
peak replicas ready       67 s
burst ends                150 s
queue empty again         155 s
replicas lowered          181 s

== done
manifest: measured/ch16/machine.json
```

## What the test asserts

`test ch16` runs the lab with one cold start, then checks events
and orderings, never a timing: the pool scaled out; the queue
crossed the threshold, then the replica count rose, then a second
replica became ready, in that order; the pool scaled back in after
the burst; no request failed before the scale-in (a replica
removed at scale-in may answer 503 to a request the Service still
sent it; the recorded run lost one of 555 that way); every cold
start really pulled the
image, loaded weights and warmed up, and its phases add up to no
more than its total; and the first request after start-up had the
slowest first token.

## Files

- `sim.yaml`, `prometheus.yaml`, `scaledobject.yaml`,
  `coldstart.yaml`: the manifests, which name images by tag;
  `run.sh` applies them with the digests in `../images.env`.
- `load.py`: the open-loop load and the timeline.
- `coldstart.py`: first-token timing and the phase split.
- `report.py`: the tables.
- Output lands in `measured/ch16/`: `scaling.json`,
  `coldstart.json`, and the raw records (`timeline.csv`,
  `requests.jsonl`, `hpa-events.txt`, `coldstart-N.log`). The
  committed cold start was re-recorded on its own
  (`PARTS=coldstart`) on a quiet machine, with its own manifest in
  `machine-coldstart.json`.
