#!/usr/bin/env bash
# No build, git checkout, global prune, database reset or changes to other projects.
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
if [[ ! -f current.env ]] && ss -H -ltn 'sport = :18173' | grep -q .; then
  echo 'Port 18173 is already in use; refusing to replace its service.' >&2
  exit 1
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
  echo 'Release failed; restoring previous application images. Database is NEVER restored automatically.' >&2
  if [[ -f current.env ]]; then
    set -a
    # shellcheck source=/dev/null
    source current.env
    set +a
    "${compose[@]}" up -d --wait --wait-timeout 180 backend frontend || true
  else
    "${compose[@]}" stop backend frontend || true
  fi
  echo "Backup retained in /opt/trace-it/$backup; inspect migrations before any data restore." >&2
  exit 1
}
trap rollback ERR
# Stop the optional mail writer before backend shutdown, backups or migrations.
# Discover by this project's exact Compose labels; never affect another stack.
# Do not restart it automatically on success or rollback. Activation is explicit.
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
unset TRACE_DATABASE_URL
if [[ ! -f INITIALIZED ]]; then
  # Seed the bundled use case and users once. Rule publication remains a manager action.
  "${compose[@]}" run --rm --no-deps -T backend python -m app.cli load /processes/invoice-payment.json
  touch INITIALIZED
fi
"${compose[@]}" up -d --wait --wait-timeout 180 backend frontend
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:18173/internal-health >/dev/null
python3 /opt/trace-it/activate-route.py
curl --config secrets/curl.conf --fail --silent --show-error --max-time 20 \
  https://gex-dashboard.hopto.org/nexia/trace-it/api/ready >/dev/null
curl --config secrets/curl.conf --fail --silent --show-error --max-time 20 \
  https://gex-dashboard.hopto.org/nexia/trace-it/ >/dev/null
[[ ! -f current.env ]] || cp current.env previous.env
cp "$release" current.env
trap - ERR
echo "Deployed $revision. Database and ingestion backup: /opt/trace-it/$backup"
