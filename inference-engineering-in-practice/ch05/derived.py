# ch05/derived.py
"""Every DERIVED number chapter 5 prints, recomputed from inputs/.

Prints JSON: the calculator's default output, then one entry per
number with the string the chapter prints ("shown").
scripts/check_derived.py reruns this and fails on any difference
from measured/ch05/derived.json.
"""
import contextlib
import io
import json
import sys

from cost import EXAMPLE_A, INPUTS, gpu_price, main, mlperf_row
from cost import per_million, toml

WORDS = {2: "twice", 4: "four", 5: "five", 6: "six"}

N = []


def num(key, value, shown):
    N.append({"key": key, "value": value, "shown": shown})


def v51(scenario):
    with open(INPUTS / "mlperf-v5.1-results.json") as f:
        rows = json.load(f)["rows"]
    return next(r["Performance_Result"] for r in rows
                if r["Scenario"] == scenario)


def run():
    ex, prices = toml("example-a.toml"), toml("prices.toml")
    day = toml("deepseek-day.toml")
    rules = toml("mlperf-rules.toml")
    shape = ex["shape"]
    n_in, n_out = shape["input_tokens"], shape["output_tokens"]

    # The DeepSeek day
    cost = day["average_nodes"] * day["gpus_per_node"] * 24 * \
        day["usd_per_gpu_hour"]
    num("deepseek.cost", cost, f"${cost:,.0f}")
    margin = (day["revenue_usd"] - day["cost_usd"]) / day["cost_usd"]
    num("deepseek.margin", margin, f"{margin:.0%}")
    total = day["input_tokens"] + day["output_tokens"]
    num("deepseek.all_tokens", total, f"{total / 1e9:.0f} billion")
    num("deepseek.total_over_output", total / day["output_tokens"],
        f"{total / day['output_tokens']:.1f} times")
    num("deepseek.peak_over_average",
        day["peak_nodes"] / day["average_nodes"],
        f"{day['peak_nodes'] / day['average_nodes']:.2f} times")

    # Worked example A and the unit check
    row = mlperf_row(EXAMPLE_A)
    usd, _, _ = gpu_price("nebius.B200")
    tok_s, gpus = float(row["Result"]), int(row["total_accelerators"])
    node = usd * gpus
    a = per_million(node, tok_s)
    num("a.node_per_hour", node, f"${node:.2f}")
    num("a.tokens_per_hour", tok_s * 3600,
        f"{tok_s * 3600 / 1e6:.2f} million")
    num("a.usd_per_m", a, f"${a:.3f}")
    num("a.per_gpu_tok_s", tok_s / gpus, f"{tok_s / gpus:,.0f}")
    num("a.per_gpu_m_per_hour", tok_s / gpus * 3.6e-3,
        f"{tok_s / gpus * 3.6e-3:.2f}")
    low = per_million(usd, tok_s)
    high = per_million(node, tok_s / gpus)
    num("a.wrong_low", low, f"${low:.3f}")
    num("a.wrong_high", high, f"${high:.2f}")
    num("a.wrong_ratio", high / low, f"by {high / low:.0f}")
    num("a.request", n_out * a / 1e6, f"${n_out * a / 1e6:.5f}")
    lam = prices["lambda"]
    more = lam["H100 x1"] / lam["H100 x8"] - 1
    num("lambda.single_gpu_premium", more, f"{more:.1%} more")
    aws, cb = prices["aws"], prices["aws_capacity_blocks"]
    num("aws.p5_per_gpu", aws["p5.48xlarge"] / 8,
        f"${aws['p5.48xlarge'] / 8:.2f}")
    num("aws.gb200_per_gpu", cb["p6e-gb200x72"] / 72,
        f"${cb['p6e-gb200x72'] / 72:.3f}")

    # Trap one: which tokens
    s = toml("parallelism.toml")["inferencex"]["summarization"]
    ratio = (s["input_k"] + s["output_k"]) / s["output_k"]
    num("infx.total_over_output", ratio, f"= {ratio:.0f}×")
    t = ex["together"]
    req = (n_in * t["input"] + n_out * t["output"]) / 1e6
    num("together.request", req, f"${req:.5f}")
    num("together.per_m_output", req / n_out * 1e6,
        f"${req / n_out * 1e6:.2f}")

    # Trap two: three GPUs, example B, the GB200 pair
    tpot = rules["gpt-oss-120b"]["Server"]["tpot_ms"]
    num("floor.gpt_oss_server", 1000 / tpot, f"{1000 / tpot:g}")
    for gpu, name in (
            ("RTX PRO 6000", "RTX_PRO_6000_PCIE_96GBx8_TRT"),
            ("B300", "B300-SXM-270GBx8_TRT")):
        r = mlperf_row(f"Nebius/{name}/gpt-oss-120b/Server")
        usd, _, _ = gpu_price(f"nebius.{gpu}")
        m_h = float(r["Result"]) * 3.6e-3
        key = gpu.split()[0].lower()
        num(f"three.{key}.node", usd * 8, f"${usd * 8:.2f}")
        num(f"three.{key}.m_per_hour", m_h, f"{m_h:.2f}")
        num(f"three.{key}.usd_per_m", usd * 8 / m_h,
            f"${usd * 8 / m_h:.3f}")
    h200 = ex["nebius"]["H200"] * 8
    num("b.node", h200, f"${h200:.2f}")
    b = {}
    for scen in ("Server", "Interactive"):
        m_h = v51(scen) * 3.6e-3
        b[scen] = h200 / m_h
        num(f"b.{scen}.m_per_hour", m_h, f"{m_h:.2f}")
        num(f"b.{scen}.usd_per_m", b[scen], f"${b[scen]:.3f}")
    fl = [1000 / rules["llama2-70b-99"][s]["tpot_ms"]
          for s in ("Server", "Interactive")]
    num("b.floors", fl[1] / fl[0], f"from {fl[0]:g} to {fl[1]:g}")
    cut = 1 - v51("Interactive") / v51("Server")
    num("b.throughput_cut", cut, f"{cut:.0%}")
    num("b.cost_ratio", b["Interactive"] / b["Server"],
        f"{b['Interactive'] / b['Server']:.2f} times")
    gb = {}
    per_gpu_usd = prices["coreweave"]["GB200"] / 4
    num("gb200.per_gpu_price", per_gpu_usd, f"${per_gpu_usd:.2f}")
    for scen in ("Server", "Interactive"):
        r = mlperf_row("NVIDIA/GB200-NVL72_GB200-186GB_aarch64x72_TRT"
                       f"/gpt-oss-120b/{scen}")
        per = float(r["Result"]) / int(r["total_accelerators"])
        gb[scen] = per_million(per_gpu_usd, per)
        num(f"gb200.{scen}.per_gpu", per, f"{per:,.0f}")
        num(f"gb200.{scen}.m_per_hour", per * 3.6e-3,
            f"{per * 3.6e-3:.2f}")
        num(f"gb200.{scen}.usd_per_m", gb[scen], f"${gb[scen]:.3f}")
    num("gb200.cost_ratio", gb["Interactive"] / gb["Server"],
        f"{gb['Interactive'] / gb['Server']:.2f} times")

    # Trap three: utilization, from example B's Interactive price
    base = b["Interactive"]
    conv = toml("traffic.toml")["conversation"]["peak_to_average"]
    code = toml("traffic.toml")["coding"]["peak_to_average"]
    cases = [("peak_sized", 1 / conv, "{:.2f}"),
             ("conversation_70", 0.70 / conv, "{:.2f}"),
             ("coding_70", 0.70 / code, "{:.2f}")]
    for key, u, fmt in cases:
        num(f"util.{key}.u", u, f"{u * 100:.3g}%")
        num(f"util.{key}.usd_per_m", base / u, "$" + fmt.format(
            base / u))
    u = 2000 / (2 * v51("Interactive"))
    num("util.two_nodes.u", u, f"{u:.1%}")
    two = 2 * h200 / (2000 * 3.6e-3)
    num("util.two_nodes.usd_per_m", two, f"${two:.2f}")
    num("util.two_nodes.times", two / base, f"{two / base:.0f} times")

    # Why output costs more than input
    an, gem, r1 = prices["anthropic"], prices["gemini"], \
        prices["semianalysis_r1"]
    for key, i, o in (("small_answer", 10000, 500),
                      ("long_answer", 500, 10000)):
        v = (i * an["input"] + o * an["output"]) / 1e6
        num(f"opus.{key}", v, f"${v:.4f}")
    t = ex["together"]
    for key, i, o in (("opus", an["input"], an["output"]),
                      ("together", t["input"], t["output"]),
                      ("gemini", gem["input"], gem["output"])):
        num(f"ratio.{key}", o / i,
            f"a ratio of {WORDS[round(o / i)]}")
    fast = an["fast_output"] / an["output"]
    num("ratio.fast_mode", fast, f"{WORDS[round(fast)]} the price")
    c = r1["cost_output"] / r1["cost_input"]
    num("ratio.r1_cost", c, f"cost ratio of {c:.0f}")


if __name__ == "__main__":
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main([])
    run()
    out = {"chapter": "05", "outputs": {"cost.py": buf.getvalue()},
           "numbers": N}
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
    print()
