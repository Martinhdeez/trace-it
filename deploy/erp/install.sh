#!/usr/bin/env bash
# Run the reviewed, checksummed bundle as root. No deployment privilege expansion.
set -Eeuo pipefail
umask 077
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
unset DOCKER_HOST DOCKER_CONTEXT COMPOSE_FILE COMPOSE_PROJECT_NAME COMPOSE_PROFILES
export TRACE_ERP_PORT=18009 TRACE_ERP_NETWORK=trace-it_default
[[ $EUID == 0 && $# == 3 ]] || { echo 'Usage: sudo bash install.sh PROCESS_ID USER_ID CUT_OFF_DATE'; exit 2; }
[[ $1 =~ ^[1-9][0-9]*$ && $2 =~ ^[1-9][0-9]*$ && $3 =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]
cd "$(dirname "$0")"
sha256sum -c SHA256SUMS
exec 9>/run/lock/trace-it-deploy.lock
flock -w 900 9
[[ -f /opt/trace-it/current.env && -f /opt/trace-it/secrets/curl.conf ]]
docker network inspect trace-it_default >/dev/null
if [[ ! -f /opt/trace-it/erp/compose.yml ]] && ss -H -ltn 'sport = :18009' | grep -q .; then
  echo 'Port 18009 is already occupied; refusing to replace another service.' >&2
  exit 1
fi
install -d -m 700 /opt/trace-it/erp
install -m 600 Dockerfile compose.yml server.py alberto_erp.py /opt/trace-it/erp/
docker compose -p trace-it-erp -f /opt/trace-it/erp/compose.yml up -d --build --wait --wait-timeout 90
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:18009/erp/estado >/dev/null

stamp=$(date -u +%Y%m%dT%H%M%SZ)
backup="/opt/trace-it/secrets/runtime.env.before-erp-$stamp"
cp -p /opt/trace-it/secrets/runtime.env "$backup"
set -a
source /opt/trace-it/current.env
set +a
compose=(docker compose --env-file /opt/trace-it/secrets/compose.env -p trace-it -f /opt/trace-it/compose.yml)
rollback() {
  trap - ERR
  cp -p "$backup" /opt/trace-it/secrets/runtime.env
  "${compose[@]}" up -d --force-recreate --wait --wait-timeout 180 backend frontend || true
  echo 'Runtime configuration restored. ERP and any appended source snapshots retained for inspection.' >&2
  exit 1
}
trap rollback ERR
python3 - <<'PY'
from pathlib import Path
path = Path('/opt/trace-it/secrets/runtime.env')
lines = path.read_text().splitlines()
updates = {
    'TRACE_ERP_URL': 'http://erp:8009',
    'TRACE_ERP_USER': 'alberto',
    'TRACE_ERP_PASSWORD': 'FACTURAS2009',
    'TRACEPAY_PROVIDER_RETRY_MAX_WAIT_S': '2',
    'TRACEPAY_VISION_PROVIDERS': 'helmcode',
    'TRACEPAY_HELMCODE_VISION_MODELS': 'qwen3.6,gemma4',
    'TRACEPAY_OCR_PROFILE': 'experimental',
}
# These are the public synthetic ERP credentials from the challenge manual.
# Leave every unrelated provider key and process setting unchanged.
retired = {'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'TRACEPAY_GEMINI_MODEL'}
lines = [line for line in lines if line.split('=', 1)[0].strip() not in updates.keys() | retired]
if not any(line.startswith('HELMCODE_API_KEY=') and line.split('=', 1)[1].strip() for line in lines):
    raise SystemExit('HELMCODE_API_KEY must be configured before retiring Gemini')
path.write_text('\n'.join(lines + [f'{k}={v}' for k, v in updates.items()]) + '\n')
path.chmod(0o600)
PY
# nginx resolves the backend at startup: recreate it too when backend IP changes.
"${compose[@]}" up -d --force-recreate --wait --wait-timeout 180 backend frontend
python3 bootstrap_sources.py --process-id "$1" --user-id "$2" --cut-off-date "$3" --workbook reference.xlsx
python3 activate-route.py --erp
curl --fail --silent --show-error --max-time 20 https://gex-dashboard.hopto.org/nexia/erp/ >/dev/null
curl --config /opt/trace-it/secrets/curl.conf --fail --silent --show-error --max-time 20 \
  https://gex-dashboard.hopto.org/nexia/trace-it/api/ready
trap - ERR
echo 'ERP installed with original faults; all four sources loaded; retry wait capped at 2 seconds.'
