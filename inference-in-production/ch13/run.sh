# ch13/run.sh
# The layout calculator: KV copies under TP, the KV a TP=2 layout
# frees, and a P:D ratio, all DERIVED from inputs/. Then every
# DERIVED number of chapter 13 into derived.json. No GPU is used.
. /lab/lib/lab.sh

step "three layout formulas"
python3 layout.py

step "every DERIVED number in chapter 13"
python3 derived.py > "$MEASURED/derived.json"
echo "$(jq '.numbers | length' "$MEASURED/derived.json") numbers," \
  "recomputed from inputs/: measured/ch13/derived.json"

step "done"
write_manifest
