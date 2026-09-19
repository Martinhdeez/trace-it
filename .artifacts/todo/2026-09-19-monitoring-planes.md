# Monitoring planes: ingestion, agents, execution

Asked by Martín on 2026-09-19. Branch `feat/monitoring-planes` from `dev`, PR into `dev`.
Constraint: reuse the `events` table and the metrics code in `features/traces`; no new
infrastructure. Written after the first implementation pass, as asked.

## 1. What exists and what is missing

| Plane | Already there (before this change) | Missing |
|---|---|---|
| Ingestion | Spans for upload, store, extraction, native text, OCR, vision, judge, focused read, `ingest_document`, workbook, re-extraction, `sync_source`; `cache_hit` and call counts in span data; p50/p95 per step in `GET /processes/{id}/metrics` | A view of these spans only; files/s; pages, OCR/vision/judge calls and cache hits as numbers; abstentions (null fields) |
| Agents | `llm_run` with model, role, agent, tokens in/out, retries, requests, `failed_attempts`, rule and norm rule links; tokens by model and role per process | Cached tokens; tokens of a failed run; fallbacks and truncations counted; tokens by model, role, rule, norm rule and use case; global view; per-hour series; compile success rate and attempts; time from norm to active |
| Execution | `run_process`, `evaluate_rule`, `decision`, `reprocess`, `resolution`, `export_outcomes`, `review_decision`, `suggest_escalation`; runs, instances/s, outcomes, escalation causes, queue, pending per process | Per-rule time; who resolved and time to resolution; a global view |
| All | Spans are named ad hoc | One map from span name to plane; a test that fails when a new span has no plane; a live view |

`cost_per_1k` does not exist in the settings, so it is not added (tokens only).

## 2. Span-to-plane map

One dict, `PLANES` in `backend/app/features/traces/service.py`.

- **ingestion:** `upload_document`, `store_file`, `extraction`, `native_text`, `ocr`,
  `vision`, `text_judge`, `focused_read`, `ingest_document`, `reextract_document`,
  `extract_document`, `upload_workbook`, `load_workbook`, `sync_source`, `demo_ingest`.
- **agents:** `load_use_case`, `load_definition`, `configure_agent`,
  `activate_agent_config`, `save_rule`, `norm`, `normalize_norm`, `compile_rules`,
  `compile_rule`, `coder_attempt`, `run_tests`, `impact_check`, `activate_rule`,
  `retire_rule`, `llm_run`, `demo_llm_down`.
- **execution:** `run_process`, `evaluate_rule`, `decision`, `reprocess`,
  `review_decision`, `suggest_escalation`, `resolution`, `export_outcomes`.

An `llm_run` is always `agents`, even under `suggest_escalation` or `review_decision`: all
tokens are counted in one plane.

## 3. Endpoints and shapes

- `GET /processes/{id}/metrics` is unchanged. `llm[]` gains `cached_tokens`, `requests`,
  `fallbacks` and `truncations`; these are additive, so old clients still work.
- `GET /processes/{id}/metrics/{plane}` and `GET /metrics/{plane}` (every process). Both
  take `since`. Common fields: `plane`, `process_id`, `since`, `spans`, `errors`, and
  `steps[]` (count, errors, p50, p95).
  - **ingestion:** `files`, `files_per_second`, `pages`, `ocr_calls`, `vision_calls`,
    `judge_calls`, `focused_reads`, `cache_hits`, `abstentions`, `abstentions_by_field`.
  - **agents:** `llm[]` (by model and role); `by_model`, `by_role`, `by_rule`,
    `by_norm_rule` and `by_use_case` (each entry has `key`, calls, errors, retries,
    requests, fallbacks, truncations, and tokens in, out and cached); `per_hour[]`;
    `compile` (compilations, valid, success rate, attempts, attempts per compilation,
    max); `norms[]` (tokens and seconds from the norm to its last activation).
  - **execution:** `runs`, `instances_decided`, `instances_per_second`, `rules[]` (per
    rule: evaluations, instances, fired, errors, p50, p95), `decisions_by_outcome`,
    `failures`, `escalated`, `pending`, `resolutions`, `resolutions_by_author`,
    `resolution_p50_s`, `resolution_p95_s`.
- `GET /health/planes` returns, per plane, `status` (`ok`, `degraded` or `down`),
  `spans`, `errors`, `error_rate`, `p95_ms` and `reason`. It uses the thresholds
  `TRACE_HEALTH_*`.
- `GET /events/stream` is SSE: `event: <plane>`, `id: <events.id>`, `data: <span>`. It
  takes the filters `plane`, `process_id` and `after`.

## 4. Real-time: both

Both are small (about 40 lines each) and do different jobs. Health answers "is anything
wrong now" in one call, for a status light or a probe. The stream answers "show me
everything as it happens". The stream polls `events` by id every second in a fresh
session. That adds no infrastructure (no LISTEN/NOTIFY, no broker), and the id index makes
each poll cheap.

## 5. LLM token recording

In `agents/llm.py`, `llm_run` also records `cached_tokens` (the provider's
`cache_read_tokens`). A failed run records `requests` and tokens in, out and cached from the
answers that came back. `TRUNCATED` names the truncation marker, so it is counted without a
copied string.

## 6. Tests

`backend/app/features/traces/tests/test_planes.py` uses scripted models and needs no key:
- Every span name emitted in `backend/app` and `tools` (by AST) is in `PLANES`, and every
  `PLANES` key is emitted.
- One process through the three planes: an upload with text, OCR and a null field; a
  compile whose first model is down and whose fallback answers; a run and a resolution.
  Each plane's numbers are checked, plus the global agents view, a 422 for an unknown plane,
  and the old metrics shape.
- A failed LLM run still records requests and tokens.
- Health moves between ok, degraded (p95) and down (error rate) with the thresholds.
- The stream sends a ping, skips other planes and sends the new execution span.

## 7. Docs

- ADR 0018 gets a "Monitoring planes" section: a table of plane, spans, key metrics and
  endpoint, plus the alternatives considered.
- `docs/api.md` gets the new endpoints.
- `docs/scale-and-cost.md` is not touched.

## 8. Live check

Start the API on :8040 against a fresh database `trace_planes` on `trace-pay-db-1`. Load
the pack, upload a handful of challenge PDFs, sync the ERP if it is up, and run. Curl the
three planes, `/health/planes` and a few seconds of `/events/stream`, and save the outputs
to `demo-logs/planes/`. Stop the API afterwards. Leave :8009, :8010 and :8020 alone.

## 9. Done when

- `make check` is green, and the golden is 471/471.
- CI is green on the PR.
