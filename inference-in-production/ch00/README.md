# ch00: smoke test

Not a chapter. It proves the whole path works on your machine before
you start the book: the model cache, the llama.cpp server, one
streamed OpenAI-compatible request, and the server's own timings.

## What it does

1. Downloads SmolLM2-135M-Instruct (Q8_0 GGUF, 138 MiB) into the
   model cache, once, and checks its SHA-256.
2. Starts the pinned llama.cpp server on the lab network as `llama`.
3. Sends one streamed chat completion with `curl -N`, prints the
   text as it arrives, and keeps the raw stream.
4. Prints the `timings` object the server puts in the last chunk.
5. Stops the server.

## Run it

```sh
docker compose run --rm inference-in-production ch00
```

The first run builds the lab runner and pulls the llama.cpp image
(about 300 MB compressed), which takes a minute or two. After that
it takes a few seconds. `test ch00` runs it and then checks the
invariants below; CI runs that on x64 and arm64.

## Expected output

Your numbers will differ; the shape will not. Recorded on the
reference laptop (Apple M2 Pro, 16 GB, OrbStack, linux/arm64, CPU
only). This block is [`../measured/ch00/output.txt`](../measured/ch00/output.txt):

```

== model
models: 1 file(s), 138 MiB, into /models
  ok      gguf/SmolLM2-135M-Instruct-Q8_0.gguf

== llama.cpp server
llama ready after ~1s

== one streamed request
The primary colors are:

1. Red: A warm, fiery hue that is often associated with fire, blood, and passion.
2. Blue:

== server timings (last chunk)
{
  "cache_n": 0,
  "prompt_n": 35,
  "prompt_ms": 125.098,
  "prompt_per_token_ms": 3.5742285714285713,
  "prompt_per_second": 279.78065196885643,
  "predicted_n": 32,
  "predicted_ms": 464.305,
  "predicted_per_token_ms": 14.977580645161291,
  "predicted_per_second": 66.76645739330827
}

== done
manifest: measured/ch00/machine.json
chunks: 34
raw stream: measured/ch00/stream.sse
```

## What the test asserts

Invariants, never timings: the stream arrived in more than one
chunk, it ended with `data: [DONE]`, the first chunk has the OpenAI
`chat.completion.chunk` shape, and `timings` has positive
`prompt_n`, `prompt_ms`, `predicted_n` and `predicted_ms`.

## Files

- `run.sh`: the lab.
- `test.sh`: runs the lab, then asserts.
- Output lands in `measured/ch00/`: the raw stream, the parsed
  chunks, the timings and `machine.json`. The copy in the
  repository is the reference laptop's run; yours replaces it in
  your checkout, and `git diff` shows how your machine differs.
