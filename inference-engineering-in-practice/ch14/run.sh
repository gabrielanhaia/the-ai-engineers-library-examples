# ch14/run.sh
# Multi-LoRA on the real vLLM CPU engine first, while the machine
# holds nothing else. Then routing on kind: a Gateway (Istio), an
# InferencePool, llm-d-router's endpoint picker and three simulated
# replicas; round-robin against prefix-aware routing on the same
# multi-turn traffic, and two priority classes under a flood. Every
# simulator number is labeled simulated: its timings are its
# configuration (sim.yaml).
. /lab/lib/lab.sh
. /lab/lib/kind.sh

CONVS=${CONVS:-12}        # conversations per routing policy
FLOOD=${FLOOD:-36}        # concurrent batch requests in the flood
PROBES=${PROBES:-20}      # probes, one a second
PARTS=${PARTS:-lora routing}   # parts to run
GW=ch14-control-plane:30080

# The two parts are independent, and each writes its own files:
# PARTS=lora re-records the real-engine step alone, leaving the
# simulated routing and priority records as they were.
if [[ $PARTS == *lora* ]]; then
step "multi-LoRA on vLLM CPU (real engine, not simulated)"
need_models hf lora >"$WORK/models.txt"
head -n 1 "$WORK/models.txt"
for n in 1 2; do
  start_vllm vllm /models/hf/SmolLM2-360M-Instruct \
    --served-model-name smollm2-360m --max-model-len 2048 \
    --enable-lora --max-loras "$n" --max-lora-rank 16 \
    --lora-modules alpaca=/models/lora/smollm2-360m-alpaca \
                   underdog=/models/lora/smollm2-360m-underdog
  wait_ready vllm http://vllm:8000/health 600
  python3 lora.py --out "$MEASURED/lora-max$n.json"
  stop_server vllm
done
python3 report.py lora "$MEASURED"
fi

if [[ $PARTS == *routing* ]]; then
step "cluster"
kind_tools istioctl
start_kind ch14
apply_pinned GATEWAY_API_CRDS
apply_pinned GAIE_CRDS
apply_pinned ROUTER_CRDS
install_istio
kubectl create configmap smollm2-epp-config \
  --from-file=epp-config.yaml >/dev/null
for f in sim.yaml epp.yaml inferencepool.yaml gateway.yaml \
         objectives.yaml; do
  pin_images <"$f" | kubectl apply -f - >/dev/null
done
kubectl rollout status deploy/smollm2-sim --timeout=300s >/dev/null
kubectl rollout status deploy/smollm2-epp --timeout=300s >/dev/null
kubectl wait gateway/inference-gateway --for=condition=Programmed \
  --timeout=300s >/dev/null
kubectl get pods -o wide --no-headers | awk '{print $1, $2, $3}'

# route_ready  wait until the gateway answers through the route
#   (a GET, so no prompt reaches a replica's cache).
route_ready() {
  for _ in $(seq 1 60); do
    curl -sf -o /dev/null "http://$GW/v1/models" && return 0
    sleep 1
  done
  die "no route through the gateway"
}

epp_metrics() {
  kubectl get --raw "/api/v1/namespaces/default/services/\
smollm2-epp:metrics/proxy/metrics"
}

# picker_ready  wait until the endpoint picker counts three ready
#   endpoints.
picker_ready() {
  for _ in $(seq 1 120); do
    epp_metrics >"$WORK/epp.txt" 2>/dev/null || true
    grep -q '^llm_d_epp_ready_endpoints{.*} 3$' "$WORK/epp.txt" \
      && return 0
    sleep 1
  done
  die "the endpoint picker never saw the new replicas"
}

# fresh_sims  restart the replicas: empty caches, zeroed counters.
#   Returns once the old ones are gone.
fresh_sims() {
  kubectl rollout restart deploy/smollm2-sim >/dev/null
  kubectl rollout status deploy/smollm2-sim --timeout=300s >/dev/null
  for _ in $(seq 1 120); do
    [ "$(kubectl get pods -l app=smollm2-sim --no-headers \
          | wc -l)" -eq 3 ] && return 0
    sleep 1
  done
  die "old replicas never went away"
}

# replicas TAG  each replica's prefix-cache counters, as JSON.
replicas() {
  local p
  for p in $(kubectl get pods -l app=smollm2-sim \
               -o jsonpath='{.items[*].metadata.name}'); do
    pod_metrics default "$p" | awk -v pod="$p" '
      /^vllm:prefix_cache_hits_total/ {h = $2}
      /^vllm:prefix_cache_queries_total/ {q = $2}
      END {printf "{\"pod\":\"%s\",\"hits\":%d,\"queries\":%d}\n",
             pod, h, q}'
  done | jq -s . >"$MEASURED/replicas-$1.json"
}

# sampler TAG  record the replicas' counters every 2 s (for the
#   per-replica hit-rate panel), until killed.
sampler() {
  local p
  while :; do
    for p in $(kubectl get pods -l app=smollm2-sim \
                 -o jsonpath='{.items[*].metadata.name}'); do
      pod_metrics default "$p" 2>/dev/null | awk -v t="$(date +%s)" \
        -v pod="$p" -v pol="$1" \
        '/^vllm:prefix_cache_(hits|queries)_total/ {
           print t, pol, pod, $1, $2}' || true
    done
    sleep 2
  done >>"$WORK/samples.txt"
}

conversations() {
  local tag=$1 s
  sampler "$2" & s=$!
  python3 traffic.py conversations --url "$GW" \
    --conversations "$CONVS" \
    --out "$MEASURED/conversations-$tag.jsonl"
  sleep 2
  kill "$s"
  replicas "$tag"
}

step "round-robin (route-rr.yaml), simulated"
: >"$WORK/samples.txt"
kubectl apply -f route-rr.yaml >/dev/null
fresh_sims
route_ready
conversations rr round-robin

step "prefix-aware (route.yaml), simulated"
kubectl delete -f route-rr.yaml >/dev/null
kubectl apply -f route.yaml >/dev/null
fresh_sims
picker_ready
route_ready
conversations pa prefix-aware
python3 report.py routing "$MEASURED"
python3 report.py om "$MEASURED" <"$WORK/samples.txt"

step "priority classes under a flood, simulated"
# queue TAG  the picker's flow-control queue depth, every second.
queue() {
  while :; do
    epp_metrics 2>/dev/null \
      | grep '^llm_d_epp_flow_control_queue_size' || true
    sleep 1
  done >"$MEASURED/queue-$1.txt"
}
fresh_sims
picker_ready
route_ready
python3 traffic.py priority --url "$GW" --probes 10 \
  --max-tokens 100 --out "$MEASURED/priority-idle.jsonl"
for cls in interactive batch; do
  queue "$cls" & q=$!
  python3 traffic.py priority --url "$GW" --flood "$FLOOD" \
    --probes "$PROBES" --probe-class "$cls" --max-tokens 100 \
    --out "$MEASURED/priority-$cls.jsonl"
  kill "$q"
done
python3 report.py priority "$MEASURED"
fi

step "done"
# A part re-recorded on its own writes its own manifest, so it never
# overwrites the manifest of the part it left alone.
if [ "$PARTS" = lora ]; then
  write_manifest "$MEASURED/machine-lora.json"
else
  kind_manifest
fi
