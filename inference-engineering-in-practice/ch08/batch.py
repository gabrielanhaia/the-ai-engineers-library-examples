# ch08/batch.py
"""The offline corner: a batch file for `vllm run-batch`, and what
came back.

  batch.py make N           the input file, one request per line
  batch.py read OUT LOG J   output tokens, and tokens per second
                            over the batch's own elapsed time (the
                            "Running batch" line in the log); the
                            numbers also go to the JSON file J
"""
import json
import re
import sys

FILLER = "the quick brown fox jumps over the lazy dog " * 4


def make(n):
    for i in range(n):
        ask = f"Note {i}: {FILLER}"
        print(json.dumps({
            "custom_id": f"req-{i}", "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "smollm2-360m", "messages": [
                    {"role": "user", "content": ask}],
                "max_tokens": 64, "ignore_eos": True,
                "temperature": 0}}))


def read(out, log, path):
    lines = [json.loads(x) for x in open(out)]
    ok = [x for x in lines if x["response"] and
          x["response"]["status_code"] == 200]
    usage = [x["response"]["body"]["usage"] for x in ok]
    done = re.findall(r"Running batch: 100%.*?\[([\d:]+)<",
                      open(log).read())
    h, m, s = ([0, 0, 0] + [int(x) for x in done[-1].split(":")])[-3:]
    secs = h * 3600 + m * 60 + s
    tokens = sum(u["completion_tokens"] for u in usage)
    prompt = sum(u["prompt_tokens"] for u in usage) / len(usage)
    print(f"requests {len(ok)} of {len(lines)}, prompt "
          f"{prompt:.0f} tokens each, {tokens:,} output tokens")
    print(f"elapsed {secs} s, output {tokens / secs:.1f} tok/s")
    with open(path, "w") as f:
        json.dump({"requests": len(ok), "output_tokens": tokens,
                   "prompt_tokens_mean": prompt, "seconds": secs,
                   "output_tok_s": tokens / secs}, f, indent=1)


if __name__ == "__main__":
    if sys.argv[1] == "make":
        make(int(sys.argv[2]))
    else:
        read(*sys.argv[2:5])
