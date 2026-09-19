#!/usr/bin/env bash
# One-time update of the already installed, still-disabled bootstrap.
set -Eeuo pipefail
[[ "$EUID" == 0 ]]
cd /home/kripta/trace-it-staging/release
sha256sum -c SHA256SUMS
[[ -d /opt/trace-it && ! -f /opt/trace-it/current.env ]]
[[ ! -f /opt/trace-it/DEPLOY_ENABLED ]]
[[ $(sha256sum /usr/local/sbin/trace-it-deploy | cut -d ' ' -f 1) == 4c0647afc0331c4ff1d73ff952ba45138bb54d262468d605c3e6c6b95407413b ]]
[[ -z $(docker ps -aq --filter label=com.docker.compose.project=trace-it) ]]
[[ -z $(find /opt/trace-it/models -mindepth 1 -print -quit) ]]
cd /home/kripta/trace-it-staging/models-release
sha256sum -c ../release/MODEL_SHA256SUMS
cp -a . /opt/trace-it/models/
chown -R root:root /opt/trace-it/models
find /opt/trace-it/models -type d -exec chmod 755 {} +
find /opt/trace-it/models -type f -exec chmod 644 {} +
install -o root -g root -m 755 /home/kripta/trace-it-staging/release/deploy.sh /usr/local/sbin/trace-it-deploy
touch /opt/trace-it/DEPLOY_ENABLED
echo 'Models installed; first-release user/use-case initialization installed; VPS deployment enabled.'
echo 'No containers started and Caddy unchanged. GitHub CI still controls release.'
