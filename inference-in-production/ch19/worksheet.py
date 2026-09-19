# ch19/worksheet.py
"""The decision worksheet: a plan file in, a plan you can defend.

It runs chapter 7's capacity count, chapter 5's cost at the
utilization you reach and chapter 6's API comparison, on rates and
prices from inputs/, then prints the levers, engine and gate the
plan names. No laptop rate is priced; no number is typed in here.
"""
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
for ch in ("ch05", "ch06", "ch07"):
    sys.path.insert(0, str(HERE.parent / ch))
from breakeven import HOURS, api_request, usd  # noqa: E402
from capacity import INPUTS, cited_rate, toml  # noqa: E402
from cost import per_million  # noqa: E402


def interactive(p, node, osl):
    """Nodes for the peak at the SLO's rate, plus spares."""
    day = toml(INPUTS / "traffic.toml")[p["pattern"]]
    peak = p["average_rps"] * day["peak_to_average"] * osl
    hw = toml(INPUTS / "hardware.toml")
    _, per_gpu = cited_rate(p | {"gpu": node["gpu"]}, hw)
    rate, need = per_gpu * node["gpus"], math.ceil(
        peak / (p["peak_load"] * per_gpu))
    nodes = spare = math.ceil(need / node["gpus"])
    while p["survive_node_loss"] and (spare - 1) * rate < peak:
        spare += 1
    print(f"1 workload  {p['average_rps']:g} requests/s average; "
          f"{p['pattern']}: peak x {day['peak_to_average']}")
    print(f"2 SLO       p99 TTFT <= {p['ttft_ms']:,} ms, TPOT <= "
          f"{p['tpot_ms']} ms: {1000 / p['tpot_ms']:g} tokens/s")
    print(f"3 capacity  peak {peak / osl:g} requests/s = "
          f"{peak:,.0f} output tokens/s")
    print(f"            {peak:,.0f} / ({p['peak_load']:.2f} x "
          f"{per_gpu:,.1f}) = {peak / p['peak_load'] / per_gpu:.2f}"
          f" -> {need} GPUs")
    down = f"; {spare} so it fits with one down" * (spare > nodes)
    print(f"            = {nodes} node of {node['gpus']}{down}")
    return spare, rate, p["average_rps"] * osl, \
        p["average_rps"] * HOURS * 3600


def batch(p, node, osl):
    """Nodes to finish the night's documents inside the window."""
    rate = node["offline"]
    busy = p["documents"] * osl / rate / 3600
    nodes = math.ceil(busy / p["window_h"])
    print(f"1 workload  {p['documents']:,} documents a night, due "
          f"in {p['window_h']} h")
    print("2 SLO       none per token: the window is the bound")
    print(f"3 capacity  {rate:,.1f} output tokens/s a node, Offline")
    print(f"            {p['documents']:,} x {osl:,} / {rate:,.1f} "
          f"= {busy:.2f} h -> {nodes} node")
    return nodes, rate, p["documents"] * osl / 86400, \
        p["documents"] * HOURS / 24


def plan(p):
    ex = toml(INPUTS / f"{p['rate']}.toml")
    node, shape = ex["node"], ex["shape"]
    isl, osl = shape["input_tokens"], shape["output_tokens"]
    print(f"plan: {p['title']} (a hypothetical)")
    size = batch if p.get("batch") else interactive
    nodes, rate, avg, month = size(p, node, osl)
    node_h = ex["nebius"][node["gpu"]] * node["gpus"]
    at_100, util = per_million(node_h, rate), avg / (nodes * rate)
    staff = p["engineers"] * ex["staff"]["usd_per_year"] / 12
    serve = nodes * node_h * HOURS + staff
    print(f"4 cost      {nodes} x {node['gpus']} {node['gpu']}: "
          f"${nodes * node_h:,.2f} an hour, {util:.1%} busy")
    print(f"            ${at_100:.4f} / {util:.3f} = "
          f"${at_100 / util:#.3g} per million output tokens")
    print(f"5 compare   {month / 1e6:.1f}M requests a month "
          f"of {isl:,} in / {osl:,} out")
    print(f"            {'serve':16}${nodes * node_h * HOURS:,.0f}"
          f" + staff ${staff:,.0f} = ${serve:,.0f}")
    apis = {}
    for api in p["apis"]:
        scale = ex[api]["batch"] if p.get("batch") else 1.0
        name = api + " batch" * bool(p.get("batch"))
        apis[name] = api_request(ex[api], isl, osl, scale)
        print(f"            {name:16}{usd(apis[name])} x "
              f"{month / 1e6:.1f}M = ${apis[name] * month:,.0f}")
    cheapest = min(apis, key=apis.get)
    gap = serve - apis[cheapest] * month
    if gap > 0:
        print(f"  verdict   buy from {cheapest}: ${gap:,.0f} a month "
              f"less than serving")
    else:
        print(f"  verdict   serve: ${-gap:,.0f} a month less than "
              f"{cheapest}")
    for title in ("levers", "engine", "gate"):
        n = {"levers": 6, "engine": 7, "gate": 8}[title]
        for i, line in enumerate(p[title]):
            print(f"{f'{n} {title}' if i == 0 else '':12}{line}")
    print("  reopen    when a price moves, a GPU or model ships, or")
    even = {}
    for name, req in apis.items():
        if p.get("batch"):
            even[name] = serve / req / (HOURS / 24)
            print(f"            above {even[name] / 1e6:.2f}M "
                  f"documents a night ({name})")
        else:
            even[name] = serve / req / (HOURS * 3600)
            print(f"            above {even[name]:.1f} requests/s "
                  f"({name})")
    return {"nodes": nodes, "util": util, "per_m": at_100 / util,
            "serve": serve, "month": month, "even": even,
            "apis": {n: r * month for n, r in apis.items()}}


def main(paths):
    for i, path in enumerate(paths or [HERE / "chat.toml",
                                       HERE / "batch.toml"]):
        print("\n" * (i > 0), end="")
        plan(toml(path))


if __name__ == "__main__":
    main(sys.argv[1:])
