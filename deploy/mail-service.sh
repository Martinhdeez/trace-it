#!/usr/bin/env bash
# Installed by the operator in /opt/trace-it; never invoked by ordinary deployments.
set -Eeuo pipefail
[[ "$EUID" == 0 ]]
cd /opt/trace-it
exec 9>/run/lock/trace-it-deploy.lock
flock -w 900 9
[[ -f current.env && -f secrets/mail-compose.env && -f compose.mail.yml ]]
set -a
# shellcheck source=/dev/null
source current.env
# shellcheck source=/dev/null
source secrets/mail-compose.env
set +a
[[ "${TRACE_MAIL_IMAGE:-}" =~ @sha256:[0-9a-f]{64}$ ]] || {
  echo 'Pin TRACE_MAIL_IMAGE to an immutable registry digest.' >&2; exit 1;
}
[[ "$TRACE_MAIL_IMAGE" == "$TRACE_BACKEND_IMAGE" ]] || {
  echo 'Mail worker must use the same tested digest as the current backend.' >&2; exit 1;
}
compose=(docker compose --env-file secrets/compose.env -p trace-it
  -f compose.yml -f compose.mail.yml --profile mail)
case "${1:-}" in
  check)
    "${compose[@]}" run --rm --no-deps mail-ingestion python -m app.features.mail_ingestion.worker check
    ;;
  initialize)
    "${compose[@]}" run --rm --no-deps mail-ingestion python -m app.features.mail_ingestion.worker initialize
    ;;
  start)
    # The worker also validates its binding, protocol version, complete configuration and cursor.
    "${compose[@]}" up -d --no-deps mail-ingestion
    ;;
  stop)
    "${compose[@]}" stop -t 300 mail-ingestion
    ;;
  *) echo 'Usage: mail-service.sh check|initialize|start|stop' >&2; exit 2 ;;
esac
