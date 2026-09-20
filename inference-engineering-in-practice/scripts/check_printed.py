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
    # `{#-` is Jinja's comment opener: without it a printed chat template
    # claims no path and is checked by nothing at all.
    r"^\s*(?:#|//|--|;|<!--|\{#-?)\s*((?:ch\d\d|inputs)/[A-Za-z0-9._/-]+)"
    r"\s*(?:-->|-?#\})?\s*$")
FENCE = re.compile(r"^(```|~~~)")


def printed_path(lines):
    """The path a file claims in its header comment, or None."""
    for line in lines[:2]:
        if line.startswith("#!"):
            continue
        m = PATH_COMMENT.match(line)
        return m.group(1) if m else None
    return None


# The 70-character limit protects the printed page, so it binds the lines the
# book PRINTS. These files reproduce something upstream whose line breaks are
# not ours to change, and the book prints only short excerpts of them. The
# manuscript check enforces both halves of that bargain: every printed line
# obeys the limit, and a file listed here may never be printed whole.
EXCERPT_ONLY = {
    "ch17/template.jinja":
        "SmolLM2's chat template; rewrapping Jinja changes the prompt it "
        "renders",
}


def excerpt_only(rel):
    return rel in EXCERPT_ONLY


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
        if excerpt_only(real):
            continue
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


CUT = re.compile(r"^\s*(?:\{#-?|#|//|--|;|%)?\s*\.\.\.\s*(?:-?#\})?\s*$")


def segments(block_lines):
    """Split a printed block on its cut markers (`# ...` lines).

    The book prints excerpts: the path comment, then the lines a chapter
    discusses, with every omission marked by a cut line. Returns the list of
    segments, and None when the block carries no cut marker at all.
    """
    if not any(CUT.match(ln) for ln in block_lines):
        return None
    out, current = [], []
    for ln in block_lines:
        if CUT.match(ln):
            if current:
                out.append(current)
            current = []
        else:
            current.append(ln)
    if current:
        out.append(current)
    return [seg for seg in out if any(ln.strip() for ln in seg)]


def find_run(file_lines, seg, start):
    """Index of seg as a contiguous run of file_lines at or after start."""
    for i in range(start, len(file_lines) - len(seg) + 1):
        if file_lines[i:i + len(seg)] == seg:
            return i
    return -1


def check_excerpt(file_text, block):
    """Verify a cut-marked excerpt segment by segment.

    Each segment must appear verbatim and contiguously in the repo file, and the
    segments must appear in the order the chapter prints them. Returns a problem
    string, or None when the excerpt is faithful.
    """
    file_lines = file_text.splitlines()
    segs = segments(block.splitlines())
    at = 0
    for n, seg in enumerate(segs, 1):
        i = find_run(file_lines, seg, at)
        if i < 0:
            first = seg[0].strip()[:48]
            return (f"excerpt segment {n} is not in the repo file "
                    f"(starts {first!r})")
        at = i + len(seg)
    return None


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
            else:
                text = target.read_text(encoding="utf-8")
                for n, line in enumerate(block.splitlines(), 1):
                    if len(line) > LIMIT:
                        problems.append(
                            f"{md.name}: {claimed} prints a "
                            f"{len(line)}-character line ({n} of the block), "
                            f"over the {LIMIT}-character print limit")
                if (excerpt_only(claimed)
                        and segments(block.splitlines()) is None):
                    problems.append(
                        f"{md.name}: {claimed} is excerpt-only "
                        f"({EXCERPT_ONLY[claimed]}) but is printed with no "
                        f"cut marker, so it claims to be the whole file")
                if segments(block.splitlines()) is not None:
                    bad = check_excerpt(text, block)
                    if bad:
                        problems.append(f"{md.name}: {claimed} {bad}")
                elif text != block:
                    # No cut marker, so the block claims to be the whole file.
                    # A chapter that quietly stops early reads as complete.
                    problems.append(f"{md.name}: {claimed} differs from "
                                    f"the repo's file (and carries no `# ...` "
                                    f"cut marker, so it claims to be whole)")
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
