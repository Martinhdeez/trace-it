#!/usr/bin/env bash
set -euo pipefail

revision=${1:?usage: build-images.sh REVISION}
attempts=${BUILD_RETRY_ATTEMPTS:-3}
delay=${BUILD_RETRY_DELAY_SECONDS:-10}

build() {
  local component=$1
  local dockerfile=$2
  local attempt
  local source_hash
  source_hash=$(python3 deploy/component-hash.py "$component")

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if docker build \
      --build-arg "REVISION=$revision" \
      --build-arg "SOURCE_HASH=$source_hash" \
      --build-arg "CRIMINAL_HASH=$(python3 deploy/component-hash.py criminal)" \
      -f "$dockerfile" \
      -t "trace-it-$component:ci" \
      .; then
      return 0
    fi
    if ((attempt == attempts)); then
      echo "$component image build failed after $attempts attempts" >&2
      return 1
    fi
    echo "$component image build failed, retrying ($attempt/$attempts)" >&2
    sleep "$delay"
  done
}

build backend deploy/backend.Dockerfile
build frontend deploy/frontend.Dockerfile
