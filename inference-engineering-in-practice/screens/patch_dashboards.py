#!/usr/bin/env python3
"""Print patches for vLLM 0.29.0's own Grafana dashboards.

The book's paperback interior is black ink on white paper, so a panel
whose series differ only by colour is unreadable there, and Grafana's
default palette (a pale green beside a pale yellow) prints as two
almost identical light greys. This adds one `custom.lineStyle`,
`custom.lineWidth` and fixed `color` override per series to the four
panels the book captures from vLLM's dashboards, and nothing else: no
query, no unit, no title, no axis and no layout is touched, so the
panel a reader sees is the panel vLLM ships, in ink that survives the
press.

    python3 screens/patch_dashboards.py .work/screens/dashboards

Idempotent: it rewrites the file in place from the fetched original
and records what it changed in `print-patches.json` beside the folder.
"""
from __future__ import annotations

import json
import pathlib
import sys

SOLID = {"fill": "solid"}

INK = "#1a1a1a"
ORANGE = "#d97b2b"
MIDGREY = "#5c5c5c"
GREY = "#9a9a9a"

PROPS = ("custom.lineStyle", "custom.lineWidth", "color",
         "custom.fillOpacity", "custom.showPoints", "displayName")


def dash(*segments: int) -> dict:
    return {"fill": "dash", "dash": list(segments)}


def dot(*segments: int) -> dict:
    return {"fill": "dot", "dash": list(segments)}


# file -> panel title -> series name -> (colour, style, width, rename)
#
# The name is the one Grafana ends up with, which is not always the
# panel's `legendFormat`: the TTFT panel asks Prometheus for `format:
# table`, and a table frame's value column is called "Value", so the
# legend of vLLM's own dashboard reads "Value" there. `rename` puts the
# panel's own intended label back, and changes nothing else.
PATCHES: dict[str, dict[str, dict[str, tuple]]] = {
    "grafana.json": {
        "Scheduler State": {
            "Num Running": (INK, SOLID, 2.4, None),
            "Num Waiting": (ORANGE, dash(12, 6), 2.2, None),
        },
        "Cache Utilization": {
            "GPU Cache Usage": (INK, SOLID, 2.4, None),
        },
    },
    "performance_statistics.json": {
        "TTFT Over Time": {
            "Value": (INK, SOLID, 2.4, "TTFT (Avg)"),
        },
        "ITL (Time Per Output Token) Over Time": {
            "ITL (Avg)": (INK, SOLID, 2.6, None),
            "ITL (p50)": (GREY, dash(14, 6), 2.2, None),
            "ITL (p90)": (ORANGE, dash(5, 5), 2.2, None),
            "ITL (p99)": (MIDGREY, dot(2, 9), 2.6, None),
        },
    },
}


def override(name: str, color: str, style: dict, width: float,
             rename: str | None) -> dict:
    props = [
        {"id": "color", "value": {"mode": "fixed", "fixedColor": color}},
        {"id": "custom.lineStyle", "value": style},
        {"id": "custom.lineWidth", "value": width},
        # Four translucent fills stacked on one another print as one
        # grey smear, so the lines carry the panel on paper.
        {"id": "custom.fillOpacity", "value": 0},
        {"id": "custom.showPoints", "value": "never"},
    ]
    if rename:
        props.append({"id": "displayName", "value": rename})
    return {"matcher": {"id": "byName", "options": name}, "properties": props}


def patch(path: pathlib.Path, wanted: dict) -> list[str]:
    doc = json.loads(path.read_text())
    done = []
    for panel in doc.get("panels", []):
        series = wanted.get(panel.get("title"))
        if not series:
            continue
        cfg = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
        cfg.setdefault("custom", {})
        ovr = panel["fieldConfig"].setdefault("overrides", [])
        # Drop any override this script wrote before, then re-add.
        keep = [
            o
            for o in ovr
            if not (
                o.get("matcher", {}).get("id") == "byName"
                and o.get("matcher", {}).get("options") in series
                and all(p.get("id") in PROPS for p in o.get("properties", []))
            )
        ]
        keep.extend(override(n, *spec) for n, spec in series.items())
        panel["fieldConfig"]["overrides"] = keep
        done.append(f'{path.name}: {panel["title"]} ({len(series)} series)')
    path.write_text(json.dumps(doc, indent=2) + "\n")
    return done


def main(argv: list[str]) -> int:
    root = pathlib.Path(argv[1] if len(argv) > 1 else ".work/screens/dashboards")
    report = []
    for name, wanted in PATCHES.items():
        path = root / name
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 1
        report.extend(patch(path, wanted))
    # Beside the folder, not inside it: Grafana provisions every
    # JSON in the dashboards folder and logs an error on this one.
    (root.parent / "print-patches.json").write_text(
        json.dumps(
            {
                "why": "black-and-white print: one line style per series",
                "patched": report,
            },
            indent=2,
        )
        + "\n"
    )
    for line in report:
        print("patched", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
