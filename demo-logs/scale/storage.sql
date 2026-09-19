-- Postgres growth of trace-it (docs/scale-and-cost.md). Run: psql -f storage.sql <database>
analyze;
select relname, n_live_tup as rows, pg_total_relation_size(relid) as total_bytes,
       pg_total_relation_size(relid) / nullif(n_live_tup, 0) as bytes_per_row
from pg_stat_user_tables order by total_bytes desc limit 8;
select step, count(*), avg(pg_column_size(e.*))::int as avg_row_bytes,
       max(pg_column_size(e.*)) as max_row_bytes
from events e group by step order by sum(pg_column_size(e.*)) desc;
select data->>'role' as llm_run_role, count(*), avg(pg_column_size(e.*))::int as avg_row_bytes,
       max(pg_column_size(e.*)) as max_row_bytes
from events e where step = 'llm_run' group by 1 order by 1;
select count(*) as spans, pg_relation_size('events') as heap_bytes,
       pg_indexes_size('events') as index_bytes,
       pg_total_relation_size('events') / nullif(count(*), 0) as total_bytes_per_span
from events;
select pg_database_size(current_database()) as database_bytes;
