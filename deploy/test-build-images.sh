#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
calls=$(mktemp)
trap 'rm -f "$calls"' EXIT

docker() {
  printf '%s\n' "$*" >> "$BUILD_CALLS_FILE"
  [[ $(wc -l < "$BUILD_CALLS_FILE") -gt 1 ]]
}
export -f docker

BUILD_CALLS_FILE=$calls BUILD_RETRY_DELAY_SECONDS=0 \
  bash "$repo/deploy/build-images.sh" test-revision

[[ $(wc -l < "$calls") -eq 3 ]]
sed -n '1p' "$calls" | grep -F -- 'deploy/backend.Dockerfile'
sed -n '2p' "$calls" | grep -F -- 'deploy/backend.Dockerfile'
sed -n '3p' "$calls" | grep -F -- 'deploy/frontend.Dockerfile'
