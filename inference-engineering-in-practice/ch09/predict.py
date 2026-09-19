# ch09/predict.py
"""Predict where preemption starts, from the model's config alone.

KV bytes per token = 2 (K and V) x layers x KV heads x head_dim
x bytes per value. The cache holds its size in bytes divided by
that. Every request in flight needs its prompt plus its output,
so the cache fits cache tokens / request tokens requests at once,
and the next one up is the first concurrency that cannot fit.
"""
import argparse
import json
import math

p = argparse.ArgumentParser()
p.add_argument("--config", default="/models/hf/"
               "SmolLM2-360M-Instruct/config.json")
p.add_argument("--kv-gib", type=float, default=1.0)
p.add_argument("--bytes", type=int, default=2, help="FP16: 2")
p.add_argument("--prompt", type=int, default=1792)
p.add_argument("--output", type=int, default=256)
p.add_argument("--json", help="also write the numbers here")
a = p.parse_args()

with open(a.config) as f:
    cfg = json.load(f)
layers = cfg["num_hidden_layers"]
kv_heads = cfg["num_key_value_heads"]
head_dim = cfg["hidden_size"] // cfg["num_attention_heads"]
per_token = 2 * layers * kv_heads * head_dim * a.bytes
cache = a.kv_gib * 2**30 / per_token
request = a.prompt + a.output
fits = cache / request
first = math.floor(fits) + 1

print(f"KV per token  2 x {layers} x {kv_heads} x {head_dim} x "
      f"{a.bytes} B = {per_token:,} B")
print(f"cache         {a.kv_gib:g} GiB / {per_token:,} B = "
      f"{cache:,.0f} tokens")
print(f"per request   {a.prompt:,} in + {a.output:,} out = "
      f"{request:,} tokens")
print(f"fits          {cache:,.0f} / {request:,} = {fits:.2f} "
      f"requests")
print(f"prediction    preemption starts at {first} concurrent "
      f"requests")
if a.json:
    with open(a.json, "w") as f:
        json.dump({"kv_bytes_per_token": per_token,
                   "cache_tokens": cache, "request_tokens": request,
                   "fits": fits, "first_preempting": first}, f,
                  indent=1)
