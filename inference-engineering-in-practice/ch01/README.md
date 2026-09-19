# ch01: the first token

Chapter 1's lab: one streamed request to llama.cpp's
OpenAI-compatible server, the moment its first text reaches the
client, and the server's own account of where the time went.

## What it does

1. Downloads SmolLM2-135M-Instruct (Q8_0 GGUF, 138 MiB) into the
   model cache, once, and checks its SHA-256.
2. Starts the pinned llama.cpp server (v0.4.1, build b10964) with
   `--metrics` and half the CPUs (`--threads`), on the lab network
   as `llama`. llama.cpp's default takes every CPU, and each step
   waits for its slowest thread: on a laptop with efficiency cores,
   or with other work running, fewer threads decode faster.
3. Sends one streamed `/v1/chat/completions` request with `curl -N`
   (`"stream": true`, temperature 0, 32 tokens at most) and stamps
   every line of the stream with the client's clock as it arrives.
4. Records client-side TTFT: the time from sending the request to
   the first chunk that carries text. The stream's first chunk only
   announces the assistant's role and holds no token, so it does
   not count.
5. Prints the `timings` object the server puts in the last chunk:
   `prompt_ms` for reading the prompt, `predicted_ms` for writing
   the answer, and the per-token rates of each.

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch01
```

The first run pulls the llama.cpp image (about 300 MB compressed)
and the model; after that it takes a few seconds.

## Expected output

Your numbers will differ; the shape will not. Recorded on the
reference laptop (Apple M2 Pro, 16 GB, OrbStack, linux/arm64, CPU
only). This block is
[`../measured/ch01/output.txt`](../measured/ch01/output.txt):

```

== model
models: 1 file(s), 138 MiB, into /models
  ok      gguf/SmolLM2-135M-Instruct-Q8_0.gguf

== llama.cpp server (build b10964)
llama ready after ~1s

== one streamed request
A token is a small, self-contained unit of information that serves as a unique identifier, a code, or a message in a digital communication system.

== server timings (last chunk)
{
  "cache_n": 0,
  "prompt_n": 39,
  "prompt_ms": 19.041,
  "prompt_per_token_ms": 0.48823076923076925,
  "prompt_per_second": 2048.2117535843704,
  "predicted_n": 32,
  "predicted_ms": 200.184,
  "predicted_per_token_ms": 6.457548387096774,
  "predicted_per_second": 154.8575310714143
}

== first token at the client
{
  "client_ttft_ms": 28.05,
  "server_prompt_ms": 19.041
}

== done
manifest: measured/ch01/machine.json
chunks: 33
raw stream: measured/ch01/stream.sse
```

## What the test asserts

`test ch01` runs the lab, then checks invariants, never timings:
the stream arrived in more than one chunk and ended with
`data: [DONE]`; the first chunk is role-only, so TTFT waits for a
later one; `timings` has positive `prompt_n`, `prompt_ms`,
`predicted_n` and `predicted_ms`; client-side TTFT is larger than
the server's `prompt_ms`; and the prompt was read faster per token
(`prompt_per_second`) than the answer was written
(`predicted_per_second`).

## Files

- `run.sh`: the lab. `test.sh`: runs it, then asserts.
- Output lands in `measured/ch01/`: `stream.sse` (the raw
  server-sent events), `chunks.jsonl` (one chunk per line),
  `timings.json`, `ttft.json` (client-side TTFT beside the server's
  `prompt_ms`) and `machine.json`.
