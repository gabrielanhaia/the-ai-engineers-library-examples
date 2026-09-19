# ch12/wallclock.py
"""Wall-clock time with and without a draft model, interleaved.

    python3 wallclock.py PLAIN_URL SPEC_URL > wallclock.json

Sends every code and prose prompt at temperature 0 to both servers,
one after the other, switching which goes first on every prompt, so
a busy moment on the machine lands on both sides alike. The ratio is
a fact about this CPU, not about a GPU.
"""
import json
import sys
import time

from generate import N_PROMPTS, complete


def main():
    sides = [("plain", sys.argv[1]), ("speculative", sys.argv[2])]
    seconds = {"plain": 0.0, "speculative": 0.0}
    tokens = {"plain": 0, "speculative": 0}
    prompts = json.load(open("prompts.json"))
    i = 0
    for task in ("code", "prose"):
        for p in prompts[task][:N_PROMPTS]:
            for name, url in sides if i % 2 == 0 else sides[::-1]:
                t0 = time.perf_counter()
                out = complete(url, p, 0.0, 1000 + i)
                seconds[name] += time.perf_counter() - t0
                tokens[name] += out["timings"]["predicted_n"]
            i += 1
    print(json.dumps({
        "prompts": i, "temperature": 0.0, "tokens": tokens,
        "plain_s": seconds["plain"],
        "speculative_s": seconds["speculative"],
        "plain_over_speculative":
            seconds["plain"] / seconds["speculative"]}))


if __name__ == "__main__":
    main()
