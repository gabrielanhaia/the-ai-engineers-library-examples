#!/usr/bin/env python3
"""Check the files the book prints.

A file the book prints announces itself: its first line (or the line
after a shebang) is a comment holding its own path, e.g.
`# ch01/run.sh`, `// ch14/route.yaml` or `# inputs/prices.toml`.
For every such file:

  1. the path in the comment is the file's real path, and
  2. no line is longer than 70 characters (the print limit).

With --manuscript DIR (the manuscript's chapter directory, which is
not in this repository), it also checks the other direction: every
code block in the book that opens with such a path comment names a
file that exists here and is byte-identical to it.
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIMIT = 70
PATH_COMMENT = re.compile(
    r"^\s*(?:#|//|--|;|<!--)\s*((?:ch\d\d|inputs)/[A-Za-z0-9._/-]+)"
    r"\s*(?:-->)?\s*$")
FENCE = re.compile(r"^(```|~~~)")


def printed_path(lines):
    """The path a file claims in its header comment, or None."""
    for line in lines[:2]:
        if line.startswith("#!"):
            continue
        m = PATH_COMMENT.match(line)
        return m.group(1) if m else None
    return None


def check_repo():
    problems, count = [], 0
    paths = [*ROOT.glob("ch[0-9][0-9]/**/*"), *ROOT.glob("inputs/**/*")]
    for path in sorted(paths):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lines = text.splitlines()
        claimed = printed_path(lines)
        if claimed is None:
            continue
        count += 1
        real = path.relative_to(ROOT).as_posix()
        if claimed != real:
            problems.append(f"{real}: header says {claimed}")
        for n, line in enumerate(lines, 1):
            if len(line) > LIMIT:
                problems.append(
                    f"{real}:{n}: {len(line)} > {LIMIT} characters")
    return count, problems


def code_blocks(md_text):
    block, fence = None, None
    for line in md_text.splitlines(keepends=True):
        m = FENCE.match(line)
        if block is None:
            if m:
                block, fence = [], m.group(1)
        elif line.startswith(fence):
            yield "".join(block)
            block = None
        else:
            block.append(line)


def check_manuscript(chapters_dir):
    problems, count = [], 0
    for md in sorted(pathlib.Path(chapters_dir).glob("*.md")):
        for block in code_blocks(md.read_text(encoding="utf-8")):
            claimed = printed_path(block.splitlines())
            if claimed is None:
                continue
            count += 1
            target = ROOT / claimed
            if not target.is_file():
                problems.append(f"{md.name}: prints {claimed}, "
                                f"which is not in the repo")
            elif target.read_text(encoding="utf-8") != block:
                problems.append(f"{md.name}: {claimed} differs from "
                                f"the repo's file")
    return count, problems


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manuscript",
                   help="the manuscript's chapters directory")
    args = p.parse_args()
    count, problems = check_repo()
    print(f"printed files in the repo: {count}")
    if args.manuscript:
        n, more = check_manuscript(args.manuscript)
        print(f"printed listings in the manuscript: {n}")
        problems += more
    else:
        print("manuscript cross-check: skipped (no --manuscript; "
              "the manuscript is not in this repository)")
    for pr in problems:
        print("FAIL", pr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
