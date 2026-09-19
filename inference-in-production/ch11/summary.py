# ch11/summary.py
"""Collect the ch11 results into one table and results.json.

Reads, from the directory given: ppl-f16.log, kld-Q8_0.log and
kld-Q4_K_M.log (llama perplexity), eval-*.json (eval.py), bench.json
(llama bench) and sizes.json (the GGUF file sizes in bytes).
"""
import json
import pathlib
import re
import sys

FORMATS = ["f16", "Q8_0", "Q4_K_M"]
NUM = r"(-?[\d.]+)"


def grab(text, label):
    m = re.search(re.escape(label) + r"\s*:\s*" + NUM, text)
    if not m:
        sys.exit(f"summary: no '{label}' in the perplexity log")
    return float(m.group(1))


def main():
    d = pathlib.Path(sys.argv[1])
    sizes = json.loads((d / "sizes.json").read_text())
    bench = {}
    for b in json.loads((d / "bench.json").read_text()):
        # fastest thread count per file, by the median of its runs
        f = pathlib.Path(b["model_filename"]).stem.rsplit("-", 1)[1]
        runs = sorted(b["samples_ts"])
        b["median_ts"] = runs[len(runs) // 2]
        if f not in bench or b["median_ts"] > bench[f]["median_ts"]:
            bench[f] = b
    rows = {}
    for f in FORMATS:
        r = rows[f] = {"format": f, "bytes": sizes[f]}
        b = bench[f]
        r["params"] = b["model_n_params"]
        r["bits_per_weight"] = sizes[f] * 8 / b["model_n_params"]
        r["tok_s"] = b["median_ts"]
        r["threads"] = b["n_threads"]
        r["runs_tok_s"] = b["samples_ts"]
        ev = json.loads((d / f"eval-{f}.json").read_text())
        r["eval"] = ev["all"]
        r["eval_date_number"] = ev["date_number"]
        if f == "f16":
            log = (d / "ppl-f16.log").read_text()
            m = re.search(r"Final estimate: PPL = " + NUM
                          + r" \+/- " + NUM, log)
            r["ppl"], r["ppl_err"] = float(m[1]), float(m[2])
            continue
        log = (d / f"kld-{f}.log").read_text()
        r["ppl"] = grab(log, "Mean PPL(Q)")
        r["ppl_base_from_logits"] = grab(log, "Mean PPL(base)")
        r["mean_ln_ratio"] = grab(log, "Mean ln(PPL(Q)/PPL(base))")
        r["mean_kld"] = grab(log, "Mean    KLD")
        r["same_top_p_pct"] = grab(log, "Same top p")
        r["dp_99_pct"] = grab(log, "99.0%   Δp")
        r["dp_1_pct"] = grab(log, " 1.0%   Δp")
    out = [rows[f] for f in FORMATS]
    (d / "results.json").write_text(json.dumps(out, indent=1) + "\n")

    print(f"{'format':<7}{'bits/w':>7}{'PPL':>8}{'KLD':>8}"
          f"{'top %':>7}{'eval':>7}{'d/n':>7}{'tok/s':>7}")
    for r in out:
        kld = f"{r['mean_kld']:.4f}" if "mean_kld" in r else "-"
        top = f"{r['same_top_p_pct']:.1f}" if "mean_kld" in r else "-"
        ev, dn = r["eval"], r["eval_date_number"]
        print(f"{r['format']:<7}{r['bits_per_weight']:>7.2f}"
              f"{r['ppl']:>8.3f}{kld:>8}{top:>7}"
              f"{ev['correct']:>4}/{ev['n']:<2}"
              f"{dn['correct']:>4}/{dn['n']:<2}{r['tok_s']:>7.1f}")
    f16, q4 = rows["f16"], rows["Q4_K_M"]
    print(f"bits/w = file bytes x 8 / {f16['params']:,} parameters")
    size = f16["bytes"] / q4["bytes"]
    speed = q4["tok_s"] / f16["tok_s"]
    print(f"Q4_K_M vs F16: {size:.2f}x fewer bytes, "
          f"{speed:.2f}x the decode speed")


if __name__ == "__main__":
    main()
