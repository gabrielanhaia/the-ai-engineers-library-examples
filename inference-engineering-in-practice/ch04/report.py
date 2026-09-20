# ch04/report.py
"""Short tables from the files ch04/run.sh records.

  report.py sweep GUIDELLM_JSON    one row per GuideLLM benchmark
  report.py loops DIR              closed vs open loop, same rate
  report.py cache DIR              the reused seed and the counter
  report.py derived DIR            every number the chapter prints
"""
import contextlib
import gzip
import io
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

        # This book's TPOT excludes the first token, which is
        # GuideLLM's inter_token_latency_ms; its own
        # time_per_output_token_ms includes it.
        conc = m["request_concurrency"]["successful"]["mean"]
        rate = m["requests_per_second"]["successful"]["mean"]
        kind = b["config"]["strategy"]["type_"]
        r = b["config"]["strategy"].get("rate")
        label = f"{kind} {r:.2f}" if r else kind
        print(f" {label:12s} {rate:6.2f} {conc:10.1f}"
              f" {pct('time_to_first_token_ms', 'p50'):6.0f} ms"
              f" {pct('time_to_first_token_ms', 'p99'):6.0f} ms"
              f" {pct('inter_token_latency_ms', 'p50'):6.0f} ms")


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


def _capture(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args)
    return buf.getvalue()


def _arrivals(bench):
    """Every request of one sweep point, by the time it went out."""
    rs = (bench["requests"]["successful"]
          + bench["requests"]["incomplete"])
    return sorted(r["info"]["timings"]["targeted_start"] for r in rs)


def derived(d):
    """Every number chapter 4 prints, from the recorded files.

    Nothing here runs a benchmark: it reads measured/ch04/ and
    prints the JSON scripts/check_derived.py compares against
    measured/ch04/derived.json.
    """
    n = []

    def num(key, value, shown):
        n.append({"key": key, "value": value, "shown": shown})

    g = load(f"{d}/guidellm.json")
    sync = g["benchmarks"][0]
    rs = sorted(sync["requests"]["successful"],
                key=lambda r: r["request_start_time"])
    t = [r["time_to_first_token_ms"] for r in rs]
    rest = sorted(t[1:])
    num("sweep.sync_first_ttft_ms", t[0], f"{t[0]:,.0f} ms")
    num("sweep.sync_rest_min_ms", rest[0], f"{rest[0]:.0f}")
    num("sweep.sync_rest_max_ms", rest[-1], f"{rest[-1]:.0f}")
    num("sweep.sync_requests", len(t), f"{len(t)} samples")
    num("sweep.prompt_tokens", rs[0]["prompt_tokens"],
        f"{rs[0]['prompt_tokens']}")

    poisson = [b for b in g["benchmarks"]
               if b["config"]["strategy"]["type_"] == "poisson"]
    first = poisson[0]
    rate = first["metrics"]["requests_per_second"]["successful"]
    num("sweep.poisson1_label_rate",
        first["config"]["strategy"]["rate"],
        f"poisson {first['config']['strategy']['rate']:.2f}")
    num("sweep.poisson1_rate", rate["mean"], f"{rate['mean']:.2f}")
    starts = _arrivals(first)
    for i, which in ((0, "first"), (10, "second"), (20, "third")):
        gap = starts[i + 1] - starts[i]
        num(f"sweep.poisson1_gap_{which}_ten", gap, f"{gap:.3f}")

    for name in ("closed", "open"):
        r = load(f"{d}/{name}.json")
        p50, p99 = r["median_ttft_ms"], r["p99_ttft_ms"]
        num(f"loops.{name}_rate", r["request_throughput"],
            f"{r['request_throughput']:.2f}")
        num(f"loops.{name}_ttft_p50_ms", p50, f"{p50:,.0f} ms")
        num(f"loops.{name}_ttft_p99_ms", p99, f"{p99:,.0f} ms")
        num(f"loops.{name}_p99_over_p50", p99 / p50,
            f"{p99 / p50:.1f} times")
        peak = peak_running(d, name)
        num(f"loops.{name}_peak_running", peak, f"{peak}")

    runs = {}
    for line in open(f"{d}/cache.tsv"):
        run, h0, q0, h1, q1 = line.split()
        r = load(f"{d}/cache-{run}.json")
        runs[run] = {"hits": float(h1) - float(h0),
                     "queries": float(q1) - float(q0),
                     "prompts": r["completed"],
                     "ttft_p50_ms": r["median_ttft_ms"],
                     "tok_s": r["total_token_throughput"]}
    again, cold, new = runs["again"], runs["first"], runs["new-seed"]
    num("cache.hits", again["hits"], f"{again['hits']:,.0f}")
    num("cache.queries", again["queries"],
        f"{again['queries']:,.0f}")
    hit_rate = again["hits"] / again["queries"]
    num("cache.hit_rate", hit_rate, f"{hit_rate:.3f}")
    per_prompt = again["hits"] / again["prompts"]
    num("cache.hits_per_prompt", per_prompt, f"{per_prompt:,.0f}")
    # The chapter prints the new seed's median inside a
    # subtraction, so that one is shown without its unit.
    for key, run, unit in (("first", cold, " ms"),
                           ("again", again, " ms"),
                           ("new_seed", new, "")):
        num(f"cache.{key}_ttft_p50_ms", run["ttft_p50_ms"],
            f"{run['ttft_p50_ms']:,.0f}{unit}")
        num(f"cache.{key}_tok_s", run["tok_s"],
            f"{run['tok_s']:,.1f}")
    num("cache.speedup", again["tok_s"] / cold["tok_s"],
        f"{again['tok_s'] / cold['tok_s']:.1f}")
    gap = cold["ttft_p50_ms"] - new["ttft_p50_ms"]
    num("cache.cold_ttft_gap_ms", gap, f"{gap:,.0f} ms")

    print(json.dumps(
        {"chapter": "04",
         "outputs": {
             "report.py sweep": _capture(
                 sweep, f"{d}/guidellm.json"),
             "report.py loops": _capture(loops, d),
             "report.py cache": _capture(cache, d)},
         "numbers": n}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    {"sweep": sweep, "loops": loops, "cache": cache,
     "derived": derived}[sys.argv[1]](*sys.argv[2:])
