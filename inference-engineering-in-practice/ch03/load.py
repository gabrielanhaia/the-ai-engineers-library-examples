# ch03/load.py
"""Open-loop load: streamed chat requests at Poisson arrivals.

    python3 load.py URL --rate R --n N          > records.jsonl
    python3 load.py URL --ramp R1,R2,... --step-s S > records.jsonl

Each request leaves at its scheduled time, whatever happened to the
ones before it, so a slow server builds a queue instead of slowing
the client down. Every streamed chunk is stamped with the client's
monotonic clock the moment it arrives. One JSON record per request.
"""
import argparse
import http.client
import json
import random
import threading
import time
import urllib.parse

PROMPTS = open("prompts.txt", encoding="utf-8").read().splitlines()


def schedule(args):
    """(offered rate, send offset in s) for every request."""
    rng, out = random.Random(args.seed), []
    if args.ramp:
        steps = [float(r) for r in args.ramp.split(",")]
        for i, rate in enumerate(steps):
            t = i * args.step_s
            while True:
                t += rng.expovariate(rate)
                if t >= (i + 1) * args.step_s:
                    break
                out.append((rate, t))
    else:
        t = 0.0
        for _ in range(args.n):
            t += rng.expovariate(args.rate)
            out.append((args.rate, t))
    return out


def one(url, model, i, rate, rec):
    u = urllib.parse.urlsplit(url)
    body = {"messages": [{"role": "user",
                          "content": PROMPTS[i % len(PROMPTS)]}],
            "max_tokens": 64, "ignore_eos": True, "temperature": 0,
            "stream": True, "stream_options": {"include_usage": True},
            "cache_prompt": False}
    if model:
        body["model"] = model
    rec.update(id=i, offered_rate=rate, text_chunk_times=[],
               chunks=0, output_tokens=None, timings=None, error=None)
    conn = http.client.HTTPConnection(u.hostname, u.port, timeout=600)
    try:
        rec["sent"] = time.perf_counter()
        conn.request("POST", "/v1/chat/completions", json.dumps(body),
                     {"Content-Type": "application/json"})
        resp = conn.getresponse()
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        while line := resp.readline():
            now = time.perf_counter()
            if not line.startswith(b"data: {"):
                continue
            ev = json.loads(line[6:])
            rec["chunks"] += 1
            ch = ev.get("choices") or [{}]
            if ch[0].get("delta", {}).get("content"):
                rec["text_chunk_times"].append(now)
            if ev.get("timings"):
                rec["timings"] = ev["timings"]
            if usage := ev.get("usage"):
                rec["output_tokens"] = usage["completion_tokens"]
    except Exception as e:  # recorded, and it fails the SLO
        rec["error"] = repr(e)
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("--model")
    p.add_argument("--rate", type=float)
    p.add_argument("--n", type=int)
    p.add_argument("--ramp")
    p.add_argument("--step-s", type=float, default=60)
    p.add_argument("--seed", type=int, default=3)
    args = p.parse_args()
    plan, records, threads = schedule(args), [], []
    start = time.perf_counter()
    for i, (rate, at) in enumerate(plan):
        time.sleep(max(0.0, start + at - time.perf_counter()))
        rec = {"scheduled": at}
        records.append(rec)
        th = threading.Thread(
            target=one, args=(args.url, args.model, i, rate, rec))
        th.start()
        threads.append(th)
    for th in threads:
        th.join()
    for rec in records:
        rec["sent"] -= start       # times relative to the run start
        rec["text_chunk_times"] = [t - start
                                   for t in rec["text_chunk_times"]]
        print(json.dumps(rec))


if __name__ == "__main__":
    main()
