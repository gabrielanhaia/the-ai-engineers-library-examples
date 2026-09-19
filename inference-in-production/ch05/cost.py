# ch05/cost.py
"""Cost per million output tokens, from a published row.

One division: the unit's price per hour over the tokens the same
unit makes in an hour. The throughput is a row of MLPerf's table
in inputs/, never a number typed in: a laptop's tokens per second
describe the laptop. Token type, latency bound and utilization
are printed beside every figure.
"""
import argparse
import csv
import math
import pathlib
import re
import tomllib

INPUTS = pathlib.Path(__file__).resolve().parents[1] / "inputs"
EXAMPLE_A = "Nebius/B200-SXM-180GBx8_TRT/gpt-oss-120b/Server"


def toml(name):
    with open(INPUTS / name, "rb") as f:
        return tomllib.load(f)


def mlperf_row(name):
    """An MLPerf row, named Organization/Platform/Model/Scenario."""
    with open(INPUTS / "mlperf-v6.1-summary.csv", newline="") as f:
        rows = csv.DictReader(x for x in f if not x.startswith("#"))
        for r in rows:
            keys = ("Organization", "Platform", "Model", "Scenario")
            if "/".join(r[k] for k in keys) == name:
                return r
    raise SystemExit(f"no MLPerf row named {name}")


def gpu_price(key):
    """$ per GPU-hour for 'table.GPU', e.g. 'nebius.B200'."""
    table, gpu = key.split(".", 1)
    t = {**toml("prices.toml"), **toml("example-a.toml")}[table]
    return t[gpu] / t.get("gpus", 1), gpu, t["checked"]


def per_million(usd_per_hour, tokens_per_s):
    """The one division: $ per million tokens."""
    return usd_per_hour / (tokens_per_s * 3600 / 1e6)


def price(row, usd_gpu_hour, gpu):
    """$/M at 100%, per unit and per GPU: the two must agree."""
    measured_on = re.split(r"\W+", row["accelerator_model_name"])
    if gpu.split()[0] not in measured_on:
        raise SystemExit(f"unit check: {gpu} price, row measured "
                         f"on {row['accelerator_model_name']}")
    gpus, tok_s = int(row["total_accelerators"]), float(row["Result"])
    by_unit = per_million(usd_gpu_hour * gpus, tok_s)
    by_gpu = per_million(usd_gpu_hour, tok_s / gpus)
    assert math.isclose(by_unit, by_gpu), "unit check failed"
    return gpus, tok_s, by_unit


def main(argv=None):
    shape = toml("example-a.toml")["shape"]
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--row", default=EXAMPLE_A)
    p.add_argument("--price", default="nebius.B200")
    p.add_argument("--input", type=int, default=shape["input_tokens"])
    p.add_argument("--output", type=int,
                   default=shape["output_tokens"])
    p.add_argument("--utilization", type=float, default=1.0)
    a = p.parse_args(argv)
    u = a.utilization
    if not 0 < u <= 1:
        raise SystemExit("utilization is a share: 0 < U <= 1")
    row = mlperf_row(a.row)
    usd, gpu, checked = gpu_price(a.price)
    gpus, tok_s, at_100 = price(row, usd, gpu)
    rules = toml("mlperf-rules.toml")
    bound = rules[row["Model"]].get(row["Scenario"])
    per_m = at_100 / u
    print(f"{row['Model']}, MLPerf {row['version']} "
          f"{row['Division']}, {row['Scenario']}")
    print(f"  system   {row['SystemName']}")
    print(f"  unit     {gpus} x ${usd:.2f} = "
          f"${usd * gpus:,.2f} an hour")
    print(f"  tokens   {tok_s:,.1f}/s x 3,600 = "
          f"{tok_s * 3600 / 1e6:,.2f} million an hour")
    print(f"  per unit ${usd * gpus:,.2f} / {tok_s * 3.6e-3:,.2f} "
          f"= ${at_100:.4f} per million")
    print(f"  per GPU  ${usd:.2f} / {tok_s / gpus * 3.6e-3:,.2f} "
          f"= ${at_100:.4f} per million (unit check)")
    print(f"\n${per_m:#.3g} per million {rules['tokens']} tokens")
    print(f"  tokens   {rules['tokens']} only; each request's "
          f"prefill is included")
    if bound:
        print(f"  latency  p99 TTFT <= {bound['ttft_ms']:,} ms, "
              f"p99 TPOT <= {bound['tpot_ms']} ms")
        print(f"           (a floor of {1000 / bound['tpot_ms']:g} "
              f"tokens/s per user)")
    else:
        print("  latency  none: Offline has no latency bound")
    if u == 1:
        print("  load     100% utilization; divide by your average")
    else:
        print(f"  load     {u * 100:g}% utilization: "
              f"${at_100:.4f} / {u:g}")
    print(f"  request  {a.input:,} in / {a.output:,} out: "
          f"${a.output * per_m / 1e6:#.2g}")
    ratio = a.input * shape["output_tokens"]
    if row["Model"] != shape["model"] or ratio != (
            a.output * shape["input_tokens"]):
        print(f"  WARNING  measured on MLPerf's {row['Model']} set, "
              f"not your shape:")
        print("           measure yours before you price it "
              "(chapter 4)")
    print(f"  inputs   MLPerf {row['version']} summary.csv; "
          f"{a.price}, {checked}")


if __name__ == "__main__":
    main()
