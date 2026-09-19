#!/usr/bin/env python3
# lib/metrics.py
"""Read a server's Prometheus /metrics from a lab, standard library
only.

  metrics.py get URL NAME...
      Print each metric's value, summed over its label sets (0 if
      the server does not export it). NAME is the scraped name,
      with its _total or _count suffix.

  metrics.py watch URL OUT [SECONDS]
      Scrape URL every SECONDS (default 1) until SIGTERM or SIGINT,
      keeping the series vLLM's dashboards and the book's panels
      read (FAMILIES) and every llamacpp: series, then write them
      to OUT as OpenMetrics text with timestamps (gzipped if OUT
      ends in .gz). The file replays into any Prometheus:
        promtool tsdb create-blocks-from openmetrics FILE DIR
"""
import gzip
import re
import signal
import sys
import time
import urllib.request

LINE = re.compile(r"^([A-Za-z_:][\w:]*)(\{[^}]*\})?\s+(\S+)")
FAMILIES = {"vllm:" + f for f in (
    "num_requests_running", "num_requests_waiting",
    "kv_cache_usage_perc", "num_preemptions",
    "prefix_cache_queries", "prefix_cache_hits",
    "prompt_tokens", "generation_tokens", "request_success",
    "time_to_first_token_seconds", "inter_token_latency_seconds",
    "e2e_request_latency_seconds",
    "request_time_per_output_token_seconds")}


def scrape(url):
    with urllib.request.urlopen(url.rstrip("/") + "/metrics",
                                timeout=10) as r:
        return r.read().decode("utf-8")


def parse(text):
    """Yield (name, labels, value, type) for every sample."""
    types = {}
    for line in text.splitlines():
        if line.startswith("# TYPE "):
            _, _, name, kind = line.split(maxsplit=3)
            types[name] = kind
            continue
        if not line or line.startswith("#"):
            continue
        m = LINE.match(line)
        if m:
            name, labels, value = m.groups()
            yield name, labels or "", float(value), types


def get(url, names):
    total = dict.fromkeys(names, 0.0)
    for name, _, value, _ in parse(scrape(url)):
        if name in total:
            total[name] += value
    for name in names:
        print(f"{total[name]:g}")


def family(name, types):
    """The metric family a sample belongs to, and its type."""
    for suffix in ("_bucket", "_count", "_sum", "_total", ""):
        base = name[: len(name) - len(suffix)] if suffix else name
        if name.endswith(suffix) and base in types:
            return base, types[base]
        if name.endswith(suffix) and base + "_total" in types:
            return base, types[base + "_total"]
    return name, "unknown"


def watch(url, out, every):
    stop = []
    signal.signal(signal.SIGTERM, lambda *a: stop.append(1))
    signal.signal(signal.SIGINT, lambda *a: stop.append(1))
    points = {}  # family -> {series: [(ts, [(name, labels, v)])]}
    kinds = {}
    while not stop:
        t0 = time.time()
        try:
            text = scrape(url)
        except OSError:
            text = ""
        ts = round(time.time(), 3)
        batch = {}
        for name, labels, value, types in parse(text):
            if name.endswith("_created"):
                continue
            fam, kind = family(name, types)
            if fam not in FAMILIES and \
                    not fam.startswith("llamacpp:"):
                continue
            kinds[fam] = kind
            series = re.sub(r',?le="[^"]*"', "", labels)
            series = series.replace("{,", "{")
            key = (fam, series)
            batch.setdefault(key, []).append((name, labels, value))
        for (fam, series), samples in batch.items():
            points.setdefault(fam, {}).setdefault(series, []).append(
                (ts, samples))
        time.sleep(max(0.0, every - (time.time() - t0)))
    opener = gzip.open if out.endswith(".gz") else open
    with opener(out, "wt", encoding="utf-8") as f:
        for fam in sorted(points):
            kind = kinds[fam].replace("untyped", "unknown")
            base = fam[:-6] if kind == "counter" and \
                fam.endswith("_total") else fam
            f.write(f"# TYPE {base} {kind}\n")
            for series in sorted(points[fam]):
                for ts, samples in points[fam][series]:
                    for name, labels, value in samples:
                        f.write(f"{name}{labels} {value!r} {ts}\n")
        f.write("# EOF\n")


if __name__ == "__main__":
    cmd, url, *rest = sys.argv[1:]
    if cmd == "get":
        get(url, rest)
    elif cmd == "watch":
        watch(url, rest[0], float(rest[1]) if len(rest) > 1 else 1.0)
    else:
        sys.exit(__doc__)
