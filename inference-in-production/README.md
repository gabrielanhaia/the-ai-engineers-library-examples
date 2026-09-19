# Inference in Production — labs

The labs for *Inference in Production* (The AI Engineer's Library, Volume 3).

**Status:** not published yet. The labs land here as the chapters are drafted; each one states
the hardware it needs, how to run it, and the output you should expect.

Every lab runs on a laptop without a GPU, and the book prints no GPU measurement of its own.
Where a chapter needs a number only a datacenter GPU can show, it cites a published figure
(MLPerf, a paper, or a vendor's labeled claim) instead.

## Run a lab

You need Docker with Compose v2 (Docker Desktop, OrbStack, or Docker Engine on Linux), on x86-64
or ARM64, and about 10 GB of free disk for the images and models. From the repository root:

```sh
docker compose run --rm inference-in-production ch00
```

`ch00` is a smoke test: it downloads the smallest lab model (138 MiB), starts llama.cpp, streams
one request and prints the server's timings. If it passes, every lab's plumbing works on your
machine. Replace `ch00` with any chapter's lab. Other commands:

```sh
docker compose run --rm inference-in-production list        # labs present
docker compose run --rm inference-in-production models list # model sets
docker compose run --rm inference-in-production test ch00   # what CI runs
docker compose run --rm inference-in-production clean       # leftovers
```

The command starts a small runner container; the runner starts the engine each lab needs
(llama.cpp, vLLM's CPU build, GuideLLM) as a separate container from a pinned image, and removes it
when the lab ends. Models download once into a Docker volume (`aiel-models`) and are checked
against their SHA-256.

## Profiles

| Profile | What | Command |
|---|---|---|
| `cpu` (default) | every lab, on the CPU | `docker compose run --rm inference-in-production chNN` |
| `apple` | llama.cpp on the Metal GPU, natively (containers cannot reach Metal) | `docker compose run --rm apple` prints the steps; see [apple/README.md](apple/README.md) |
| `screens` | Prometheus + Grafana, scraping the running lab's servers | `docker compose --profile screens up -d` (Prometheus on `127.0.0.1:9090`, Grafana on `127.0.0.1:3000`) |

There is no GPU profile: nothing here needs a GPU.

## Labs

| Dir | Lab | Needs |
|---|---|---|
| [`ch00/`](ch00/) | Smoke test: model cache, llama.cpp, one streamed request, the server's timings | any laptop |
| [`ch05/`](ch05/) | Cost calculator: $ per million output tokens from MLPerf's row and a dated price, with its three labels; your own request shape | any laptop (no model) |
| [`ch06/`](ch06/) | Break-even calculator: self-host vs API per request, three scenarios | any laptop (no model) |
| [`ch07/`](ch07/) | Capacity calculator: fit at 0.92, running batch by Little's law, KV needed, GPUs by throughput with headroom | any laptop (no model) |
| [`ch13/`](ch13/) | Layout calculator: KV copies under TP, the KV freed by TP=2, the P:D ratio | any laptop (no model) |
| [`ch14/`](ch14/) | Routing on kind: Istio Gateway, `InferencePool`, llm-d-router's endpoint picker, three simulated replicas; round-robin vs prefix-aware, priority classes under a flood, multi-LoRA on vLLM CPU | ~5 GB free memory; nothing installed on the host |
| [`ch16/`](ch16/) | KEDA scaling a simulated pool on queue depth; three phase-by-phase cold starts of the vLLM CPU container | ~5 GB free memory |
| [`ch18/`](ch18/) | Release gates proven to fail (quality: ch11's eval vs a broken chat template; performance: `vllm bench serve` vs a slower simulator), a canary route, Xid and SLO alert rules | any laptop |
| [`ch19/`](ch19/) | The decision worksheet: two worked plans on the ch05–ch07 calculators | any laptop (no model) |

## Where things are

- [`images.env`](images.env): the engine images, pinned by digest.
- [`models.lock.json`](models.lock.json): the lab models, pinned by commit SHA, with sizes and hashes.
- [`inputs/`](inputs/): every cited number the calculators use, with its URL and check date.
- [`../docs/versions.md`](../docs/versions.md): every pin, why, and when it was verified.
- [`CONTRIBUTING-LABS.md`](CONTRIBUTING-LABS.md): how a lab is built.
