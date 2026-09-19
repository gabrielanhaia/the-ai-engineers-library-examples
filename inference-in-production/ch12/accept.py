# ch12/accept.py
"""Acceptance from two scrapes of llama.cpp's /metrics.

    python3 accept.py BEFORE AFTER

Counters only go up, so what one setting did is AFTER minus BEFORE.
The names are as scraped at build b10964, _total suffix included.
"""
import json
import sys

PREFIX = "llamacpp:spec_decode_num_"
NAMES = {"drafted": "draft_tokens_total",     # tokens proposed
         "accepted": "accepted_tokens_total", # tokens kept
         "drafts": "drafts_total"}            # verification steps


def counters(path):
    out = {}
    for line in open(path):
        name, _, value = line.partition(" ")
        if name.startswith(PREFIX):
            out[name[len(PREFIX):]] = float(value)
    return out


def main():
    a, b = counters(sys.argv[1]), counters(sys.argv[2])
    d = {k: b[n] - a[n] for k, n in NAMES.items()}
    print(json.dumps({
        **d,
        # share of proposed tokens the target model kept
        "acceptance": d["accepted"] / d["drafted"],
        # tokens emitted per target pass: the accepted ones, plus
        # the one the target always adds itself
        "tokens_per_step": 1 + d["accepted"] / d["drafts"]}))


if __name__ == "__main__":
    main()
