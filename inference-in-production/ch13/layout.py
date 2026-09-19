# ch13/layout.py
"""Three layout formulas, on cited inputs from inputs/.

Nothing here runs a GPU. Every result is DERIVED: KV copies under
tensor parallelism, the KV budget a TP=2 layout frees, and a P:D
ratio from per-phase rates.
"""
import pathlib
import tomllib

INPUTS = pathlib.Path(__file__).resolve().parents[1] / "inputs"


def toml(name):
    with open(INPUTS / name, "rb") as f:
        return tomllib.load(f)


def kv_copies(tp, kv_heads):
    """Copies of the same KV at TP; -dcp runs from 1 to this."""
    return max(1, tp // kv_heads)


def kv_budget_gb(hbm_gb, fraction, weight_bytes, tp=1, replicas=1):
    """KV GB left when each replica stores the weights once."""
    per = round(tp * hbm_gb * 1e9 * fraction) - weight_bytes
    return replicas * per / 1e9


def pd_ratio(isl, osl, prefill_tok_s, decode_tok_s, rate=1.0):
    """Prefill nodes per decode node. The arrival rate cancels."""
    return (rate * isl / prefill_tok_s) / (rate * osl / decode_tok_s)


def main():
    hw, models = toml("hardware.toml"), toml("models.toml")
    par = toml("parallelism.toml")
    print("KV copies at TP 8: TP / KV heads, never below 1")
    print(f"{'model':18}{'KV heads':>9}{'copies':>8}{'-dcp':>10}")
    for name in ("deepseek-r1", "qwen3-235b-a22b", "llama-3_1-70b"):
        m = models[name]
        n = kv_copies(8, m["kv_heads"])
        print(f"{m['name']:18}{m['kv_heads']:>9}{n:>8}"
              f"{'1 to ' + str(n):>10}")

    m, h100 = models["llama-3_1-70b"], hw["H100"]
    frac, weights = hw["engine"]["memory_fraction"], m["params"]
    per_tok = 2 * m["layers"] * m["kv_heads"] * m["head_dim"] * 1
    print(f"\n{m['name']} in FP8 ({weights / 1e9:.2f} GB) on H100: "
          f"{h100['hbm_gb']} x {frac}")
    print(f"= {h100['hbm_gb'] * frac:.2f} GB per GPU; FP8 KV is "
          f"{per_tok:,} bytes a token")
    print(f"{'layout':14}{'GPUs':>5}{'KV GB':>8}{'KV tokens':>12}"
          f"{'8K chats':>10}")
    gb = {}
    for label, tp, n in [("TP=1", 1, 1), ("two replicas", 1, 2),
                         ("TP=2", 2, 1)]:
        gb[label] = kv_budget_gb(h100["hbm_gb"], frac, weights, tp, n)
        tokens = round(gb[label] * 1e9) // n // per_tok * n
        chats = tokens // n // 8192 * n
        print(f"{label:14}{tp * n:>5}{gb[label]:>8.2f}{tokens:>12,}"
              f"{chats:>10}")
    two, tp2 = gb["two replicas"], gb["TP=2"]
    print(f"TP=2 holds {tp2 / two:.1f}x the KV of two replicas; the "
          f"{tp2 - two:.2f} GB")
    print("between them is the second copy of the weights, now KV")
    small = models["llama-3_1-8b"]
    left = kv_budget_gb(h100["hbm_gb"], frac, small["params"] * 2)
    print(f"{small['name']} in BF16 leaves {left:.2f} GB on one H100;"
          f" TP=2 frees")
    print(f"only the second copy of its "
          f"{small['params'] * 2 / 1e9:.2f} GB of weights")

    sg = par["sglang"]
    print("\nP:D = (ISL / R_prefill) : (OSL / R_decode)")
    print(f"per node: {sg['prefill_tok_s']:,} input, "
          f"{sg['decode_tok_s']:,} output tokens/s (SGLang)")
    print(f"{'shape':20}{'ISL:OSL':>8}{'P:D':>8}"
          f"{'prefill : decode':>18}")
    ratios = []
    for name in ("summarization", "chat", "reasoning"):
        s = par["inferencex"][name]
        i, o = s["input_k"], s["output_k"]
        r = pd_ratio(i, o, sg["prefill_tok_s"], sg["decode_tok_s"])
        ratios.append(r)
        nodes = f"{r:.1f} : 1" if r >= 1 else f"1 : {1 / r:.1f}"
        print(f"{name + f' {i}k/{o}k':20}{f'{i}:{o}':>8}"
              f"{r:>8.{2 if r >= 1 else 3}f}{nodes:>18}")
    print(f"the right ratio moves {max(ratios) / min(ratios):.0f}x "
          f"across the three shapes")
    move = 8192 * per_tok
    print(f"an 8K prompt's KV to move: 8,192 x {per_tok:,} B = "
          f"{move / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
