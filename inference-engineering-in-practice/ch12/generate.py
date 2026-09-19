# ch12/generate.py
"""Send one prompt set to a llama.cpp server, one request at a time.

    python3 generate.py URL SET TEMPERATURE > run.json

SET is "code" or "prose" (prompts.json). Only the temperature varies:
top-k, top-p and min-p stay fixed at llama.cpp's defaults (40, 0.95,
0.05), and each prompt has a fixed seed, so a rerun samples the same
way. Prints the wall-clock time and each request's timings,
including the server's draft counts.
"""
import json
import os
import sys
import time
import urllib.request

MAX_TOKENS = int(os.environ.get("CH12_MAX_TOKENS", 128))
N_PROMPTS = int(os.environ.get("CH12_PROMPTS", 8))


def complete(url, prompt, temperature, seed):
    body = {"messages": [{"role": "user", "content": prompt}],
            "max_tokens": MAX_TOKENS, "temperature": temperature,
            "top_k": 40, "top_p": 0.95, "min_p": 0.05, "seed": seed,
            "cache_prompt": False}
    req = urllib.request.Request(
        url + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def main():
    url, task, temperature = sys.argv[1], sys.argv[2], sys.argv[3]
    prompts = json.load(open("prompts.json"))[task][:N_PROMPTS]
    runs, t0 = [], time.perf_counter()
    for i, p in enumerate(prompts):
        out = complete(url, p, float(temperature), 1000 + i)
        runs.append({"prompt": p,
                     "text": out["choices"][0]["message"]["content"],
                     "timings": out["timings"]})
    print(json.dumps({"task": task, "temperature": float(temperature),
                      "wall_s": time.perf_counter() - t0,
                      "requests": runs}, indent=1))


if __name__ == "__main__":
    main()
