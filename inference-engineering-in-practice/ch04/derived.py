# ch04/derived.py
"""Every number chapter 4 prints, recomputed from measured/ch04/.

This lab's numbers are MEASURED, not arithmetic on cited inputs,
so nothing here re-runs a benchmark: it recomputes the chapter's
numbers from the files the recorded run left in measured/ch04/.
scripts/check_derived.py reruns this and fails on any difference
from measured/ch04/derived.json, which run.sh records.
"""
import sys

from report import derived

if __name__ == "__main__":
    derived(sys.argv[1] if len(sys.argv) > 1
            else "../measured/ch04")
