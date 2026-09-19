#!/usr/bin/env python3
"""Download the lab models, pinned by Hugging Face commit SHA.

Every file is listed in models.lock.json with its size and SHA-256,
and a download that does not match both is deleted, never used.
Standard library only, so it also runs natively on a Mac for the
`apple` profile (see apple/README.md).

    fetch_models.py fetch [SET_OR_ARTIFACT ...]   # default: smoke
    fetch_models.py list
    fetch_models.py relock [--latest]             # maintainers

Only ungated Apache-2.0 / MIT models are listed, so no token is ever
needed and none is ever sent.
"""
import argparse
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
LOCK = HERE.parent / "models.lock.json"
ENDPOINT = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
CHUNK = 1 << 20


def load_lock():
    with open(LOCK, encoding="utf-8") as f:
        return json.load(f)


def expand(lock, names):
    """Turn set names, artifact names and artifact:file selectors
    into a list of (artifact_name, file_entry) pairs."""
    out, seen = [], set()

    def add(name, stack=()):
        if name in stack:
            sys.exit(f"set {name} includes itself")
        if name in lock["sets"]:
            for member in lock["sets"][name]:
                add(member, stack + (name,))
            return
        art, _, only = name.partition(":")
        if art not in lock["artifacts"]:
            sys.exit(f"unknown set or artifact: {name} "
                     f"(try: fetch_models.py list)")
        for entry in lock["artifacts"][art]["files"]:
            if only and entry["path"] != only:
                continue
            key = (art, entry["path"])
            if key not in seen:
                seen.add(key)
                out.append((art, entry))
        if only and not any(k == (art, only) for k in seen):
            sys.exit(f"{art} has no file {only}")

    for n in names:
        add(n)
    return out


def url_for(artifact, path):
    return (f"{ENDPOINT}/{artifact['repo']}/resolve/"
            f"{artifact['revision']}/{path}")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def download(url, target, size):
    """Stream url to target, resuming a partial .part file."""
    part = target.with_name(target.name + ".part")
    have = part.stat().st_size if part.exists() else 0
    if have > size:
        part.unlink()
        have = 0
    req = urllib.request.Request(url, headers={
        "User-Agent": "the-ai-engineers-library-examples"})
    if have:
        req.add_header("Range", f"bytes={have}-")
    for attempt in range(1, 6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                mode = "ab" if have and r.status == 206 else "wb"
                with open(part, mode) as f:
                    while True:
                        block = r.read(CHUNK)
                        if not block:
                            break
                        f.write(block)
            return part
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == 5:
                raise
            print(f"  retry {attempt}/4 after: {e}", flush=True)
            time.sleep(2 * attempt)
            have = part.stat().st_size if part.exists() else 0
            req.remove_header("Range")
            if have:
                req.add_header("Range", f"bytes={have}-")
    return part


def fetch(args):
    lock = load_lock()
    dest = pathlib.Path(args.dest)
    wanted = expand(lock, args.names or ["smoke"])
    total = sum(e["size"] for _, e in wanted)
    print(f"models: {len(wanted)} file(s), "
          f"{total / 2**20:,.0f} MiB, into {dest}", flush=True)
    failed = 0
    for art_name, entry in wanted:
        art = lock["artifacts"][art_name]
        target = dest / art["dest"] / entry["path"]
        marker = target.with_name(target.name + ".sha256")
        rel = target.relative_to(dest)
        if (target.exists() and target.stat().st_size == entry["size"]
                and marker.exists()
                and marker.read_text().strip() == entry["sha256"]
                and not args.verify):
            print(f"  ok      {rel}", flush=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_size == entry["size"]:
            part = target
        else:
            print(f"  fetch   {rel} "
                  f"({entry['size'] / 2**20:,.1f} MiB)", flush=True)
            part = download(url_for(art, entry["path"]), target,
                            entry["size"])
        got = sha256_of(part)
        if got != entry["sha256"] or part.stat().st_size != entry["size"]:
            print(f"  BAD     {rel}: sha256 {got} != "
                  f"{entry['sha256']}", flush=True)
            part.unlink()
            failed += 1
            continue
        if part != target:
            part.replace(target)
        marker.write_text(entry["sha256"] + "\n")
        print(f"  ok      {rel} (sha256 verified)", flush=True)
    if failed:
        sys.exit(f"{failed} file(s) failed verification")


def list_(args):
    lock = load_lock()
    print("sets:")
    for name in lock["sets"]:
        files = expand(lock, [name])
        mib = sum(e["size"] for _, e in files) / 2**20
        print(f"  {name:<10} {len(files):>2} files {mib:>8,.0f} MiB")
    print("artifacts:")
    for name, art in lock["artifacts"].items():
        mib = sum(e["size"] for e in art["files"]) / 2**20
        print(f"  {name:<22} {art['license']:<11} {mib:>8,.0f} MiB"
              f"  {art['repo']}@{art['revision'][:12]}")


def api(path):
    req = urllib.request.Request(f"{ENDPOINT}/api/{path}", headers={
        "User-Agent": "the-ai-engineers-library-examples"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def relock(args):
    """Refresh sizes and hashes (and, with --latest, revisions)."""
    lock = load_lock()
    for name, art in lock["artifacts"].items():
        info = api(f"models/{art['repo']}")
        if args.latest:
            art["revision"] = info["sha"]
        tree = api(f"models/{art['repo']}/tree/{art['revision']}"
                   "?recursive=true")
        by_path = {t["path"]: t for t in tree if t["type"] == "file"}
        for entry in art["files"]:
            t = by_path.get(entry["path"])
            if t is None:
                sys.exit(f"{art['repo']}@{art['revision']} has no "
                         f"{entry['path']}")
            entry["size"] = t["size"]
            if t.get("lfs"):
                entry["sha256"] = t["lfs"]["oid"]
            else:
                url = url_for(art, entry["path"])
                with urllib.request.urlopen(url, timeout=60) as r:
                    entry["sha256"] = hashlib.sha256(r.read()).hexdigest()
        print(f"  {name}: {art['repo']}@{art['revision'][:12]}")
    with open(LOCK, "w", encoding="utf-8") as f:
        json.dump(lock, f, indent=2)
        f.write("\n")
    print(f"wrote {LOCK}")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download and verify")
    f.add_argument("names", nargs="*",
                   help="sets or artifacts (default: smoke)")
    f.add_argument("--dest", default=os.environ.get("AIEL_MODELS",
                                                    "/models"))
    f.add_argument("--verify", action="store_true",
                   help="re-hash files that are already present")
    f.set_defaults(func=fetch)
    sub.add_parser("list").set_defaults(func=list_)
    r = sub.add_parser("relock", help="refresh models.lock.json")
    r.add_argument("--latest", action="store_true",
                   help="move every revision to the repo's main")
    r.set_defaults(func=relock)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
