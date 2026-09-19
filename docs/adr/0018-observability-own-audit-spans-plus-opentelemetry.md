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
  per instance (fired rules, reason, `rules_hash`); `reprocess` the same, with unchanged,
  changed and conflicts; a run or reprocess refused with 409 (rules compiling, none
  enforced) is an `error` span, so it shows in the metrics; `upload_document` > `store_file`,
  `extraction` > `native_text`, `ocr`, `vision`, `text_judge`, then the `ingest_document`
  point with the reading and symbols; `sync_source` (the
  connector's requests, retries, 429s, logins, pages); `suggest_escalation`;
  `export_outcomes`; `resolution`. Who changed what (author, before and after): `save_rule`,
  `norm`, `compile_rule` (`author`: a person, `cli` or `auto`), `activate_rule` and
  `retire_rule` (`before`/`after` status, `rule_hash`, `findings`), `impact_check` with
  `preview` (GET impact), `configure_agent` and `activate_agent_config` (`use_case_id`, `role`,
  `before_version`/`after_version`), `load_use_case`, `load_definition`, `resolution`
  (`before`, `previous_author`, `reason`). A refused change (409) is an `error` span with its
  author. The process feed (`GET /processes/{id}/events`) also lists its use case's
  configuration spans; `GET /rules/{id}/trace` has the rule's `lifecycle`.
- Read API (`features/traces`): `GET /traces`, `GET /traces/{trace_id}`,
  `GET /instances/{id}/trace`, `GET /rules/{id}/trace`, `GET /processes/{id}/metrics`, and
  the monitoring planes below.

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

- Coverage audit (2026-09-19), every entry point on `dev` after #45, #46, #48 and the OCR
  integration; gaps closed in the same change:

  | Entry point | Before | After |
  |---|---|---|
  | Load pack / `POST /processes/definition` / CLI `load` | no span | `load_use_case`, `load_definition` |
  | `PUT /use-cases/{id}/agents/{role}`, `POST /agent-configs/{id}/activate` | no span | `configure_agent`, `activate_agent_config` (author, versions) |
  | Norm, save rule, recompile | spans without author | `author` on `norm`, `save_rule`, `compile_rule` |
  | Compile: valid, `blocked`, LLM down, fallback | `compile_rule` tree, `llm_run` error / `failed_attempts` | unchanged (verified) |
  | Activate (manual, CLI, auto) | `activate_rule` without author; refusal untraced | author, before/after, findings; 409 = error span |
  | Retire | no span | `retire_rule` |
  | `GET /rules/{id}/impact` | no span | `impact_check` (`preview`) |
  | Run, refused run, reprocess (+dry run), decisions | spans | unchanged (verified) |
  | Sandbox crash | `evaluate_rule` error | unchanged (tested) |
  | Resolve | `resolution` with author | + previous decision and reason |
  | Export full / per batch | `export_outcomes` (`batch`) | unchanged (verified) |
  | Findings | not counted | `findings` on activate/retire |
  | ERP sync, ERP down | `sync_source`, error | unchanged (verified live) |
  | Upload PDF (store, native, OCR, vision, judge, `ingest_document`) | spans; OCR failure = error span | unchanged (tested) |
  | Focused re-reading of identifiers (OCR/vision) | untraced model calls | `focused_read` per reader |
  | `POST /instances/{id}/extract` | reading steps were orphan traces | `reextract_document` trace |
  | `POST /processes/{id}/sources/workbook` | extraction was an orphan trace | `upload_workbook` trace |
  | Assistant suggestion | `suggest_escalation` > `llm_run` | unchanged |
  | `tools/demo_run.py` | wrote instances with no audit | `demo_ingest` > `ingest_document` per instance |
  | `tools/bench_scale.py` | through the API | covered by the API spans |

  Live check on a scratch database: pack loaded by the CLI, a second process, workbook, ERP
  sync, 20 PDFs (2 scans, OCR) through `POST /processes/{id}/files`, the client's
  `Norma_Pagos_v3` (1 normalizer call, 12 checks compiled and auto-activated with real
  models), run (18 PAGAR, 2 ESCALAR), a suggestion, a person's resolution, an agent config
  change and rollback, impact preview, dry-run reprocess, full and per-batch export, a
  retirement, the ERP stopped (error span). Every step was in `/traces`; the scan's
  `/instances/{id}/trace` read upload > store > extraction > native text > OCR x2 >
  `ingest_document`, run > rules > decision, suggestion, resolution, exports.
- Tests: `traces/tests/test_coverage.py` (config and rule changes with author and versions,
  refusals, failed compile with every model down, sandbox crash);
  `ingestion/tests/test_pdf.py` (OCR failure); `ingestion/tests/test_process_api.py`
  (upload and re-extraction as one trace each; needs `TRACEPAY_TEST_POSTGRES=1`).

## Monitoring planes (2026-09-19)
The same spans, cut three ways so that each question has its own view. `PLANES` in
`features/traces/service.py` maps every span name to exactly one plane.
`traces/tests/test_planes.py` reads every `events.span`/`events.record` call in
`backend/app` and `tools`, and fails if a span has no plane or if a plane lists a span that
nothing emits. An `llm_run` always belongs to `agents`, whichever step called it, so all
tokens are counted in one place.

| Plane | Spans | Key metrics | Endpoint |
|---|---|---|---|
| ingestion | `upload_document`, `store_file`, `extraction`, `native_text`, `ocr`, `vision`, `text_judge`, `focused_read`, `ingest_document`, `reextract_document`, `extract_document`, `upload_workbook`, `load_workbook`, `sync_source` | files, files/s (first reading's start to last reading's end), pages, OCR/vision/judge/focused calls, cache hits, abstentions (declared symbols read as null) by field, errors, p50/p95 per step | `GET /processes/{id}/metrics/ingestion`, `GET /metrics/ingestion` |
| agents | `load_use_case`, `load_definition`, `configure_agent`, `activate_agent_config`, `save_rule`, `norm`, `normalize_norm`, `compile_rules`, `compile_rule`, `coder_attempt`, `run_tests`, `impact_check`, `activate_rule`, `retire_rule`, `llm_run`, `demo_llm_down`, `learn_norms`, `validate_norm`, `adopt_norm`, `reject_norm` | tokens in/out/cached, requests, retries, fallbacks, truncations and errors by model, role (agent), rule, norm rule and use case; tokens per hour; compile success rate, attempts per compilation; per norm: tokens and seconds from the norm to its last rule active | `GET /processes/{id}/metrics/agents`, `GET /metrics/agents` |
| execution | `run_process`, `evaluate_rule`, `decision`, `reprocess`, `review_decision`, `suggest_escalation`, `resolution`, `export_outcomes` | runs, invoices/s, per-rule evaluations, fired, errors and p50/p95; decisions by type; escalations by cause (`MISSING_DATA`, `RULE_ERROR`...); the human queue; pending; resolutions by author; engine decision to a person's decision (p50/p95 s) | `GET /processes/{id}/metrics/execution`, `GET /metrics/execution` |

All of these take `since`. `GET /processes/{id}/metrics` is unchanged: its `llm[]` only
gains fields. Live: `GET /health/planes` gives each plane `ok`, `degraded` or `down` from
its error rate and p95 over the last `TRACE_HEALTH_WINDOW_MINUTES`, measured against
`TRACE_HEALTH_*` thresholds. `GET /events/stream` sends every new span as a server-sent
event named after its plane; it polls `events` by id every second and can filter by plane
and process.

Every `llm_run` now records the provider's `cached_tokens` too. A failed run still records
the requests and tokens of the answers that came back. Cost stays in tokens: there is no
per-model price setting.

Alternatives considered:
- **Prometheus + Grafana (or OTel metrics to a collector).**
  - Pros: standard dashboards and alerts.
  - Cons: two more services, and a second copy of numbers the `events` table already
    holds; they could not join spans with decisions or rules.
- **A plane column on `events`.**
  - Pros: cheaper filters.
  - Cons: a migration, and every emitter would have to write the plane. At this scale a
    dict in one place and `step IN (...)` over the process's (indexed) spans are enough.
- **One endpoint with `?plane=`.**
  - Pros: one URL.
  - Cons: the response shape would depend on a query parameter. A path parameter per
    plane keeps each shape typed in OpenAPI, and leaves the existing response untouched.
- **Postgres LISTEN/NOTIFY or WebSockets for the live view.**
  - Pros: push instead of polling.
  - Cons: a listener connection per client, or a trigger. A one-second poll by primary
    key is cheap at this scale.

Live check, 2026-09-19 (`demo-logs/planes/`). The setup was a fresh database, the pack
loaded by the CLI, the workbook, an ERP sync, 11 PDFs (1 scan), a one-sentence norm
compiled with real models, a run, a resolution and an export. The three planes held 61,
29 and 31 spans. The live stream sent 121 events, and every one had its plane.

- **Ingestion:** 11 files at 18 files/s, 11 pages and 2 OCR calls, both in error because
  the local OCR models are missing. Abstentions: `issuer_name` was null on all 11 files,
  and 9 other fields were null once, on the scan.
- **Agents:** 3 LLM calls, 12,066 tokens in and 2,422 out. The norm went active in 12.8 s,
  and the one compilation was valid on its first attempt.
- **Execution:** 22.7 invoices/s, rules at a p50 of 26 ms, 1 escalation for
  `MISSING_DATA`, resolved by Martín 0.5 s later.
- **Health:** all three planes `ok`. Ingestion's error rate was 3.3 %, under the 5 %
  threshold.

## Related
ADR 0004, 0006, 0008, 0011, 0016, 0017.
