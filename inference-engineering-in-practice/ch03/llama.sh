# ch03/llama.sh
# Part 1 of the ch03 lab: an SLO report and goodput on llama.cpp.
# Streams requests at a series of offered rates, stamps every chunk
# at the client, and judges each run against slo.toml.
. /lab/lib/lab.sh
RATES=${CH03_RATES:-1 2 3 4 6 8}        # offered requests/s
N=${CH03_N:-40}                          # requests per rate

# Half the CPUs for the server: the load generator stamping chunks
# runs on the same machine and must not wait for a core.
THREADS=$(( ($(nproc) + 1) / 2 ))

step "llama.cpp (build b10964): SmolLM2-135M-Instruct Q8_0, 4 slots"
need_models smoke
start_llama llama -m /models/gguf/SmolLM2-135M-Instruct-Q8_0.gguf \
  --ctx-size 8192 --parallel 4 --threads "$THREADS" --metrics
wait_ready llama http://llama:8080/health

BUILD=$(curl -sf http://llama:8080/props | jq -r .build_info)
rm -rf "$MEASURED/llama"
mkdir -p "$MEASURED/llama"
for r in $RATES; do
  step "llama.cpp: $N requests at $r requests/s (Poisson)"
  python3 load.py http://llama:8080 --rate "$r" --n "$N" \
    > "$MEASURED/llama/rate-$r.jsonl"
  jq -rs '"errors: \(map(select(.error)) | length); last chunk at "
    + "\(map(.text_chunk_times[-1]) | max | . * 10 | round / 10) s"' \
    "$MEASURED/llama/rate-$r.jsonl"
done

FIRST=${RATES%% *}
step "SLO report at $FIRST requests/s"
HEADER="llama.cpp $BUILD, SmolLM2-135M Q8_0, $(date -u +%F)
${AIEL_MACHINE:-this machine}"
python3 report.py "$MEASURED/llama/rate-$FIRST.jsonl" \
  "$MEASURED/report.json" "$HEADER"

step "goodput at the SLO in slo.toml"
python3 goodput.py "$MEASURED"/llama/rate-*.jsonl \
  > "$MEASURED/goodput.json"
jq -r '.curve[] | "rate \(.offered_rate) req/s: attainment "
  + "\(.attainment * 100 | round)%"' "$MEASURED/goodput.json"
jq -r '"goodput: \(.goodput_per_replica) req/s per replica, at TTFT"
  + " <= \(.slo.ttft.target_ms) ms and TPOT <= \(.slo.tpot.target_ms)"
  + " ms for \(.slo.attainment.share * 100 | round)% of requests"' \
  "$MEASURED/goodput.json"
