#!/usr/bin/env bash
# An isolated, disposable stack. Never source the developer/production .env.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
export COMPOSE_PROJECT_NAME=trace-it-ci
export TRACE_BACKEND_IMAGE=trace-it-backend:ci
export TRACE_FRONTEND_IMAGE=trace-it-frontend:ci
export POSTGRES_PASSWORD=ci-only-database
export TRACE_PORT=18174
export TRACE_ENV_FILE="$PWD/deploy/.env.ci"
export TRACE_AUTH_FILE="$PWD/deploy/.htpasswd"
export TRACE_MODEL_DIR="$PWD/deploy/models"
compose=(docker compose --env-file /dev/null -p trace-it-ci -f deploy/compose.yml)
case "${1:-}" in
  up)
    mkdir -p "$TRACE_MODEL_DIR"
    printf 'TRACEPAY_OCR_PROFILE=experimental\n' > "$TRACE_ENV_FILE"
    printf 'ci:%s\n' "$(openssl passwd -apr1 ci-only-password)" > "$TRACE_AUTH_FILE"
    "${compose[@]}" up -d --wait --wait-timeout 120 db
    "${compose[@]}" run --rm --no-deps backend alembic upgrade head
    "${compose[@]}" run --rm --no-deps backend python -m app.cli load /processes/invoice-payment.json
    "${compose[@]}" up -d --wait --wait-timeout 180
    ;;
  down) "${compose[@]}" down --volumes ;;
  backup-check)
    # Expansion must happen inside the PostgreSQL container.
    # shellcheck disable=SC2016
    "${compose[@]}" exec -T db sh -eu -c '
      psql -v ON_ERROR_STOP=1 -U trace -d trace -c "CREATE TABLE ci_backup_probe (id integer PRIMARY KEY); INSERT INTO ci_backup_probe VALUES (42);"
      pg_dump -U trace -d trace -Fc -f /tmp/trace-ci.dump
      createdb -U trace trace_backup_ci
      pg_restore --exit-on-error -U trace -d trace_backup_ci /tmp/trace-ci.dump
      test "$(psql -At -U trace -d trace_backup_ci -c "SELECT id FROM ci_backup_probe")" = 42
      psql -v ON_ERROR_STOP=1 -U trace -d trace -c "DROP TABLE ci_backup_probe"
      dropdb -U trace trace_backup_ci
      rm /tmp/trace-ci.dump
    '
    ;;
  logs) "${compose[@]}" logs --no-color --tail=150 ;;
  *) echo 'Usage: deploy/ci-stack.sh up|backup-check|down|logs' >&2; exit 2 ;;
esac
