# ch19/test.sh
# Asserts that each plan is internally consistent, never its
# numbers: the verdict is the cheapest option, an interactive
# fleet still holds its peak with one node down, and a batch fits
# its window.
. /lab/lib/lab.sh

bash run.sh

step "assertions"
jq -e '.numbers | length > 0' "$MEASURED/derived.json" >/dev/null \
  || die "derived.json has no numbers"
echo "ok  derived.json recorded"

python3 - <<'PY' || die "an invariant failed"
import contextlib
import io
import worksheet as ws

for name in ("chat", "batch"):
    p = ws.toml(ws.HERE / f"{name}.toml")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        r = ws.plan(p)
    text = out.getvalue()
    for n in range(1, 9):
        assert f"\n{n} " in "\n" + text, f"section {n} missing"
    options = dict(r["apis"], serve=r["serve"])
    best = min(options, key=options.get)
    assert ("serve:" in text) == (best == "serve")
    assert 0 < r["util"] <= 1
    ex = ws.toml(ws.INPUTS / f"{p['rate']}.toml")
    osl = ex["shape"]["output_tokens"]
    if p.get("batch"):
        busy = p["documents"] * osl / ex["node"]["offline"] / 3600
        assert busy <= p["window_h"] * r["nodes"]
    else:
        day = ws.toml(ws.INPUTS / "traffic.toml")[p["pattern"]]
        peak = p["average_rps"] * day["peak_to_average"] * osl
        assert (r["nodes"] - 1) * ex["node"]["server"] >= peak
    print(f"ok  {name}: eight sections, the cheapest option wins,"
          f" the fleet holds")
PY
