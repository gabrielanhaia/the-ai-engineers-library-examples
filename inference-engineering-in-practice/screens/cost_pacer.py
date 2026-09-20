#!/usr/bin/env python3
"""Drive llm-d-inference-sim at an exact output-token rate, and record
the counter as OpenMetrics.

Chapter 15's cost rule divides a node's hourly price by the output
tokens the node made in that hour. Fed a laptop's tokens it prints a
confident dollar figure that means nothing, so the lab never loads it.
The screenshot instead drives the simulator at chapter 5's CITED rate
-- MLPerf v6.1 Server, 89,856.3 output tokens a second for one node of
eight B200s -- so the panel shows chapter 5's own number and nothing
the laptop earned.

The pacing is closed-loop on the simulator's own counter, not on a
request schedule: every tick it asks for exactly the tokens the line
`rate x elapsed` is short, with `ignore_eos` so the simulator emits
exactly that many. The counter therefore tracks the cited rate to
within one tick, and `rate(...[5m])` over it is the cited rate.

    python3 screens/cost_pacer.py --url http://127.0.0.1:8011 \\
        --minutes 12 --out measured/ch15/cost-sim.om

Nothing here is a measurement. The output file says `kind="simulated"`
on every sample, and so does the figure's caption.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

# MLPerf Inference v6.1 Server, one node of eight B200s, output tokens
# per second, as chapter 5 cites it (inputs/ch05/).
CITED_RATE = 89856.3
COUNTER = "vllm:generation_tokens_total"


def scrape(url: str) -> float:
    with urllib.request.urlopen(url + "/metrics", timeout=10) as r:
        for line in r.read().decode().splitlines():
            if line.startswith(COUNTER):
                return float(line.rsplit(None, 1)[1])
    return 0.0


def ask(url: str, model: str, tokens: int) -> None:
    body = json.dumps(
        {"model": model, "prompt": "x", "max_tokens": tokens,
         "ignore_eos": True}
    ).encode()
    req = urllib.request.Request(
        url + "/v1/completions", data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        r.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8011")
    ap.add_argument("--model", default="gpt-oss")
    ap.add_argument("--rate", type=float, default=CITED_RATE)
    ap.add_argument("--minutes", type=float, default=12.0)
    ap.add_argument("--tick", type=float, default=0.1)
    ap.add_argument("--scrape-every", type=float, default=5.0)
    ap.add_argument("--max-tokens-per-request", type=int, default=60000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    base = scrape(a.url)
    t0 = time.time()
    samples: list[tuple[float, float]] = []
    next_scrape = t0
    end = t0 + a.minutes * 60
    worst = 0.0

    while True:
        now = time.time()
        if now >= next_scrape:
            samples.append((now, scrape(a.url) - base))
            next_scrape += a.scrape_every
        if now >= end:
            break
        want = a.rate * (now - t0)
        have = scrape(a.url) - base
        worst = max(worst, abs(want - have))
        short = int(round(want - have))
        while short > 0:
            n = min(short, a.max_tokens_per_request)
            ask(a.url, a.model, n)
            short -= n
        slack = a.tick - (time.time() - now)
        if slack > 0:
            time.sleep(slack)

    with open(a.out, "w") as fh:
        fh.write("# TYPE vllm:generation_tokens counter\n")
        for ts, v in samples:
            fh.write(
                f'{COUNTER}{{model_name="{a.model}",kind="simulated"}}'
                f" {v:.0f} {ts:.3f}\n"
            )
        fh.write("# EOF\n")

    span = samples[-1][0] - samples[0][0]
    got = (samples[-1][1] - samples[0][1]) / span
    print(f"wrote {a.out}: {len(samples)} samples over {span:.0f}s")
    print(f"configured rate {a.rate:,.1f} tok/s, "
          f"achieved {got:,.1f} tok/s ({100 * got / a.rate:.4f}%)")
    print(f"worst drift from the line: {worst:,.0f} tokens "
          f"({worst / a.rate * 1000:.0f} ms of generation)")
    print(f"window {samples[0][0]:.0f} .. {samples[-1][0]:.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
