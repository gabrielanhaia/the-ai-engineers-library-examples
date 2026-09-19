# ch02/bandwidth.py
"""A STREAM-style copy test, standard library only.

One process per CPU copies its own share of two large arrays, all
at the same moment. As in STREAM's Copy kernel, a copied byte counts
twice (read once, written once), and the best trial is reported.
Prints one JSON object: the copy bandwidth in GB (1e9 bytes)/s.
"""
import json
import multiprocessing as mp
import os
import time

MIB = 1 << 20


def worker(n_bytes, trials, reps, barrier, out):
    src = bytearray(b"\x5a") * n_bytes      # touches every page
    dst = bytearray(n_bytes)
    s, d = memoryview(src), memoryview(dst)
    d[:] = s                                 # fault dst in, warm up
    for trial in range(trials):
        barrier.wait()
        t0 = time.perf_counter()
        for _ in range(reps):
            d[:] = s
        out.put((trial, t0, time.perf_counter()))


def main():
    procs = int(os.environ.get("BW_PROCS", os.cpu_count()))
    mib = int(os.environ.get("BW_ARRAY_MIB", 512))  # per array
    trials = int(os.environ.get("BW_TRIALS", 10))
    reps = 4
    share = mib * MIB // procs
    ctx = mp.get_context("fork")
    barrier, out = ctx.Barrier(procs), ctx.Queue()
    ps = [ctx.Process(target=worker,
                      args=(share, trials, reps, barrier, out))
          for _ in range(procs)]
    for p in ps:
        p.start()
    spans = {}
    for _ in range(procs * trials):
        trial, t0, t1 = out.get()
        a, b = spans.get(trial, (t0, t1))
        spans[trial] = (min(a, t0), max(b, t1))
    for p in ps:
        p.join()
    moved = 2 * share * procs * reps         # read + write
    rates = sorted(moved / (b - a) / 1e9 for a, b in spans.values())
    print(json.dumps({
        "copy_gb_s": round(rates[-1], 1),
        "median_gb_s": round(rates[len(rates) // 2], 1),
        "processes": procs, "array_mib": mib,
        "trials": trials, "counted": "2 bytes per byte copied"}))


if __name__ == "__main__":
    main()
