# ch03/goodput.py
"""Goodput: the highest offered rate at which the SLO still held.

    python3 goodput.py RUN.jsonl... > goodput.json

Each file holds the records of one run at one offered rate. A
request counts only if it met BOTH targets; attainment is the share
of a run's requests that did. Rates are walked upward, and the walk
stops at the first rate whose attainment misses the target.
"""
import json
import sys
import tomllib

from metrics import per_request

SLO = tomllib.load(open("slo.toml", "rb"))


def met(rec):
    if rec["error"] or not rec["text_chunk_times"]:
        return False
    r = per_request(rec)
    ttft_ok = r["ttft"] * 1000 <= SLO["ttft"]["target_ms"]
    tpot_ok = (r["tpot"] is None
               or r["tpot"] * 1000 <= SLO["tpot"]["target_ms"])
    return ttft_ok and tpot_ok


def main():
    runs = {}
    for path in sys.argv[1:]:
        recs = [json.loads(line) for line in open(path)]
        runs[recs[0]["offered_rate"]] = recs
    curve, goodput = [], 0.0
    for rate in sorted(runs):
        recs = runs[rate]
        att = sum(met(r) for r in recs) / len(recs)
        curve.append({"offered_rate": rate, "requests": len(recs),
                      "attainment": att})
    for point in curve:
        if point["attainment"] < SLO["attainment"]["share"]:
            break
        goodput = point["offered_rate"]
    print(json.dumps({
        "slo": SLO, "curve": curve,
        "goodput_per_replica": goodput / SLO["goodput"]["replicas"]},
        indent=1))


if __name__ == "__main__":
    main()
