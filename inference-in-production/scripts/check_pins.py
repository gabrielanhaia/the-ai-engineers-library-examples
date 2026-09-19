#!/usr/bin/env python3
"""Fail if a pin is used but not recorded in docs/versions.md.

Collects every image digest, Debian package pin, Python == pin and
model revision this book's tree and the compose file use, and checks
each one appears in docs/versions.md. Also refuses an image
reference that has a tag but no digest.
"""
import json
import pathlib
import re
import sys

BOOK = pathlib.Path(__file__).resolve().parent.parent
REPO = BOOK.parent
VERSIONS = (REPO / "docs" / "versions.md").read_text(encoding="utf-8")

DIGEST = re.compile(r"@(sha256:[0-9a-f]{64})")
IMAGE_LINE = re.compile(r"(?:^|\s|=|image:\s*|FROM\s+)"
                        r"([a-z0-9.-]+(?:/[a-z0-9._-]+)+:[\w.-]+)"
                        r"(@sha256:[0-9a-f]{64})?")
APT = re.compile(r"^\s+([a-z0-9.+-]+)=([0-9][\w.+:~-]*)", re.M)
PY = re.compile(r"^([A-Za-z0-9._-]+)==([\w.+-]+)", re.M)

problems, seen = [], 0


def need(token, where):
    global seen
    seen += 1
    if token not in VERSIONS:
        problems.append(f"{where}: {token} is not in docs/versions.md")


files = [REPO / "docker-compose.yml", BOOK / "images.env",
         BOOK / "Dockerfile", REPO / ".github" / "workflows" / "ci.yml"]
for f in files:
    text = f.read_text(encoding="utf-8")
    for m in DIGEST.finditer(text):
        need(m.group(1), f.name)
    for m in IMAGE_LINE.finditer(text):
        ref = m.group(1)
        if ref.startswith("aiel/"):
            continue  # built locally from this repository
        if not m.group(2):
            problems.append(f"{f.name}: {ref} has no @sha256 digest")

dockerfile = (BOOK / "Dockerfile").read_text(encoding="utf-8")
for name, version in APT.findall(dockerfile):
    need(f"{name} {version}", "Dockerfile (apt)")
snap = re.search(r"DEBIAN_SNAPSHOT=(\w+)", dockerfile)
if snap:
    need(snap.group(1), "Dockerfile (snapshot)")

req = (BOOK / "requirements.txt").read_text(encoding="utf-8")
for name, version in PY.findall(req):
    need(f"{name} {version}", "requirements.txt")

lock = json.loads((BOOK / "models.lock.json").read_text("utf-8"))
for name, art in lock["artifacts"].items():
    need(art["revision"], f"models.lock.json ({name})")

for p in problems:
    print("FAIL", p)
print(f"checked {seen} pin(s), {len(problems)} problem(s)")
sys.exit(1 if problems else 0)
