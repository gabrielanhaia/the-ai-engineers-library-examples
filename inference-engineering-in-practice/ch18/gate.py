# ch18/gate.py
"""Release gates: compare a candidate serving stack with the current
one (the baseline) and exit non-zero when it must not ship.

  quality BASE CAND      ch11's task eval, run against each (JSON).
      Fails when the candidate answers more than MAX_LOST fewer
      items correctly, or when fewer than MIN_SAME of its replies
      are the baseline's: at temperature 0 on the same weights, a
      changed reply is a changed output, whatever the score says.
  performance BASE CAND  `vllm bench serve` results at one fixed
      input and output length (JSON). Fails when the candidate's
      goodput is below MIN_GOODPUT of the baseline's.
"""
import json
import sys

MAX_LOST = 2        # correct answers the candidate may lose
MIN_SAME = 0.90     # share of replies that must not change
MIN_GOODPUT = 0.90  # candidate goodput / baseline goodput


def quality(base, cand):
    lost = base["all"]["correct"] - cand["all"]["correct"]
    was = {it["id"]: it["reply"] for it in base["items"]}
    same = sum(was.get(it["id"]) == it["reply"]
               for it in cand["items"]) / len(cand["items"])
    n = cand["all"]["n"]
    return [
        (f"correct: {cand['all']['correct']}/{n} "
         f"(baseline {base['all']['correct']}/{n})",
         lost <= MAX_LOST),
        (f"replies unchanged: {same:.0%} (need {MIN_SAME:.0%})",
         same >= MIN_SAME)]


def performance(base, cand):
    gb, gc = base["request_goodput"], cand["request_goodput"]
    return [
        (f"goodput: {gc:.2f} req/s, baseline {gb:.2f} "
         f"({gc / gb:.0%}, need {MIN_GOODPUT:.0%})",
         gc >= MIN_GOODPUT * gb),
        (f"median TPOT: {cand['median_tpot_ms']:.1f} ms, "
         f"baseline {base['median_tpot_ms']:.1f} ms", True)]


def main():
    kind, base, cand = sys.argv[1:4]
    checks = {"quality": quality, "performance": performance}[kind](
        json.load(open(base)), json.load(open(cand)))
    for text, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {text}")
    passed = all(ok for _, ok in checks)
    verdict = "PASS" if passed else "FAIL, do not ship"
    print(f"  {kind} gate: {verdict}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
