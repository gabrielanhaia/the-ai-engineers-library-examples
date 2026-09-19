# ch07/capacity.py
"""How many GPUs: the larger of two counts, rounded to what you buy.

Memory: the running batch by Little's law (W = prefill + decode;
queued requests hold no KV) times the mean resident context,
against KV budget = HBM x 0.92 - TOTAL weight bytes, in decimal
GB: an upper bound. Throughput: peak output tokens over a cited
per-GPU rate at a stated bound, run below the rate for headroom.
A laptop's rate is refused: it describes the laptop.
"""
import math
import pathlib
import sys
import tomllib

HERE = pathlib.Path(__file__).resolve().parent
INPUTS = HERE.parent / "inputs"


def toml(path):
    with open(path, "rb") as f:
        return tomllib.load(f)


def kv_per_token(m, kv_bytes):
    return 2 * m["layers"] * m["kv_heads"] * m["head_dim"] * kv_bytes


def kv_budget(gpu, weights, fraction):
    """Bytes left for KV on one GPU: an upper bound."""
    return gpu["hbm_gb"] * 1e9 * fraction - weights


def running_batch(rps, ttft_s, osl, tpot_s):
    """Little's law, L = rate x W, with W the time in service."""
    return rps * (ttft_s + (osl - 1) * tpot_s)


def cited_rate(w, gpus):
    """Per-GPU output tokens/s, measured at w's bound or tighter."""
    r = toml(INPUTS / f"{w['rate']}.toml")["node"]
    if r["gpu"] not in gpus:
        sys.exit(f"refused: {r['gpu']} is not a GPU in inputs/")
    if r["gpu"] != w["gpu"] or r["tokens"] != "output":
        sys.exit("refused: a rate for another GPU or token type")
    if r["tpot_ms"] > w["tpot_ms"] or r["ttft_ms"] > w["ttft_ms"]:
        sys.exit("refused: the rate was measured at a looser bound")
    return r, r["server"] / r["gpus"]


def main(path=HERE / "examples.toml"):
    ex, hw = toml(path), toml(INPUTS / "hardware.toml")
    models = toml(INPUTS / "models.toml")
    frac = hw["engine"]["memory_fraction"]
    print(f"fit: KV budget <= HBM x {frac} - weights (decimal GB),")
    print("an upper bound: activations and workspace are left out")
    print(f"{'model':18} {'GPU':5} {f'HBMx{frac}':>8} {'weights':>8} "
          f"{'for KV':>7} {'KV tokens':>10}")
    for label, name, wb, kvb, g in ex["fit"]:
        m, weights = models[name], models[name]["params"] * wb
        left = kv_budget(hw[g], weights, frac)
        print(f"{label:18} {g:5} {hw[g]['hbm_gb'] * frac:8.2f} "
              f"{weights / 1e9:8.2f} {left / 1e9:7.2f} "
              f"{left // kv_per_token(m, kvb):10,.0f}")
    for w in ex["workload"]:
        plan(w, hw, models, frac)


def plan(w, hw, models, frac):
    m, gpu, unit = models[w["model"]], hw[w["gpu"]], w["unit"]
    if "shape" in w:
        w |= toml(INPUTS / f"{w['shape']}.toml")["shape"]
    isl, osl = w["input_tokens"], w["output_tokens"]
    ttft, tpot = w["ttft_ms"] / 1000, w["tpot_ms"] / 1000
    print(f"\n{w['title']}: {m['name']} on {w['gpu']}")
    if "pattern" in w:
        day = toml(INPUTS / "traffic.toml")[w["pattern"]]
        peak = w["average_rps"] * day["peak_to_average"]
        print(f"  average    {w['average_rps']:g} requests/s x "
              f"{day['peak_to_average']} ({w['pattern']}) = "
              f"{peak:g} at peak")
    else:
        peak = w["peak_rps"]
        print(f"  peak       {peak:g} requests/s (the busiest hour)")
    print(f"  shape      {isl:,} in / {osl:,} out; SLO TTFT <= "
          f"{w['ttft_ms']:,} ms, TPOT <= {w['tpot_ms']} ms")
    need = 0
    if "layers" in m:
        per_tok = kv_per_token(m, w["kv_bytes"])
        weights = m["params"] * w["weight_bytes"]
        fits = kv_budget(gpu, weights, frac) // per_tok
        batch = running_batch(peak, ttft, osl, tpot)
        tokens = batch * (isl + osl / 2)
        need = math.ceil(tokens / fits) * unit
        each = tokens / (need // unit)
        step = (weights + each * per_tok) / (gpu["tb_s"] * 1e12)
        print(f"  W          <= {ttft:g} + {osl - 1} x {tpot:g} = "
              f"{batch / peak:.2f} s in service")
        print(f"  running    {peak:g} x {batch / peak:.2f} = "
              f"{batch:,.1f} sequences")
        print(f"  KV needed  {batch:,.1f} x ({isl:,} + {osl:,} / 2)"
              f" = {tokens:,.0f} tokens")
        print(f"             x {per_tok:,} B = "
              f"{tokens * per_tok / 1e9:,.1f} GB")
        print(f"  memory     {tokens:,.0f} / {fits:,.0f} = "
              f"{tokens / fits:.2f} -> {need} {w['gpu']}")
        print(f"             each {batch / (need // unit):,.1f} "
              f"seqs, {each:,.0f} tokens ({each / fits:.0%} of fit)")
        print(f"  step       >= ({weights / 1e9:.2f} + "
              f"{each * per_tok / 1e9:.2f}) GB / {gpu['tb_s']} TB/s"
              f" = {step * 1000:.1f} ms")
    else:
        print("  memory     no KV shape in inputs/: not counted")
    if "rate" not in w:
        print("  throughput no cited rate at this SLO: measure one")
        print(f"  fleet      {need} {w['gpu']}, the memory count")
        return need, 0, need
    r, per_gpu = cited_rate(w, hw)
    load, busy_tok = w["peak_load"], peak * osl
    by_rate = math.ceil(busy_tok / (load * per_gpu))
    fleet = max(need, math.ceil(by_rate / unit) * unit)
    print(f"  rate       {r['server']:,.1f} / {r['gpus']} = "
          f"{per_gpu:,.1f} output tokens/s per GPU")
    print(f"             {r['system']}")
    print(f"             at p99 TTFT <= {r['ttft_ms']:,} ms, TPOT <= "
          f"{r['tpot_ms']} ms")
    print(f"  throughput {busy_tok:,.0f} / ({load:.2f} x "
          f"{per_gpu:,.1f}) = {busy_tok / (load * per_gpu):.2f}"
          f" -> {by_rate} GPUs")
    print(f"  fleet      {fleet} {w['gpu']}, bought {unit} at a time")
    usd = toml(INPUTS / f"{w['rate']}.toml")[w["price"]][w["gpu"]]
    hours = [("load", w.get("average_rps", peak))]
    if "pattern" in w:
        hours.append(("valley", peak / day["peak_to_valley"]))
    for when, rps in hours:
        tok, can = rps * osl, fleet * per_gpu
        print(f"  {when:10} {rps:.1f} requests/s: {tok:,.0f} / "
              f"{can:,.1f} = {tok / can:.1%}")
        print(f"             {fleet} x ${usd:.2f} = "
              f"${fleet * usd:,.2f} / {tok * 3.6e-3:,.2f}M = "
              f"${fleet * usd / (tok * 3.6e-3):#.3g} per M out")
    return need, by_rate, fleet


if __name__ == "__main__":
    main(*sys.argv[1:])
