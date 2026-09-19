# Versions

Every pinned dependency, why it is pinned there, and when the pin was last verified against the
upstream release. An undated pin is not a pin. `inference-in-production/scripts/check_pins.py` fails
CI if the repository uses a digest, package version or model revision that is not written here.

Images are pinned by tag **and** digest; the digest is the pin, the tag is for humans. The lab
images live in [`inference-in-production/images.env`](../inference-in-production/images.env), the
model revisions in [`inference-in-production/models.lock.json`](../inference-in-production/models.lock.json).

## Inference in Production — images and tools

All verified 2026-09-19 against the registry (digest resolved with `docker buildx imagetools
inspect` or the registry API) and the upstream release page.

| Component | Pin | Used by | Why this version | Last verified |
|---|---|---|---|---|
| llama.cpp server image | `ghcr.io/ggml-org/llama.cpp:server-v0.4.1@sha256:283ed1799f2711361dadd863305ffe31c9fca3321a099712a8cc65061502b523` (arm64 `sha256:e90d05d99945a0292be6423d62ba278cc81b8a77a6d27e939c23707cb4c29864`, amd64 `sha256:66fa257bac8323663bc9f3380149b85c8e0a67e56259ee8e619e6936a7b3fe96`) | ch00 and every llama.cpp lab | v0.4.1 is the latest semver-stable llama.cpp (2026-09-14), the version the prose quotes. The project maps it to build **b10964** (commit `b29c606e2`): the v0.4.1 release's only asset, `nightly-tag.txt`, reads `b10964`, and the image reports `version: 0.4.1-dev (build 10964, commit b29c606e2)`. The git tag `v0.4.1` points five commits later (`391fac164`, released as b10969: build/CI changes and one qwen4exp fusion, no server change). Entrypoint `llama-server`; `/app/llama` is a multi-call binary with `bench`, `perplexity`, `quantize`, `batched-bench`, `completion`, `cli`. | 2026-09-19 |
| llama.cpp native macOS build | `llama-b10964-bin-macos-arm64.tar.gz`, sha256 `033c845c1df9bf945ff37bb193238b40910b2244be3e1e637b2ceb5878f1a6f5` | `apple` profile | The same build as the image, for Metal. Ran on the reference Mac (`MTL0: Apple M2 Pro`). | 2026-09-19 |
| vLLM CPU image | `vllm/vllm-openai-cpu:v0.29.0@sha256:c2414ae3dfe4fbcd1fb5d1430f032618aca92dcfb0d8e5179165d512a0336f91` (arm64 `sha256:527ec4e8188f2ad480aca5863ab3b7e7c39cfda84f6c0bbb06525363a3eb5a0f`, amd64 `sha256:66064cf683152e60eff2e5b18ec2d4ace236fb063c0a241f918691db9caddcf4`) | ch04, ch09, ch10, ch15, ch16, ch17 | vLLM 0.29.0 (GitHub release and PyPI, 2026-09-09) is the book's pin; this is vLLM's official CPU image of that release, multi-arch. Inside: `vllm 0.29.0+cpu`, `torch 2.13.0+cpu`. | 2026-09-19 |
| GuideLLM image | `ghcr.io/vllm-project/guidellm:v0.7.4@sha256:97f528d4ac8f692ee2e945bb3ff74c37638766825f5d155d59fcef58efeb823e` | ch04 | GuideLLM 0.7.4 (PyPI 2026-09-16), the book's pin. The official multi-arch image keeps torch out of the runner. `guidellm --version` prints `guidellm version: 0.7.4`. | 2026-09-19 |
| Prometheus | `prom/prometheus:v3.14.0@sha256:5ce7540c3c00ef4ab0c9d2c995c6a5b9c421f44b4a115d97a2c7af3b1c21cbb0` | `screens` profile, ch15 | Latest release (2026-08-18), the book's pin. | 2026-09-19 |
| Grafana | `grafana/grafana:13.2.2@sha256:ac461fb352abc50da10a51c7d02462e9c05488f11f53f14b3ad79a8145f638a0` | `screens` profile, ch15 | Latest release (2026-09-15), the book's pin. | 2026-09-19 |
| OpenTelemetry Collector (contrib) | `otel/opentelemetry-collector-contrib:0.161.0@sha256:fd328de2552466ad78385e1b1289c3f2402b1c45f265b252aab1955b42845ac1` (arm64 `sha256:d497a11a3088097e4054ffbfd4b4f5244a8c036dc77c96cf2f14f86113ee9b86`, amd64 `sha256:b5cf983651c32c3ca13f936deb51742015a54d121f388cac248923ddeb8cc9fc`) | ch15 | Latest release (2026-09-16); the collector Vol. 1's trace stack is built on. ch15 uses its OTLP receiver and the contrib `file` exporter. | 2026-09-19 |
| vLLM's Grafana dashboards | `tools.env` `VLLM_DASHBOARD` (`examples/observability/prometheus_grafana/grafana.json`, `sha256:651f1cf353024072197214df101a6f641839099736939b22b2f46b11c9faf527`), `VLLM_DASHBOARD_PERF` (`dashboards/grafana/performance_statistics.json`, `sha256:507f481a47ed3606826aa373704dd84b28dfc311456398fed73dc992d649c637`), `VLLM_DASHBOARD_QUERY` (`dashboards/grafana/query_statistics.json`, `sha256:459de6707d482b462fc3922b5964a743bd5b2cc1f45365661eb04d7b7fd1faaa`), all at the `v0.29.0` tag | ch15 | The dashboards vLLM ships with the pinned release, fetched at run time and checked by SHA-256. | 2026-09-19 |
| Lab runner base | `python:3.13.15-slim-trixie@sha256:8d9d0b8bcf6506481eae4907c18f5e3e7902e629f5f6d684f9e7c32e85e3ddf0` | the runner image | Python 3.13.15 (2026-08-05) on Debian 13.7. 3.13, not 3.14, because AIPerf (a possible ch04 tool) requires `<3.14`. | 2026-09-19 |
| Docker CLI | `docker:29.8.1-cli@sha256:018edbc908e08fcc9dbf029c812c34251e9b4719e6f71ca0e5eae2a987d014ca` | the runner image (binary copied in) | Latest CLI (tag 2026-09-15). The runner starts engines as sibling containers. Tested against daemon 29.4.0 (OrbStack), and with `DOCKER_API_VERSION=1.48`, the API of the GitHub runners' Docker 28.0.4. | 2026-09-19 |
| Debian snapshot | `snapshot.debian.org` at `20260918T000000Z` (trixie, trixie-updates, trixie-security) | the runner image | A dated archive, so every build installs the same package versions. `apt-get update` from it took 2 s. | 2026-09-19 |
| curl | curl 8.14.1-2+deb13u5 | the runner image | The version in the snapshot. | 2026-09-19 |
| jq | jq 1.7.1-6+deb13u3 | the runner image | The version in the snapshot. | 2026-09-19 |
| Python packages | none | — | The shared scripts use the standard library only. `requirements.txt` is installed with `--require-hashes`; add exact `==` pins with hashes there and a row here. | 2026-09-19 |
| ShellCheck | `koalaman/shellcheck:v0.11.0@sha256:61862eba1fcf09a484ebcc6feea46f1782532571a34ed51fedf90dd25f925a8d` | CI `lint` | Latest release (2025-08-04). Pinned so lint does not drift with the runner image, which ships 0.9.0. | 2026-09-19 |
| actionlint | `rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667` | CI `lint` | Latest release (2026-03-30). | 2026-09-19 |
| actions/checkout | `3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1) | CI | Latest release (2026-07-20), pinned by commit. | 2026-09-19 |
| actions/upload-artifact | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` (v7.0.1) | CI at-latest job | Latest release (2026-04-10), pinned by commit. | 2026-09-19 |
| actions/download-artifact | `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c` (v8.0.1) | CI at-latest job | Latest release (2026-03-11), pinned by commit. | 2026-09-19 |
| STREAM-style bandwidth test | `inference-in-production/ch02/bandwidth.py`, standard-library Python in the runner (3.13.15, pinned above) | ch02 | No external tool to pin: one process per CPU copies its share of two 512 MiB arrays at once, counting two bytes per byte copied (read and write) and keeping the best of 10 trials, as STREAM's Copy kernel does. | 2026-09-19 |
| WikiText-2 (raw) test text | `ggml-org/ci` dataset @ `927b3642933080f1b0e811e2f916e14c292992f9`, `wikitext-2-raw-v1.zip`, 4,721,645 bytes, sha256 `ef7edb566e3e2b2d31b29c1fdb0c89a4cc683597484c3dc2517919c615435a11` | ch11 | The file llama.cpp's own `scripts/get-wikitext-2.sh` fetches (from `main`; pinned here to its commit). CC BY-SA 3.0: downloaded at run time and checked, never committed. | 2026-09-19 |

Not pinned yet, because no lab uses them yet (each gets a row when its lab lands): AIPerf, and the
structured-output libraries for ch17.

## Inference in Production — the kind-based labs (ch14, ch16, ch18)

The kind labs run through the same command as every other lab (`docker compose run --rm
inference-in-production ch14`): the runner downloads kind, kubectl and istioctl once into
`.work/tools/`, checks each against its SHA-256, and creates the cluster's node as a sibling container
on the host's Docker (`lib/kind.sh`). Images are pinned in
[`images.env`](../inference-in-production/images.env) like every other image; the downloaded binaries and
upstream manifests are pinned by URL and SHA-256 in [`tools.env`](../inference-in-production/tools.env),
which `scripts/check_pins.py` also reads. The manifests the book prints name images by tag;
`pin_images` (in `lib/kind.sh`) swaps each tag for the digest below before applying them. All
verified 2026-09-19 against the release page, the release asset's own `.sha256`/digest, and the
registry (`docker buildx imagetools inspect`).

| Component | Pin | Used by | Why this version | Last verified |
|---|---|---|---|---|
| kind | v0.33.0 (2026-08-26): `kind-linux-amd64` `sha256:aee6151561422756b764a4ae28e7f44cda5af5a9eead3cc9985112b1de8d8e0d`, `kind-linux-arm64` `sha256:20022bee6cfcd5086cb7234d218e3454e6090022f2a8f55d1fa7fcf42c3867a2` | ch14, ch16, ch18 | Latest release, the book's pin. Runs from inside the runner through the Docker socket; tested on OrbStack 29.4.0. | 2026-09-19 |
| kind node image | `kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed` (arm64 `sha256:10210eabcf5dc4b585756bbd3f7fbb60cc0a12a252f28aeba269d93e0070c025`, amd64 `sha256:597367624b4748b74b98e4fe2d661cd78063d02ecdaca702fd90572375b83e67`) | ch14, ch16, ch18 | Kubernetes 1.36.4, one of the four images kind v0.33.0 lists (by digest) for itself. Not its default 1.37.0: Istio 1.30 supports Kubernetes 1.32–1.36 (istio.io `supportStatus.yml`). | 2026-09-19 |
| kubectl | v1.36.4: linux/amd64 `sha256:8b8f088da2dab964f853b38464033b1be15ede2839eca751482357c45abdd05a`, linux/arm64 `sha256:0ecf44450ee6063bf19dd166a103ee6df4a9034455c2abce626e6eea657d73fb` (dl.k8s.io) | ch14, ch16, ch18 | The node image's version. | 2026-09-19 |
| Gateway API CRDs | v1.5.1 `standard-install.yaml`, `sha256:751002b3b91a87f7ae3bd2517c79a47a8d7ed6702901808a1cf9bd97d284f9b8` | ch14, ch18 | Not the latest (v1.6.2): v1.5.1 is the version Istio 1.30.4, GAIE v1.6.2 and llm-d-router v0.10.0 are all built against (each one's `go.mod`), and the one llm-d v0.9.0's guides install. | 2026-09-19 |
| Gateway API implementation: Istio | 1.30.4 (2026-08-27). `istioctl-1.30.4-linux-amd64.tar.gz` `sha256:feda625a00dfc69135f4692442ef66eb2fa8aea848b483348c330a1138fe392f`, `…-linux-arm64.tar.gz` `sha256:1045d90978d5cc46ad77a7447bebf1a26c66c796c4499bbd83f62cfcb4631f95`; `docker.io/istio/pilot:1.30.4@sha256:c236c1df5cc127fe193e5a17d8ece9cdd0dc17c5d89b4e20baf01d464f029dce` (arm64 `sha256:125a02ea65e31925130479445b2986c6dffdae1b65e44109a232a29285065b2d`, amd64 `sha256:eb8860804a8877f63351b367b731f0b2f13039ea4ccf92a0b3a0d628e2646901`); `docker.io/istio/proxyv2:1.30.4@sha256:43b6aeab7428470d3d0ea6b6f0bc217e5b36df2b279bba337643df48590226d9` (arm64 `sha256:27ca30f7e67a658e333d1f24b8fd9f90e922c42c05ac25f66f5e59f852a06f4b`, amd64 `sha256:372b2de1c4e48797d54a8a129e4710a6c41496a387a95d717c8b16f009092bf8`) | ch14 | The one implementation the lab pins (the research left the choice to the repo build). Istio 1.30 is the line with a full-pass GAIE conformance report (1.30.1: 13 of 13 core tests, GAIE v1.5.0 suite, in the GAIE repo at v1.6.2); NGINX Gateway Fabric's report skips `GatewayDestinationEndpointServed`; Envoy Gateway needs Envoy AI Gateway on top; agentgateway and kgateway install by Helm only. llm-d v0.9.0 documents Istio for its guides and llm-d-router v0.10.0's own kind dev environment runs it. Installed with `istioctl install --set profile=minimal` and `ENABLE_GATEWAY_API_INFERENCE_EXTENSION=true`; 1.30.4 is the line's latest patch. | 2026-09-19 |
| Gateway API Inference Extension | v1.6.2 (2026-09-17) `v1-manifests.yaml` (the `InferencePool` CRD, `inference.networking.k8s.io/v1`), `sha256:f410dfca474608c02903087b47f1ac081706dfb6dfe7f83d00a7cc7e00c4ad0d` | ch14, ch18 | Latest release, the book's pin. | 2026-09-19 |
| llm-d-router | v0.10.0 (2026-08-17). CRDs: release asset `manifests.yaml` (`InferenceObjective`, `InferenceModelRewrite`, `llm-d.ai/v1alpha2`), `sha256:488c0f48f4d41067d2319e20761bae1e531cfcfc8c73ba979067365302ec1df0`. Endpoint picker: `ghcr.io/llm-d/llm-d-router-endpoint-picker:v0.10.0@sha256:2e516fa1310da7be59b82beb1445362139597d6d553ef04d546716abe3aaaa70` (arm64 `sha256:110a7225ff00abdec72d485cb215296352492476a8f87bc229229c5a35b539ad`, amd64 `sha256:9862ae38658824b2560c547237363fe21f269e649b873a4ee84fe3137b554ba9`) | ch14 | Latest stable release, the book's pin (v0.11.0-rc.1 of 2026-09-18 is a pre-release). Configured by an `EndpointPickerConfig` (`llm-d.ai/v1alpha1`); flow control behind the `flowControl` feature gate. | 2026-09-19 |
| llm-d-inference-sim | `ghcr.io/llm-d/llm-d-inference-sim:v0.11.2@sha256:32144df791330a0006b747edfdf2b114a0fe728e023a9d1b3463eeb48d32abb9` (arm64 `sha256:ce569791376be239b2431fc3513a1498d6e70e05f2cc31f46970d38f055644b5`, amd64 `sha256:351d413e80602d227c262883079d8beb17bea91d0bc7ecd642b2d8d8e59bd7ea`) | ch03, ch14, ch16, ch18 | Latest release (2026-08-31), the book's pin. Its timings are its configuration; every result it produces is labeled simulated. | 2026-09-19 |
| KEDA | v2.20.2 (2026-07-31). Manifest `keda-2.20.2.yaml`, `sha256:9bae123eb64fab8f96c67bbd576bb5819e4794df346c5aaa402a01c68b0557ab`; `ghcr.io/kedacore/keda:2.20.2@sha256:fe74c7b8849586a67ad2201bcb89e7f5ac221ff90399ecaa8fd28427f1ef11e6` (arm64 `sha256:19ddecf229490d4ef550ce3d5ee10677c5ccf4027455494b8f8ac566f1fa5e26`, amd64 `sha256:6c2ded1ae8ab5a6b3452e1ff64468ce76de30b2983fd7d5783719c325f806393`); `ghcr.io/kedacore/keda-metrics-apiserver:2.20.2@sha256:27286536a8a775aeeee37a7e343f8ecebb27ebf680ee1181a4f99e82eefb253b` (arm64 `sha256:1a6343daca2e703d57d3995de693d1a34e0004831026d0757f44d4d5d82e6086`, amd64 `sha256:3b6c694aed71a5480760062de91e53288e9b8b67d4b6c7e5eac49459e75b96d2`); `ghcr.io/kedacore/keda-admission-webhooks:2.20.2@sha256:41f74102aba7959c6e8d08b433ab8a5fd6cae7c5646c78f7fe3de40a52df3439` (arm64 `sha256:1a3d060789637a1464e999e07a60a22d781df890110ee8ed6c76fbb7676a0e20`, amd64 `sha256:c915db826c054e6b76ef9f9904a2a620db931e0244f3f6fc815d81682f9e5365`) | ch16 | Latest release, the book's pin. `lib/kind.sh` swaps the manifest's three image tags for these digests. | 2026-09-19 |

## Inference in Production — models

Every lab model is ungated and Apache-2.0 (per its model card), pinned by Hugging Face commit SHA,
and checked by size and SHA-256 on download (`scripts/fetch_models.py`). Per-file sizes and hashes
are in `models.lock.json`. Every file downloaded and verified on 2026-09-19.

| Artifact (set) | Repository @ revision | Files | Bytes | License | Used by |
|---|---|---|---|---|---|
| `smollm2-135m-gguf` (`smoke`: Q8_0 only; `gguf`) | `bartowski/SmolLM2-135M-Instruct-GGUF` @ `09816acd5d99df7be770d85ea30822623dab342c` | f16 270,885,952 · Q8_0 144,811,360 · Q4_K_M 105,454,432 | 521,151,744 | apache-2.0 | ch00 (Q8_0), ch02, ch11, ch12 draft |
| `smollm2-360m-gguf` (`gguf`) | `bartowski/SmolLM2-360M-Instruct-GGUF` @ `7be6f65f1db715fe5dc5a4634c0d459b4eed42ec` | f16 725,553,792 · Q8_0 386,405,280 · Q4_K_M 270,590,880 | 1,382,549,952 | apache-2.0 | ch02, ch11, ch12 target |
| `smollm2-135m-hf` (`hf`) | `HuggingFaceTB/SmolLM2-135M-Instruct` @ `12fd25f77366fa6b3b4b768ec3050bf629380bac` | BF16 safetensors, tokenizer, configs (8 files) | 272,437,573 | apache-2.0 | vLLM draft model; the `run-batch` check |
| `smollm2-360m-hf` (`hf`) | `HuggingFaceTB/SmolLM2-360M-Instruct` @ `a10cc1512eabd3dde888204e902eca88bddb4951` | BF16 safetensors, tokenizer, configs (8 files) | 727,051,918 | apache-2.0 | every vLLM-CPU lab |
| `lora-360m-alpaca` (`lora`) | `nadaashraff/smollm2-360m-alpaca-lora` @ `16227d3053472fe28f59a99c3f851ab77057655f` | LoRA r=8 on all seven projections | 17,426,298 | apache-2.0 | ch14 multi-LoRA step |
| `lora-360m-underdog` (`lora`) | `sammoftah/underdog-lab-smollm2-360m-lora` @ `6e40f48915868a8b34a32c8b3de16f8fc9524766` | LoRA r=16 on q_proj, v_proj | 3,294,773 | apache-2.0 | ch14 multi-LoRA step |
| `qwen3.5-0.8b-hf` (`qwen35`; not in `all`) | `Qwen/Qwen3.5-0.8B` @ `2fc06364715b967f1860aea9cf38778875588b17` | BF16 safetensors, tokenizer, configs (10 files) | 1,769,905,646 | apache-2.0 | the hybrid-attention sidebar |

`all` = `gguf` + `hf` + `lora`: 26 files, 2,788 MiB. `docker compose run --rm
inference-in-production models list` prints the current totals.

**KV bytes per token for SmolLM2-360M-Instruct, from its config at the pinned SHA** [CRIT L5]:
32 layers, 5 KV heads, head_dim 64 (hidden 960 / 15 heads), BF16, so
2 × 32 × 5 × 64 × 2 = **40,960 B = 40 KiB per token**, and 1 GiB holds 26,214 tokens.
vLLM 0.29.0 on CPU with `VLLM_CPU_KVCACHE_SPACE=1` reports `GPU KV cache size: 26,112 tokens`
(check a): 204 blocks of 128 tokens, the same budget rounded down to whole blocks. On the CPU
backend vLLM 0.29.0 defaults to 128-token KV blocks, not the 16 it uses on a GPU: its
`vllm:cache_config_info` series reports `block_size="128"` and `num_gpu_blocks="204"`
(`measured/ch09/startup.txt`; `vllm/platforms/cpu.py` sets 128 when the user does not).

## Settled checks (2026-09-19, reference laptop)

The five open checks from the book bible, run on the build machine: Apple M2 Pro, 16 GB RAM,
OrbStack (Docker 29.4.0; linux/arm64 VM with 10 CPUs and 7.8 GiB), CPU only. Each shows the command
and its real output, trimmed to the lines that answer the question.

### a. vLLM CPU on linux/arm64 in OrbStack: **yes**, and SmolLM2-360M serves with a 1 GiB KV cache

```sh
docker compose run --rm -e LAB=checka inference-in-production shell -c '
. /lab/lib/lab.sh
VLLM_CPU_KVCACHE_SPACE=1 start_vllm vllm \
  /models/hf/SmolLM2-360M-Instruct \
  --served-model-name smollm2-360m --max-model-len 2048
wait_ready vllm http://vllm:8000/health 600
...'
```

```
vllm ready after ~58s
(APIServer pid=1) INFO ... version 0.29.0
(APIServer pid=1) WARNING ... Model Runner V2 requires Triton; using the V1 model runner instead.
(Worker pid=110) INFO ... [cpu_worker.py:255] Explicitly set (1.0/7.81) GiB for KV cache on node 0.
(EngineCore pid=73) INFO ... GPU KV cache size: 26,112 tokens, Maximum concurrency for 2,048 tokens per request: 12.75x
{"model":"smollm2-360m","text":"1. Red\n2. Blue\n3. Yellow","usage":{"prompt_tokens":35,"total_tokens":47,"completion_tokens":12,...}}
vllm:kv_cache_usage_perc{engine="0",model_name="smollm2-360m"} 0.0
vllm:prefix_cache_queries_total{engine="0",model_name="smollm2-360m"} 35.0
vllm:prefix_cache_hits_total{engine="0",model_name="smollm2-360m"} 0.0
vllm:num_preemptions_total{engine="0",model_name="smollm2-360m"} 0.0
aiel-checka-vllm 3.868GiB / 7.806GiB 88.70%
```

So the vLLM labs run locally. Two things the chapters must not get wrong: on the CPU backend vLLM
0.29.0 **falls back to the V1 model runner** (Model Runner V2 needs Triton), and the scraped counters
carry `_total` (`vllm:num_preemptions_total`, `vllm:prefix_cache_hits_total`). The engine used about
3.9 GiB with this model and a 1 GiB cache; run one vLLM lab at a time.

### b. The vLLM CPU image vs a 14 GB-SSD runner: **fits**; 4.85 GB unpacked on x64, 2.67 GB on arm64

```sh
curl -s https://hub.docker.com/v2/repositories/vllm/vllm-openai-cpu/tags/v0.29.0 \
  | jq '[.images[] | {architecture, size}]'
docker run --rm --platform linux/amd64 --entrypoint sh \
  vllm/vllm-openai-cpu@sha256:c2414ae3... -c 'uname -m; du -sxb /'
docker run --rm --entrypoint sh \
  vllm/vllm-openai-cpu@sha256:c2414ae3... -c 'du -sxb /'
```

```
[{"architecture":"amd64","size":1842802680},{"architecture":"arm64","size":881855250}]
x86_64
4849407593
2665303479
```

| Arch | Compressed (pull) | Unpacked | Worst case on disk (containerd store keeps both) |
|---|---|---|---|
| amd64 | 1.84 GB | 4.85 GB | 6.69 GB |
| arm64 | 0.88 GB | 2.67 GB | 3.55 GB |

GitHub's standard Linux runners (x64 and arm64) list 14 GB of SSD (4 CPU / 16 GB RAM for public
repositories, 2 CPU / 8 GB for private ones; docs read 2026-09-19). The vLLM image, the `hf` models
(0.95 GB), the runner and the llama.cpp image stay under 9 GB on x64 even in the worst case. The
`cpu-labs` job prints `docker system df` and `df -h /` after every lab, so the first real CI run
records the actual headroom. The older research figure (2.28 GB compressed amd64) is a nightly tag,
not v0.29.0.

### c. Qwen3.5 hybrid attention on the vLLM CPU backend: **yes** (Qwen3.5-0.8B)

```sh
start_vllm vllm /models/hf/Qwen3.5-0.8B \
  --served-model-name qwen3.5-0.8b --max-model-len 2048 \
  --language-model-only
```

```
vllm ready after ~74s
INFO ... Mamba cache mode is set to 'align' for Qwen3_5ForConditionalGeneration by default when prefix caching is enabled
INFO ... [qwen_gdn_linear_attn.py:155] Using CPU GDN prefill kernel (head_k_dim=128).
INFO ... [qwen_gdn_linear_attn.py:519] GDN decode kernel: CPU
INFO ... Setting attention block size to 640 tokens to ensure that attention page size is >= mamba page size.
INFO ... Padding mamba page size by 20.75% to ensure that mamba page size and attention page size are exactly equal.
INFO ... Explicitly set (1.0/7.81) GiB for KV cache on node 0.
INFO ... GPU KV cache size: 27,852 tokens, Maximum concurrency for 2,048 tokens per request: 13.60x
{"text":"The three primary colors of light are **Red**, **Green**, and **Blue**. ...","usage":{"prompt_tokens":17,"total_tokens":57,"completion_tokens":40}}
```

The model's config at the pinned SHA: 24 layers, `layer_types` = 18 `linear_attention` + 6
`full_attention`, 2 KV heads, head_dim 256. Tested with `--language-model-only` (the checkpoint is
`Qwen3_5ForConditionalGeneration` and carries a vision tower the sidebar does not need); not tested
without it. Caution for the sidebar: vLLM sizes a hybrid model's cache in shared pages (640-token
attention blocks padded to the linear-attention state), so its "KV cache size" in tokens is **not**
the 12 KiB-per-token full-attention arithmetic. Quote the arithmetic and this log line as two
different things.

### d. LoRA for ch14: **vLLM CPU serves LoRA adapters** (two public Apache-2.0 adapters at once)

```sh
start_vllm vllm /models/hf/SmolLM2-360M-Instruct \
  --served-model-name smollm2-360m --max-model-len 2048 \
  --enable-lora --max-loras 2 --max-lora-rank 16 \
  --lora-modules alpaca=/models/lora/smollm2-360m-alpaca \
                 underdog=/models/lora/smollm2-360m-underdog
```

```
vllm ready after ~27s
(Worker pid=111) INFO ... [punica_selector.py:20] Using PunicaWrapperCPU.
(APIServer pid=1) INFO ... Loaded new LoRA adapter: name 'alpaca', path '/models/lora/smollm2-360m-alpaca'
(APIServer pid=1) INFO ... Loaded new LoRA adapter: name 'underdog', path '/models/lora/smollm2-360m-underdog'
[{"id":"smollm2-360m","root":"/models/hf/SmolLM2-360M-Instruct","parent":null},{"id":"alpaca","root":"/models/lora/smollm2-360m-alpaca","parent":"smollm2-360m"},{"id":"underdog","root":"/models/lora/smollm2-360m-underdog","parent":"smollm2-360m"}]
smollm2-360m  "One tip for staying focused is to eliminate distractions. This can be achieved by turning off notifications on"
alpaca        "One tip for staying focused is to create a conducive environment for concentration. This can be achieved by el"
underdog      "One tip for staying focused is to break your tasks into smaller, manageable chunks, and to take regular breaks"
vllm:lora_requests_info{max_lora="2",running_lora_adapters="alpaca",waiting_lora_adapters="alpaca"} 1.789828498802105e+09
```

Same prompt, temperature 0, three different answers: the adapter is chosen per request by the
`model` field. The llama.cpp `--lora` path was not needed and was not tested (it would need the
adapters converted to GGUF first).

### e. `vllm run-batch` at v0.29.0: **exists, and works on CPU**

```sh
docker compose run --rm -e LAB=checke inference-in-production shell -c '
. /lab/lib/lab.sh
run_tool "$VLLM_CPU_IMAGE" --entrypoint vllm -- --help
run_tool "$VLLM_CPU_IMAGE" --entrypoint vllm \
  -e VLLM_CPU_KVCACHE_SPACE=1 -- run-batch \
  -i /scratch/checke/in.jsonl -o /scratch/checke/out.jsonl \
  --model /models/hf/SmolLM2-135M-Instruct --max-model-len 1024'
```

```
positional arguments:
  {chat,complete,serve,launch,bench,collect-env,run-batch}
    run-batch           Run batch prompts and write results to file.
usage: vllm run-batch -i INPUT.jsonl -o OUTPUT.jsonl --model <model>
run-batch exit=0 in 55s
{"custom_id":"req-1","status":200,"text":"1. 1. 1. 1. 1. 1","error":null}
{"custom_id":"req-2","status":200,"text":"Count to 2.","error":null}
{"custom_id":"req-3","status":200,"text":"I'm counting to 3.","error":null}
```

Each input line is an OpenAI batch-format request (`custom_id`, `method`, `url`
`/v1/chat/completions`, `body`). ch08's offline corner can use it.

## Other findings from the build (2026-09-19)

- **GuideLLM 0.7.4's command is `guidellm run`**, not `guidellm benchmark`
  (`Error: No such command 'benchmark'`). Its options take `kind=...` specs:
  `--backend kind=openai_http,...`, `--profile kind=synchronous|concurrent|sweep|...`,
  `--constraint kind=max_requests,...`, `--data kind=synthetic_text,...`. A full GuideLLM run was not
  part of this foundation; ch04 settles the exact flags.
- **llama.cpp's `--metrics`** at the pin exports, among others, `llamacpp:prompt_tokens_total`,
  `llamacpp:prompt_tokens_cached_total`, `llamacpp:tokens_predicted_total`,
  `llamacpp:n_decode_total` and `llamacpp:spec_decode_num_accepted_tokens_total`. Prometheus in the
  `screens` profile scraped them from a running lab (target `llama` up, value read back).
- **The native Metal path works.** The same b10964 build on the reference Mac, the ch00 request:
  `predicted_per_second` 201.5 natively on Metal vs 76.1 in the container on the CPU. One run each;
  an illustration, not a measurement.
- **The x64 images run under emulation too.** ch00's test passed with
  `DOCKER_DEFAULT_PLATFORM=linux/amd64` (runner and llama.cpp both amd64, via Rosetta) and
  `DOCKER_API_VERSION=1.48`. Not a substitute for the x64 CI leg, which runs natively.
