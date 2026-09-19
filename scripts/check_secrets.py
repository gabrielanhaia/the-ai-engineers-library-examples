#!/usr/bin/env python3
"""Fail if a .env file or anything key-shaped is committed.

Runs in CI on every push. The cost of catching a leaked key late is a
rotated key and a bad afternoon, so this is cheap insurance.
"""
import pathlib
import re
import subprocess
import sys

KEY_SHAPES = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),        # OpenAI-style
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),    # Anthropic-style
    re.compile(r"hf_[A-Za-z0-9]{30,}"),          # Hugging Face
    re.compile(r"AKIA[0-9A-Z]{16}"),             # AWS access key id
    re.compile(r"ghp_[A-Za-z0-9]{36}"),          # GitHub token
]

files = subprocess.run(["git", "ls-files"], capture_output=True,
                       text=True, check=True).stdout.split()
problems = []
for name in files:
    path = pathlib.Path(name)
    if path.name == ".env":
        problems.append(f"{name}: a .env file is committed")
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    for shape in KEY_SHAPES:
        if shape.search(text):
            problems.append(f"{name}: matches {shape.pattern}")

for p in problems:
    print("FAIL", p)
print(f"checked {len(files)} files, {len(problems)} problem(s)")
sys.exit(1 if problems else 0)
