#!/bin/sh
set -eu

bootstrap_hiring() {
  sleep 5
  process_id=$(python -c '
import json, urllib.request
rows = json.load(urllib.request.urlopen("http://127.0.0.1:8000/processes"))
print(next((row["id"] for row in rows if row["name"] == "Hiring screening"), ""))
')
  set -- --base-url http://127.0.0.1:8000 --auto --skip-learning \
    --report /tmp/hiring-bootstrap.md
  if [ -n "$process_id" ]; then
    set -- "$@" --process "$process_id"
  fi
  python /srv/hiring_demo.py "$@"
}

bootstrap_hiring &
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --root-path /nexia/trace-it/api
