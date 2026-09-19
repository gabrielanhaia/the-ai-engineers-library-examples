# ch18/test.sh
# Runs the lab, then asserts that each gate passes the candidate
# that changes nothing and fails the one with the injected
# regression, and that the route and the rules validate.
. /lab/lib/lab.sh

bash run.sh

step "assertions"
g=$MEASURED/gates.json
jq -e '.quality.rerun == "pass"' "$g" >/dev/null \
  || die "the quality gate failed an unchanged stack"
echo "ok  quality gate passes an unchanged stack"

jq -e '.quality["broken-template"] == "fail"' "$g" >/dev/null \
  || die "the quality gate passed a broken chat template"
echo "ok  quality gate fails the broken chat template"

jq -e '.performance.rerun == "pass"' "$g" >/dev/null \
  || die "the performance gate failed an unchanged stack"
echo "ok  performance gate passes an unchanged stack (simulated)"

jq -e '.performance["slower-config"] == "fail"' "$g" >/dev/null \
  || die "the performance gate passed a slower configuration"
echo "ok  performance gate fails the slower config (simulated)"

jq -e '.manifests == "valid" and .alert_rules == "pass"' "$g" \
  >/dev/null || die "a manifest or an alert rule did not validate"
echo "ok  canary route validates; alert rules pass promtool"
