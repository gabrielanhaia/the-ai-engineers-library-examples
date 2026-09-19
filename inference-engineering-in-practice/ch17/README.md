# ch17: a verifier of your own

Chapter 17's lab: a mini vendor verifier. The same 40 requests go
to two engines serving the same model with the same chat template,
and every answer is checked against the schema its request carried.

## What it does

1. `cases.py` is the fixed request set, the same every run:
   - 20 tool-call requests: four tools (`get_weather`,
     `convert_currency`, `book_table`, `set_reminder`), all four
     offered every time, `tool_choice: "auto"` and
     `parallel_tool_calls: false` (each question wants one call),
     five questions per tool;
   - 20 JSON-schema requests in the OpenAI-standard shape,
     `response_format: {"type": "json_schema", ...}`, four schemas
     (`person`, `order`, `event`, `review`), five texts each.
   Every schema is strict: required keys, no extra keys, enums,
   ranges, patterns.
2. `template.jinja` is SmolLM2's chat template plus the
   tool-calling system prompt from the SmolLM2-1.7B-Instruct model
   card, rendered when a request carries tools. The model is asked
   to answer `<tool_call>[{"name": ..., "arguments": {...}}]
   </tool_call>`, and the template renders an assistant's tool
   calls in that same format. That second half matters: llama.cpp
   learns how to parse tool calls by rendering one through the
   template. Without it, llama.cpp reports `supports_tool_calls:
   false` and returns every call as plain text.
3. Serves SmolLM2-360M-Instruct from llama.cpp (build b10964, F16
   GGUF, `--jinja --chat-template-file`), runs `verify.py`, stops
   it; then from vLLM 0.29.0's CPU backend (FP16, `--chat-template`,
   `--enable-auto-tool-choice --tool-call-parser xlam`, the parser
   for that `<tool_call>[...]` list format), and runs `verify.py`
   again.
4. `verify.py` sends each request (temperature 0, at most 96
   tokens) and judges the answer. A tool call is valid when the
   answer holds a call to one of the offered tools whose arguments
   are JSON that pass that tool's schema. A JSON-schema answer is
   valid when its content is JSON that passes the request's schema.
   It prints the schema-valid rate per engine and kind and, for
   tool calls, how many of the valid calls named the tool the
   question was about: schema-valid is not the same as right.
5. `gate.py` compares each rate with `thresholds.json`, the floor
   recorded from the reference laptop's run, minus a margin for
   another CPU's arithmetic: 0.45 for llama.cpp's tool calls
   (measured 0.60), 0.90 for both engines' JSON-schema answers
   (measured 1.00). vLLM's tool calls have no floor: at 0 of 20
   there is nothing to protect, and the 0 is the finding.
   Chapter 18's quality gate reuses the same two files:
   `verify.py` against a candidate stack, then
   `gate.py thresholds.json DIR`.

What the rates show. Both engines turn every JSON-schema request
into valid JSON: each compiles the schema into a grammar and masks
the tokens that would break it. The tool calls differ, on the same
weights, template and requests. This 360M model often copies the
system prompt's example, `{"name": "func_name1", "arguments":
{"argument1": "value1", ...}}`. llama.cpp, once the model opens
`<tool_call>`, constrains what follows with a grammar built from
the offered tools, so the call it returns names a real tool and
passes its schema. vLLM's parser takes the model's text as written,
so it returns `func_name1`, or no call at all when the text is not
valid JSON (`measured/ch17/vllm.jsonl` holds every message).

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch17
```

It downloads the `smollm2-360m-gguf` (1,319 MiB) and
`smollm2-360m-hf` (693 MiB) models once. The run takes about 5
minutes on the reference laptop.

## Expected output

The rates are set by the model, the template and each engine's
parsing and grammar code, at temperature 0; they can move a little
between CPU architectures. Recorded on the reference laptop (Apple
M2 Pro, 16 GB, OrbStack, linux/arm64, CPU only). This block is
[`../measured/ch17/output.txt`](../measured/ch17/output.txt):

```text

== models and the chat template
models: 11 file(s), 2,012 MiB, into /models
  ok      gguf/SmolLM2-360M-Instruct-f16.gguf
  ok      gguf/SmolLM2-360M-Instruct-Q8_0.gguf
  ok      gguf/SmolLM2-360M-Instruct-Q4_K_M.gguf
  ok      hf/SmolLM2-360M-Instruct/config.json
  ok      hf/SmolLM2-360M-Instruct/generation_config.json
  ok      hf/SmolLM2-360M-Instruct/merges.txt
  ok      hf/SmolLM2-360M-Instruct/model.safetensors
  ok      hf/SmolLM2-360M-Instruct/special_tokens_map.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer.json
  ok      hf/SmolLM2-360M-Instruct/tokenizer_config.json
  ok      hf/SmolLM2-360M-Instruct/vocab.json

== llama.cpp (build b10964), F16 GGUF
ch17-llama ready after ~2s
 llama.cpp  tool call          20     12   0.60          11
 llama.cpp  json schema        20     20   1.00

== vLLM 0.29.0 CPU backend, FP16, xLAM tool-call parser
ch17-vllm ready after ~65s
 vllm       tool call          20      0   0.00           0
 vllm       json schema        20     20   1.00

== schema-valid rates
 engine     kind         requests  valid   rate  right tool
 llama.cpp  tool call          20     12   0.60          11
 llama.cpp  json schema        20     20   1.00
 vllm       tool call          20      0   0.00           0
 vllm       json schema        20     20   1.00

the gate chapter 18 reuses (thresholds.json):
 pass  llama.cpp  tool call     0.60 >= 0.45
 pass  llama.cpp  json schema   1.00 >= 0.90
 pass  vllm       json schema   1.00 >= 0.90

== done
manifest: measured/ch17/machine.json
```

## What the test asserts

`test ch17` runs the lab, then asserts that both engines answered
all 40 requests and that `gate.py` passes: every engine's
schema-valid rate, per kind, is at or above `thresholds.json`.

## Files

- `cases.py`: the request set and its schemas.
- `template.jinja`: the chat template both engines load.
- `verify.py`: the replay and the checks.
- `gate.py`, `thresholds.json`: the gate chapter 18 reuses.
- In `measured/ch17/`: `llama.cpp.jsonl` and `vllm.jsonl` (every
  request's verdict, problems and the engine's message) and
  `summary.txt`.
