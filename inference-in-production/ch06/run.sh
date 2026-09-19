# ch06/run.sh
# The break-even calculator: one request shape, three scenarios,
# every input from inputs/example-a.toml. Then every DERIVED number
# of chapter 6 into derived.json.
. /lab/lib/lab.sh

step "break-even, three scenarios"
python3 breakeven.py

step "every DERIVED number in chapter 6"
python3 derived.py > "$MEASURED/derived.json"
echo "$(jq '.numbers | length' "$MEASURED/derived.json") numbers," \
  "recomputed from inputs/: measured/ch06/derived.json"

step "done"
write_manifest
