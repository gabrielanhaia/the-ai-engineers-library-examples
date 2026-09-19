# ch14/lora.py
"""The multi-LoRA step, against a real vLLM CPU engine.

1. One prompt, temperature 0, to the base model and to each adapter:
   the `model` field alone picks the adapter.
2. A mixed burst, four requests per adapter at once: with one
   adapter slot (--max-loras 1) the two adapters' requests cannot
   share a batch, so they finish in two groups. The engine's
   vllm:lora_requests_info gauge is sampled throughout, and every
   label pair it showed is recorded.
"""
import argparse
import json
import re
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PROMPT = "Give one tip for staying focused."
ADAPTERS = ("alpaca", "underdog")


def post(url, body):
    req = urllib.request.Request(
        url + "/v1/chat/completions", json.dumps(body).encode(),
        {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def ask(url, model, tokens, ignore_eos=False):
    body = {"model": model, "temperature": 0, "max_tokens": tokens,
            "ignore_eos": ignore_eos,
            "messages": [{"role": "user", "content": PROMPT}]}
    t0 = time.monotonic()
    text = post(url, body)["choices"][0]["message"]["content"]
    return text, time.monotonic() - t0


def lora_state(url):
    """(running, waiting) from the newest lora_requests_info row."""
    with urllib.request.urlopen(url + "/metrics", timeout=10) as r:
        lines = r.read().decode().splitlines()
    best = None
    for ln in lines:
        if not ln.startswith("vllm:lora_requests_info{"):
            continue
        labels, value = ln.rsplit(" ", 1)
        kv = dict(re.findall(r'(\w+)="([^"]*)"', labels))
        row = (float(value), kv["running_lora_adapters"],
               kv["waiting_lora_adapters"])
        best = max(best, row) if best else row
    return best[1:] if best else ("", "")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://vllm:8000")
    p.add_argument("--base", default="smollm2-360m")
    p.add_argument("--per-adapter", type=int, default=4)
    p.add_argument("--tokens", type=int, default=64)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    same = {m: ask(a.url, m, 24)[0] for m in (a.base, *ADAPTERS)}

    seen, stop = [], threading.Event()

    def sample():
        while not stop.is_set():
            run, wait = lora_state(a.url)
            seen.append({"t": time.monotonic(), "running": run,
                         "waiting": wait})
            time.sleep(0.2)

    s = threading.Thread(target=sample)
    s.start()
    jobs = [m for m in ADAPTERS for _ in range(a.per_adapter)]
    t0 = time.monotonic()
    with ThreadPoolExecutor(len(jobs)) as ex:
        e2e = list(ex.map(
            lambda m: ask(a.url, m, a.tokens, True)[1], jobs))
    burst = time.monotonic() - t0
    stop.set()
    s.join()

    states = sorted({(x["running"], x["waiting"]) for x in seen})
    done = {m: [min(t for j, t in zip(jobs, e2e) if j == m),
                max(t for j, t in zip(jobs, e2e) if j == m)]
            for m in ADAPTERS}
    first, second = sorted(done.values())
    json.dump({"same_prompt": same, "burst_requests": len(jobs),
               "tokens_each": a.tokens,
               "burst_s": round(burst, 2),
               "done_s": {m: [round(x, 2) for x in v]
                          for m, v in done.items()},
               "serialized": first[1] < second[0],
               "lora_requests_info_labels": [list(x) for x in states],
               "labels_show_both_active": any(
                   set(ADAPTERS) <= set(r.split(","))
                   for r, _ in states)},
              open(a.out, "w"), indent=2)


if __name__ == "__main__":
    main()
