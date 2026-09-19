# ch04/test.sh
# The invariant is the cache, not the clock: running the same
# command twice (one seed) raises the prefix-hit counter and the
# throughput; a new seed does not hit. CI runs only that part.
. /lab/lib/lab.sh

PARTS=${PARTS:-cache} bash run.sh

step "assertions"
hit() {
  awk -v r="$1" '$1 == r {print ($4 - $2) / ($5 - $3)}' \
    "$MEASURED/cache.tsv"
}
tput() {
  jq '.total_token_throughput * 10 | round / 10' \
    "$MEASURED/cache-$1.json"
}
awk -v f="$(hit first)" 'BEGIN {exit !(f < 0.1)}' \
  || die "the first run already hit the cache: $(hit first)"
echo "ok  first run: hit rate $(hit first)"
awk -v a="$(hit again)" 'BEGIN {exit !(a > 0.8)}' \
  || die "the repeated seed did not hit: $(hit again)"
echo "ok  same seed again: hit rate $(hit again) > 0.8"
awk -v n="$(hit new-seed)" 'BEGIN {exit !(n < 0.1)}' \
  || die "a new seed hit the cache: $(hit new-seed)"
echo "ok  new seed: hit rate $(hit new-seed)"
awk -v a="$(tput again)" -v f="$(tput first)" \
  'BEGIN {exit !(a > f)}' || die "no throughput inflation"
echo "ok  total tok/s inflated: $(tput first) -> $(tput again)"
