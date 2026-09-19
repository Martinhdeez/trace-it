#!/usr/bin/env bash
# Adopt the existing service without restarting it; install the restricted CD entrypoint.
set -Eeuo pipefail
umask 077
[[ "$EUID" == 0 ]]
here=$(cd -- "$(dirname -- "$0")" && pwd)
exec 9>/run/lock/trace-it-deploy.lock
flock -w 900 9
[[ -f /opt/trace-it/erp/compose.yml && -f /opt/trace-it/DEPLOY_ENABLED ]]
bash -n "$here/deploy.sh" "$here/../receive.sh"
backup="/opt/trace-it/backups/erp-cd-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup"
cp /usr/local/bin/trace-it-receive /etc/sudoers.d/trace-it-deploy "$backup/"
if [[ ! -f /opt/trace-it/erp/current.env ]]; then
  image=$(docker inspect trace-it-erp-erp-1 --format '{{.Image}}')
  [[ "$image" =~ ^sha256:[0-9a-f]{64}$ ]]
  printf 'TRACE_ERP_IMAGE=%s\n' "$image" > /opt/trace-it/erp/current.env
fi
install -o root -g root -m 600 "$here/compose.release.yml" /opt/trace-it/erp/compose.release.yml
install -o root -g root -m 755 "$here/deploy.sh" /usr/local/sbin/trace-it-erp-deploy
cp /etc/sudoers.d/trace-it-deploy "$backup/sudoers.candidate"
if ! grep -q '/usr/local/sbin/trace-it-erp-deploy' "$backup/sudoers.candidate"; then
  printf '\nkripta ALL=(root) NOPASSWD: /usr/local/sbin/trace-it-erp-deploy\n' >> "$backup/sudoers.candidate"
fi
visudo -cf "$backup/sudoers.candidate"
install -o root -g root -m 440 "$backup/sudoers.candidate" /etc/sudoers.d/trace-it-deploy
install -o root -g root -m 755 "$here/../receive.sh" /usr/local/bin/trace-it-receive
echo "ERP CD installed; running containers unchanged. Backup: $backup"
