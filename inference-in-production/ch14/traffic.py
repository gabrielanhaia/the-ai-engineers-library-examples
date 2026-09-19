# ch14/traffic.py
"""Traffic for the ch14 lab, sent through the gateway.

  conversations  multi-turn chats, each with its own long context;
                 records which replica served each turn, and TTFT.
  priority       a flood of requests plus one probe a second;
                 records every request's class and TTFT.

Standard library only. Writes one JSON object per request (JSONL).
"""
import argparse
import http.client
import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor

MODEL = "smollm2-360m"
WORDS = ("cache prefix token replica router batch queue model "
         "tenant adapter latency budget request stream decode "
         "prefill gateway picker weight shard").split()


def chat(url, messages, max_tokens, headers=None):
    """One streamed chat completion through the gateway."""
    host, port = url.split(":")
    body = json.dumps({"model": MODEL, "messages": messages,
                       "max_tokens": max_tokens, "stream": True,
                       "ignore_eos": True})  # exactly max_tokens
    conn = http.client.HTTPConnection(host, int(port), timeout=300)
    t0 = time.monotonic()
    conn.request("POST", "/v1/chat/completions", body,
                 {"Content-Type": "application/json",
                  **(headers or {})})
    resp = conn.getresponse()
    out = {"status": resp.status,
           "pod": resp.getheader("x-inference-pod"),
           "ttft": None}
    text = []
    for line in resp:
        if not line.startswith(b"data: {"):
            continue
        delta = json.loads(line[6:])["choices"][0]["delta"]
        if delta.get("content"):
            if out["ttft"] is None:
                out["ttft"] = time.monotonic() - t0
            text.append(delta["content"])
    out["e2e"] = time.monotonic() - t0
    conn.close()
    return out, "".join(text)


def words(rng, n):
    return " ".join(rng.choice(WORDS) for _ in range(n))


def conversation(i, args, emit):
    """One user: a long private context, then args.turns turns."""
    rng = random.Random(args.seed * 1000 + i)
    msgs = [{"role": "system",
             "content": f"Context {i}: " + words(rng, args.context)}]
    for turn in range(1, args.turns + 1):
        msgs.append({"role": "user", "content": words(rng, 24)})
        res, text = chat(args.url, msgs, args.max_tokens)
        emit({"conv": i, "turn": turn, **res})
        msgs.append({"role": "assistant", "content": text})
        time.sleep(args.think)


def flood(args, stop, emit):
    rng = random.Random()
    hdr = {"x-llm-d-inference-objective": args.flood_class}
    while not stop.is_set():
        msgs = [{"role": "user", "content": words(rng, 32)}]
        res, _ = chat(args.url, msgs, args.max_tokens, hdr)
        emit({"cls": "flood", **res})


def probe(args, emit):
    rng = random.Random()
    hdr = {"x-llm-d-inference-objective": args.probe_class}
    msgs = [{"role": "user", "content": words(rng, 32)}]
    res, _ = chat(args.url, msgs, args.max_tokens, hdr)
    emit({"cls": "probe", "objective": args.probe_class, **res})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["conversations", "priority"])
    p.add_argument("--url", default="ch14-control-plane:30080")
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=14)
    p.add_argument("--max-tokens", type=int, default=40)
    p.add_argument("--conversations", type=int, default=12)
    p.add_argument("--parallel", type=int, default=6)
    p.add_argument("--turns", type=int, default=6)
    p.add_argument("--context", type=int, default=400)
    p.add_argument("--think", type=float, default=0.2)
    p.add_argument("--flood", type=int, default=0)
    p.add_argument("--flood-class", default="batch")
    p.add_argument("--probes", type=int, default=20)
    p.add_argument("--probe-class", default="interactive")
    args = p.parse_args()

    lock = threading.Lock()
    with open(args.out, "w") as f:
        def emit(rec):
            rec["t"] = round(time.time(), 3)
            with lock:
                f.write(json.dumps(rec) + "\n")
                f.flush()

        if args.mode == "conversations":
            with ThreadPoolExecutor(args.parallel) as ex:
                list(ex.map(lambda i: conversation(i, args, emit),
                            range(args.conversations)))
            return
        stop = threading.Event()
        workers = [threading.Thread(target=flood,
                                    args=(args, stop, emit))
                   for _ in range(args.flood)]
        for w in workers:
            w.start()
        time.sleep(5 if args.flood else 0)  # let the queue form
        probes = []
        for _ in range(args.probes):
            t = threading.Thread(target=probe, args=(args, emit))
            t.start()
            probes.append(t)
            time.sleep(1)
        for t in probes:
            t.join()
        stop.set()
        for w in workers:
            w.join()


if __name__ == "__main__":
    main()
