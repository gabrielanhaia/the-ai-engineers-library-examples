# ch02/test.sh
# Asserts invariants, never numbers: a bandwidth was measured, each
# format has a prediction and a measurement, and both quantized
# files decode faster than F16. (Q4_K_M against Q8_0 is not asserted:
# on a small model their gap is narrow, and a busy machine flips it.)
. /lab/lib/lab.sh

bash run.sh

step "assertions"
jq -e '.copy_gb_s > 0' "$MEASURED/bandwidth.json" >/dev/null \
  || die "no bandwidth measured"
echo "ok  copy bandwidth measured"

jq -e 'length == 3 and all(.[]; .predicted_tok_s > 0
       and .measured_tok_s > 0
       and (.format as $f | .file | endswith("-" + $f + ".gguf")))' \
  "$MEASURED/results.json" >/dev/null \
  || die "results.json lacks a prediction or measurement per format"
echo "ok  one prediction and one measurement per format"

jq -e 'map(.bytes) | .[0] > .[1] and .[1] > .[2]' \
  "$MEASURED/results.json" >/dev/null \
  || die "file sizes are not F16 > Q8_0 > Q4_K_M"
echo "ok  bytes: F16 > Q8_0 > Q4_K_M"

jq -e 'map(.measured_tok_s) | .[1] > .[0] and .[2] > .[0]' \
  "$MEASURED/results.json" >/dev/null \
  || die "a quantized file did not decode faster than F16"
echo "ok  measured tok/s: Q8_0 > F16 and Q4_K_M > F16"
