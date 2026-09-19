# ch10/prompts.py
"""Two workloads with the same words in a different order.

shared: the long system prompt (a store's catalogue) comes first,
        and the part that changes (who is asking) comes last.
unique: the part that changes comes first, so no two prompts
        share even their first token block.

Each workload sends N chat requests one at a time, streams them,
and records the client-side TTFT: request sent to the first chunk
that carries text. The prefix-cache hit rate comes from the
server's own counters, read before and after each workload.
"""
import json
import statistics
import sys
import time
import urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else "http://ch10-vllm:8000"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 20
OUT = sys.argv[3] if len(sys.argv) > 3 else "."

ITEMS = ["hex bolt", "wood screw", "wall plug", "hinge", "bracket",
         "washer", "cable tie", "hook", "latch", "rivet"]
FINISH = ["zinc", "brass", "steel", "black", "nickel", "copper"]
CATALOGUE = "\n".join(
    f"SKU-{1000 + i}: {ITEMS[i % 10]}, {4 + i % 9} mm, "
    f"{FINISH[i % 6]}, ${0.15 + i * 0.07:.2f}, aisle {1 + i % 12}"
    for i in range(64))
STABLE = ("You are the help desk of a hardware store. Answer in one "
          "sentence, using only this catalogue.\n" + CATALOGUE)


def messages(layout, i):
    who = f"Customer {i:03d}, visit {i * 7 % 13}."
    ask = f"Which aisle has SKU-{1000 + i * 5 % 64}?"
    if layout == "shared":
        return [{"role": "system", "content": STABLE},
                {"role": "user", "content": f"{who} {ask}"}]
    return [{"role": "system", "content": f"{who}\n{STABLE}"},
            {"role": "user", "content": ask}]


def counters():
    with urllib.request.urlopen(URL + "/metrics") as r:
        text = r.read().decode()
    got = {"hits": 0.0, "queries": 0.0}
    for line in text.splitlines():
        for k in got:
            if line.startswith(f"vllm:prefix_cache_{k}_total"):
                got[k] += float(line.split()[-1])
    return got


def ask(msgs):
    body = json.dumps({"model": "smollm2-360m", "messages": msgs,
                       "max_tokens": 16, "temperature": 0,
                       "stream": True,
                       "stream_options": {"include_usage": True}})
    req = urllib.request.Request(
        URL + "/v1/chat/completions", body.encode(),
        {"Content-Type": "application/json"})
    t0, ttft, usage = time.perf_counter(), None, None
    with urllib.request.urlopen(req) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data: {"):
                continue
            chunk = json.loads(line[6:])
            if chunk.get("usage"):
                usage = chunk["usage"]
            delta = (chunk.get("choices") or [{}])[0].get("delta", {})
            if ttft is None and delta.get("content"):
                ttft = time.perf_counter() - t0
    if usage is None:
        sys.exit("the stream ended before its usage chunk")
    return ttft, usage["prompt_tokens"]


rows = []
print(" workload  requests  prompt tokens  hit rate  TTFT p50"
      "  TTFT p90")
for layout in ("unique", "shared"):
    before, ttfts, sizes = counters(), [], []
    for i in range(N):
        t, n = ask(messages(layout, i))
        ttfts.append(t * 1000)
        sizes.append(n)
    after = counters()
    hits = after["hits"] - before["hits"]
    queries = after["queries"] - before["queries"]
    p50 = statistics.median(ttfts)
    p90 = statistics.quantiles(ttfts, n=10)[-1]
    rows.append({"workload": layout, "requests": N,
                 "prompt_tokens": statistics.mean(sizes),
                 "hits": hits, "queries": queries,
                 "hit_rate": hits / queries, "ttft_ms": ttfts,
                 "ttft_p50_ms": p50, "ttft_p90_ms": p90})
    print(f" {layout:8s}  {N:8d}  {statistics.mean(sizes):13,.0f}"
          f"  {hits / queries:8.2f}  {p50:5.0f} ms  {p90:5.0f} ms")
with open(f"{OUT}/workloads.json", "w") as f:
    json.dump(rows, f, indent=1)
