# ch05/run.sh
# The cost calculator. No arguments: worked example A from MLPerf's
# row and a dated price, one example of a different request shape,
# and every DERIVED number of chapter 5 into derived.json. With
# arguments, it prices your own request shape, for example:
#   ch05 --input 2000 --output 500 --utilization 0.4
. /lab/lib/lab.sh

if [ $# -gt 0 ]; then
  python3 cost.py "$@"
  exit
fi

step "worked example A"
python3 cost.py

step "another shape: 20,000 in / 500 out at 41.2% utilization"
python3 cost.py --input 20000 --output 500 --utilization 0.412 \
  | tee "$MEASURED/other-shape.txt"

step "every DERIVED number in chapter 5"
python3 derived.py > "$MEASURED/derived.json"
echo "$(jq '.numbers | length' "$MEASURED/derived.json") numbers," \
  "recomputed from inputs/: measured/ch05/derived.json"

step "done"
write_manifest
