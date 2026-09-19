#!/usr/bin/env bash
# Installed root-owned; authorized_keys forces this command for the CI key only.
set -Eeuo pipefail
read -r -a args <<< "${SSH_ORIGINAL_COMMAND:-}"
case "${args[0]:-}" in
  deploy)
    [[ ${#args[@]} == 5 ]]
    action=${args[0]} revision=${args[1]} backend=${args[2]} frontend=${args[3]} actor=${args[4]}
    [[ "$revision" =~ ^[0-9a-f]{40}$ ]]
    [[ "$backend" =~ ^sha256:[0-9a-f]{64}$ && "$frontend" =~ ^sha256:[0-9a-f]{64}$ ]]
    [[ "$actor" =~ ^[A-Za-z0-9_-]+(\[bot\])?$ ]]
    exec sudo -n /usr/local/sbin/trace-it-deploy "$revision" "$backend" "$frontend" "$actor"
    ;;
  deploy-erp)
    [[ ${#args[@]} == 4 ]]
    revision=${args[1]} digest=${args[2]} actor=${args[3]}
    [[ "$revision" =~ ^[0-9a-f]{40}$ && "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]
    [[ "$actor" =~ ^[A-Za-z0-9_-]+(\[bot\])?$ ]]
    exec sudo -n /usr/local/sbin/trace-it-erp-deploy "$revision" "$digest" "$actor"
    ;;
  *) exit 1 ;;
esac
