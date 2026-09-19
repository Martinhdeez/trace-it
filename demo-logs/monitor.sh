#!/bin/sh
# Every 10 s: rule statuses of process 2 and the agent runs recorded as events.
while true; do
  echo "=== $(date +%H:%M:%S)"
  docker exec trace-pay-db-1 psql -U trace -d trace_demo -tAF' | ' -c "
    select 'rule '||id, status, coalesce(report->>'attempts','-')||' attempts', left(text,60)
    from rules where process_id=2 order by id"
  docker exec trace-pay-db-1 psql -U trace -d trace_demo -tAF' | ' -c "
    select to_char(created_at,'HH24:MI:SS'), step, data->>'role', 'rule '||(data->>'rule_id'), data->>'model',
           latency_ms||'ms', (data->>'input_tokens')||' in', (data->>'output_tokens')||' out', 'retries '||(data->>'retries')
    from events where created_at > now() - interval '15 seconds' order by id"
  sleep 10
done
