# ch16/run.sh
# Two halves on one kind cluster. First, the real vLLM CPU container
# starts from nothing three times, and each start is split into its
# phases: a laptop's CPU cold start, never a GPU's. Then KEDA scales
# a simulated pool on queue depth (vllm:num_requests_waiting) while
# open-loop load steps up and down: simulated, the timings are the
# simulator's configuration.
. /lab/lib/lab.sh
. /lab/lib/kind.sh

PHASES=${PHASES:-1:30,4:120,0.5:90}    # rate:seconds, open loop
RUNS=${RUNS:-3}                        # cold starts
PARTS=${PARTS:-coldstart scaling}      # halves to run
NODE=ch16-control-plane

step "cluster"
kind_tools
start_kind ch16

# The two halves are independent, and each writes its own files:
# PARTS=coldstart re-records the laptop cold start alone, leaving
# the simulated scale-out as it was recorded.
if [[ $PARTS == *coldstart* ]]; then
step "cold start: vLLM CPU container, $RUNS runs (laptop)"
need_models hf >"$WORK/models.txt"
head -n 1 "$WORK/models.txt"
docker exec "$NODE" mkdir -p /models/hf
docker cp /models/hf/SmolLM2-360M-Instruct "$NODE:/models/hf/"
: >"$MEASURED/coldstart.jsonl"
for i in $(seq 1 "$RUNS"); do
  # Forget the image, so the node pulls it again.
  img=$(docker exec "$NODE" crictl images -o json | jq -r \
    '.images[] | select(any(.repoDigests[]?;
       contains("vllm-openai-cpu"))) | .id')
  [ -z "$img" ] || docker exec "$NODE" crictl rmi "$img" >/dev/null
  t_apply=$(date +%s.%N)
  pin_images <coldstart.yaml | kubectl apply -f - >/dev/null
  n=0
  until kubectl get --raw \
      /api/v1/namespaces/default/pods/vllm:8000/proxy/health \
      >/dev/null 2>&1; do
    n=$((n + 1))
    [ "$n" -lt 1800 ] || die "vLLM not up after 15 minutes"
    if [ "$(kubectl get pod vllm -o \
          jsonpath='{.status.containerStatuses[0].restartCount}')" \
         -gt 0 ] 2>/dev/null; then
      kubectl logs vllm --previous | tail -n 20 >&2
      die "the vLLM container crashed"
    fi
    sleep 0.5
  done
  t_up=$(date +%s.%N)
  kubectl wait pod/vllm --for=condition=Ready --timeout=120s \
    >/dev/null
  for _ in $(seq 1 120); do       # the NodePort follows Ready
    curl -sf -o /dev/null "http://$NODE:30081/health" && break
    sleep 0.5
  done
  t1=$(python3 coldstart.py ttft "http://$NODE:30081" "Say hello.")
  t2=$(python3 coldstart.py ttft "http://$NODE:30081" "Name a color.")
  uid=$(kubectl get pod vllm -o jsonpath='{.metadata.uid}')
  kubectl get events --field-selector "involvedObject.uid=$uid" \
    -o json >"$WORK/events-$i.json"
  kubectl logs vllm --timestamps >"$MEASURED/coldstart-$i.log"
  python3 coldstart.py phases "$i" "$t_apply" "$t_up" \
    "$WORK/events-$i.json" "$MEASURED/coldstart-$i.log" "$t1" "$t2" \
    >>"$MEASURED/coldstart.jsonl"
  kubectl delete pod vllm --grace-period=0 --force >/dev/null 2>&1
  kubectl wait pod/vllm --for=delete --timeout=120s >/dev/null 2>&1 \
    || true
done
python3 report.py coldstart "$MEASURED"
fi

if [[ $PARTS == *scaling* ]]; then
step "scale on queue depth (load $PHASES), simulated"
install_keda
for f in prometheus.yaml sim.yaml; do
  pin_images <"$f" | kubectl apply -f - >/dev/null
done
kubectl rollout status deploy/prometheus --timeout=300s >/dev/null
kubectl rollout status deploy/smollm2-sim --timeout=300s >/dev/null
kubectl apply -f scaledobject.yaml >/dev/null
kubectl wait scaledobject/smollm2-sim --for=condition=Ready \
  --timeout=120s >/dev/null
kubectl get pods -A --no-headers | awk '$1 != "kube-system" {
  print $1, $2, $4}'

python3 load.py --url "$NODE:30080" --phases "$PHASES" \
  --out "$MEASURED/requests.jsonl" --timeline "$MEASURED/timeline.csv"
kubectl get events --field-selector \
  involvedObject.name=keda-hpa-smollm2-sim \
  -o custom-columns=TIME:.lastTimestamp,MSG:.message --no-headers \
  >"$MEASURED/hpa-events.txt"
python3 report.py scaling "$MEASURED"
fi

step "done"
kind_manifest
