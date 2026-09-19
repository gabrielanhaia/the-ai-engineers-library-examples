# ch16/report.py
"""Summarise what the ch16 lab recorded in measured/ch16/.

  scaling    the queue and the replica count over time, and when
             each step of the scale-out happened (simulated)
  coldstart  the vLLM CPU container's phases, run by run (laptop)
"""
import csv
import json
import pathlib
import statistics
import sys

M = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else ".")


def num(x):
    return float(x) if x not in ("", None) else None


def scaling():
    rows = [{k: num(v) for k, v in r.items()}
            for r in csv.DictReader(open(M / "timeline.csv"))]
    reqs = [json.loads(x) for x in open(M / "requests.jsonl")]
    burst = min(r["t"] for r in reqs if r["phase"] == 1)
    calm = min(r["t"] for r in reqs if r["phase"] == 2)

    def first(cond, after=0.0):
        return next((r["t"] for r in rows
                     if r["t"] >= after and cond(r)), None)

    top = max(r["replicas"] or 0 for r in rows)
    ev = {
        "burst_starts": burst,
        "queue_reaches_threshold": first(
            lambda r: (r["waiting"] or 0) >= 5, burst),
        "replicas_raised": first(
            lambda r: (r["replicas"] or 0) > 1, burst),
        "second_replica_ready": first(
            lambda r: (r["ready"] or 0) > 1, burst),
        "peak_replicas_ready": first(
            lambda r: (r["ready"] or 0) >= top, burst),
        "burst_ends": calm,
        "queue_empty_again": first(
            lambda r: (r["waiting"] or 0) == 0, calm),
        "replicas_lowered": first(
            lambda r: (r["replicas"] or top) < top, calm),
    }
    peak = {"waiting": max(r["waiting"] or 0 for r in rows),
            "replicas": top}
    print("simulated: timings are the simulator's configuration")
    print(f"{'t (s)':>6}{'waiting':>9}{'running':>9}"
          f"{'desired':>9}{'replicas':>10}{'ready':>7}")
    shown = -15.0
    for r in rows:
        if r["t"] - shown >= 15:
            shown = r["t"]
            print(f"{r['t']:>6.0f}" + "".join(
                f"{'' if r[k] is None else int(r[k]):>{w}}"
                for k, w in (("waiting", 9), ("running", 9),
                             ("desired", 9), ("replicas", 10),
                             ("ready", 7))))
    for k, v in ev.items():
        print(f"{k.replace('_', ' '):<26}"
              f"{'-' if v is None else f'{v:.0f} s'}")
    lat = [r["ttft"] for r in reqs if r["ttft"] is not None]
    out = {"kind": "simulated (llm-d-inference-sim v0.11.2, "
                   "KEDA 2.20.2, kind)",
           "events_s": ev, "peak": peak,
           "requests": len(reqs),
           "errors": sum(r["status"] != 200 for r in reqs),
           "ttft_p50_s": round(statistics.median(lat), 3),
           "ttft_max_s": round(max(lat), 3)}
    (M / "scaling.json").write_text(json.dumps(out, indent=2) + "\n")

    om = ["# TYPE lab_queue_waiting gauge"]
    om += [f'lab_queue_waiting{{kind="simulated"}} {r["waiting"]:g} '
           f'{r["ts"]:.1f}' for r in rows if r["waiting"] is not None]
    om += ["# TYPE lab_replicas gauge"]
    om += [f'lab_replicas{{kind="simulated",state="{k}"}} '
           f'{r[k]:g} {r["ts"]:.1f}'
           for k in ("desired", "ready") for r in rows
           if r[k] is not None]
    om.append("# EOF")
    (M / "timeline.om").write_text("\n".join(om) + "\n")


def coldstart():
    runs = [json.loads(x) for x in open(M / "coldstart.jsonl")]
    print("laptop, CPU container; not a GPU cold start (seconds)")
    cols = (("pull", "pull_s"), ("start", "start_s"),
            ("weights", "weights_s"), ("warm-up", "warmup_s"),
            ("compile", "compile_s"), ("rest", "rest_s"),
            ("total", "total_s"), ("TTFT 1", "first_ttft_s"),
            ("TTFT 2", "second_ttft_s"))
    print("run" + "".join(f"{h:>8}" for h, _ in cols))
    for r in runs:
        print(f"{r['run']:>3}" + "".join(
            f"{'-' if r[k] is None else f'{r[k]:.2f}':>8}"
            for _, k in cols))
    med = {k: round(statistics.median(r[k] for r in runs), 3)
           for _, k in cols if all(r[k] is not None for r in runs)}
    print("med" + "".join(f"{med[k]:>8.2f}" if k in med
                          else f"{'-':>8}" for _, k in cols))
    out = {"kind": "measured (vLLM 0.29.0 CPU image in kind, "
                   "reference laptop)",
           "runs": runs, "median": med}
    text = json.dumps(out, indent=2) + "\n"
    (M / "coldstart.json").write_text(text)


if __name__ == "__main__":
    {"scaling": scaling, "coldstart": coldstart}[sys.argv[1]]()
