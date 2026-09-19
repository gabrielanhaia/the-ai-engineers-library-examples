# ch09/report.py
"""One row per concurrency: was it predicted to fit, and what did
the engine's own series say while that batch ran? The last column
is vllm:num_preemptions_total itself, after the batch.

Reads measured/ch09/: prediction.json, levels.tsv (concurrency,
start, end, preemptions before and after, written by run.sh) and
metrics.om.gz (the /metrics series, scraped once a second).
"""
import gzip
import json
import re
import sys

d = sys.argv[1] if len(sys.argv) > 1 else "."
pred = json.load(open(f"{d}/prediction.json"))
series = {}
pat = re.compile(r"^(vllm:\w+?)(?:\{[^}]*\})? (\S+) (\S+)$")
for line in gzip.open(f"{d}/metrics.om.gz", "rt"):
    m = pat.match(line)
    if m:
        ts, v = float(m.group(3)), float(m.group(2))
        series.setdefault(m.group(1), []).append((ts, v))


def peak(name, t0, t1):
    vals = [v for ts, v in series.get(name, []) if t0 <= ts <= t1]
    return max(vals, default=0.0)


rows = []
print(" conc  predicted  peak running  peak KV use  preemptions"
      "  counter")
for line in open(f"{d}/levels.tsv"):
    n, t0, t1, p0, p1 = line.split()
    n, t0, t1 = int(n), float(t0), float(t1)
    fit = "fits" if n < pred["first_preempting"] else "overflows"
    run = int(peak("vllm:num_requests_running", t0, t1))
    kv = peak("vllm:kv_cache_usage_perc", t0, t1)
    pre = int(float(p1) - float(p0))
    total = int(float(p1))
    rows.append({"concurrency": n, "predicted": fit,
                 "peak_running": run, "peak_kv_usage": kv,
                 "preemptions": pre, "counter_after": total,
                 "seconds": round(t1 - t0, 1)})
    print(f"{n:5d}  {fit:9s}  {run:12d}  {kv:11.2f}  {pre:11d}"
          f"  {total:7d}")
with open(f"{d}/levels.json", "w") as f:
    json.dump(rows, f, indent=1)
