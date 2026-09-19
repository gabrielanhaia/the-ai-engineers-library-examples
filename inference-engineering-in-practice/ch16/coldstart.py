# ch16/coldstart.py
"""Helpers for the ch16 cold start.

  ttft URL TEXT     one streamed chat request; prints seconds to the
                    first chunk that carries text
  phases FILE ...   turn one run's records into its phases (JSON)

The phases add up to the total, from `kubectl apply` to a healthy
server: the image pull (the kubelet's own figure); start, up to the
container's first log line; the weight load and the engine warm-up
(vLLM's own log lines; warm-up includes torch.compile); and the
rest (engine set-up and the API server), the remainder.
"""
import json
import re
import sys
import time
import urllib.request
from datetime import datetime


def ttft(url, text):
    body = json.dumps({
        "model": "smollm2-360m", "max_tokens": 16, "stream": True,
        "messages": [{"role": "user", "content": text}]})
    req = urllib.request.Request(
        url + "/v1/chat/completions", body.encode(),
        {"Content-Type": "application/json"})
    t0 = time.monotonic()
    seen = []
    with urllib.request.urlopen(req, timeout=600) as r:
        for line in r:
            seen.append(line)
            if line.startswith(b"data: {"):
                d = json.loads(line[6:])
                if d.get("choices") and \
                        d["choices"][0]["delta"].get("content"):
                    return time.monotonic() - t0
    body = b"".join(seen).decode(errors="replace")[:400]
    raise SystemExit(f"no text in the stream: {body}")


def go_seconds(s):
    """Go's duration text (1m2.5s, 812ms) in seconds."""
    total = 0.0
    for n, unit in re.findall(r"([\d.]+)(ms|s|m|h)", s):
        total += float(n) * {"ms": 1e-3, "s": 1, "m": 60,
                             "h": 3600}[unit]
    return total


def stamp(line):
    """The UTC time `kubectl logs --timestamps` put on a line."""
    head, _, frac = line.split()[0].rstrip("Z").partition(".")
    t = datetime.fromisoformat(head + "+00:00").timestamp()
    return t + float("0." + (frac or "0"))


def phases(run, t_apply, t_up, events, log, t1, t2):
    pull, cached = None, False
    for e in json.load(open(events))["items"]:
        msg = e.get("message", "")
        if e.get("reason") == "Pulled":
            m = re.search(r"pulled image .* in (\S+) \(", msg)
            if m:
                pull = go_seconds(m.group(1))
            elif "already present" in msg:
                pull, cached = 0.0, True
    lines = open(log).read().splitlines()

    def took(pattern):
        for ln in lines:
            m = re.search(pattern + r" took ([\d.]+) s", ln)
            if m:
                return float(m.group(1))
        return None

    def at(text):
        return next((stamp(ln) for ln in lines if text in ln), None)

    t_apply, t_up = float(t_apply), float(t_up)
    total = t_up - t_apply
    start = stamp(lines[0]) - t_apply - (pull or 0.0)
    weights = took(r"Loading weights")
    warm = took(r"init engine \(profile, create kv cache, "
                r"warmup model\)")
    c0 = at("Warming up model for the compilation")
    c1 = at("saved AOT compiled function")
    known = [x for x in (pull, start, weights, warm) if x is not None]
    return {"run": int(run), "image_cached": cached,
            "pull_s": pull, "start_s": round(start, 2),
            "weights_s": weights, "warmup_s": warm,
            "compile_s": round(c1 - c0, 2) if c0 and c1 else None,
            "rest_s": round(total - sum(known), 2),
            "total_s": round(total, 2),
            "first_ttft_s": round(float(t1), 3),
            "second_ttft_s": round(float(t2), 3)}


if __name__ == "__main__":
    if sys.argv[1] == "ttft":
        print(f"{ttft(sys.argv[2], sys.argv[3]):.3f}")
    else:
        print(json.dumps(phases(*sys.argv[2:])))
