# ch12: acceptance belongs to the text

Chapter 12's lab: SmolLM2-135M-Instruct drafts for
SmolLM2-360M-Instruct in llama.cpp, on the CPU. It measures how
often the target keeps the draft's guesses, per task type (code
against prose) and per sampling temperature, from the server's own
counters. Then it runs the same prompts with no draft model, once,
for a wall-clock ratio that is reported and labeled "CPU, not
representative": it is a fact about this laptop, not about a GPU.

## What it does

1. Fetches the pinned Q8_0 GGUF files of both models.
2. Starts llama.cpp (build b10964) with the draft model and a fixed
   draft length: `--spec-type draft-simple --spec-draft-model ...
   --spec-draft-n-max 4 --spec-draft-n-min 0 --spec-draft-p-min 0`
   (k = 4: up to 4 tokens per step, fewer only near the answer's
   token limit; `p-min` 0 keeps the draft from stopping early on a
   low-confidence guess).
3. For each task type (8 code prompts, 8 prose prompts, in
   `prompts.json`) and each temperature (0, 0.4, 0.8, 1.2), sends
   the prompts one at a time (128 tokens each; top-k, top-p and
   min-p fixed at llama.cpp's defaults of 40, 0.95 and 0.05, a fixed
   seed per prompt), scraping `/metrics` before and after.
4. `accept.py` turns the two scrapes into acceptance =
   accepted ÷ drafted and tokens per step = 1 + accepted ÷ drafts,
   from the deltas of `llamacpp:spec_decode_num_draft_tokens_total`,
   `..._accepted_tokens_total` and `..._drafts_total`.
5. Starts a second llama.cpp server with no draft model and sends
   every prompt at temperature 0 to both, one after the other,
   switching which goes first on every prompt so that a busy moment
   on the machine lands on both sides alike (`wallclock.py`); then
   prints plain ÷ speculative wall-clock time.

How llama.cpp verifies at this build: the draft proposes its own
top token at each position (greedy); the target samples its token
at the request's temperature and keeps the draft token only when
the two match (`common_sampler_sample_and_accept_n`). The output is
always a sample from the target, so its distribution is the
target's; at temperature above 0, acceptance is the target's
probability of the draft's top choice.

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch12
```

About five minutes on the reference laptop after the first run
(which pulls the llama.cpp image and 507 MiB of models).

## Expected output

Recorded on the reference laptop (Apple M2 Pro, 16 GB, OrbStack,
linux/arm64, CPU only). This block is
[`../measured/ch12/output.txt`](../measured/ch12/output.txt):

```

== models: target and draft
models: 2 file(s), 507 MiB, into /models
  ok      gguf/SmolLM2-360M-Instruct-Q8_0.gguf
  ok      gguf/SmolLM2-135M-Instruct-Q8_0.gguf

== llama.cpp (build b10964) with a draft model, k = 4
llama ready after ~3s
task    temp  drafted  accepted  acceptance  tokens/step
code       0      852       699       0.820         4.24
code     0.4      780       642       0.823         4.24
code     0.8      733       579       0.790         4.13
code     1.2      828       551       0.665         3.64
prose      0     1457       644       0.442         2.75
prose    0.4     1542       626       0.406         2.61
prose    0.8     1807       555       0.307         2.22
prose    1.2     1893       510       0.269         2.07

== the same prompts at temperature 0, with and without a draft
plain ready after ~1s
plain 13.9 s, speculative 19.6 s: 0.71x (CPU, not representative)

== done
manifest: measured/ch12/machine.json
```

## What the test asserts

`test ch12` runs the lab on two prompts per task, 48 tokens and two
temperatures, then checks invariants, never rates: one row per task
type and temperature; every setting drafted tokens and had some
accepted; 0 < acceptance <= 1, tokens per step >= 1 and k = 4; and
the wall-clock times were recorded.

## Files

- `run.sh`: the lab. `generate.py`: sends one prompt set at one
  temperature. `accept.py`: acceptance from two `/metrics` scrapes.
  `wallclock.py`: the interleaved timing. `prompts.json`: the two
  prompt sets. `test.sh`: runs, asserts.
- Output lands in `measured/ch12/`: `acceptance.jsonl` (one row
  per setting), `spec-<task>-t<T>.json` (every request's text and
  timings, including the server's per-request `draft_n` and
  `draft_n_accepted`), `wallclock.json` and `machine.json`.
