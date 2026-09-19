# ch08/derived.py
"""Every DERIVED number chapter 8 prints, recomputed from inputs/.

Prints JSON: bound.py's default output, then one entry per number
with the string the chapter prints ("shown").
scripts/check_derived.py reruns this and fails on any difference
from measured/ch08/derived.json.
"""
import contextlib
import io
import json
import sys

from bound import main, toml

N = []


def num(key, value, shown):
    N.append({"key": key, "value": value, "shown": shown})


def run():
    gpu = toml("hardware.toml")["H100"]
    m = toml("models.toml")["llama-3_1-8b"]
    bw, w = gpu["tb_s"] * 1e12, m["params"] * 2
    k = 2 * m["layers"] * m["kv_heads"] * m["head_dim"] * 2
    seq = 4096 * k

    def agg(b):
        return b * bw / (w + b * seq)

    num("weights_gb", w / 1e9, f"{w / 1e9:.2f} GB")
    num("kv_per_sequence_gb", seq / 1e9, f"{seq / 1e9:.3f} GB")
    num("b1.tok_s", agg(1), f"{agg(1):,.0f}")
    num("b64.tok_s", agg(64), f"{agg(64):,.0f}")
    num("b64.per_user", agg(64) / 64, f"{agg(64) / 64:,.0f}")
    num("b64.step_ms", (w + 64 * seq) / bw * 1e3,
        f"{(w + 64 * seq) / bw * 1e3:.2f} ms")
    num("ceiling", bw / seq, f"{bw / seq:,.0f}")
    num("half_batch", w / seq, f"{w / seq:.0f}")
    num("b64.share_of_ceiling", agg(64) / (bw / seq),
        f"{agg(64) / (bw / seq):.0%}")
    num("b128.tok_s", agg(128), f"{agg(128):,.0f}")


if __name__ == "__main__":
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main([])
    run()
    out = {"chapter": "08", "outputs": {"bound.py": buf.getvalue()},
           "numbers": N}
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
    print()
