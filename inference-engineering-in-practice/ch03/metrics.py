# ch03/metrics.py
"""TTFT, TPOT and ITL from the client's chunk timestamps.

A record is one streamed request as load.py saved it: when it was
sent, and when each chunk carrying text arrived (seconds).
"""


def per_request(rec):
    t, sent = rec["text_chunk_times"], rec["sent"]
    n = rec["output_tokens"] or rec["timings"]["predicted_n"]
    ttft = t[0] - sent                  # client-side TTFT
    e2e = t[-1] - sent
    # TPOT: the time after the first token, shared by the rest.
    tpot = (e2e - ttft) / (n - 1) if n > 1 else None
    # ITL: every gap between consecutive chunks of this request.
    itl = [b - a for a, b in zip(t, t[1:])]
    return {"ttft": ttft, "tpot": tpot, "e2e": e2e, "itl": itl}


def pct(xs, p):
    """The p-th percentile, interpolating between ranks."""
    xs = sorted(xs)
    k = (len(xs) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summarize(records):
    rs = [per_request(r) for r in records]
    samples = {
        # one TTFT and one TPOT per request...
        "ttft": [r["ttft"] for r in rs],
        "tpot": [r["tpot"] for r in rs if r["tpot"] is not None],
        # ...but ITL pools every gap of every request.
        "itl": [g for r in rs for g in r["itl"]],
    }
    return {name: {"n": len(xs), "mean": sum(xs) / len(xs),
                   **{f"p{p}": pct(xs, p) for p in (50, 90, 99)}}
            for name, xs in samples.items()}
