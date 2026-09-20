#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
work=$(mktemp -d)
container=""
cleanup() {
  [[ -z "$container" ]] || docker rm -f "$container" >/dev/null 2>&1 || true
  rm -rf -- "$work"
}
trap cleanup EXIT
active=$(python3 -c 'import json; print(json.load(open("deploy/erp/active.json"))["release"])')
for manifest in deploy/erp/releases/*/release.json; do
  name=$(basename "$(dirname "$manifest")")
  python3 deploy/erp/release.py --release "$name" --output "$work/$name"
  source_hash=$(python3 - "$work/$name" <<'PYHASH'
import hashlib, pathlib, sys
root = pathlib.Path(sys.argv[1])
digest = hashlib.sha256(b"trace-it-erp-v1\0")
for path in sorted(root.iterdir()):
    digest.update(path.name.encode() + b"\0")
    digest.update(hashlib.sha256(path.read_bytes()).digest())
print(digest.hexdigest())
PYHASH
  )
  docker build --build-arg "SOURCE_HASH=$source_hash" --build-arg "REVISION=${REVISION:-$(git rev-parse HEAD)}" -t "trace-it-erp:ci-$name" "$work/$name"
  container=$(docker run -d --network none --read-only --cap-drop ALL \
    --security-opt no-new-privileges --memory 128m --cpus 0.25 --pids-limit 64 \
    --tmpfs /tmp:size=16m,mode=1777 "trace-it-erp:ci-$name")
  for attempt in {1..30}; do
    if docker exec "$container" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8009/healthz", timeout=2)' >/dev/null 2>&1; then break; fi
    sleep 1
  done
  docker exec "$container" python smoke.py
  docker rm -f "$container" >/dev/null
  container=""
done
docker tag "trace-it-erp:ci-$active" trace-it-erp:ci
