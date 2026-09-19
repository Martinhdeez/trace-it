#!/usr/bin/env bash
# Installed root-owned; authorized_keys forces this command for the CI key only.
set -Eeuo pipefail
read -r action revision backend frontend actor extra <<< "${SSH_ORIGINAL_COMMAND:-}"
[[ "$action" == deploy && -z "${extra:-}" ]]
[[ "$revision" =~ ^[0-9a-f]{40}$ ]]
[[ "$backend" =~ ^sha256:[0-9a-f]{64}$ && "$frontend" =~ ^sha256:[0-9a-f]{64}$ ]]
[[ "$actor" =~ ^[A-Za-z0-9_-]+(\[bot\])?$ ]]
exec sudo -n /usr/local/sbin/trace-it-deploy "$revision" "$backend" "$frontend" "$actor"
