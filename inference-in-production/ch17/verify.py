# ch17/verify.py
"""A mini vendor verifier. Replay the fixed request set (cases.py)
against one OpenAI-compatible endpoint and check every answer
against the schema its request carried.

  verify.py ENGINE URL OUT_DIR

A tool call is valid when the answer holds a tool call to one of
the offered tools whose arguments are JSON that pass that tool's
schema. A JSON-schema answer is valid when its content is JSON
that passes the request's schema. Writes OUT_DIR/ENGINE.jsonl
(one line per request) and prints the rates, and for tool calls
how many valid calls named the tool the question was about.
"""
import json
import re
import sys
import urllib.request

from cases import SCHEMAS, TOOLS, cases

TYPES = {"object": dict, "array": list, "string": str,
         "boolean": bool, "integer": int, "number": (int, float)}


def check(v, s, path="$"):
    """The problems with value v under JSON schema s ([] if none).
    Covers the keywords cases.py uses, nothing more."""
    t = s.get("type")
    if t and (not isinstance(v, TYPES[t]) or
              (t in ("integer", "number") and isinstance(v, bool))):
        return [f"{path}: not {t}"]
    if "enum" in s and v not in s["enum"]:
        return [f"{path}: {v!r} not in enum"]
    out = []
    if isinstance(v, dict):
        for k in s.get("required", []):
            if k not in v:
                out.append(f"{path}: missing {k}")
        for k, x in v.items():
            if k in s.get("properties", {}):
                out += check(x, s["properties"][k], f"{path}.{k}")
            elif s.get("additionalProperties") is False:
                out.append(f"{path}: extra key {k}")
    if isinstance(v, list):
        if len(v) < s.get("minItems", 0):
            out.append(f"{path}: fewer than {s['minItems']} items")
        for i, x in enumerate(v):
            out += check(x, s.get("items", {}), f"{path}[{i}]")
    if isinstance(v, str):
        if len(v) < s.get("minLength", 0):
            out.append(f"{path}: too short")
        if "pattern" in s and not re.search(s["pattern"], v):
            out.append(f"{path}: {v!r} does not match")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if v < s.get("minimum", v) or v > s.get("maximum", v):
            out.append(f"{path}: {v} out of range")
    return out


def ask(url, body):
    body = {"model": "smollm2-360m", "temperature": 0,
            "max_tokens": 96, **body}
    req = urllib.request.Request(
        url + "/v1/chat/completions", json.dumps(body).encode(),
        {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["choices"][0]


def judge(case, choice):
    msg = choice["message"]
    if case["kind"] == "json schema":
        try:
            v = json.loads(msg.get("content") or "")
        except ValueError:
            return [f"content is not JSON "
                    f"(finish_reason {choice['finish_reason']})"]
        return check(v, SCHEMAS[case["expect"]])
    calls = msg.get("tool_calls") or []
    if not calls:
        return ["no tool call"]
    out = []
    for c in calls:
        fn = c["function"]
        if fn["name"] not in TOOLS:
            out.append(f"unknown tool {fn['name']!r}")
            continue
        try:
            args = json.loads(fn["arguments"])
        except ValueError:
            out.append("arguments are not JSON")
            continue
        out += check(args, TOOLS[fn["name"]], fn["name"])
    return out


engine, url, out_dir = sys.argv[1:4]
rows = []
with open(f"{out_dir}/{engine}.jsonl", "w") as f:
    for case in cases():
        choice = ask(url, case["body"])
        problems = judge(case, choice)
        names = [c["function"]["name"] for c in
                 choice["message"].get("tool_calls") or []]
        row = {"id": case["id"], "kind": case["kind"],
               "valid": not problems, "problems": problems,
               "right_tool": case["expect"] in names,
               "finish_reason": choice["finish_reason"],
               "message": choice["message"]}
        rows.append(row)
        f.write(json.dumps(row) + "\n")
        f.flush()
for kind in ("tool call", "json schema"):
    got = [r for r in rows if r["kind"] == kind]
    ok = sum(r["valid"] for r in got)
    right = sum(r["valid"] and r["right_tool"] for r in got)
    print(f" {engine:10s} {kind:12s} {len(got):8d} {ok:6d}"
          f" {ok / len(got):6.2f}"
          + (f" {right:11d}" if kind == "tool call" else ""))
