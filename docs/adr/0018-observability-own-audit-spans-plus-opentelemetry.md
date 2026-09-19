---
status: accepted
---

# Trace every step as spans in our own database, and mirror them to OpenTelemetry

## Context
The jury scores traceability: for any invoice we must show what was read, which rules
answered and why, what a person did and what was exported; for any rule, how it was
produced (norm, tests, attempts, reviews, activation). We also need to see time and tokens
per step: per LLM call, per rule compilation, per rule over a run, per whole run. The
`events` table already held flat events (`step`, `data`, `latency_ms`) with no parent, so a
compilation or a run could not be shown as one tree. Constraints: free, lightweight (one
Postgres, no extra services required), no secret leaves the machine by default, and the
audit must survive without any external service.

## Alternatives considered
- **Logfire (or any hosted OTel backend) only.**
  - Pros: great UI, zero schema work, pydantic-ai and FastAPI integrations.
  - Cons: the audit would live in a third party with retention limits; the API could not
    join spans with decisions and rules; nothing without a token.
- **Langfuse self-hosted.**
  - Pros: LLM-focused UI, prompt management.
  - Cons: Postgres + ClickHouse + Redis + S3 to run; heavy for a weekend MVP; still not
    joined with our tables.
- **Arize Phoenix only.**
  - Pros: one container, OTLP in, good LLM views.
  - Cons: a live monitor, not an audit store; same join problem.
- **Jaeger / Grafana Tempo.**
  - Pros: standard tracing.
  - Cons: no LLM semantics; another service; still not the audit.
- **Own database only.**
  - Pros: joinable, durable, no dependency.
  - Cons: no live UI; we would rebuild what OTel backends already show.
- **Own spans in Postgres as the audit, mirrored to OpenTelemetry via the Logfire SDK
  (chosen).**
  - Pros: the audit is ours and queryable next to decisions and rules; live monitoring is
    free (Logfire free tier or a local Phoenix) and optional; one span API for both.
  - Cons: two writes per span; a small amount of code to own.

## Decision
- `events` becomes a span table (migration `0008`): `trace_id`, `span_id`, `parent_id`,
  `step` (name), `status` (`ok`/`error`), `started_at`, `duration_ms`, `data` JSONB and the
  links `instance_id`, `process_id`, `rule_id`, `norm_rule_id`. No foreign keys: the audit
  never blocks the transaction it describes. `cost` is dropped: cost is tokens
  (`data.input_tokens`, `data.output_tokens`).
- `app/core/events.py`: `with events.span("step", rule_id=..., **data) as s:`. The current
  span is a context variable, so children attach across `await`, `asyncio.gather` and
  threads; a background job continues a trace with `parent=`. Links `process_id`,
  `rule_id`, `norm_rule_id` are inherited. An exception marks the span `error` and
  propagates. A trace's rows are written in one insert when its outermost local span ends;
  a failed write is logged, never raised. `events.record(...)` stays for points saved with
  the caller's transaction (a decision, a resolution).
- Every span is also an OpenTelemetry span (`logfire.span`) with the same ids, so both
  layers show the same tree. `configure_observability()` (API and CLI) calls
  `logfire.configure(send_to_logfire="if-token-present")` and instruments pydantic-ai,
  httpx and SQLAlchemy; the API also instruments FastAPI. `LOGFIRE_TOKEN` sends to Logfire;
  `OTEL_EXPORTER_OTLP_ENDPOINT` sends traces to any OTLP backend (metrics and logs are off
  for it: Phoenix refuses them). Neither set: nothing leaves the process.
- Every `llm_run` span keeps what the model saw and answered: effective instructions
  (platform prompt, use case guidance, examples), user message, output, retry prompts,
  model, tokens, retries, `config_id`, `prompt_hash` (ADR 0011).
- Spans: `norm` > `normalize_norm` > `llm_run`; `compile_rules` > `compile_rule` > `llm_run`
  (tester), `coder_attempt` > (`llm_run`, `run_tests`), `impact_check`, `activate_rule`;
  `run_process` (escalations by cause, `MISSING_DATA` included) > `evaluate_rule` per
  rule (instances, fired, errors) + a `decision` point
  per instance (fired rules, reason, `rules_hash`); `upload_document` > `store_file`,
  `extraction` > `native_text`, `ocr`, `vision`, `text_judge`, then the `ingest_document`
  point with the reading and symbols; `sync_source` (the
  connector's requests, retries, 429s, logins, pages); `suggest_escalation`;
  `export_outcomes`; `resolution`.
- Read API (`features/traces`): `GET /traces`, `GET /traces/{trace_id}`,
  `GET /instances/{id}/trace`, `GET /rules/{id}/trace`, `GET /processes/{id}/metrics`.

## Consequences
- One synchronous insert per trace on the event loop (milliseconds); a writer thread if it
  ever shows up in latency.
- Per-rule engine spans, not per rule x instance: 16 rows per run of 16 rules, plus the
  decision points that already existed.
- Prompts are stored in full on each `llm_run` (not deduplicated by `prompt_hash`): simple
  and auditable, larger rows. A `prompts` table if storage matters.
- A process killed mid-trace loses that trace's unwritten spans.
- Spans of the standalone extraction worker (`/v1/extractions`) are traces of their own,
  not tied to an instance.
- Found while measuring: activating a freshly compiled rule runs the impact check twice
  (`impact_check`, then `activate_rule`), about 1 s each on 471 invoices.

## Evidence
- Measured locally (M-series Mac, Postgres in Docker), real sandbox over the 471 batch-1
  golden invoices, 16 hand-written rules; compile with scripted models (no network):
  `run_process` 1048 ms (449 invoices/s), each `evaluate_rule` 38-90 ms (p50 40 ms, p95
  90 ms); a norm with one check: `norm` 31 ms, then in the background `compile_rule`
  2059 ms = tester 3 ms + `coder_attempt` 32 ms (`run_tests` 28 ms, 6/6) + `impact_check`
  1033 ms + `activate_rule` 981 ms. The same spans arrived in a local Phoenix
  (`docker compose --profile observability up -d`), with FastAPI, SQL and pydantic-ai spans.
- Tests: `traces/tests/test_spans.py` (nesting across gather and threads, background
  parent, error status, nothing sent without a token and OTel ids equal to ours);
  `agents/tests/test_compiler.py` (compile span tree with prompts and outputs);
  `agents/tests/test_normalizer.py` (one trace from norm to three concurrent compilations,
  rule trace); `agents/tests/test_assistant.py` (retry prompts);
  `traces/tests/test_api.py` (run spans, instance journey, rule runtime, metrics).

## Related
ADR 0004, 0006, 0008, 0011, 0016, 0017.
