# ch07/derived.py
"""Every DERIVED number chapter 7 prints, recomputed from inputs/.

Prints JSON: the calculator's default output, then one entry per
number with the string the chapter prints ("shown").
scripts/check_derived.py reruns this and fails on any difference
from measured/ch07/derived.json.
"""
import contextlib
import csv
import io
import json
import math
import sys

from capacity import HERE, INPUTS, kv_budget, kv_per_token, main
from capacity import running_batch, toml

N = []


def num(key, value, shown):
    N.append({"key": key, "value": value, "shown": shown})


def run():
    hw, models = toml(INPUTS / "hardware.toml"), \
        toml(INPUTS / "models.toml")
    ex = toml(HERE / "examples.toml")
    a = toml(INPUTS / "example-a.toml")
    frac = hw["engine"]["memory_fraction"]

    # Will it fit? The six rows of the table
    places = [0, 1, 0, 0, 0, 0]
    for i, (label, name, wb, kvb, g) in enumerate(ex["fit"]):
        m = models[name]
        weights = m["params"] * wb
        left = kv_budget(hw[g], weights, frac)
        tokens = left // kv_per_token(m, kvb)
        key = f"fit.{i + 1}"
        hbm = hw[g]["hbm_gb"] * frac
        num(f"{key}.hbm", hbm, f"{hbm:.2f}".rstrip("0") + " GB")
        num(f"{key}.weights", weights, f"{weights / 1e9:.2f} GB")
        num(f"{key}.left", left, f"{left / 1e9:.2f} GB")
        num(f"{key}.tokens", tokens,
            f"≈ {tokens / 1000:.{places[i]}f}K")
    m8 = models["llama-3_1-8b"]
    per8 = kv_per_token(m8, 2)
    fit8 = kv_budget(hw["H100"], m8["params"] * 2, frac) // per8
    num("fit.8b.tokens", fit8, f"≈ {fit8:,.0f} tokens")
    num("fit.8b.chats", fit8 // 8192, f"about {fit8 // 8192:.0f}")
    m70 = models["llama-3_1-70b"]
    b200 = kv_budget(hw["B200"], m70["params"], frac)
    bf16kv = b200 // kv_per_token(m70, 2)
    num("fit.70b_b200.bf16_kv", bf16kv, f"{bf16kv / 1000:.0f}K")
    g = models["granite-4_2-8b"]
    small, big = (kv_budget(hw[x], g["params"] * 2, frac) //
                  kv_per_token(g, 2) for x in ("L4", "L40S"))
    num("fit.granite.ratio", big / small, f"{big / small:.0f} times")

    # Mixture of experts: total bytes decide the fit
    oss = models["gpt-oss-120b"]
    bits = models["mxfp4"]["bits_per_value"]
    num("oss.active_bf16", oss["active"] * 2,
        f"{oss['active'] * 2 / 1e9:.1f} GB")
    num("oss.total_bf16", oss["params"] * 2,
        f"{oss['params'] * 2 / 1e9:.0f} GB")
    floor = oss["params"] * bits / 8
    num("oss.mxfp4_floor", floor, f"≈ {floor / 1e9:.1f} GB")
    left = hw["H100"]["hbm_gb"] * frac * 1e9 - floor
    num("oss.left_on_h100", left, f"≈ {left / 1e9:.1f} GB")
    o20 = models["gpt-oss-20b"]["params"] * 2
    num("oss20.bf16", o20, f"{o20 / 1e9:.1f} GB")

    # Little's law, and the support assistant
    w = ex["workload"][0]
    tpot, ttft = w["tpot_ms"] / 1000, w["ttft_ms"] / 1000
    decode = (w["output_tokens"] - 1) * tpot
    num("support.decode", decode, f"{decode:.2f} s")
    batch = running_batch(w["peak_rps"], ttft, w["output_tokens"],
                          tpot)
    num("support.w", batch / w["peak_rps"],
        f"{batch / w['peak_rps']:.2f} s")
    num("support.batch", batch, f"{batch:.1f} sequences")
    ctx = w["input_tokens"] + w["output_tokens"] / 2
    num("support.context", ctx, f"{ctx:,.0f} tokens")
    need = batch * ctx
    num("support.kv_tokens", need, f"{need:,.0f} tokens")
    num("support.kv_per_token", per8, f"{per8:,} bytes")
    num("support.kv_gb", need * per8, f"{need * per8 / 1e9:.1f} GB")
    num("support.cards", need / fit8, f"{need / fit8:.2f} cards")
    replicas = math.ceil(need / fit8)
    words = {3: "three"}
    num("support.replicas", replicas,
        f"{words[replicas]} H100 replicas")
    each = need / replicas
    num("support.each_seqs", batch / replicas,
        f"about {batch / replicas:.0f} sequences")
    num("support.each_tokens", each, f"{each:,.0f} tokens")
    num("support.each_share", each / fit8, f"{each / fit8:.0%}")
    kv = each * per8
    num("support.step_kv", kv, f"{kv / 1e9:.2f} GB")
    step = m8["params"] * 2 + kv
    num("support.step_bytes", step, f"{step / 1e9:.2f} GB")
    t = step / (hw["H100"]["tb_s"] * 1e12)
    num("support.step_ms", t, f"{t * 1000:.1f} ms")
    out = w["peak_rps"] * w["output_tokens"]
    num("support.out_tok_s", out, f"{out:,} output tokens")
    num("support.per_replica", out / replicas,
        f"{out / replicas:,.0f} per replica")

    # The throughput count: a product on gpt-oss-120b
    p = ex["workload"][1]
    day = toml(INPUTS / "traffic.toml")[p["pattern"]]
    osl = a["shape"]["output_tokens"]
    peak = p["average_rps"] * day["peak_to_average"]
    num("oss.peak_rps", peak, f"{peak:g} requests a second")
    num("oss.peak_tok_s", peak * osl, f"{peak * osl:,.0f} output")
    # The chapter multiplies the per-GPU rate as it prints it.
    per_gpu = round(a["node"]["server"] / a["node"]["gpus"])
    num("oss.per_gpu", per_gpu, f"{per_gpu:,}")
    num("oss.edge", peak * osl / per_gpu,
        f"≈ {peak * osl / per_gpu:.1f} GPUs")
    run_at = p["peak_load"] * per_gpu
    num("oss.run_at", run_at, f"{run_at:,.1f}")
    gpus = peak * osl / run_at
    num("oss.gpus", gpus, f"≈ {gpus:.1f}")
    bought = math.ceil(math.ceil(gpus) / p["unit"]) * p["unit"]
    num("oss.bought", bought, f"{bought} GPUs")
    avg = p["average_rps"] * osl
    num("oss.average", avg, f"{avg:,} output tokens")
    can = bought * per_gpu
    num("oss.capacity", can, f"{can:,}")
    num("oss.util", avg / can, f"≈ {avg / can:.1%}")
    usd = a["nebius"]["B200"] * bought
    num("oss.fleet_hour", usd, f"${usd:.2f}")
    num("oss.tokens_hour", avg * 3600,
        f"{avg * 3600 / 1e6:.0f} million")
    num("oss.per_m", usd / (avg * 3.6e-3),
        f"${usd / (avg * 3.6e-3):.3f}")
    valley = peak / day["peak_to_valley"]
    num("valley.rps", valley, f"≈ {valley:.1f} requests")
    v_tok = valley * osl
    num("valley.tok_s", v_tok, f"about {round(v_tok, -1):,.0f}")
    num("valley.util", v_tok / can, f"{v_tok / can:.1%}")
    num("valley.tokens_hour", v_tok * 3600,
        f"{v_tok * 3600 / 1e6:.1f} million")
    num("valley.per_m", usd / (v_tok * 3.6e-3),
        f"${usd / (v_tok * 3.6e-3):.2f}")
    with open(INPUTS / "mlperf-v6.1-summary.csv", newline="") as f:
        rows = {r["Scenario"]: float(r["Result"])
                for r in csv.DictReader(
                    x for x in f if not x.startswith("#"))
                if r["Platform"].startswith("GB200-NVL72")}
    ratio = rows["Server"] / rows["Interactive"]
    num("gb200.ratio", ratio, f"≈ {ratio:.2f} times")

    # Choosing the silicon
    bw = hw["H200"]["tb_s"] / hw["H100"]["tb_s"] - 1
    num("h200.more_bandwidth", bw, f"{bw:.0%} more bandwidth")


if __name__ == "__main__":
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main()
    run()
    out = {"chapter": "07", "numbers": N,
           "outputs": {"capacity.py": buf.getvalue()}}
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
    print()
