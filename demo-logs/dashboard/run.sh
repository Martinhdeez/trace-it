#!/bin/sh
# Start the throwaway dashboard on :8020 (stop: kill $(cat demo-logs/dashboard/server.pid)).
cd "$(dirname "$0")/../../backend" || exit 1
set -a; . ../.env; set +a
export TRACE_DATABASE_URL=postgresql+psycopg://trace:trace@localhost:5432/trace_demo
nohup uv run uvicorn --app-dir ../demo-logs/dashboard server:app --port 8020 > ../demo-logs/dashboard/server.log 2>&1 &
echo $! > ../demo-logs/dashboard/server.pid
