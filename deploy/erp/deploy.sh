#!/usr/bin/env bash
# Root-owned ERP release receiver. Never changes application sources or decisions.
set -Eeuo pipefail
umask 077
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
unset DOCKER_HOST DOCKER_CONTEXT COMPOSE_FILE COMPOSE_PROJECT_NAME COMPOSE_PROFILES
unset TRACE_ERP_IMAGE TRACE_ERP_PORT TRACE_ERP_NETWORK
[[ "$EUID" == 0 && "$#" == 3 ]]
revision=$1 digest=$2 actor=$3
[[ "$revision" =~ ^[0-9a-f]{40}$ && "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]
[[ "$actor" =~ ^[A-Za-z0-9_-]+(\[bot\])?$ ]]
cd /opt/trace-it
exec 9>/run/lock/trace-it-deploy.lock
flock -w 900 9
[[ -f DEPLOY_ENABLED && -f erp/current.env && -f erp/compose.release.yml ]]
available=$(df --output=avail -k . | tail -1)
(( available >= 2 * 1024 * 1024 )) || { echo 'ERP release needs 2 GiB free.' >&2; exit 1; }
export DOCKER_CONFIG
DOCKER_CONFIG=$(mktemp -d /run/trace-it-erp-docker.XXXXXX)
canary=""
cleanup() {
  [[ -z "$canary" ]] || docker rm -f "$canary" >/dev/null 2>&1 || true
  rm -rf -- "$DOCKER_CONFIG"
}
trap cleanup EXIT
docker login ghcr.io --username "$actor" --password-stdin >/dev/null
export TRACE_ERP_IMAGE="ghcr.io/martinhdeez/trace-it/erp@$digest"
docker pull "$TRACE_ERP_IMAGE" >/dev/null
[[ $(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$TRACE_ERP_IMAGE") == "$revision" ]]
# Revision labels change on every commit; compare the actual versioned build inputs.
previous_image=$(sed -n 's/^TRACE_ERP_IMAGE=//p' erp/current.env)
previous_hash=$(docker image inspect --format '{{index .Config.Labels "org.trace-it.source-hash"}}' "$previous_image")
candidate_hash=$(docker image inspect --format '{{index .Config.Labels "org.trace-it.source-hash"}}' "$TRACE_ERP_IMAGE")
[[ "$candidate_hash" =~ ^[0-9a-f]{64}$ ]]
if [[ "$previous_hash" =~ ^[0-9a-f]{64}$ && "$previous_hash" == "$candidate_hash" ]]; then
  echo 'ERP inputs unchanged; keeping its running image.'
  exit 0
fi
# Probe the exact candidate before replacing the live ERP. No shared network or ports.
canary=$(docker run -d --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --memory 128m --cpus 0.25 --pids-limit 64 \
  --tmpfs /tmp:size=16m,mode=1777 "$TRACE_ERP_IMAGE")
for attempt in {1..30}; do
  if docker exec "$canary" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8009/healthz", timeout=2)' >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "$canary" python smoke.py
mkdir -p erp/releases
stamp=$(date -u +%Y%m%dT%H%M%SZ)
record="erp/releases/$stamp-$revision"
docker exec "$canary" cat /srv/release.json > "$record.json"
printf 'TRACE_ERP_IMAGE=%s\n' "$TRACE_ERP_IMAGE" > "$record.env"
compose=(docker compose --env-file erp/current.env -p trace-it-erp -f erp/compose.release.yml)
rollback() {
  trap - ERR
  echo 'ERP deployment failed; restoring its previous image. Historical sources and decisions are unchanged.' >&2
  unset TRACE_ERP_IMAGE
  "${compose[@]}" up -d --no-build --wait --wait-timeout 120 erp || true
  exit 1
}
trap rollback ERR
"${compose[@]}" up -d --no-build --wait --wait-timeout 120 erp
"${compose[@]}" exec -T erp python smoke.py
curl --fail --silent --show-error --max-time 15 \
  https://gex-dashboard.hopto.org/nexia/erp/healthz > "$record.public.json"
python3 - "$record.json" "$record.public.json" <<'PY'
import json, sys
expected, actual = [json.load(open(path)) for path in sys.argv[1:]]
assert actual == {**expected, "rows": expected["expected_rows"]}, 'Public ERP release mismatch'
PY
cp erp/current.env erp/previous.env
cp "$record.env" erp/current.env.next
mv erp/current.env.next erp/current.env
trap - ERR
echo "ERP deployed: $revision ($digest). Release evidence: $record.json"
