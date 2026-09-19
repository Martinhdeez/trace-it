#!/usr/bin/env bash
# Root bootstrap only. Does not start containers, reload Caddy or enable deployment.
set -Eeuo pipefail
umask 077
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
[[ "$EUID" == 0 ]] || { echo 'Run this installer with sudo.' >&2; exit 1; }
stage=/home/kripta/trace-it-staging
source_dir="$stage/bootstrap"
[[ ! -e /opt/trace-it ]] || { echo '/opt/trace-it exists; review updates manually.' >&2; exit 1; }
for file in compose.yml deploy.sh receive.sh activate-route.py; do
  [[ -f "$source_dir/$file" && ! -L "$source_dir/$file" ]]
done
[[ -s "$stage/secrets/runtime.env" && -s "$stage/secrets/ci-deploy.pub" ]]
[[ ! -L "$stage/secrets/runtime.env" && ! -L "$stage/secrets/ci-deploy.pub" ]]
ssh-keygen -lf "$stage/secrets/ci-deploy.pub" >/dev/null
docker info >/dev/null
docker compose version
systemctl is-active --quiet caddy
if ss -H -ltn 'sport = :18173' | grep -q .; then
  echo 'Port 18173 is occupied; choose a new loopback port before installing.' >&2
  exit 1
fi
install -d -m 700 /opt/trace-it /opt/trace-it/secrets /opt/trace-it/backups /opt/trace-it/releases
install -d -m 755 /opt/trace-it/models
install -m 600 "$stage/secrets/runtime.env" /opt/trace-it/secrets/runtime.env
install -m 600 "$source_dir/compose.yml" /opt/trace-it/compose.yml
install -m 700 "$source_dir/activate-route.py" /opt/trace-it/activate-route.py
install -o root -g root -m 755 "$source_dir/deploy.sh" /usr/local/sbin/trace-it-deploy
install -o root -g root -m 755 "$source_dir/receive.sh" /usr/local/bin/trace-it-receive
# URL-safe database and HTTP credentials. Existing API provider keys remain server-side.
database_password=$(openssl rand -hex 32)
http_password=$(openssl rand -hex 24)
printf 'POSTGRES_PASSWORD=%s\nTRACE_ENV_FILE=/opt/trace-it/secrets/runtime.env\nTRACE_AUTH_FILE=/opt/trace-it/secrets/htpasswd\nTRACE_MODEL_DIR=/opt/trace-it/models\nTRACE_PORT=18173\n' \
  "$database_password" > /opt/trace-it/secrets/compose.env
printf 'trace-it:%s\n' "$(printf '%s' "$http_password" | openssl passwd -apr1 -stdin)" > /opt/trace-it/secrets/htpasswd
# nginx's unprivileged UID must read the file mounted from this root-only directory.
chmod 644 /opt/trace-it/secrets/htpasswd
printf 'user = "trace-it:%s"\n' "$http_password" > /opt/trace-it/secrets/curl.conf
printf 'TRACE_HTTP_USER=trace-it\nTRACE_HTTP_PASSWORD=%s\n' "$http_password" > /opt/trace-it/secrets/access.env
# A private copy lets the operator retrieve the access credentials without sudo.
install -o kripta -g kripta -m 600 /opt/trace-it/secrets/access.env "$stage/secrets/access.env"
printf 'kripta ALL=(root) NOPASSWD: /usr/local/sbin/trace-it-deploy\n' > /opt/trace-it/sudoers.candidate
visudo -cf /opt/trace-it/sudoers.candidate
install -o root -g root -m 440 /opt/trace-it/sudoers.candidate /etc/sudoers.d/trace-it-deploy
install -d -o kripta -g kripta -m 700 /home/kripta/.ssh
touch /home/kripta/.ssh/authorized_keys
chown kripta:kripta /home/kripta/.ssh/authorized_keys
chmod 600 /home/kripta/.ssh/authorized_keys
public_key=$(cat "$stage/secrets/ci-deploy.pub")
if ! grep -Fq -- "$public_key" /home/kripta/.ssh/authorized_keys; then
  printf '\nrestrict,command="/usr/local/bin/trace-it-receive" %s\n' "$public_key" >> /home/kripta/.ssh/authorized_keys
fi
echo 'Bootstrap installed. No container started; Caddy unchanged; deployment still disabled.'
echo 'After CI passes: sudo touch /opt/trace-it/DEPLOY_ENABLED and enable TRACE_DEPLOY_ENABLED in GitHub.'
echo 'Access credentials: /home/kripta/trace-it-staging/secrets/access.env (mode 600).'
