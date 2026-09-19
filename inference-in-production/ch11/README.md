# ch11: prove the accuracy

Chapter 11's lab: one model, SmolLM2-360M-Instruct, in three GGUF
files (F16, Q8_0, Q4_K_M), judged against F16 three ways on the
same pinned text, then timed.

## What it does

1. Fetches the three GGUF files (1,319 MiB) and the pinned text:
   WikiText-2 (raw), test split, from the `ggml-org/ci` dataset at
   commit `927b3642933080f1b0e811e2f916e14c292992f9`, checked
   against its SHA-256. It is downloaded at run time, never stored
   in this repository.
2. `llama perplexity` on F16 over the first 100 chunks of 512
   tokens, with `--kl-divergence-base`: F16's perplexity, and its
   logits saved as the reference (about 2.5 GB in the scratch
   volume, deleted when the step is done).
3. `llama perplexity` on Q8_0 and Q4_K_M with
   `--kl-divergence-base` and `--kl-divergence`: each file's
   perplexity on the same tokens, and how far its next-token
   distribution moved from F16's (mean KL divergence, how often the
   top token is the same, and the percentiles of the change in the
   correct token's probability).
4. A small task eval (`tasks.json`, written 2026-09-19): 40 fixed
   questions with checkable answers, 20 of them a date or a number,
   asked of each file greedily through llama.cpp's server
   (`eval.py`).
5. `llama bench` decode speed for each file, measured as in ch02
   (64 generated tokens, 5 runs, at 2, 4, 6, ... threads; each
   file's fastest thread count by the median of its runs), and bits
   per weight as file bytes x 8 / parameters.
6. `summary.py` collects everything into one table and
   `results.json`.

## Run it

```sh
docker compose run --rm inference-in-production ch11
```

About ten minutes on the reference laptop, plus the first
download. `CH11_CHUNKS` sets the number of 512-token chunks
(default 100).

## Expected output

Recorded on the reference laptop (Apple M2 Pro, 16 GB, OrbStack,
linux/arm64, CPU only). This block is
[`../measured/ch11/output.txt`](../measured/ch11/output.txt):

```

== models and the pinned text
models: 3 file(s), 1,319 MiB, into /models
  ok      gguf/SmolLM2-360M-Instruct-f16.gguf
  ok      gguf/SmolLM2-360M-Instruct-Q8_0.gguf
  ok      gguf/SmolLM2-360M-Instruct-Q4_K_M.gguf
/scratch/ch11/wikitext.zip: OK

== F16: perplexity; its logits become the reference
Final estimate: PPL = 13.9634 +/- 0.25031

== Q8_0: perplexity and KL divergence against F16
Mean PPL(Q)                   :  13.990674 ±   0.250594
Mean PPL(base)                :  13.942580 ±   0.249247
Mean PPL(Q)/PPL(base)         :   1.003449 ±   0.000664
Mean PPL(Q)-PPL(base)         :   0.048094 ±   0.009324
Mean    KLD:   0.002944 ±   0.000022
99.0%   Δp:  4.022%
 1.0%   Δp: -4.346%
Same top p: 96.694 ± 0.112 %

== Q4_K_M: perplexity and KL divergence against F16
Mean PPL(Q)                   :  14.268128 ±   0.256326
Mean PPL(base)                :  13.942580 ±   0.249247
Mean PPL(Q)/PPL(base)         :   1.023349 ±   0.001673
Mean PPL(Q)-PPL(base)         :   0.325548 ±   0.024095
Mean    KLD:   0.025471 ±   0.000244
99.0%   Δp: 10.858%
 1.0%   Δp: -13.876%
Same top p: 91.110 ± 0.178 %

== task eval: f16 (greedy, 40 items)
llama ready after ~2s
39/40 correct; dates and numbers 20/20

== task eval: Q8_0 (greedy, 40 items)
llama ready after ~2s
38/40 correct; dates and numbers 19/20

== task eval: Q4_K_M (greedy, 40 items)
llama ready after ~1s
38/40 correct; dates and numbers 19/20

== decode speed: llama bench, CPU, threads 2,4,6,8,10
llama.cpp build b10964, commit b29c606e2

== summary (perplexity and KLD on 100 chunks of 512 tokens)
format  bits/w     PPL     KLD  top %   eval    d/n  tok/s
f16      16.04  13.963       -      -  39/40  20/20  128.0
Q8_0      8.54  13.991  0.0029   96.7  38/40  19/20  200.4
Q4_K_M    5.98  14.268  0.0255   91.1  38/40  19/20  223.3
bits/w = file bytes x 8 / 361,821,120 parameters
Q4_K_M vs F16: 2.68x fewer bytes, 1.74x the decode speed

== done
manifest: measured/ch11/machine.json
```

## What the test asserts

`test ch11` runs the lab on 16 chunks, then checks orderings that
the model and the algorithm set, with a wide margin: Q4_K_M's
perplexity is above both Q8_0's and F16's; Q8_0 stays closer to F16
than Q4_K_M does; Q4_K_M's KL divergence is above Q8_0's and its
same-top-token share below; the eval scored all 40 items on every
file; and bits per weight order F16 > Q8_0 > Q4_K_M > 4.89. It does
not assert F16 <= Q8_0 on perplexity: on a short text their
difference is smaller than its noise, and either can come out
lower.

## Files

- `run.sh`: the lab. `eval.py`, `tasks.json`: the task eval.
  `summary.py`: the table. `test.sh`: runs, asserts.
- Output lands in `measured/ch11/`: `ppl-f16.log`, `kld-Q8_0.log`,
  `kld-Q4_K_M.log` (llama perplexity, as written), `eval-*.json`
  (every question's reply and score), `bench.json`, `sizes.json`,
  `results.json` and `machine.json`.
