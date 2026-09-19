#!/usr/bin/env bash
# No build, git checkout, global prune or changes to other projects.
# This demo installation can explicitly reset test data after its verified backup.
set -Eeuo pipefail
umask 077
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
unset DOCKER_HOST DOCKER_CONTEXT COMPOSE_FILE COMPOSE_PROJECT_NAME COMPOSE_PROFILES
unset POSTGRES_PASSWORD TRACE_ENV_FILE TRACE_MODEL_DIR TRACE_AUTH_FILE TRACE_PORT
unset TRACE_DATABASE_USER TRACE_DATABASE_PASSWORD TRACE_DATABASE_URL TRACE_APP_DATABASE_PASSWORD
[[ "$EUID" == 0 && "$#" == 4 ]]
revision=$1 backend=$2 frontend=$3 actor=$4
[[ "$revision" =~ ^[0-9a-f]{40}$ ]]
[[ "$backend" =~ ^sha256:[0-9a-f]{64}$ && "$frontend" =~ ^sha256:[0-9a-f]{64}$ ]]
[[ "$actor" =~ ^[A-Za-z0-9_-]+(\[bot\])?$ ]]
cd /opt/trace-it
exec 9>/run/lock/trace-it-deploy.lock
flock -w 900 9
[[ -f secrets/runtime.env && -f secrets/compose.env && -f secrets/htpasswd ]]
# An operator must explicitly enable deployment after the CI gate is green.
[[ -f DEPLOY_ENABLED ]] || { echo 'Root bootstrap is installed but deployment is disabled.' >&2; exit 1; }
available=$(df --output=avail -k /opt/trace-it | tail -1)
(( available >= 6 * 1024 * 1024 )) || { echo 'Need at least 6 GiB free; no global cleanup attempted.' >&2; exit 1; }
if [[ ! -f current.env ]]; then
  for port in 18173 18010; do
    if ss -H -ltn "sport = :$port" | grep -q .; then
      echo "Port $port is already in use; refusing to replace its service." >&2
      exit 1
    fi
  done
fi
export DOCKER_CONFIG
DOCKER_CONFIG=$(mktemp -d /run/trace-it-docker.XXXXXX)
cleanup() { rm -rf -- "$DOCKER_CONFIG"; }
trap cleanup EXIT
# Token arrives on SSH stdin, expires with this Actions job, never enters process argv.
docker login ghcr.io --username "$actor" --password-stdin >/dev/null
export TRACE_BACKEND_IMAGE="ghcr.io/martinhdeez/trace-it/backend@$backend"
export TRACE_FRONTEND_IMAGE="ghcr.io/martinhdeez/trace-it/frontend@$frontend"
compose=(docker compose --env-file secrets/compose.env -p trace-it -f compose.yml)
"${compose[@]}" pull
for image in "$TRACE_BACKEND_IMAGE" "$TRACE_FRONTEND_IMAGE"; do
  [[ $(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$image") == "$revision" ]]
done
# The preceding release may predate this optional service entirely.
previous_criminal=$(docker ps -q \
  --filter label=com.docker.compose.project=trace-it \
  --filter label=com.docker.compose.service=criminal-records)
mkdir -p backups releases
stamp=$(date -u +%Y%m%dT%H%M%SZ)
release="releases/$stamp-$revision.env"
printf 'TRACE_BACKEND_IMAGE=%s\nTRACE_FRONTEND_IMAGE=%s\n' "$TRACE_BACKEND_IMAGE" "$TRACE_FRONTEND_IMAGE" > "$release"

"${compose[@]}" up -d --wait --wait-timeout 120 db
# Consistent DB snapshot plus a filesystem snapshot with this app's writers stopped.
backup="backups/$stamp-$revision"
mkdir "$backup"
rollback() {
  trap - ERR
  if [[ -n "${mail_ids:-}" ]]; then
    docker stop --time 300 trace-it-mail-ingestion-1 >/dev/null 2>&1 || true
  fi
  echo 'Release failed; restoring previous application images. Database is NEVER restored automatically.' >&2
  if [[ -f current.env ]]; then
    set -a
    # shellcheck source=/dev/null
    source current.env
    set +a
    "${compose[@]}" up -d --wait --wait-timeout 180 backend frontend || true
    if [[ -n "$previous_criminal" ]]; then
      "${compose[@]}" up -d --wait --wait-timeout 120 criminal-records || true
    else
      "${compose[@]}" stop criminal-records || true
    fi
  else
    "${compose[@]}" stop criminal-records backend frontend || true
  fi
  echo "Backup retained in /opt/trace-it/$backup; inspect migrations before any data restore." >&2
  exit 1
}
trap rollback ERR
# Stop the optional mail writer before backend shutdown, backups or migrations.
# Discover by this project's exact Compose labels; never affect another stack.
# Resume a previously running worker only after successful demo deployment; never initialize it.
mail_ids=$(docker ps -q \
  --filter label=com.docker.compose.project=trace-it \
  --filter label=com.docker.compose.service=mail-ingestion)
if [[ -n "$mail_ids" ]]; then
  mapfile -t mail_containers <<< "$mail_ids"
  docker stop --time 300 "${mail_containers[@]}"
fi
"${compose[@]}" stop frontend backend
"${compose[@]}" exec -T db pg_dump -U trace -d trace -Fc > "$backup/database.dump"
"${compose[@]}" exec -T db pg_restore --list < "$backup/database.dump" > "$backup/database.list"
"${compose[@]}" run --rm --no-deps -T backend python -c \
  'import sys, tarfile; t=tarfile.open(fileobj=sys.stdout.buffer, mode="w|gz"); t.add("/srv/.data", arcname="data"); t.close()' > "$backup/ingestion.tar.gz"
tar -tzf "$backup/ingestion.tar.gz" > "$backup/ingestion.list"
# Runtime may be restricted; only this one-off migration container receives owner credentials.
set -a
# shellcheck source=/dev/null
source secrets/compose.env
set +a
export TRACE_DATABASE_URL="postgresql+psycopg://trace:${POSTGRES_PASSWORD}@db:5432/trace"
"${compose[@]}" run --rm --no-deps -T -e TRACE_DATABASE_URL backend alembic upgrade head
if [[ "${TRACE_DATABASE_USER:-trace}" == trace_app ]]; then
  export TRACE_APP_DATABASE_PASSWORD="${TRACE_DATABASE_PASSWORD:?Missing runtime database password}"
  "${compose[@]}" run --rm --no-deps -T -e TRACE_DATABASE_URL -e TRACE_APP_DATABASE_PASSWORD \
    backend python -m app.features.database_api.provision
  unset TRACE_APP_DATABASE_PASSWORD
fi
if [[ -f DEMO_RESET_ENABLED ]]; then
  [[ -s reset-demo.py && -s demo-seed.json ]]
  "${compose[@]}" run --rm --no-deps -T -e TRACE_DATABASE_URL \
    -v /opt/trace-it/reset-demo.py:/srv/reset-demo.py:ro \
    -v /opt/trace-it/demo-seed.json:/srv/demo-seed.json:ro \
    backend python /srv/reset-demo.py reset --seed /srv/demo-seed.json --confirm-demo-reset \
    > "$backup/demo-reset.json"
  "${compose[@]}" run --rm --no-deps -T -e TRACE_DATABASE_URL \
    backend python -m app.features.decisions.demo_seed > "$backup/demo-seed-run.json"
fi
unset TRACE_DATABASE_URL
if [[ ! -f INITIALIZED ]]; then
  # Seed the bundled use case and users once. Rule publication remains a manager action.
  "${compose[@]}" run --rm --no-deps -T backend python -m app.cli load /processes/invoice-payment.json
  touch INITIALIZED
fi
"${compose[@]}" up -d --wait --wait-timeout 180 criminal-records backend frontend
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:18173/internal-health >/dev/null
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:18010/criminal/status >/dev/null
python3 /opt/trace-it/activate-route.py
python3 /opt/trace-it/activate-route.py --criminal-records
curl --fail --silent --show-error --max-time 20 \
  https://gex-dashboard.hopto.org/nexia/criminal-records/ >/dev/null
curl --config secrets/curl.conf --fail --silent --show-error --max-time 20 \
  https://gex-dashboard.hopto.org/nexia/trace-it/api/ready >/dev/null
curl --config secrets/curl.conf --fail --silent --show-error --max-time 20 \
  https://gex-dashboard.hopto.org/nexia/trace-it/ >/dev/null
if [[ -f DEMO_RESET_ENABLED && -n "$mail_ids" ]]; then
  # Explicit demo policy: retain the cursor and resume with the candidate backend digest.
  set -a
  source secrets/mail-compose.env
  set +a
  export TRACE_MAIL_IMAGE="$TRACE_BACKEND_IMAGE"
  mail_compose=(docker compose --env-file secrets/compose.env -p trace-it
    -f compose.yml -f compose.mail.yml --profile mail)
  "${mail_compose[@]}" run --rm --no-deps -T mail-ingestion \
    python -m app.features.mail_ingestion.worker check
  "${mail_compose[@]}" up -d --no-deps mail-ingestion
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
[[ ! -f current.env ]] || cp current.env previous.env
cp "$release" current.env
trap - ERR
echo "Deployed $revision. Database and ingestion backup: /opt/trace-it/$backup"
