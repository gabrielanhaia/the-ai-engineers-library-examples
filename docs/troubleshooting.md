# Troubleshooting

Real causes, most common first. Entries are added as the labs are written and tested.

## Inference in Production

**`permission denied ... /var/run/docker.sock`.** The lab runner starts each engine as a sibling
container through the Docker socket. On Linux, run Compose as a user in the `docker` group (or with
rootless Docker, point the mount at your socket). Docker Desktop and OrbStack need nothing.

**A lab behaves like an old version after `git pull`.** The runner image is built once and reused.
Rebuild it: `docker compose build inference-in-production`.

**`no ch07/run.sh in this checkout`.** That lab has not landed yet, or you are on an older checkout.
`docker compose run --rm inference-in-production list` shows the labs present.

**`FAIL: vllm not ready after ...` or the vLLM container exits.** vLLM on the CPU needs about 4 GiB
of memory for the SmolLM2-360M labs. On Docker Desktop, raise the VM's memory limit; close other
containers. Only one vLLM engine runs at a time.

**`Warning: numa_migrate_pages failed. errno: 1` in vLLM's log.** Harmless: the container is not
allowed to move memory between NUMA nodes, and a laptop has one node.

**A crashed lab left containers behind** (`Conflict. The container name "/aiel-..." is already in
use`). `docker compose run --rm inference-in-production clean` removes every lab container.

**`models: ... BAD ... sha256`.** A download was corrupted or cut short. The file was deleted; run
the lab again to fetch it again. Behind a proxy or mirror, set `HF_ENDPOINT`.

**Out of disk.** Everything lives in Docker: `docker system df` shows it. The model cache is the
`aiel-models` volume (up to 2.8 GB for the `all` set); `docker volume rm aiel-models` frees it and
the labs download again on demand.
