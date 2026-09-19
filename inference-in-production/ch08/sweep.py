# ch08/sweep.py
"""The laptop's curve: one row per concurrency, from the result
files `vllm bench serve --save-result` wrote into measured/ch08/.
Also writes sweep.csv, the data behind the chapter's figure.
"""
import csv
import glob
import json
import sys

d = sys.argv[1] if len(sys.argv) > 1 else "."
runs = [json.load(open(f)) for f in glob.glob(f"{d}/bench-c*.json")]
runs.sort(key=lambda r: r["max_concurrency"])
cols = ["concurrency", "requests", "output_tok_s", "ttft_p50_ms",
        "tpot_mean_ms", "tpot_p99_ms"]
rows = [[r["max_concurrency"], r["completed"], r["output_throughput"],
         r["median_ttft_ms"], r["mean_tpot_ms"], r["p99_tpot_ms"]]
        for r in runs]
print(" conc  output tok/s  x conc 1  TTFT p50  TPOT mean  TPOT p99")
for c, _, tput, ttft, tpot, tpot99 in rows:
    print(f"{c:5d}  {tput:12.1f}  {tput / rows[0][2]:8.1f}"
          f"  {ttft:5.0f} ms  {tpot:6.0f} ms  {tpot99:5.0f} ms")
with open(f"{d}/sweep.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(cols)
    w.writerows(rows)
