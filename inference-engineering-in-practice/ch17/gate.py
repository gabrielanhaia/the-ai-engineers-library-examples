# ch17/gate.py
"""The verifier as a release gate: every engine's schema-valid rate,
per kind, must reach the threshold recorded in thresholds.json.
Exits 1 if any rate falls below. Chapter 18's quality gate runs it.

  gate.py THRESHOLDS DIR    (DIR holds ENGINE.jsonl from verify.py)
"""
import json
import sys

limits = json.load(open(sys.argv[1]))
failed = False
for engine, kinds in limits.items():
    with open(f"{sys.argv[2]}/{engine}.jsonl") as f:
        rows = [json.loads(x) for x in f]
    for kind, floor in kinds.items():
        got = [r["valid"] for r in rows if r["kind"] == kind]
        rate = sum(got) / len(got)
        ok = rate >= floor
        failed |= not ok
        print(f" {'pass' if ok else 'FAIL'}  {engine:10s} {kind:12s}"
              f" {rate:5.2f} >= {floor:.2f}")
sys.exit(1 if failed else 0)
