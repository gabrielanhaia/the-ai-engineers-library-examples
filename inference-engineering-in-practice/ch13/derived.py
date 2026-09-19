# ch13/derived.py
"""Every DERIVED number chapter 13 prints, recomputed from inputs/.

Prints JSON: the calculator's default output, then one entry per
number with the string the chapter prints ("shown").
scripts/check_derived.py reruns this and fails on any difference
from measured/ch13/derived.json.
"""
import contextlib
import io
import json
import sys

from layout import kv_budget_gb, kv_copies, main, pd_ratio, toml

N = []


def num(key, value, shown):
    N.append({"key": key, "value": value, "shown": shown})


def run():
    hw, models = toml("hardware.toml"), toml("models.toml")
    par = toml("parallelism.toml")
    h100, frac = hw["H100"], hw["engine"]["memory_fraction"]

    # Two machines for one model
    big = models["llama-3-405b"]["params"] * 2
    box = 8 * h100["hbm_gb"] * 1e9
    num("405b.weights", big, f"{big / 1e9:.0f} GB")
    num("405b.box", box, f"{box / 1e9:.0f} GB")
    num("405b.over", big - box, f"{(big - box) / 1e9:.0f} GB")

    # Four ways to split; TP or more replicas
    per_layer = par["megatron"]["all_reduces_per_layer"]
    for key in ("llama-3_1-70b", "llama-3_1-8b"):
        n = models[key]["layers"] * per_layer
        num(f"all_reduces.{key}", n, f"= {n} all-reduces"
            if key == "llama-3_1-70b" else f"{n} all-reduces")
    m = models["llama-3_1-70b"]
    per_tok = 2 * m["layers"] * m["kv_heads"] * m["head_dim"]
    for tp in (1, 2):
        gb = m["params"] / tp / 1e9
        ms = gb / h100["tb_s"]
        num(f"floor.tp{tp}.gb", gb, f"{gb:.2f} GB")
        num(f"floor.tp{tp}.ms", ms, f"{ms:.2f} ms")
    one = kv_budget_gb(h100["hbm_gb"], frac, m["params"])
    two = kv_budget_gb(h100["hbm_gb"], frac, m["params"], 1, 2)
    tp2 = kv_budget_gb(h100["hbm_gb"], frac, m["params"], 2)
    num("kv.tp1.gb", one, f"{one:.2f} GB")
    t1 = round(one * 1e9) // per_tok
    num("kv.tp1.tokens", t1, f"about {t1 / 1000:.1f}K tokens")
    num("kv.replicas.gb", two, f"{two:.1f} GB of KV")
    num("kv.tp2.gb", tp2, f"= {tp2:.2f} GB")
    t2 = round(tp2 * 1e9) // per_tok
    num("kv.tp2.tokens", t2, f"about {t2 / 1000:.0f}K tokens")
    num("kv.tp2.chats", t2 // 8192, f"about {t2 // 8192} concurrent")
    num("kv.ratio", tp2 / two, f"= {tp2 / two:.1f} times")
    num("kv.freed", tp2 - two, f"= {tp2 - two:.2f} GB")
    s = models["llama-3_1-8b"]
    left = kv_budget_gb(h100["hbm_gb"], frac, s["params"] * 2)
    num("kv.8b.left", left, f"= {left:.1f} GB of KV")
    num("kv.8b.weights", s["params"] * 2,
        f"{s['params'] * 2 / 1e9:.2f} GB of weights")

    # KV duplication
    for key in ("deepseek-r1", "qwen3-235b-a22b", "llama-3_1-70b"):
        n = kv_copies(8, models[key]["kv_heads"])
        num(f"copies.{key}", n, f"-dcp {n}" if n > 1
            else "stores it once")

    # Two jobs, two machines: the KV to move, and the P:D ratio
    move = 8192 * per_tok
    num("move.bytes", move, f"= {move / 1e9:.2f} GB")
    sg = par["sglang"]
    base = sg["decode_tok_s"] / sg["prefill_tok_s"]
    num("pd.base", base, f"= {base:.3f}")
    ratios = {}
    for name in ("summarization", "chat", "reasoning"):
        x = par["inferencex"][name]
        ratios[name] = pd_ratio(x["input_k"], x["output_k"],
                                sg["prefill_tok_s"],
                                sg["decode_tok_s"])
    r = ratios
    num("pd.summarization", r["summarization"],
        f"= {r['summarization']:.2f}")
    num("pd.chat.decode_nodes", 1 / r["chat"],
        f"every {1 / r['chat']:.1f} decode nodes")
    num("pd.reasoning", r["reasoning"], f"= {r['reasoning']:.3f}")
    num("pd.reasoning.decode_nodes", 1 / r["reasoning"],
        f"every {1 / r['reasoning']:.0f} decode nodes")
    swing = r["summarization"] / r["reasoning"]
    num("pd.swing", swing, f"factor of {swing:.0f}")


if __name__ == "__main__":
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main()
    run()
    out = {"chapter": "13", "numbers": N,
           "outputs": {"layout.py": buf.getvalue()}}
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
    print()
