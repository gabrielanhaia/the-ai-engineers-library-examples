# ch15/spans.py
"""What reached the collector: count the spans in the OTLP JSON
file the collector's file exporter wrote, by name, and print the
attributes of one request span."""
import collections
import json
import sys

spans = []
for line in open(sys.argv[1]):
    for rs in json.loads(line).get("resourceSpans", []):
        res = {a["key"]: a["value"] for a in
               rs.get("resource", {}).get("attributes", [])}
        for ss in rs.get("scopeSpans", []):
            for s in ss.get("spans", []):
                spans.append((res, s))

if not spans:
    sys.exit("no spans reached the collector")
services = {r.get("service.name", {}).get("stringValue")
            for r, _ in spans}
names = collections.Counter(s["name"] for _, s in spans)
print(f"spans received: {len(spans)}, service.name "
      f"{', '.join(sorted(map(str, services)))}")
for name, n in names.most_common():
    print(f"  {n:4d}  {name}")
req = [s for _, s in spans if s["name"] == "llm_request"]
if req:
    print("one llm_request span:")
    for a in sorted(req[0]["attributes"], key=lambda a: a["key"]):
        v = next(iter(a["value"].values()))
        if isinstance(v, float):
            v = round(v, 3)
        print(f"  {a['key']:40s} {v}")
