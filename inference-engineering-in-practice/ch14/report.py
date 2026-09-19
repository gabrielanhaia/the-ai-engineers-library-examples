# ch14/report.py
"""Summarise what the ch14 lab recorded in measured/ch14/.

  routing   per-replica prefix-cache hit rate, stickiness and TTFT,
            round-robin vs prefix-aware (simulated)
  priority  probe and flood TTFT under each class (simulated)
  lora      the multi-LoRA step on the real vLLM CPU engine
  om        the replicas' counters sampled every 2 s (stdin) as
            OpenMetrics, for the per-replica hit-rate panel

Each mode prints a table and writes a JSON summary next to its
inputs. Every simulator number is labeled "simulated".
"""
import json
import pathlib
import statistics
import sys
import textwrap

M = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else ".")


def rows(name):
    with open(M / name) as f:
        return [json.loads(line) for line in f if line.strip()]


def pct(xs, q):
    xs = sorted(xs)
    return xs[round(q * (len(xs) - 1))]


def routing():
    out = {"kind": "simulated (llm-d-inference-sim v0.11.2)"}
    print("simulated: timings are the simulator's configuration")
    print(f"{'policy':<14}{'replica hit rates':<22}{'all':>6}"
          f"{'same':>7}{'TTFT p50':>10}")
    for pol, tag in (("round-robin", "rr"), ("prefix-aware", "pa")):
        reps = json.loads((M / f"replicas-{tag}.json").read_text())
        hits = sum(r["hits"] for r in reps)
        qs = sum(r["queries"] for r in reps)
        reqs = rows(f"conversations-{tag}.jsonl")
        last, same, n = {}, 0, 0
        for r in sorted(reqs, key=lambda r: (r["conv"], r["turn"])):
            if r["turn"] > 1:
                n += 1
                same += r["pod"] == last[r["conv"]]
            last[r["conv"]] = r["pod"]
        ttft = [r["ttft"] for r in reqs]
        per = [r["hits"] / r["queries"] for r in reps]
        out[pol] = {
            "requests": len(reqs),
            "replica_hit_rates": [round(x, 3) for x in per],
            "hit_rate": round(hits / qs, 3),
            "same_replica_as_last_turn": round(same / n, 3),
            "ttft_p50_s": round(statistics.median(ttft), 3),
            "ttft_p90_s": round(pct(ttft, 0.9), 3),
        }
        o = out[pol]
        rates = " ".join(f"{x:.2f}" for x in per)
        print(f"{pol:<14}{rates:<22}{o['hit_rate']:>6.2f}"
              f"{o['same_replica_as_last_turn']:>7.2f}"
              f"{o['ttft_p50_s']:>9.3f}s")
    (M / "routing.json").write_text(json.dumps(out, indent=2) + "\n")


def priority():
    out = {"kind": "simulated (llm-d-inference-sim v0.11.2)"}
    print("simulated: timings are the simulator's configuration")
    print(f"{'run':<22}{'class':<8}{'n':>4}{'TTFT p50':>10}"
          f"{'p95':>8}{'errors':>8}")
    runs = (("no flood", "idle"),
            ("flood, probes 100", "interactive"),
            ("flood, probes -10", "batch"))
    for label, tag in runs:
        reqs = rows(f"priority-{tag}.jsonl")
        out[tag] = {}
        for cls in ("probe", "flood"):
            rs = [r for r in reqs if r["cls"] == cls]
            if not rs:
                continue
            t = [r["ttft"] for r in rs if r["ttft"] is not None]
            err = sum(r["status"] != 200 for r in rs)
            out[tag][cls] = {
                "requests": len(rs), "errors": err,
                "ttft_p50_s": round(statistics.median(t), 3),
                "ttft_p95_s": round(pct(t, 0.95), 3)}
            o = out[tag][cls]
            print(f"{label:<22}{cls:<8}{len(rs):>4}"
                  f"{o['ttft_p50_s']:>9.3f}s{o['ttft_p95_s']:>7.3f}s"
                  f"{err:>8}")
        q = M / f"queue-{tag}.txt"
        if q.exists():
            depth = [int(float(x.split()[-1])) for x in
                     q.read_text().splitlines()
                     if 'priority="-10"' in x]
            out[tag]["peak_batch_queue"] = max(depth, default=0)
    print("peak EPP queue, priority -10: "
          f"{out['interactive'].get('peak_batch_queue', 0)} and "
          f"{out['batch'].get('peak_batch_queue', 0)}")
    (M / "priority.json").write_text(json.dumps(out, indent=2) + "\n")


def lora():
    out = {"kind": "measured (vLLM 0.29.0 CPU, reference laptop)"}
    first = json.loads((M / "lora-max1.json").read_text())
    print("same prompt, temperature 0:")
    for model, text in first["same_prompt"].items():
        print(textwrap.fill(text, 68, initial_indent=f"{model}: ",
                            subsequent_indent="  "))
    print(f"burst: {first['burst_requests']} requests, "
          f"{first['tokens_each']} tokens each; seconds to finish")
    for n in (1, 2):
        run = json.loads((M / f"lora-max{n}.json").read_text())
        out[f"max_loras_{n}"] = run
        spans = "  ".join(f"{m} {lo:.1f}-{hi:.1f}"
                          for m, (lo, hi) in run["done_s"].items())
        print(f"--max-loras {n}: {spans}")
    (M / "lora.json").write_text(json.dumps(out, indent=2) + "\n")


def om():
    series = {}
    for line in sys.stdin:
        t, pol, pod, name, value = line.split()
        key = (name.split("{")[0], pol, pod)
        series.setdefault(key, {})[int(t)] = float(value)
    out = []
    fams = ("vllm:prefix_cache_hits", "vllm:prefix_cache_queries")
    for fam in fams:
        out.append(f"# TYPE {fam} counter")
        for (name, pol, pod), pts in sorted(series.items()):
            if name != fam + "_total":
                continue
            for t in sorted(pts):
                out.append(f'{name}{{policy="{pol}",pod="{pod}",'
                           f'kind="simulated"}} {pts[t]:g} {t}')
    out.append("# EOF")
    (M / "replicas.om").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    {"routing": routing, "priority": priority, "lora": lora,
     "om": om}[sys.argv[1]]()
