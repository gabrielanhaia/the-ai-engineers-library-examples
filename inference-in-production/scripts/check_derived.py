#!/usr/bin/env python3
"""Recompute every DERIVED number from inputs/ and compare.

A lab whose chapter prints DERIVED numbers (arithmetic on cited
inputs) has a `chNN/derived.py`. It prints JSON: the default
output of the chapter's calculator(s) and one entry per number,
with its full value and the string the chapter prints ("shown").
The lab records that JSON as `measured/chNN/derived.json`.

This script (CI job `derived-data`) reruns every derived.py and
fails on any difference from the recorded JSON: a changed input,
a changed formula or a hand-edited record. It also checks that
each recorded calculator output appears in the lab's recorded
`output.txt`, that every table in inputs/*.toml names its source
URL and check date, and that worked example A's transcription in
inputs/example-a.toml matches MLPerf's rows and rules.

With --manuscript DIR (the manuscript's chapter directory, which
is not in this repository) it also checks the other direction:
every "shown" string appears in its chapter.
"""
import argparse
import csv
import datetime
import json
import math
import os
import pathlib
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
INPUTS = ROOT / "inputs"


def recompute(lab):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "derived.py"], cwd=ROOT / lab,
                       capture_output=True, text=True, env=env)
    if r.returncode:
        raise RuntimeError(f"{lab}/derived.py failed:\n{r.stderr}")
    return json.loads(r.stdout)


def compare(lab, new, old):
    problems = []
    for name, text in new["outputs"].items():
        if old["outputs"].get(name) != text:
            problems.append(f"{lab}: output of {name} differs from "
                            f"measured/{lab}/derived.json")
    out = ROOT / "measured" / lab / "output.txt"
    for name, text in new["outputs"].items():
        if out.is_file() and text not in out.read_text("utf-8"):
            problems.append(f"{lab}: output of {name} is not in "
                            f"measured/{lab}/output.txt")
    old_n = {n["key"]: n for n in old["numbers"]}
    new_n = {n["key"]: n for n in new["numbers"]}
    for key in sorted(old_n.keys() ^ new_n.keys()):
        problems.append(f"{lab}: {key} is only in one of the two")
    for key in new_n.keys() & old_n.keys():
        a, b = new_n[key], old_n[key]
        if a["shown"] != b["shown"]:
            problems.append(f"{lab}: {key} shows {a['shown']!r}, "
                            f"recorded {b['shown']!r}")
        elif not math.isclose(a["value"], b["value"], rel_tol=1e-9,
                              abs_tol=1e-12):
            problems.append(f"{lab}: {key} = {a['value']!r}, "
                            f"recorded {b['value']!r}")
    return problems


def check_inputs():
    problems = []
    for path in sorted(INPUTS.glob("*.toml")):
        with open(path, "rb") as f:
            doc = tomllib.load(f)
        top = "url" in doc and "checked" in doc
        for name, table in doc.items():
            if not isinstance(table, dict) or top:
                continue
            for field in ("url", "checked"):
                if field not in table:
                    problems.append(f"inputs/{path.name} [{name}] "
                                    f"has no {field}")
            if not isinstance(table.get("checked"), datetime.date):
                problems.append(f"inputs/{path.name} [{name}] "
                                f"checked is not a date")
    with open(INPUTS / "example-a.toml", "rb") as f:
        ex = tomllib.load(f)
    with open(INPUTS / "mlperf-rules.toml", "rb") as f:
        rules = tomllib.load(f)
    node = ex["node"]
    with open(INPUTS / "mlperf-v6.1-summary.csv", newline="") as f:
        rows = list(csv.DictReader(
            x for x in f if not x.startswith("#")))
    for scenario, key in (("Server", "server"),
                          ("Offline", "offline")):
        hit = [r for r in rows if r["SystemName"] == node["system"]
               and r["Model"] == node["model"]
               and r["Scenario"] == scenario]
        if len(hit) != 1 or float(hit[0]["Result"]) != node[key]:
            problems.append(f"inputs/example-a.toml [node] {key} "
                            f"does not match MLPerf's {scenario} row")
    bound = rules[node["model"]]["Server"]
    if (bound["ttft_ms"], bound["tpot_ms"]) != (
            node["ttft_ms"], node["tpot_ms"]):
        problems.append("inputs/example-a.toml [node] bound does "
                        "not match inputs/mlperf-rules.toml")
    return problems


def check_manuscript(chapters, lab, new):
    problems, found = [], 0
    pattern = f"{new['chapter']}-*.md"
    md = sorted(pathlib.Path(chapters).glob(pattern))
    if not md:
        print(f"{lab}: no chapter {new['chapter']} in the "
              f"manuscript; skipped")
        return problems
    # Prose is wrapped: compare with every run of white space as one.
    text = " ".join(md[0].read_text("utf-8").split())
    for n in new["numbers"]:
        if " ".join(n["shown"].split()) in text:
            found += 1
        else:
            problems.append(f"{md[0].name}: {n['key']} = "
                            f"{n['shown']!r} is not in the chapter")
    print(f"{lab}: {found} of {len(new['numbers'])} numbers found "
          f"in {md[0].name}")
    return problems


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manuscript",
                   help="the manuscript's chapters directory")
    args = p.parse_args()
    problems = check_inputs()
    labs = sorted(d.parent.name for d in ROOT.glob("ch[0-9][0-9]/"
                                                   "derived.py"))
    for lab in labs:
        new = recompute(lab)
        rec = ROOT / "measured" / lab / "derived.json"
        if not rec.is_file():
            problems.append(f"{lab}: no measured/{lab}/derived.json; "
                            f"run the lab to record it")
        else:
            old = json.loads(rec.read_text("utf-8"))
            problems += compare(lab, new, old)
        print(f"{lab}: {len(new['numbers'])} numbers and "
              f"{len(new['outputs'])} output(s) recomputed")
        if args.manuscript:
            problems += check_manuscript(args.manuscript, lab, new)
    if not args.manuscript:
        print("manuscript cross-check: skipped (no --manuscript; "
              "the manuscript is not in this repository)")
    for pr in problems:
        print("FAIL", pr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
