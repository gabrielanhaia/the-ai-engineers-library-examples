#!/usr/bin/env python3
"""Write screens/dashboards/book-screens.json.

vLLM 0.29.0 ships three Grafana dashboards, and the book captures two
panels from them (S1, S3). The other replayed captures need panels
vLLM does not ship: the preemption counter, a prefix-cache hit ratio,
a per-replica version of it, a queue-against-replicas panel and the
cost recording rule. They live here, one dashboard, one panel per
capture, so `screens/capture.py` can address each by its panel id.

Every panel is built for a 4.4-inch black-and-white page: series are
separated by line style as well as colour, the colours are chosen to
stay apart in greyscale, and no panel carries more series than a
reader can follow at that size.

    python3 screens/make_dashboards.py
"""
from __future__ import annotations

import json
import pathlib

DS = {"type": "prometheus", "uid": "prometheus"}

# Print palette: near-black, the series' burnt orange, and two greys.
# Each is a clearly different grey when the page is printed in B&W.
INK = "#1a1a1a"
ORANGE = "#d97b2b"
GREY = "#8a8a8a"
MIDGREY = "#5c5c5c"

SOLID = {"fill": "solid"}


def dash(*seg: int) -> dict:
    return {"fill": "dash", "dash": list(seg)}


def dot(*seg: int) -> dict:
    return {"fill": "dot", "dash": list(seg)}


def series(name: str, color: str, style: dict, width: float = 2.0,
           extra: list | None = None) -> dict:
    props = [
        {"id": "color", "value": {"mode": "fixed", "fixedColor": color}},
        {"id": "custom.lineStyle", "value": style},
        {"id": "custom.lineWidth", "value": width},
    ]
    props.extend(extra or [])
    return {"matcher": {"id": "byName", "options": name}, "properties": props}


def panel(pid: int, title: str, targets: list[dict], *, unit: str = "short",
          decimals: int | None = None, mn=0, mx=None, overrides=None,
          axis_label: str = "", legend: bool = True,
          interpolation: str = "linear", axis_soft_max=None) -> dict:
    custom = {
        "drawStyle": "line",
        "lineInterpolation": interpolation,
        "lineWidth": 2,
        "fillOpacity": 0,
        "gradientMode": "none",
        "showPoints": "never",
        "spanNulls": True,
        "axisLabel": axis_label,
        "axisPlacement": "auto",
        "axisBorderShow": True,
        "scaleDistribution": {"type": "linear"},
        "thresholdsStyle": {"mode": "off"},
    }
    if axis_soft_max is not None:
        custom["axisSoftMax"] = axis_soft_max
    defaults = {
        "custom": custom,
        "unit": unit,
        "color": {"mode": "fixed", "fixedColor": INK},
        "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
    }
    if decimals is not None:
        defaults["decimals"] = decimals
    if mn is not None:
        defaults["min"] = mn
    if mx is not None:
        defaults["max"] = mx
    return {
        "id": pid,
        "type": "timeseries",
        "title": title,
        "datasource": DS,
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "fieldConfig": {"defaults": defaults, "overrides": overrides or []},
        "options": {
            "legend": {
                "showLegend": legend,
                "displayMode": "list",
                "placement": "bottom",
                "calcs": [],
            },
            "tooltip": {"mode": "multi", "sort": "none"},
        },
        "targets": [
            dict(t, refId=chr(ord("A") + i), datasource=DS, range=True)
            for i, t in enumerate(targets)
        ],
    }


PANELS = [
    # S2 -- ch09. The preemption counter's own increase, so the panel
    # reads as the alert does: flat, then one step per preemption.
    panel(
        2,
        "Preemptions",
        [{"expr": 'increase(vllm:num_preemptions_total[6m])',
          "legendFormat": "Preemptions (6m increase)"}],
        decimals=0,
        axis_soft_max=2.5,
        overrides=[series("Preemptions (6m increase)", INK, SOLID, 2.4)],
        axis_label="requests preempted",
    ),
    # S4 -- ch10, two panels stacked by the capture.
    panel(
        4,
        "Prefix cache hit rate",
        [{"expr": "sum(rate(vllm:prefix_cache_hits_total[15s]))"
                  " / sum(rate(vllm:prefix_cache_queries_total[15s]))",
          "legendFormat": "Hit rate (prompt tokens)"}],
        unit="percentunit",
        mn=0,
        mx=1,
        overrides=[series("Hit rate (prompt tokens)", INK, SOLID, 2.4)],
    ),
    panel(
        5,
        "Time to first token",
        [{"expr": "rate(vllm:time_to_first_token_seconds_sum[15s])"
                  " / rate(vllm:time_to_first_token_seconds_count[15s])",
          "legendFormat": "TTFT (mean)"}],
        unit="s",
        overrides=[series("TTFT (mean)", INK, SOLID, 2.4)],
    ),
    # S5 -- ch14. Token-weighted hit rate per replica, the same ratio
    # the lab prints, for the round-robin run and the prefix-aware run.
    # Its six series are styled in main(), from the pod names in
    # measured/ch14/replicas.om.
    panel(
        6,
        "Prefix cache hit rate per replica",
        [{"expr": 'label_replace(vllm:prefix_cache_hits_total'
                  ' / vllm:prefix_cache_queries_total,'
                  ' "r", "$1", "pod", ".*-(.....)$")',
          "legendFormat": "{{policy}} · {{r}}"}],
        unit="percentunit",
        mn=0,
        mx=1,
        legend=True,
    ),
    # S6 -- ch16. Queue depth on the left axis, replicas on the right.
    panel(
        7,
        "Queue depth and replicas",
        [
            {"expr": "lab_queue_waiting", "legendFormat": "Requests waiting"},
            {"expr": 'lab_replicas{state="desired"}',
             "legendFormat": "Replicas desired"},
            {"expr": 'lab_replicas{state="ready"}',
             "legendFormat": "Replicas ready"},
        ],
        decimals=0,
        interpolation="stepAfter",
        axis_label="requests waiting",
        overrides=[
            series("Requests waiting", INK, SOLID, 2.4),
            series("Replicas desired", ORANGE, dash(12, 6), 3.4,
                   [{"id": "custom.axisPlacement", "value": "right"},
                    {"id": "custom.axisLabel", "value": "replicas"},
                    {"id": "max", "value": 6},
                    {"id": "min", "value": 0}]),
            series("Replicas ready", "#3d3d3d", dot(2, 8), 2.0,
                   [{"id": "custom.axisPlacement", "value": "right"},
                    {"id": "custom.axisLabel", "value": "replicas"},
                    {"id": "max", "value": 6},
                    {"id": "min", "value": 0}]),
        ],
    ),
    # S12 -- ch15. The cost recording rule, read from a simulator
    # driven at chapter 5's cited per-node output-token rate.
    panel(
        8,
        "Cost per million output tokens (simulated at a cited rate)",
        [{"expr": "fleet:usd_per_million_output_tokens:rate5m",
          "legendFormat": "$ / M output tokens"}],
        unit="currencyUSD",
        decimals=3,
        mn=0,
        axis_soft_max=0.3,
        overrides=[series("$ / M output tokens", INK, SOLID, 2.4)],
    ),
]

# Three styles, reused for each policy's three replicas: inside one
# run the replicas are told apart by style, and the two runs sit in
# different halves of the time axis.
REPLICA_STYLES = [
    (INK, SOLID, 3.4),
    (ORANGE, dash(12, 6), 2.1),
    (MIDGREY, dot(1, 5), 1.1),
]


def replica_overrides(om: pathlib.Path) -> list[dict]:
    """One override per series of the ch14 panel, named as Grafana will
    name it once `label_replace` has cut the pod name down to its last
    five characters."""
    import re

    seen: dict[str, list[str]] = {}
    for line in om.read_text().splitlines():
        m = re.search(r'policy="([^"]*)".*?pod="[^"]*-(.{5})"', line)
        if not m:
            continue
        seen.setdefault(m.group(1), [])
        if m.group(2) not in seen[m.group(1)]:
            seen[m.group(1)].append(m.group(2))
    out = []
    for policy in sorted(seen):
        for i, r in enumerate(seen[policy]):
            color, style, width = REPLICA_STYLES[i % len(REPLICA_STYLES)]
            out.append(series(f"{policy} · {r}", color, style, width))
    return out


def main() -> int:
    out = pathlib.Path(__file__).resolve().parent / "dashboards"
    out.mkdir(exist_ok=True)
    om = pathlib.Path(__file__).resolve().parents[1] / "measured/ch14/replicas.om"
    if om.exists():
        for p in PANELS:
            if p["id"] == 6:
                p["fieldConfig"]["overrides"] = replica_overrides(om)
    doc = {
        "uid": "book-screens",
        "title": "Book screens",
        "description": "Panels the book captures that vLLM's own "
                       "dashboards do not ship. Built by "
                       "screens/make_dashboards.py.",
        "schemaVersion": 41,
        "version": 1,
        "editable": False,
        "time": {"from": "now-1h", "to": "now"},
        "timezone": "utc",
        "refresh": "",
        "panels": PANELS,
    }
    # Lay the panels out so the dashboard is also readable as a page.
    for i, p in enumerate(doc["panels"]):
        p["gridPos"] = {"h": 8, "w": 12, "x": (i % 2) * 12, "y": (i // 2) * 8}
    (out / "book-screens.json").write_text(json.dumps(doc, indent=2) + "\n")
    print("wrote", out / "book-screens.json", f"({len(PANELS)} panels)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
