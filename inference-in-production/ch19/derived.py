# ch19/derived.py
"""The worksheet's numbers for chapter 19's two worked plans.

Prints JSON: the worksheet's default output, then one entry per
number with the string the worksheet prints ("shown").
scripts/check_derived.py reruns this and fails on any difference
from measured/ch19/derived.json.
"""
import contextlib
import io
import json
import sys

from worksheet import HERE, main, plan, toml

N = []


def num(key, value, shown):
    N.append({"key": key, "value": value, "shown": shown})


def run():
    for name in ("chat", "batch"):
        with contextlib.redirect_stdout(io.StringIO()):
            r = plan(toml(HERE / f"{name}.toml"))
        num(f"{name}.nodes", r["nodes"], f"{r['nodes']} x 8")
        num(f"{name}.util", r["util"], f"{r['util']:.1%} busy")
        num(f"{name}.per_m", r["per_m"], f"${r['per_m']:#.3g} per")
        num(f"{name}.requests", r["month"],
            f"{r['month'] / 1e6:.1f}M requests")
        num(f"{name}.serve", r["serve"], f"= ${r['serve']:,.0f}")
        for api, cost in r["apis"].items():
            num(f"{name}.{api}", cost, f"= ${cost:,.0f}")
        best = min(r["apis"].values())
        num(f"{name}.gap", abs(r["serve"] - best),
            f"${abs(r['serve'] - best):,.0f} a month")
        for api, even in r["even"].items():
            shown = (f"above {even / 1e6:.2f}M" if name == "batch"
                     else f"above {even:.1f} requests/s")
            num(f"{name}.even.{api}", even, shown)


if __name__ == "__main__":
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main([])
    run()
    out = {"chapter": "19", "numbers": N,
           "outputs": {"worksheet.py": buf.getvalue()}}
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
    print()
