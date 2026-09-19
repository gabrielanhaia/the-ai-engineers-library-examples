# Helpers for the kind-based labs (ch14, ch16, ch18). Source them
# after lib/lab.sh:
#
#   . /lab/lib/lab.sh
#   . /lab/lib/kind.sh
#
# The runner image carries no kind, kubectl or istioctl. kind_tools
# downloads the pinned binaries (tools.env) once into .work/tools/
# and checks each one's SHA-256. start_kind creates a cluster whose
# node is a sibling container on the host's Docker, joins the node
# to the lab network, and points kubectl at it. Every cluster a lab
# starts is deleted when the lab exits, however it exits (set
# AIEL_KEEP=1 to keep it for poking at).

# shellcheck source=../tools.env
. "${AIEL_TOOLS_FILE:-/lab/tools.env}"

AIEL_TOOLS=${AIEL_TOOLS:-/lab/.work/tools}
_AIEL_KINDS=()

case "$(uname -m)" in
  x86_64 | amd64) _AIEL_ARCH=AMD64 ;;
  aarch64 | arm64) _AIEL_ARCH=ARM64 ;;
  *) die "no pinned tools for $(uname -m)" ;;
esac

# pinned_file NAME  print the local path of the file tools.env pins
#   as NAME (URL@sha256:HEX), downloading and verifying it once.
pinned_file() {
  local spec=${!1:?"$1 is not in tools.env"}
  local url=${spec%@sha256:*} sum=${spec##*@sha256:}
  local out=$AIEL_TOOLS/sha256/$sum
  if [ ! -f "$out" ]; then
    mkdir -p "$AIEL_TOOLS/sha256"
    curl -fsSL --retry 5 -o "$out.part" "$url" \
      || die "download failed: $url"
    echo "$sum  $out.part" | sha256sum -c --quiet - >/dev/null \
      || { rm -f "$out.part"; die "SHA-256 mismatch: $url"; }
    mv "$out.part" "$out"
  fi
  printf '%s\n' "$out"
}

# kind_tools [istioctl]  put kind and kubectl (and istioctl) on PATH.
kind_tools() {
  local bin=$AIEL_TOOLS/bin f
  mkdir -p "$bin"
  f=$(pinned_file "KIND_$_AIEL_ARCH")
  install -m 0755 "$f" "$bin/kind"
  f=$(pinned_file "KUBECTL_$_AIEL_ARCH")
  install -m 0755 "$f" "$bin/kubectl"
  if [ "${1:-}" = istioctl ]; then
    f=$(pinned_file "ISTIOCTL_$_AIEL_ARCH")
    tar -xzf "$f" -C "$bin" istioctl
  fi
  export PATH=$bin:$PATH
  printf 'tools: %s, kubectl %s%s\n' \
    "$(kind version | cut -d' ' -f1-2)" \
    "$(kubectl version --client -o json | jq -r .clientVersion.gitVersion)" \
    "$([ "${1:-}" = istioctl ] \
       && echo ", istioctl $(istioctl version --remote=false \
         | sed "s/.*: //")")"
}

# start_kind NAME [CONFIG]  create a one-node cluster (node container
#   NAME-control-plane, on the lab network as that host name), and
#   export KUBECONFIG for it. NodePorts are then reachable from the
#   lab at http://NAME-control-plane:PORT.
start_kind() {
  local name=$1 cfg=${2:-}
  kind delete cluster --name "$name" >/dev/null 2>&1 || true
  _AIEL_KINDS+=("$name")
  local args=(--name "$name" --image "$KIND_NODE_IMAGE"
              --kubeconfig "$WORK/kubeconfig.host" --wait 300s)
  [ -n "$cfg" ] && args+=(--config "$cfg")
  kind create cluster "${args[@]}" >"$WORK/kind-create.log" 2>&1 \
    || { cat "$WORK/kind-create.log" >&2; die "kind create failed"; }
  docker network connect "$AIEL_NET" "$name-control-plane"
  export KUBECONFIG=$WORK/kubeconfig
  kind get kubeconfig --internal --name "$name" >"$KUBECONFIG"
  kubectl wait --for=condition=Ready node --all --timeout=300s \
    >/dev/null
  printf 'cluster %s: Kubernetes %s, node %s\n' "$name" \
    "$(kubectl version -o json | jq -r .serverVersion.gitVersion)" \
    "$name-control-plane"
}

# stop_kind NAME  delete one cluster before the lab ends.
stop_kind() {
  kind delete cluster --name "$1" >/dev/null 2>&1 || true
}

# apply_pinned NAME  server-side apply a manifest tools.env pins.
apply_pinned() {
  kubectl apply --server-side -f "$(pinned_file "$1")" >/dev/null
}

# install_istio  Istio (minimal profile: istiod only) with the
#   Gateway API Inference Extension switched on. Gateways it creates
#   run the pinned proxy image. Needs `kind_tools istioctl`.
install_istio() {
  istioctl install -y --set profile=minimal \
    --set values.pilot.image="$ISTIO_PILOT_IMAGE" \
    --set values.global.proxy.image="$ISTIO_PROXY_IMAGE" \
    --set values.pilot.resources.requests.cpu=100m \
    --set values.pilot.resources.requests.memory=256Mi \
    --set values.pilot.env.ENABLE_GATEWAY_API_INFERENCE_EXTENSION=true \
    >"$WORK/istioctl.log" 2>&1 \
    || { tail -n 20 "$WORK/istioctl.log" >&2; die "istio install"; }
}

# install_keda  KEDA's release manifest, its three image tags swapped
#   for the pinned digests, then wait until it serves metrics.
install_keda() {
  local f
  f=$(pinned_file KEDA_MANIFEST)
  sed -e "s|image: ghcr.io/kedacore/keda:.*|image: $KEDA_IMAGE|" \
      -e "s|image: ghcr.io/kedacore/keda-metrics-apiserver:.*|image: \
$KEDA_METRICS_IMAGE|" \
      -e "s|image: ghcr.io/kedacore/keda-admission-webhooks:.*|image: \
$KEDA_WEBHOOKS_IMAGE|" "$f" \
    | kubectl apply --server-side -f - >/dev/null
  kubectl -n keda rollout status deploy --timeout=300s >/dev/null
}

# pin_images  copy stdin to stdout, turning every `image: REPO:TAG`
#   that images.env pins into `image: REPO:TAG@sha256:...`. The
#   manifests the book prints name images by tag; the lab runs them
#   by digest.
pin_images() {
  local args=() k v ref
  for k in $(compgen -A variable | grep '_IMAGE$'); do
    v=${!k}
    [[ $v == *@sha256:* ]] || continue
    ref=${v%@*}
    args+=(-e "s|^\\( *image: *\\)${ref//./\\.}\$|\\1$v|")
  done
  sed "${args[@]}"
}

# pod_metrics NS POD [PORT]  a pod's /metrics through the API server.
pod_metrics() {
  kubectl get --raw \
    "/api/v1/namespaces/$1/pods/$2:${3:-8000}/proxy/metrics"
}

# kind_manifest  write_manifest, plus the pinned downloads (tools).
kind_manifest() {
  write_manifest
  jq --arg tools "$(grep -E '^[A-Z0-9_]+=' "${AIEL_TOOLS_FILE:-/lab/tools.env}")" \
    '. + {tools: ($tools | split("\n"))}' "$MEASURED/machine.json" \
    >"$WORK/machine.json.tmp"
  mv "$WORK/machine.json.tmp" "$MEASURED/machine.json"
}

_aiel_kind_exit() {
  local c
  if [ "${AIEL_KEEP:-0}" != 1 ]; then
    for c in "${_AIEL_KINDS[@]}"; do
      kind delete cluster --name "$c" >/dev/null 2>&1 || true
    done
  fi
  _aiel_cleanup || true
}
trap _aiel_kind_exit EXIT
