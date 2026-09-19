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

## Where things are

- [`images.env`](images.env): the engine images, pinned by digest.
- [`models.lock.json`](models.lock.json): the lab models, pinned by commit SHA, with sizes and hashes.
- [`../docs/versions.md`](../docs/versions.md): every pin, why, and when it was verified.
- [`CONTRIBUTING-LABS.md`](CONTRIBUTING-LABS.md): how a lab is built.
