# ch04/report.py
"""Short tables from the files ch04/run.sh records.

  report.py sweep GUIDELLM_JSON    one row per GuideLLM benchmark
  report.py loops DIR              closed vs open loop, same rate
  report.py cache DIR              the reused seed and the counter
"""
import gzip
import json
import re
import sys


def load(path):
    with open(path) as f:
        return json.load(f)


def sweep(path):
    print(" strategy      req/s  in flight  TTFT p50  TTFT p99"
          "  TPOT p50")
    for b in load(path)["benchmarks"]:
        m = b["metrics"]

        def pct(name, p):
            return m[name]["successful"]["percentiles"][p]

        conc = m["request_concurrency"]["successful"]["mean"]
        rate = m["requests_per_second"]["successful"]["mean"]
        kind = b["config"]["strategy"]["type_"]
        r = b["config"]["strategy"].get("rate")
        label = f"{kind} {r:.2f}" if r else kind
        print(f" {label:12s} {rate:6.2f} {conc:10.1f}"
              f" {pct('time_to_first_token_ms', 'p50'):6.0f} ms"
              f" {pct('time_to_first_token_ms', 'p99'):6.0f} ms"
              f" {pct('time_per_output_token_ms', 'p50'):6.0f} ms")


def peak_running(d, name):
    """The most requests the server ran at once during run NAME,
    from its own gauge, scraped once a second."""
    t0, t1 = next(map(float, x.split()[1:]) for x in
                  open(f"{d}/runs.tsv") if x.split()[0] == name)
    pat = re.compile(r"^vllm:num_requests_running\{.*\} (\S+) (\S+)$")
    vals = [float(m[1]) for m in map(pat.match, gzip.open(
        f"{d}/metrics.om.gz", "rt")) if m and t0 <= float(m[2]) <= t1]
    return int(max(vals, default=0))


def loops(d):
    print(" loop     rate req/s  peak running  TTFT p50  TTFT p99")
    for name in ("closed", "open"):
        r = load(f"{d}/{name}.json")
        print(f" {name:7s} {r['request_throughput']:11.2f}"
              f" {peak_running(d, name):13d}"
              f" {r['median_ttft_ms']:6.0f} ms"
              f" {r['p99_ttft_ms']:6.0f} ms")


def cache(d):
    print(" run       seed  hit rate  TTFT p50  total tok/s")
    for line in open(f"{d}/cache.tsv"):
        run, h0, q0, h1, q1 = line.split()
        r = load(f"{d}/cache-{run}.json")
        hits, queries = float(h1) - float(h0), float(q1) - float(q0)
        seed = 1 if run == "new-seed" else 0
        print(f" {run:9s} {seed:4d} {hits / queries:9.2f}"
              f" {r['median_ttft_ms']:6.0f} ms"
              f" {r['total_token_throughput']:12.1f}")


if __name__ == "__main__":
    {"sweep": sweep, "loops": loops, "cache": cache}[sys.argv[1]](
        *sys.argv[2:])
