# ch17/test.sh
# The verifier's own gate: each engine's schema-valid rate, per
# kind, must reach the threshold recorded in thresholds.json.
. /lab/lib/lab.sh

bash run.sh

step "assertions"
for e in llama.cpp vllm; do
  n=$(wc -l < "$MEASURED/$e.jsonl")
  [ "$n" -eq 40 ] || die "$e answered $n of 40 requests"
  echo "ok  $e answered all 40 requests"
done
python3 gate.py thresholds.json "$MEASURED" \
  || die "a schema-valid rate fell below its threshold"
echo "ok  every rate at or above thresholds.json"
