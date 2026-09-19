# inputs

Every cited number the calculators use (`ch05/`, `ch06/`, `ch07/`,
`ch13/`, `ch19/`), each with the URL it came from and the date it was
read. The book's DERIVED numbers are arithmetic on these files and on
nothing else: no number the book prints is typed into a script.

## The files

| File | What | Used by |
|---|---|---|
| `example-a.toml` | Worked example A: MLPerf's request shape and rates for gpt-oss-120b on a Nebius 8 x B200 node, the Nebius GPU prices, the Together, Baseten and Fireworks API prices, a developer's wage. Printed in chapter 6. | ch05, ch06, ch07, ch19 |
| `mlperf-v6.1-summary.csv` | MLPerf Inference v6.1 results: the header and the rows used, copied verbatim from `summary.csv` at a pinned commit | ch05 (reads its rows), ch06, ch07 |
| `mlperf-v5.1-results.json` | MLPerf Inference v5.1: the two result objects used (Nebius 8 x H200, Llama 2 70B), verbatim | ch05, ch06 |
| `mlperf-rules.toml` | MLPerf's p99 TTFT and TPOT bounds per benchmark and scenario; MLPerf counts output tokens | ch05, ch06 |
| `prices.toml` | The other list prices: CoreWeave, AWS, Lambda, dedicated endpoints, SemiAnalysis's modeled costs, Anthropic, Gemini | ch05, ch06 |
| `hardware.toml` | GPU memory and bandwidth as the datasheets print them (decimal GB, TB/s); vLLM's memory fraction, 0.92 | ch07, ch13 |
| `models.toml` | Parameter counts and attention shapes (layers, KV heads, head size), at pinned revisions | ch07, ch13 |
| `traffic.toml` | Peak-to-average and peak-to-valley load from Azure production traces (DynamoLLM) | ch05, ch06, ch07, ch19 |
| `parallelism.toml` | Megatron-style TP's all-reduces per layer; SGLang's per-phase rates; InferenceX's request shapes | ch05, ch13 |
| `deepseek-day.toml` | DeepSeek's published day of V3/R1 inference | ch05 |

## The rules

- Every TOML table (or the file, at its top) carries `url` and
  `checked`, a date. `scripts/check_derived.py` fails if one is missing.
- One number, one place. The one exception is a transcription the book
  prints: `example-a.toml` repeats two MLPerf rows and their bound, and
  the check fails if they ever differ from `mlperf-v6.1-summary.csv`
  and `mlperf-rules.toml`.
- The MLPerf files are copied verbatim, with our provenance lines
  (starting with `#`) on top; the rest is MLCommons's, Apache-2.0.
- No laptop measurement lives here. A laptop's tokens per second
  describe the laptop, and no calculator multiplies them by a GPU
  price.

## When a price moves

Change it here, run the labs that use it, and commit the new
`measured/chNN/derived.json` with it:

```sh
docker compose run --rm inference-in-production ch06
python3 inference-in-production/scripts/check_derived.py
```

The `derived-data` CI job reruns every `chNN/derived.py` against these
files and fails on any difference from `measured/chNN/derived.json`, so
a changed input cannot go unnoticed. Against the manuscript (not in
this repository), `--manuscript <book>/en/content/chapters` also checks
that every number the chapter prints is the one recomputed here.
