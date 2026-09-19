# ch19/run.sh
# The decision worksheet. No arguments: chapter 19's two worked
# plans (ch19/chat.toml, ch19/batch.toml). With arguments, your own
# plan files: copies of those two with your numbers in them.
. /lab/lib/lab.sh

if [ $# -gt 0 ]; then
  python3 worksheet.py "$@"
  exit
fi

step "two worked plans"
python3 worksheet.py

step "the plans' numbers"
python3 derived.py > "$MEASURED/derived.json"
echo "$(jq '.numbers | length' "$MEASURED/derived.json") numbers," \
  "recomputed from inputs/: measured/ch19/derived.json"

step "done"
write_manifest
