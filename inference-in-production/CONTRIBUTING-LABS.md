# The lab contract

How a chapter lab is built in this directory. Every rule here exists
because the book is printed and cannot be patched: the repository
moves to match the book, never the other way round, and nothing is
printed that has not run here.

## 1. The one command

Every lab runs with the command the book prints, exactly:

```sh
docker compose run --rm inference-in-production chNN
```

`bin/lab` (the runner's entrypoint) turns `chNN` into
`bash chNN/run.sh`, run from inside `chNN/`, saves its stdout to
`measured/chNN/output.txt`, and sets:

| Variable   | Value                                    |
|------------|------------------------------------------|
| `LAB`      | `chNN`                                   |
| `LAB_DIR`  | `/lab/chNN`                              |
| `MEASURED` | `/lab/measured/chNN` (created; committed) |
| `WORK`     | `/lab/.work/chNN` (created; git-ignored) |

Extra arguments after `chNN` are passed to `run.sh`. Other runner
commands: `test chNN`, `list`, `models [SET]`, `models list`,
`clean`, `apple`, `shell [-c CMD]`.

**The kind-based labs (ch14, ch16, ch18) print the same command.**
There is no `make` target and nothing to install on the host: the
entry point is `docker compose run --rm inference-in-production
chNN` (52 characters), and `test chNN` for CI, exactly as for every
other lab. The runner creates the Kubernetes cluster itself (section
4a) and deletes it when the lab ends.

The runner holds bash, Python 3.13 (standard library), curl, jq and
the Docker CLI. It has **no inference engine**: a lab starts the
engines it needs as sibling containers through the mounted Docker
socket, using the helpers below. Never start a second copy of the
runner from a lab, and never `docker compose` from inside it.

## 2. The directory

```
inference-in-production/
  chNN/
    README.md    what it does, how to run, expected output
    run.sh       the lab (starts with `. /lab/lib/lab.sh`)
    test.sh      runs the lab, asserts invariants (CI runs it)
    ...          any file the chapter prints, at the path it prints
  measured/chNN/ what the lab records, with machine.json;
                 committed (see section 7)
  inputs/        cited inputs the calculators use, with URLs
  .work/chNN/    scratch output; git-ignored
```

Directory names are bare (`ch07/`, never `ch07-capacity/`): the
book prints them inside paths the reader copies.

**README.md** has four sections, in this order: *What it does*,
*Run it* (the printed command, first-run cost, how long it takes),
*Expected output* (real output pasted from a run on the reference
laptop, with the machine named, never typed by hand), and *What the
test asserts*. See `ch00/README.md`.

**run.sh** starts with its own path as a comment, then sources the
helpers:

```sh
# ch01/run.sh
. /lab/lib/lab.sh
```

It prints what a reader should see to stdout and writes what it
records (JSON, JSONL, CSV, the raw stream) to `$MEASURED/`, which is
`measured/chNN/`. Anything it throws away goes to `$WORK/`. It ends
with `write_manifest`. It exits non-zero on any failure. It does not
clean up after itself: `lib/lab.sh` removes every container the lab
started, on any exit, including Ctrl-C.

**test.sh** runs `run.sh` (with a smaller workload via environment
variables if the full run is too slow for CI), then asserts on the
files in `$MEASURED/`. A lab is in CI when, and only when, it has a
`test.sh`: the `cpu-labs` job finds it and runs
`docker compose run --rm -T inference-in-production test chNN` on
Linux x64 and Linux arm64.

## 3. Test invariants, never numbers

Tokens per second on a shared CI runner is noise. Assert what the
workload and the algorithm set, never what the hardware sets:

- orderings: Q4_K_M decodes faster than Q8_0, faster than F16;
  perplexity F16 <= Q8_0 <= Q4_K_M;
- thresholds that hold with a wide margin: prefix-cache hit rate
  above 0.8 on the shared-prefix workload;
- events: preemptions > 0 above the predicted concurrency, and 0
  well below it;
- shapes: the stream arrived in chunks; `timings` is present; a
  report file exists and parses.

Print each assertion as it passes (`ok  ...`) and fail with
`die "reason"`. A MEASURED number the book prints comes from
`measured/chNN/`, recorded once on the reference laptop, and is
never asserted by `test.sh`.

CI budget per lab: GitHub's standard runners give 4 CPUs, 16 GB RAM
and 14 GB of disk for a public repository (2 CPUs and 8 GB while it
is private), no GPU. Keep a test under 15 minutes and within one
vLLM engine at a time.

## 4. Engines and tools: the helpers in lib/lab.sh

| Helper | Does |
|---|---|
| `need_models SET...` | download once, verify SHA-256 |
| `start_llama NAME FLAGS...` | llama-server at `http://NAME:8080` |
| `start_vllm NAME MODEL FLAGS...` | `vllm serve` at `http://NAME:8000` |
| `run_tool IMAGE [OPTS --] ARGS...` | one-shot container, output to you |
| `wait_ready NAME URL [SECS]` | poll until 200; logs + fail if it dies |
| `server_logs NAME` | the server's log so far |
| `stop_server NAME` | remove one server early |
| `write_manifest [FILE]` | machine.json for `measured/` |
| `step TEXT`, `die TEXT` | a section header; fail with a reason |

The names you give servers are their host names on the lab network
(`aiel-inference`). Use `llama` and `vllm` when you can: the
`screens` Prometheus scrapes `llama:8080` and `vllm:8000`.

Engine notes, verified at the pins (docs/versions.md):

- **llama.cpp.** The image's entrypoint is `llama-server`, so
  `start_llama` takes only its flags. The benchmark tools are in the
  same image behind a multi-call binary:
  `run_tool "$LLAMA_CPP_IMAGE" --entrypoint /app/llama -- bench ...`
  (also `perplexity`, `quantize`, `batched-bench`). There is no
  `llama-bench` binary in this image. `--metrics` is off by default.
- **vLLM CPU.** The KV cache size is `VLLM_CPU_KVCACHE_SPACE` in GiB
  (`start_vllm` defaults it to 1; set it in the environment of the
  call). Startup took 25 to 75 s on the reference laptop: use
  `wait_ready vllm http://vllm:8000/health 600`. On CPU, 0.29.0 runs
  the V1 model runner (Model Runner V2 needs Triton). Scraped
  counters end in `_total`: copy every metric name from a live
  `curl http://vllm:8000/metrics`, never from the docs. For tools
  inside the image: `run_tool "$VLLM_CPU_IMAGE" --entrypoint vllm --
  bench serve ...` or `... -- run-batch ...`.
- **GuideLLM 0.7.4.** `run_tool "$GUIDELLM_IMAGE" --entrypoint
  guidellm -- run ...`. The subcommand is `run`, not `benchmark`,
  and its options take `kind=...` specs.
- **One engine at a time.** vLLM with SmolLM2-360M and a 1 GiB cache
  uses about 3.9 GiB. Do not run two vLLM engines in one lab.

Images come only from `images.env`, pinned by tag and digest. To add
one, resolve its digest (`docker buildx imagetools inspect`), add it
there, and add a row to `docs/versions.md`; CI fails on a digest that
is not written down.

## 4a. Kubernetes labs: the helpers in lib/kind.sh

A kind lab sources `lib/kind.sh` after `lib/lab.sh`. kind runs inside
the runner and creates the cluster's node as a sibling container on
the host's Docker, like any engine; the node joins the lab network,
so the lab reaches a NodePort at `http://chNN-control-plane:PORT`
and the API server at `chNN-control-plane:6443`.

| Helper | Does |
|---|---|
| `kind_tools [istioctl]` | kind, kubectl (and istioctl) onto PATH |
| `start_kind NAME [CONFIG]` | a one-node cluster; exports KUBECONFIG |
| `stop_kind NAME` | delete one cluster early (free memory) |
| `apply_pinned NAME` | apply an upstream manifest `tools.env` pins |
| `install_istio` | Istio, minimal profile, inference extension on |
| `install_keda` | KEDA, its images swapped for the pinned digests |
| `pin_images` | stdin to stdout, `image: REPO:TAG` made `@sha256:` |
| `pod_metrics NS POD [PORT]` | a pod's `/metrics`, via the API server |

- **Pins.** The binaries the runner image lacks (kind, kubectl,
  istioctl) and the upstream manifests (Gateway API, Inference
  Extension and llm-d-router CRDs, KEDA) are pinned by URL and
  SHA-256 in `tools.env` (`NAME=URL@sha256:HEX`) and downloaded once
  into `.work/tools/`; `scripts/check_pins.py` reads `tools.env` too.
  Images come from `images.env` as usual. Manifests the book prints
  name images by tag; apply them through `pin_images`.
- **Name the cluster after the lab** (`start_kind ch14`): its node
  is then `ch14-control-plane`, and `clean` removes leftover nodes of
  clusters named `chNN`. `start_kind` deletes a same-named cluster
  first, and the lab's exit deletes it (`AIEL_KEEP=1` keeps it).
- **Memory.** A node with the ch14 stack (Istio, one endpoint picker,
  three simulators) peaked at 1.1 GiB; a vLLM CPU pod adds about
  4 GiB. Delete the cluster (`stop_kind`) before starting a vLLM
  engine beside it.
- **Simulated.** Anything llm-d-inference-sim produces is labeled
  "simulated" in every file: its timings are its configuration.

## 5. Models

The model cache is the `aiel-models` volume: read-write at `/models`
in the runner, read-only at `/models` in every server and tool.

```
/models/gguf/SmolLM2-{135M,360M}-Instruct-{f16,Q8_0,Q4_K_M}.gguf
/models/hf/SmolLM2-{135M,360M}-Instruct/      (vLLM, BF16)
/models/hf/Qwen3.5-0.8B/                      (set qwen35)
/models/lora/smollm2-360m-{alpaca,underdog}/  (set lora)
```

Call `need_models SET` before you use a model; it is a no-op when the
files are already there and verified. Sets: `smoke`, `gguf`, `hf`,
`lora`, `qwen35`, `all` (`models list` shows sizes). To add a model:
ungated, Apache-2.0 or MIT only; add it to `models.lock.json` with
its commit SHA, run `scripts/fetch_models.py relock`, and add a row
to `docs/versions.md`.

Files a server must read (a chat template, a config) go in
`/scratch`, the `aiel-scratch` volume shared by the runner and every
container a lab starts. Bind mounts of `/lab` paths do not work for
sibling containers: the Docker daemon resolves host paths, not the
runner's.

## 6. What the book prints

- **70 characters per line**, for every file the book prints. A
  printed file announces itself with its own path as its first line
  (after a shebang, if any): `# ch07/capacity.py`, `// ...` or
  `-- ...`. `scripts/check_printed.py` (CI `lint`) checks that the
  header matches the real path and that no line is over 70.
- **Byte-identical.** Every file a chapter prints is the same file,
  byte for byte, in the book and here. The manuscript is not in this
  repository; run the cross-check against it before a chapter is
  called done:
  `scripts/check_printed.py --manuscript <book>/en/content/chapters`.
- **Paths the book prints resolve here.** If the book and the repo
  disagree about a path, the repo moves.
- **Commands the book prints are the repo's real commands**: the one
  command above, `test chNN`, `models ...`.
- Code only, English only (comments too). No manuscript prose, and no
  key in any file or recorded output.

## 7. measured/chNN: committed, and the source of what is printed

`measured/chNN/` is where a lab writes what it records, and it is
committed. The book copies every MEASURED number, every figure's
data and every expected-output block from these files, never from a
terminal. It holds:

- `output.txt`: the lab's stdout, which `bin/lab` saves on every
  `chNN` run; the lab README's *Expected output* block is this file;
- the raw outputs the lab wrote (JSON, CSV, the stream, the
  benchmark report), as written, never edited by hand;
- `machine.json` from `write_manifest`: the date, the Docker host,
  every image digest and every model revision. The container cannot
  see the host's CPU model, so record with it set:
  `AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64
  VM)" docker compose run --rm inference-in-production chNN`;
- a `README.md` naming the command and the date (see
  `measured/ch00/`).

The committed copy is the reference laptop's run. Every run
rewrites it (CI's, a reader's, yours), so re-record on the reference
laptop and commit when the lab changes, and paste the lab README's
*Expected output* from that same run. Scratch output goes to
`$WORK/` (`.work/chNN/`, ignored), never to `measured/`. An ad-hoc
run (`shell -c` with `LAB` not `chNN`) records into `$WORK/`.

**DERIVED numbers** (arithmetic on cited inputs: the calculators,
roofline bounds) are recomputed, not measured, so CI checks them
exactly. Every cited input lives in `inputs/`, each TOML table with
its `url` and `checked` date (see `inputs/README.md`). A lab whose
chapter prints DERIVED numbers adds `chNN/derived.py`, which prints
JSON `{"chapter": "NN", "outputs": {calculator: its default stdout},
"numbers": [{"key", "value", "shown"}]}`, where `shown` is the
string the chapter prints; `run.sh` records it as
`measured/chNN/derived.json`. The `derived-data` CI job
(`scripts/check_derived.py`) reruns every `derived.py` and fails on
any difference from the record; with `--manuscript <book>/en/content/
chapters` it also finds every `shown` string in its chapter.

## 8. Pitfalls already hit

- `set -o pipefail` is on. `cmd | head -n 5` makes `cmd` die of
  SIGPIPE and fails the whole lab: write to a file and `head` that.
- A lab that crashed outside the trap (a killed Docker daemon) can
  leave containers behind: `docker compose run --rm
  inference-in-production clean` removes every container labelled
  `aiel.lab`.
- After changing `Dockerfile` or `requirements.txt`, rebuild the
  runner: `docker compose build inference-in-production`.
- The kind labs run in the `cpu-labs` CI job like every other lab
  (`test chNN`); there is no separate `k8s-labs` job, because the
  runner brings its own kind.
- `cmd | grep -q PATTERN` fails under pipefail as soon as grep finds
  a match early (SIGPIPE upstream): grep a file instead.
- A Kubernetes Service named `vllm` puts `VLLM_PORT=tcp://...` into
  every pod started after it, and vLLM reads `VLLM_PORT` as its own
  setting and exits. Set `enableServiceLinks: false` on vLLM pods.
- KEDA's Prometheus scaler refuses a query that returns more than
  one series: scale on `sum(vllm:num_requests_waiting)`, never on
  the bare per-replica metric.
