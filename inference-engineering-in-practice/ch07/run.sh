# ch07/run.sh
# The capacity calculator. No arguments: chapter 7's fit table and
# its two worked examples (ch07/examples.toml), then every DERIVED
# number of the chapter into derived.json. With an argument, your
# own forecast: a copy of examples.toml with your numbers in it.
. /lab/lib/lab.sh

if [ $# -gt 0 ]; then
  python3 capacity.py "$@"
  exit
fi

step "fit, and the two worked examples"
python3 capacity.py

step "every DERIVED number in chapter 7"
python3 derived.py > "$MEASURED/derived.json"
echo "$(jq '.numbers | length' "$MEASURED/derived.json") numbers," \
  "recomputed from inputs/: measured/ch07/derived.json"

step "done"
write_manifest
