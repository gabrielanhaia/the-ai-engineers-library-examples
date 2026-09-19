# ch06/derived.py
"""Every DERIVED number chapter 6 prints, recomputed from inputs/.

Prints JSON: the calculator's default output, then one entry per
number with the string the chapter prints ("shown").
scripts/check_derived.py reruns this and fails on any difference
from measured/ch06/derived.json.
"""
import contextlib
import io
import json
import math
import pathlib
import sys

from breakeven import HOURS, api_request, load, main, per_million

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "ch05"))
from cost import INPUTS, mlperf_row, toml  # noqa: E402

N = []
SECONDS = HOURS * 3600


def num(key, value, shown):
    N.append({"key": key, "value": value, "shown": shown})


def money(x):
    return f"${x:,.0f}"


def run():
    ex, prices = load(), toml("prices.toml")
    n_in = ex["shape"]["input_tokens"]
    n_out = ex["shape"]["output_tokens"]
    node = ex["node"]
    b200 = ex["nebius"]["B200"]
    node_h = b200 * node["gpus"]
    at_100 = per_million(node_h, node["server"])
    self_req = n_out * at_100 / 1e6
    num("at_100", at_100, f"${at_100:.4f}")
    tog, bas = ex["together"], ex["baseten"]
    tog_req = api_request(tog, n_in, n_out)
    bas_req = api_request(bas, n_in, n_out)
    num("together.input", n_in * tog["input"] / 1e6, "$0.00075 +")
    num("together.request", tog_req, f"${tog_req:.5f}")
    num("baseten.input", n_in * bas["input"] / 1e6,
        f"${n_in * bas['input'] / 1e6:.5f}")
    num("baseten.output", n_out * bas["output"] / 1e6,
        f"${n_out * bas['output'] / 1e6:.6f}")
    num("baseten.request", bas_req, f"${bas_req:.6f}")
    num("self.request", self_req, f"${self_req:.6f}")
    num("times.together", tog_req / self_req,
        f"{tog_req / self_req:.1f} times")
    num("times.baseten", bas_req / self_req,
        f"{bas_req / self_req:.1f} times")
    num("together.all_in", tog_req / n_out * 1e6,
        f"${tog_req / n_out * 1e6:.2f}")
    wrong = at_100 / tog["output"]
    num("wrong_floor", wrong, f"{wrong:.1%}")
    u_t, u_b = self_req / tog_req, self_req / bas_req
    num("u.together", u_t, f"**{u_t:.1%}**")
    num("u.baseten", u_b, f"**{u_b:.1%}**")

    # The monthly view
    month = node_h * HOURS
    tokens = node["server"] * SECONDS
    requests = tokens / n_out
    num("month.node", month, money(month))
    num("month.tokens", tokens, f"{tokens / 1e9:.1f} billion")
    num("month.requests", requests, f"{requests / 1e6:.1f} million")
    num("month.api_bill", requests * tog_req,
        f"about {money(requests * tog_req)}")
    for key, req in (("together", tog_req), ("baseten", bas_req)):
        even = month / req
        num(f"even.{key}", even, f"{even / 1e6:.1f} million")
    even = month / tog_req
    num("seconds", SECONDS, f"{SECONDS:,}")
    num("even.together.rps", even / SECONDS,
        f"{even / SECONDS:.1f} requests per")
    num("even.together.tok_s", even / SECONDS * n_out,
        f"{even / SECONDS * n_out:,.0f} output tokens")
    num("two_nodes", 2 * month, money(2 * month))
    half = month / (tog_req / 2)
    num("even.halved", half, f"{half / 1e6:.1f} million")

    # The $2 H100: the floor scales with the GPU-hour
    aws = prices["aws"]["p6-b200.48xlarge"] / 8
    num("aws.b200_per_gpu", aws, f"${aws:.2f}")
    for key, usd in (("aws", aws),
                     ("tco", prices["semianalysis_tco"]["B200"])):
        u = u_t * usd / b200
        num(f"floor.{key}", u, f"**{u:.1%}**")

    # Speed, redundancy, people
    tpot = {s: toml("mlperf-rules.toml")["gpt-oss-120b"][s]["tpot_ms"]
            for s in ("Server", "Interactive")}
    num("speed.server", 1000 / tpot["Server"],
        f"= {1000 / tpot['Server']:g} tokens")
    num("speed.interactive", 1000 / tpot["Interactive"],
        f"{1000 / tpot['Interactive']:g} tokens per second")
    gb = [float(mlperf_row(
        "NVIDIA/GB200-NVL72_GB200-186GB_aarch64x72_TRT/gpt-oss-120b/"
        + s)["Result"]) for s in ("Server", "Interactive")]
    with open(INPUTS / "mlperf-v5.1-results.json") as f:
        v51 = {r["Scenario"]: r["Performance_Result"]
               for r in json.load(f)["rows"]}
    num("pair.gb200", gb[0] / gb[1], f"= {gb[0] / gb[1]:.2f}")
    llama = v51["Server"] / v51["Interactive"]
    num("pair.llama", llama, f"= {llama:.2f}")
    num("floor.interactive", u_t * gb[0] / gb[1],
        f"{u_t * gb[0] / gb[1]:.1%}")
    num("redundancy.rps", 2 * month / tog_req / SECONDS,
        f"{2 * month / tog_req / SECONDS:.1f} per second")
    wage = ex["staff"]["usd_per_year"] / 12
    num("wage.month", wage, f"${round(wage, -1):,.0f}")
    num("wage.half", wage / 2, money(wage / 2))
    honest = 2 * month + wage / 2
    num("honest.month", honest, money(honest))
    num("honest.even", honest / tog_req,
        f"{honest / tog_req / 1e6:.1f} million")
    num("honest.rps", honest / tog_req / SECONDS,
        f"{honest / tog_req / SECONDS:.1f} per second")
    num("honest.u", honest / tog_req / requests,
        f"{honest / tog_req / requests:.1%}")

    # A hypothetical team at 1,000 requests a minute
    team = 1000 * 60 * HOURS
    num("team.requests", team, f"{team / 1e6:.1f} million")
    num("team.api", team * tog_req, money(team * tog_req))
    num("team.saving", team * tog_req - month,
        money(team * tog_req - month))
    num("team.u", team / requests, f"{team / requests:.1%}")
    num("team.honest_extra", honest - team * tog_req,
        money(honest - team * tog_req))
    r1 = prices["semianalysis_r1"]
    for key in ("input", "output"):
        m = 1 - r1[f"cost_{key}"] / r1[f"price_{key}"]
        num(f"margin.{key}", m, f"{m:.0%}")

    # The middle of the menu
    bd = prices["baseten_dedicated"]["B200"] * 60
    fd = prices["fireworks_dedicated"]["B200"]
    num("baseten.dedicated_hour", bd, f"${bd:.2f}")
    num("baseten.dedicated_ratio", bd / b200, f"{bd / b200:.2f}")
    num("fireworks.dedicated_ratio", fd / b200, f"{fd / b200:.2f}")
    code = toml("traffic.toml")["coding"]["peak_to_average"]
    num("coding.u", 0.70 / code, f"= {0.70 / code:.0%}")

    # Offline batch, in the valleys
    gap = 1 - node["offline"] / node["server"]
    num("offline.gap", gap, f"within {math.ceil(gap * 100)}%")
    off = per_million(node_h, node["offline"])
    fw = ex["fireworks"]
    batch = api_request(fw, n_in, n_out, fw["batch"])
    num("offline.per_m", off, f"${off:.4f}")
    num("offline.request", n_out * off / 1e6,
        f"${n_out * off / 1e6:.6f}")
    num("batch.request", batch, f"{'$'}{batch:.5f} for this")
    num("batch.floor", n_out * off / 1e6 / batch,
        f"{n_out * off / 1e6 / batch:.1%}")

    # When it never will
    h200 = ex["nebius"]["H200"] * 8 * HOURS
    num("h200.month", h200, money(h200))
    num("h200.two", 2 * h200, money(2 * h200))
    halving = 12 * math.log10(2)
    num("llmflation.halving", halving, f"{halving:.1f} months")
    off_res = prices["nebius_reserved"]["discount_up_to"]
    u = self_req * (1 - off_res) / (tog_req / 2)
    num("reserved.floor", u, f"{u:.1%}")
    stack = honest / (tog_req / 2)
    num("stack.requests", stack, f"{stack / 1e6:.1f} million")
    num("stack.rps", stack / SECONDS, f"{stack / SECONDS:.1f} per")


if __name__ == "__main__":
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main()
    run()
    out = {"chapter": "06", "numbers": N,
           "outputs": {"breakeven.py": buf.getvalue()}}
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
    print()
