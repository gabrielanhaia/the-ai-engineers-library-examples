# ch13: the layout calculator

Nothing in chapter 13 runs on a laptop, and this lab does not pretend
otherwise: it computes. Three formulas, every input a cited number in
`inputs/`, every result DERIVED. No GPU is used or needed.

## What it does

1. KV copies under tensor parallelism: TP / KV heads, never below one,
   and the valid `-dcp` range (1 to TP / KV heads), at TP 8 for
   DeepSeek-R1, Qwen3-235B-A22B and Llama-3.1-70B.
2. The TP memory unlock: the KV budget of Llama-3.1-70B in FP8 on
   H100 (80 GB x 0.92) at TP=1, as two replicas and at TP=2, in GB,
   tokens and 8K conversations; and the 8B model that already fits.
3. The P:D ratio = (ISL / R_prefill) : (OSL / R_decode), from SGLang's
   per-node rates and InferenceX's three request shapes, and the KV an
   8K prompt moves from prefill to decode.
4. Recomputes every DERIVED number chapter 13 prints into
   `measured/ch13/derived.json` (`derived.py`).

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch13
```

Pure Python on the runner, a few seconds. For your own rates and
shapes, change them in `inputs/parallelism.toml`.

## Expected output

Recorded on the reference laptop (Apple M2 Pro, 16 GB, OrbStack,
linux/arm64). This block is
[`../measured/ch13/output.txt`](../measured/ch13/output.txt):

```

== three layout formulas
KV copies at TP 8: TP / KV heads, never below 1
model              KV heads  copies      -dcp
DeepSeek-R1               1       8    1 to 8
Qwen3-235B-A22B           4       2    1 to 2
Llama-3.1-70B             8       1    1 to 1

Llama-3.1-70B in FP8 (70.55 GB) on H100: 80 x 0.92
= 73.60 GB per GPU; FP8 KV is 163,840 bytes a token
layout         GPUs   KV GB   KV tokens  8K chats
TP=1              1    3.05      18,593         2
two replicas      2    6.09      37,186         4
TP=2              2   76.65     467,811        57
TP=2 holds 12.6x the KV of two replicas; the 70.55 GB
between them is the second copy of the weights, now KV
Llama-3.1-8B in BF16 leaves 57.54 GB on one H100; TP=2 frees
only the second copy of its 16.06 GB of weights

P:D = (ISL / R_prefill) : (OSL / R_decode)
per node: 52,300 input, 22,300 output tokens/s (SGLang)
shape                ISL:OSL     P:D  prefill : decode
summarization 8k/1k      8:1    3.41           3.4 : 1
chat 1k/1k               1:1   0.426           1 : 2.3
reasoning 1k/8k          1:8   0.053          1 : 18.8
the right ratio moves 64x across the three shapes
an 8K prompt's KV to move: 8,192 x 163,840 B = 1.34 GB

== every DERIVED number in chapter 13
29 numbers, recomputed from inputs/: measured/ch13/derived.json

== done
manifest: measured/ch13/machine.json
```

## What the test asserts

`test ch13` runs the lab, then checks what must stay true of the
formulas, never their numbers: copies never fall below one; the TP=2
budget exceeds the two-replica budget by exactly one copy of the
weights, to the byte; the P:D ratio does not move when the arrival
rate doubles. The numbers themselves are checked by the
`derived-data` CI job (`scripts/check_derived.py`).

## Files

- `layout.py`: the calculator (printed in chapter 13).
- `derived.py`: every DERIVED number chapter 13 prints, as JSON.
- `run.sh`, `test.sh`: the lab and its test.
