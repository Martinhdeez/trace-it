#!/usr/bin/env bash
# Root-owned deployment receiver. Normal releases preserve all demo data.
set -Eeuo pipefail
umask 077
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
unset DOCKER_HOST DOCKER_CONTEXT COMPOSE_FILE COMPOSE_PROJECT_NAME COMPOSE_PROFILES
unset POSTGRES_PASSWORD TRACE_ENV_FILE TRACE_MODEL_DIR TRACE_AUTH_FILE TRACE_PORT
unset TRACE_DATABASE_USER TRACE_DATABASE_PASSWORD TRACE_DATABASE_URL TRACE_APP_DATABASE_PASSWORD
unset TRACE_BACKEND_IMAGE TRACE_FRONTEND_IMAGE TRACE_CRIMINAL_RECORDS_IMAGE TRACE_MAIL_IMAGE
[[ "$EUID" == 0 ]]
mode=deploy
if [[ "$#" == 1 && "$1" == --reset-demo ]]; then
  # Local operator command only; the restricted SSH receiver cannot request a reset.
  mode=reset
else
  [[ "$#" == 4 ]]
  revision=$1 backend=$2 frontend=$3 actor=$4
  [[ "$revision" =~ ^[0-9a-f]{40}$ ]]
  [[ "$backend" =~ ^sha256:[0-9a-f]{64}$ && "$frontend" =~ ^sha256:[0-9a-f]{64}$ ]]
  [[ "$actor" =~ ^[A-Za-z0-9_-]+(\[bot\])?$ ]]
fi
cd /opt/trace-it
exec 9>/run/lock/trace-it-deploy.lock
flock -w 900 9
[[ -f DEPLOY_ENABLED && -f secrets/runtime.env && -f secrets/compose.env ]]
available=$(df --output=avail -k . | tail -1)
(( available >= 6 * 1024 * 1024 )) || { echo 'Need at least 6 GiB free.' >&2; exit 1; }
# This receiver upgrades an initialized installation. Bootstrap routes separately.
[[ -f current.env && -f INITIALIZED ]] || { echo 'Initialize the installation before component deployment.' >&2; exit 1; }
set -a
source current.env
set +a
old_backend=$TRACE_BACKEND_IMAGE
old_frontend=$TRACE_FRONTEND_IMAGE
old_criminal=${TRACE_CRIMINAL_RECORDS_IMAGE:-$old_backend}
export TRACE_CRIMINAL_RECORDS_IMAGE=$old_criminal
export DOCKER_CONFIG
DOCKER_CONFIG=$(mktemp -d /run/trace-it-docker.XXXXXX)
cleanup() { rm -rf -- "$DOCKER_CONFIG"; }
trap cleanup EXIT
compose=(docker compose --env-file secrets/compose.env -p trace-it -f compose.yml)
backend_changed=false frontend_changed=false criminal_changed=false
same_component() {
  local old=$1 new=$2 label=${3:-org.trace-it.source-hash} before after
  before=$(docker image inspect --format "{{index .Config.Labels \"$label\"}}" "$old")
  after=$(docker image inspect --format "{{index .Config.Labels \"$label\"}}" "$new")
  [[ "$before" =~ ^[0-9a-f]{64}$ && "$before" == "$after" ]]
}
if [[ "$mode" == deploy ]]; then
  docker login ghcr.io --username "$actor" --password-stdin >/dev/null
  candidate_backend="ghcr.io/martinhdeez/trace-it/backend@$backend"
  candidate_frontend="ghcr.io/martinhdeez/trace-it/frontend@$frontend"
  # Pull and authenticate ALL candidates before interrupting a service.
  for image in "$candidate_backend" "$candidate_frontend"; do
    docker pull "$image" >/dev/null
    [[ $(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$image") == "$revision" ]]
    hash=$(docker image inspect --format '{{index .Config.Labels "org.trace-it.source-hash"}}' "$image")
    [[ "$hash" =~ ^[0-9a-f]{64}$ ]]
  done
  if ! same_component "$old_backend" "$candidate_backend"; then
    backend_changed=true
    export TRACE_BACKEND_IMAGE=$candidate_backend
  fi
  if ! same_component "$old_frontend" "$candidate_frontend"; then
    frontend_changed=true
    export TRACE_FRONTEND_IMAGE=$candidate_frontend
  fi
  if ! same_component "$old_criminal" "$candidate_backend" org.trace-it.criminal-hash; then
    criminal_changed=true
    export TRACE_CRIMINAL_RECORDS_IMAGE=$candidate_backend
  fi
else
  revision=$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$old_backend")
  [[ "$revision" =~ ^[0-9a-f]{40}$ ]]
fi
maintenance=false
if [[ "$backend_changed" == true || "$mode" == reset ]]; then maintenance=true; fi
"${compose[@]}" config --quiet
# Commands here must be read-only and must not start a second ingestion worker.
if [[ "$backend_changed" == true ]]; then
  "${compose[@]}" run --rm --no-deps -T backend alembic heads >/dev/null
fi
if [[ "$frontend_changed" == true ]]; then
  "${compose[@]}" run --rm --no-deps -T frontend nginx -t
fi
mail_ids="" old_mail=""
mail_compose=(docker compose --env-file secrets/compose.env -p trace-it
  -f compose.yml -f compose.mail.yml --profile mail)
if [[ "$maintenance" == true ]]; then
  mail_ids=$(docker ps -q --filter label=com.docker.compose.project=trace-it \
    --filter label=com.docker.compose.service=mail-ingestion)
  if [[ -n "$mail_ids" ]]; then
    set -a
    source secrets/mail-compose.env
    set +a
    old_mail=$TRACE_MAIL_IMAGE
    cp secrets/mail-compose.env "$DOCKER_CONFIG/mail-compose.env"
    export TRACE_MAIL_IMAGE=$TRACE_BACKEND_IMAGE
    "${mail_compose[@]}" config --quiet
    "${mail_compose[@]}" run --rm --no-deps -T mail-ingestion \
      python -m app.features.mail_ingestion.worker check
  fi
fi
if [[ "$mode" == reset ]]; then
  [[ -s reset-demo.py && -s demo-seed.json ]]
  seed_version=$(python3 -c 'import json; print(json.load(open("demo-seed.json"))["version"])')
  [[ "$seed_version" == 3 || "$seed_version" == 4 ]]
  if [[ "$seed_version" == 4 ]]; then
    [[ -s run-seed.py && -s seed_cache.py ]]
    "${compose[@]}" run --rm --no-deps -T \
      -v /opt/trace-it/run-seed.py:/srv/run-seed.py:ro \
      -v /opt/trace-it/seed_cache.py:/srv/seed_cache.py:ro \
      -v /opt/trace-it/demo-seed.json:/srv/demo-seed.json:ro \
      backend python /srv/run-seed.py verify-cache --seed /srv/demo-seed.json \
      > "$DOCKER_CONFIG/demo-cache-check.json"
  fi
fi
mkdir -p backups releases
stamp=$(date -u +%Y%m%dT%H%M%SZ)
backup="backups/$stamp-$revision-$mode"
backend_touched=false frontend_touched=false criminal_touched=false mail_stopped=false
rollback() {
  trap - ERR
  unset TRACE_DATABASE_URL TRACE_APP_DATABASE_PASSWORD
  echo 'Release failed; restoring changed services. Database is NEVER restored automatically.' >&2
  export TRACE_BACKEND_IMAGE=$old_backend TRACE_FRONTEND_IMAGE=$old_frontend
  export TRACE_CRIMINAL_RECORDS_IMAGE=$old_criminal
  if [[ "$backend_touched" == true ]]; then
    "${compose[@]}" up -d --no-deps --wait --wait-timeout 180 backend || true
  fi
  if [[ "$criminal_touched" == true ]]; then
    "${compose[@]}" up -d --no-deps --wait --wait-timeout 120 criminal-records || true
  fi
  if [[ "$frontend_touched" == true ]]; then
    "${compose[@]}" up -d --no-deps --wait --wait-timeout 120 frontend || true
  fi
  if [[ "$mail_stopped" == true ]]; then
    export TRACE_MAIL_IMAGE=$old_mail
    cp "$DOCKER_CONFIG/mail-compose.env" secrets/mail-compose.env
    "${mail_compose[@]}" up -d --no-deps mail-ingestion || true
  fi
  echo "Inspect /opt/trace-it/$backup if recovery is needed." >&2
  exit 1
}
trap rollback ERR
if [[ "$maintenance" == true ]]; then
  mkdir "$backup"
  if [[ -f "$DOCKER_CONFIG/demo-cache-check.json" ]]; then
    cp "$DOCKER_CONFIG/demo-cache-check.json" "$backup/demo-cache-check.json"
  fi
  if [[ -n "$mail_ids" ]]; then
    mapfile -t mail_containers <<< "$mail_ids"
    mail_stopped=true
    docker stop --time 300 "${mail_containers[@]}"
  fi
  backend_touched=true
  "${compose[@]}" stop backend
  # The frontend remains running; the gateway serves maintenance errors for the API.
  "${compose[@]}" exec -T db pg_dump -U trace -d trace -Fc > "$backup/database.dump"
  "${compose[@]}" exec -T db pg_restore --list < "$backup/database.dump" > "$backup/database.list"
  "${compose[@]}" run --rm --no-deps -T backend python -c \
    'import sys, tarfile; t=tarfile.open(fileobj=sys.stdout.buffer, mode="w|gz"); t.add("/srv/.data", arcname="data"); t.close()' > "$backup/ingestion.tar.gz"
  tar -tzf "$backup/ingestion.tar.gz" > "$backup/ingestion.list"
  set -a
  source secrets/compose.env
  set +a
  export TRACE_DATABASE_URL="postgresql+psycopg://trace:${POSTGRES_PASSWORD}@db:5432/trace"
  if [[ "$backend_changed" == true ]]; then
    "${compose[@]}" run --rm --no-deps -T -e TRACE_DATABASE_URL backend alembic upgrade head
    if [[ "${TRACE_DATABASE_USER:-trace}" == trace_app ]]; then
      export TRACE_APP_DATABASE_PASSWORD="${TRACE_DATABASE_PASSWORD:?Missing runtime database password}"
      "${compose[@]}" run --rm --no-deps -T -e TRACE_DATABASE_URL -e TRACE_APP_DATABASE_PASSWORD \
        backend python -m app.features.database_api.provision
      unset TRACE_APP_DATABASE_PASSWORD
    fi
  fi
  if [[ "$mode" == reset ]]; then
    [[ -s reset-demo.py && -s demo-seed.json ]]
    seed_version=$(python3 -c 'import json; print(json.load(open("demo-seed.json"))["version"])')
    "${compose[@]}" run --rm --no-deps -T -e TRACE_DATABASE_URL \
      -v /opt/trace-it/reset-demo.py:/srv/reset-demo.py:ro \
      -v /opt/trace-it/demo-seed.json:/srv/demo-seed.json:ro \
      backend python /srv/reset-demo.py reset --seed /srv/demo-seed.json --confirm-demo-reset \
      > "$backup/demo-reset.json"
    if [[ "$seed_version" == 4 ]]; then
      "${compose[@]}" run --rm --no-deps -T -e TRACE_DATABASE_URL \
        -v /opt/trace-it/run-seed.py:/srv/run-seed.py:ro \
        -v /opt/trace-it/seed_cache.py:/srv/seed_cache.py:ro \
        -v /opt/trace-it/demo-seed.json:/srv/demo-seed.json:ro \
        backend python /srv/run-seed.py run --seed /srv/demo-seed.json \
        > "$backup/demo-seed-run.json"
    else
      "${compose[@]}" run --rm --no-deps -T -e TRACE_DATABASE_URL \
        backend python -m app.features.decisions.demo_seed > "$backup/demo-seed-run.json"
    fi
  fi
  unset TRACE_DATABASE_URL
  "${compose[@]}" up -d --no-deps --wait --wait-timeout 180 backend
fi
if [[ "$criminal_changed" == true ]]; then
  criminal_touched=true
  "${compose[@]}" up -d --no-deps --wait --wait-timeout 120 criminal-records
fi
if [[ "$frontend_changed" == true ]]; then
  frontend_touched=true
  "${compose[@]}" up -d --no-deps --wait --wait-timeout 120 frontend
fi
curl --fail --silent --show-error --retry 6 --retry-delay 2 --retry-all-errors --max-time 10 \
  http://127.0.0.1:18173/internal-health >/dev/null
curl --config secrets/curl.conf --fail --silent --show-error --max-time 20 \
  https://gex-dashboard.hopto.org/nexia/trace-it/api/ready >/dev/null
if [[ "$mail_stopped" == true ]]; then
  export TRACE_MAIL_IMAGE=$TRACE_BACKEND_IMAGE
  "${mail_compose[@]}" up -d --no-deps mail-ingestion
fi
if [[ "$mode" == deploy ]]; then
  release="releases/$stamp-$revision.env"
  printf 'TRACE_BACKEND_IMAGE=%s\nTRACE_FRONTEND_IMAGE=%s\nTRACE_CRIMINAL_RECORDS_IMAGE=%s\n' \
    "$TRACE_BACKEND_IMAGE" "$TRACE_FRONTEND_IMAGE" "$TRACE_CRIMINAL_RECORDS_IMAGE" > "$release"
  if [[ "$mail_stopped" == true ]]; then
    python3 - <<'PIN_MAIL'
import os
from pathlib import Path
p = Path("secrets/mail-compose.env")
lines = [line for line in p.read_text().splitlines() if not line.startswith("TRACE_MAIL_IMAGE=")]
lines.append("TRACE_MAIL_IMAGE=" + os.environ["TRACE_MAIL_IMAGE"])
staged = p.with_suffix(".env.next")
staged.write_text("\n".join(lines) + "\n")
staged.chmod(p.stat().st_mode & 0o777)
staged.replace(p)
PIN_MAIL
  fi
  cp current.env previous.env
  cp "$release" current.env.next
  mv current.env.next current.env
fi
trap - ERR
echo "Completed $mode $revision: backend=$backend_changed frontend=$frontend_changed criminal-records=$criminal_changed"
