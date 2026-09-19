# ch11/eval.py
"""A small task eval: fixed questions with checkable answers.

Asks every question in tasks.json of the llama.cpp server at URL,
greedy (temperature 0), and scores the reply: correct when one of
the accepted answers appears in it as a whole word or number.
Prints one JSON object with the score, overall and per kind.

    python3 eval.py URL LABEL > result.json
"""
import json
import re
import sys
import urllib.request


def ask(url, system, question):
    body = {"messages": [{"role": "system", "content": system},
                         {"role": "user", "content": question}],
            "temperature": 0, "max_tokens": 24,
            "cache_prompt": False}
    req = urllib.request.Request(
        url + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def correct(reply, answers):
    for a in answers:
        # Whole words or numbers only: "1969" must not match
        # "19690", and "Au" must not match "August".
        pat = r"(?<![\w.])" + re.escape(a) + r"(?![\w])"
        if re.search(pat, reply, re.IGNORECASE):
            return True
    return False


def main():
    url, label = sys.argv[1], sys.argv[2]
    tasks = json.load(open("tasks.json", encoding="utf-8"))
    rows = []
    for it in tasks["items"]:
        reply = ask(url, tasks["system"], it["q"])
        rows.append({"id": it["id"], "kind": it["kind"],
                     "reply": reply,
                     "correct": correct(reply, it["a"])})

    def score(kinds):
        sel = [r for r in rows if r["kind"] in kinds]
        return {"correct": sum(r["correct"] for r in sel),
                "n": len(sel)}

    print(json.dumps({
        "label": label, "written": tasks["written"],
        "all": score({"date", "number", "fact"}),
        "date_number": score({"date", "number"}),
        "fact": score({"fact"}),
        "items": rows}, indent=1))


if __name__ == "__main__":
    main()
