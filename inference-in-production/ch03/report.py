# ch03/report.py
"""The SLO report for one run: TTFT at both measurement points,
TPOT and ITL, at the mean and at p50, p90 and p99, in ms.

    python3 report.py RUN.jsonl OUT.json HEADER

Prints the table and writes the numbers behind it to OUT.json.

Server-side TTFT is llama.cpp's own timings.prompt_ms: the slot's
prompt work, from the moment a slot picks the request up.
"""
import json
import sys

from metrics import pct, per_request, summarize


def main():
    path, out_path, header = sys.argv[1:4]
    recs = [json.loads(line) for line in open(path)]
    ok = [r for r in recs if not r["error"]]
    s = summarize(ok)
    server = [r["timings"]["prompt_ms"] / 1000 for r in ok]
    s["server_ttft"] = {"n": len(server),
                        "mean": sum(server) / len(server),
                        **{f"p{p}": pct(server, p)
                           for p in (50, 90, 99)}}
    client = [per_request(r)["ttft"] for r in ok]
    gaps = [c - v for c, v in zip(client, server)]
    one_per_chunk = sum(
        len(r["text_chunk_times"])
        == (r["output_tokens"] or r["timings"]["predicted_n"])
        for r in ok)
    out = {"file": path, "requests": len(recs), "errors":
           len(recs) - len(ok), "summary": s,
           "client_minus_server_ttft": {
               "min": min(gaps), "p50": pct(gaps, 50)},
           "requests_one_token_per_chunk": one_per_chunk}
    with open(out_path, "w") as f:
        json.dump(out, f, indent=1)

    rows = [("TTFT, client", "ttft"), ("TTFT, server", "server_ttft"),
            ("TPOT", "tpot"), ("ITL (pooled)", "itl")]
    lines = [header,
             f"{'ms':<14}{'n':>6}{'mean':>9}{'p50':>9}"
             f"{'p90':>9}{'p99':>9}"]
    for label, key in rows:
        m = s[key]
        lines.append(f"{label:<14}{m['n']:>6}" + "".join(
            f"{m[k] * 1000:>9.1f}"
            for k in ("mean", "p50", "p90", "p99")))
    lines += [
        f"client - server TTFT: p50 {pct(gaps, 50) * 1000:.1f} ms,"
        f" min {min(gaps) * 1000:.1f} ms",
        f"requests with one token per chunk: {one_per_chunk}"
        f" of {len(ok)}"]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
