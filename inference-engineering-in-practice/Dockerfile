# The lab runner: the container behind
#   docker compose run --rm inference-engineering-in-practice chNN
# It holds the lab scripts' tools (bash, python, curl, jq, the docker
# CLI) but no inference engine. Each lab starts the engine it needs
# (llama.cpp, vLLM CPU, GuideLLM) as a sibling container from the
# pinned images in images.env, through the mounted Docker socket.
#
# Every input is pinned: both base images by digest, the Debian
# packages by version from a dated snapshot.debian.org archive, and
# Python packages by == with hashes in requirements.txt.

FROM docker:29.8.1-cli@sha256:018edbc908e08fcc9dbf029c812c34251e9b4719e6f71ca0e5eae2a987d014ca AS docker-cli

FROM python:3.13.15-slim-trixie@sha256:8d9d0b8bcf6506481eae4907c18f5e3e7902e629f5f6d684f9e7c32e85e3ddf0

ARG DEBIAN_SNAPSHOT=20260918T000000Z
RUN set -eux; \
    rm -f /etc/apt/sources.list.d/debian.sources; \
    for s in "debian trixie" "debian trixie-updates" \
             "debian-security trixie-security"; do \
      set -- $s; \
      echo "deb [check-valid-until=no]" \
        "http://snapshot.debian.org/archive/$1/$DEBIAN_SNAPSHOT" \
        "$2 main"; \
    done > /etc/apt/sources.list; \
    apt-get -o Acquire::Retries=5 update; \
    apt-get install -y --no-install-recommends \
      curl=8.14.1-2+deb13u5 \
      jq=1.7.1-6+deb13u3; \
    rm -rf /var/lib/apt/lists/*

COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --root-user-action=ignore --require-hashes \
      -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

ENV AIEL_MODELS=/models \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /lab
ENTRYPOINT ["bash", "/lab/bin/lab"]
CMD ["help"]
