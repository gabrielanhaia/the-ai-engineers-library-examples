# Shared helpers for chNN/run.sh and chNN/test.sh. Source it first:
#
#   . /lab/lib/lab.sh
#
# The runner has no inference engine. start_llama and start_vllm
# start one as a sibling container on the lab network, reachable
# from the lab at http://NAME:PORT. Every container a lab starts is
# removed when the lab exits, however it exits (set AIEL_KEEP=1 to
# keep them for poking at).

set -euo pipefail

# MEASURED  what the lab records: measured/chNN/, committed. The book
#           copies every MEASURED number and output block from here.
# WORK      scratch the lab may throw away: .work/chNN/, git-ignored.
# An ad-hoc run (LAB not chNN) records into WORK, never measured/.
: "${LAB:=adhoc}"
: "${WORK:=/lab/.work/$LAB}"
if [[ $LAB =~ ^ch[0-9][0-9]$ ]]; then
  : "${MEASURED:=/lab/measured/$LAB}"
else
  : "${MEASURED:=$WORK}"
fi
mkdir -p "$MEASURED" "$WORK"

# shellcheck source=../images.env
. "${AIEL_IMAGES_FILE:-/lab/images.env}"

AIEL_NET=${AIEL_NET:-aiel-inference}
AIEL_MODELS_VOLUME=${AIEL_MODELS_VOLUME:-aiel-models}
AIEL_SCRATCH_VOLUME=${AIEL_SCRATCH_VOLUME:-aiel-scratch}
_AIEL_STARTED=()

step() { printf '\n== %s\n' "$*"; }
die() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

# need_models SET_OR_ARTIFACT...  download (once) and verify.
need_models() {
  python3 /lab/scripts/fetch_models.py fetch "$@"
}

_cname() { printf 'aiel-%s-%s' "$LAB" "$1"; }

# _start NAME IMAGE [docker-run options...] -- [container args...]
_start() {
  local name=$1 image=$2 c
  shift 2
  local opts=()
  while [ $# -gt 0 ] && [ "$1" != -- ]; do opts+=("$1"); shift; done
  [ "${1:-}" = -- ] && shift
  c=$(_cname "$name")
  docker rm -f "$c" >/dev/null 2>&1 || true
  docker run -d --name "$c" \
    --label aiel.lab="$LAB" \
    --network "$AIEL_NET" --network-alias "$name" \
    -v "$AIEL_MODELS_VOLUME:/models:ro" \
    -v "$AIEL_SCRATCH_VOLUME:/scratch" \
    "${opts[@]}" "$image" "$@" >/dev/null
  _AIEL_STARTED+=("$c")
}

# start_llama NAME [llama-server flags...]
#   Serves on http://NAME:8080. The image's entrypoint is
#   llama-server, so pass only its flags.
start_llama() {
  local name=$1
  shift
  _start "$name" "$LLAMA_CPP_IMAGE" -- --port 8080 "$@"
}

# start_vllm NAME MODEL [vllm serve flags...]
#   Serves on http://NAME:8000. The KV cache size comes from
#   VLLM_CPU_KVCACHE_SPACE (GiB, default 1 here). The image's
#   entrypoint is `vllm serve`, so pass the model and its flags.
start_vllm() {
  local name=$1
  shift
  _start "$name" "$VLLM_CPU_IMAGE" \
    --shm-size 1g \
    -e VLLM_CPU_KVCACHE_SPACE="${VLLM_CPU_KVCACHE_SPACE:-1}" \
    -- "$@" --port 8000
}

# run_tool IMAGE [args...]
# run_tool IMAGE [docker-run options...] -- [args...]
#   A one-shot container on the lab network (GuideLLM, `vllm bench`,
#   `llama bench`...). Its stdout is yours. Options such as
#   --entrypoint go before a literal --.
run_tool() {
  local image=$1
  shift
  local opts=() a
  for a in "$@"; do
    if [ "$a" = -- ]; then
      while [ "$1" != -- ]; do opts+=("$1"); shift; done
      shift
      break
    fi
  done
  docker run --rm --network "$AIEL_NET" \
    --label aiel.lab="$LAB" \
    -v "$AIEL_MODELS_VOLUME:/models:ro" \
    -v "$AIEL_SCRATCH_VOLUME:/scratch" \
    "${opts[@]}" "$image" "$@"
}

# wait_ready NAME URL [TIMEOUT_SECONDS]  poll until URL answers 200.
wait_ready() {
  local name=$1 url=$2 timeout=${3:-180} c t=0
  c=$(_cname "$name")
  until curl -sf -o /dev/null "$url"; do
    if [ "$(docker inspect -f '{{.State.Running}}' "$c" \
            2>/dev/null)" != true ]; then
      docker logs --tail 40 "$c" >&2 || true
      die "$name exited before it was ready"
    fi
    t=$((t + 1))
    if [ "$t" -ge "$timeout" ]; then
      docker logs --tail 40 "$c" >&2 || true
      die "$name not ready after ${timeout}s"
    fi
    sleep 1
  done
  printf '%s ready after ~%ss\n' "$name" "$t"
}

# server_logs NAME [docker logs options]
server_logs() {
  local name=$1
  shift
  docker logs "$@" "$(_cname "$name")" 2>&1
}

# stop_server NAME  remove one server before the lab ends.
stop_server() {
  docker rm -f "$(_cname "$1")" >/dev/null 2>&1 || true
}

# write_manifest [FILE]  record what this run ran on, next to its
#   results (default $MEASURED/machine.json). The container cannot
#   see the host's CPU model: set AIEL_MACHINE to describe it, e.g.
#   AIEL_MACHINE="Apple M2 Pro, 16 GB, OrbStack".
write_manifest() {
  local out=${1:-$MEASURED/machine.json}
  docker info --format '{{json .}}' | jq \
    --arg machine "${AIEL_MACHINE:-unspecified}" \
    --arg date "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg lab "$LAB" \
    --arg images "$(grep -E '^[A-Z_]+_IMAGE=' \
                     "${AIEL_IMAGES_FILE:-/lab/images.env}")" \
    --slurpfile models /lab/models.lock.json \
    '{lab: $lab, date: $date, machine: $machine,
      docker: {server: .ServerVersion, os: .OperatingSystem,
               arch: .Architecture, cpus: .NCPU,
               memory_bytes: .MemTotal},
      images: ($images | split("\n")),
      models: ($models[0].artifacts
               | map_values(.repo + "@" + .revision))}' > "$out"
  echo "manifest: ${out#/lab/}"
}

_aiel_cleanup() {
  local rc=$?
  if [ "${AIEL_KEEP:-0}" != 1 ] && [ ${#_AIEL_STARTED[@]} -gt 0 ]; then
    docker rm -f "${_AIEL_STARTED[@]}" >/dev/null 2>&1 || true
  fi
  return $rc
}
trap _aiel_cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
