# ch15/panels.py
"""Does each panel of vLLM's own dashboards show data here?

Asks Grafana for the dashboards it provisioned, then runs every
panel's PromQL against Prometheus, with Grafana's variables filled
in, and counts the panels whose queries return a number.
"""
import json
import math
import sys
import urllib.parse
import urllib.request

GRAFANA, PROM, MODEL = sys.argv[1:4]
VARS = {"$model_name": MODEL, "$Deployment_id": MODEL,
        "$__rate_interval": "1m", "$__interval": "1m",
        "$__range": "5m"}


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def has_data(expr):
    for k, v in VARS.items():
        expr = expr.replace(k, v)
    q = urllib.parse.urlencode({"query": expr})
    res = get(f"{PROM}/api/v1/query?{q}")["data"]["result"]
    return any(not math.isnan(float(s["value"][1])) for s in res)


def panels(items):
    for p in items:
        yield from panels(p.get("panels", []))
        exprs = [t["expr"] for t in p.get("targets", [])
                 if t.get("expr")]
        if exprs:
            yield p["title"], exprs


report = []
print(" dashboard                 panels  with data")
for hit in get(f"{GRAFANA}/api/search?type=dash-db"):
    dash = get(f"{GRAFANA}/api/dashboards/uid/{hit['uid']}")
    rows = [(t, any(has_data(e) for e in exprs))
            for t, exprs in panels(dash["dashboard"]["panels"])]
    shown = sum(ok for _, ok in rows)
    print(f" {hit['title'][:24]:24s} {len(rows):7d} {shown:10d}")
    report.append({"dashboard": hit["title"], "uid": hit["uid"],
                   "panels": [{"title": t, "data": ok}
                              for t, ok in rows]})
for d in report:
    for p in d["panels"]:
        if not p["data"]:
            print(f"   no data: {d['dashboard']} / {p['title']}")
with open(sys.argv[4], "w") as f:
    json.dump(report, f, indent=1)
