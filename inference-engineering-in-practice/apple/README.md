# Apple silicon: the native (Metal) path

Containers on a Mac cannot reach the Metal GPU, so the `cpu` labs
run llama.cpp on the CPU. For the llama.cpp labs you can also run
the same pinned llama.cpp build natively, on the GPU. Nothing else
(vLLM CPU, GuideLLM, kind) has a native path here.

`docker compose run --rm apple` prints this file.

## 1. The pinned llama.cpp build (v0.4.1 = build b10964)

```sh
V=b10964
F=llama-$V-bin-macos-arm64.tar.gz
curl -LO https://github.com/ggml-org/llama.cpp/releases/download/$V/$F
echo "033c845c1df9bf945ff37bb193238b40910b2244be3e1e637b2ceb5878f1a6f5  $F" \
  | shasum -a 256 -c
tar -xzf "$F"
./llama-$V/llama-server --list-devices    # expect MTL0: Apple M...
```

## 2. The models, outside Docker

The fetcher is standard-library Python, so it runs on the Mac as is,
with the same pins and SHA-256 checks as in the container:

```sh
python3 inference-engineering-in-practice/scripts/fetch_models.py \
  fetch gguf --dest ~/aiel-models
```

## 3. Serve on the GPU

```sh
./llama-b10964/llama-server --port 8080 --ctx-size 2048 --metrics \
  -m ~/aiel-models/gguf/SmolLM2-135M-Instruct-Q8_0.gguf -ngl 99
```

`-ngl 99` offloads every layer to Metal; `-ngl 0` keeps them on the
CPU, which is the comparison the ch02 lab asks for.

## 4. One request

```sh
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages": [{"role": "user",
        "content": "Name three primary colors."}],
       "max_tokens": 32, "temperature": 0}' | jq .timings
```

The bench and perplexity tools ship in the same archive:
`./llama-b10964/llama-bench` and `./llama-b10964/llama-perplexity`.
