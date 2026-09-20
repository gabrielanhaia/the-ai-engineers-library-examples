#!/usr/bin/env bash
# screens/shoot.sh [SHOT...] -- make the book's replayed screenshots.
#
# For every `grafana` shot in screens/shots.json it brings the replay
# stack up on that shot's committed data (screens/replay.sh) at that
# lab's own scrape interval, then captures the panels
# (screens/capture.py). With no argument it does all of them.
#
#   bash screens/shoot.sh              # every replayed shot
#   bash screens/shoot.sh S1 S2        # just these
#
# The live shots (S10, S11) and the simulator-driven one (S12) have
# their own scripts, because each needs a server running first.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
PY=${PY:-$ROOT/.work/screens/venv/bin/python}
OUT=${OUT:-$HOME/WebstormProjects/book-inference-engineering/en/content/chapters/images}

PLAN=$ROOT/.work/screens/plan.tsv
mkdir -p "$(dirname "$PLAN")"
"$PY" - "$@" > "$PLAN" <<'EOF'
import json, sys, pathlib
shots = json.loads(pathlib.Path("screens/shots.json").read_text())
want = sys.argv[1:]
for s in shots:
    if s["kind"] != "grafana":
        continue
    if want and s["id"] not in want and s["id"].split("-")[0] not in want:
        continue
    print("|".join([s["id"], s["replay"], s.get("scrapeInterval", "5s"),
                    s.get("promArgs", ""), " ".join(s["data"])]))
EOF
[ -s "$PLAN" ] || { echo "nothing to do" >&2; exit 1; }

while IFS='|' read -r id replay scrape promargs files; do
  [ -n "$id" ] || continue
  echo "== $id  (replay $replay, scrape $scrape)"
  # shellcheck disable=SC2086
  SCRAPE=$scrape EXTRA_PROM_ARGS=$promargs \
    bash screens/replay.sh "$replay" $files >/dev/null
  "$PY" screens/capture.py "$id" --out "$OUT"
done < "$PLAN"

bash screens/replay.sh --down >/dev/null
