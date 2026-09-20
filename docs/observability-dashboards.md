# Traceability dashboards: one per plane

**Status:** required for the frontend integration (Martín, 2026-09-19). The frontend handoff and the integration plan (phase 1.9) link here.

## The requirement

The frontend shows traceability as **three separate dashboards**, one for each monitoring plane. The Metrics overview also shows a combined recorded total, immediately split by plane in a Sankey diagram. Each dashboard shows its own activity, quality, token spend and cost, and every number drills down to the spans behind it.

| Plane | What it covers | The question it answers |
|---|---|---|
| **Ingestion** (`ingestion`) | Reading documents and reference data: PDF text, OCR, vision and judge providers, the workbook, source sync | How much did it cost to read the data, and how reliable was the reading? |
| **Agents** (`agents`) | Turning a norm into code: normalizer, tester, coder/compiler, assistant, reviewer | How much did it cost to create or change the rules, and did the agents get them right? |
| **Execution** (`execution`) | Running the published rules on the cases: engine, decisions, escalations, resolutions, export | What was decided, how fast, and why? |

## Why the split matters

One live demo run on v1.0 (process 9, 500 invoices, OCR forced) spent **214,734 LLM tokens**. As a single number, that suggests each invoice costs AI. By plane it looks like this:

| Plane | Tokens | Where they went | When they are spent |
|---|---|---|---|
| Ingestion | 52,395 (24%) | Jev text selection 44,334 and Gemini vision 8,061, all on the 29 scans | The first time a scan is read. Replays from the cache cost 0 |
| Agents | 162,339 (76%) | Compiler 87,777, tester 68,220, normalizer 6,342 | Once per norm version, and only for new or changed rules |
| Execution | **0** | The engine never calls an LLM (ADR 0002) | Never |

Deciding 500 invoices cost 0 tokens. The AI cost is in reading scans and in writing the rules. A total without its decomposition hides exactly that, so every combined overview must keep the planes visible.

## Data sources (already in the backend)

| Need | Endpoint |
|---|---|
| Per-plane metrics for a process | `GET /processes/{id}/metrics/{plane}` with `plane` = `ingestion`, `agents` or `execution` |
| Per-plane metrics across processes | `GET /metrics/{plane}` |
| Health of each plane | `GET /health/planes`, with `ok` / `degraded` / `down`, error rate, p95 and the reason |
| Live spans | `GET /events/stream?plane={plane}&process_id={id}` (SSE, `event` = plane) |
| Drill-down | `GET /traces?process_id=&name=&status=`, `GET /instances/{id}/trace`, `GET /rules/{id}/trace`, `GET /traces/{trace_id}` |

## Dashboard 1: Ingestion (data and OCR)

**Headline:** documents read; share of native text vs OCR vs scans; tokens and cost per document, split by native and scan; errors.

**Content** (from `/metrics/ingestion`):
- Volume and speed: `files`, `pages`, `files_per_second`, `spans`.
- Reading work: `ocr_calls`, `focused_reads`, `judge_calls`, `cache_hits`.
- Quality: `abstentions` and `abstentions_by_field` (the fields the reader refused to guess), `errors`.
- One row per provider and model (`providers[]`): `network_requests`, `replays`, `blocked`, `fallbacks`, `errors`, `input_tokens`, `output_tokens`, `cached_tokens`, `reasoning_tokens`, `known_cost_usd`, `unpriced_requests`, `network_p50_ms` and `network_p95_ms`.
- Rate-limit visibility: requests that failed with HTTP 429, per provider (a forced demo exhausted the Gemini quota on 2026-09-19).
- Reference data: workbook loads and ERP syncs (rows, pages, retries, logins, duration).

**Drill-down:** document → `/instances/{id}/trace` spans (`upload_document → extraction → native_text | ocr | vision | focused_read → provider_call → ingest_document`) → each symbol with its value and origin (page and offset, or source row). The PDF opens next to it.

## Dashboard 2: Agents (norm → rules → code)

**Headline:** tokens and cost per norm version and per rule; first-try compile rate; cache hit rate (`cached_tokens / input_tokens`).

**Content** (from `/metrics/agents`):
- `by_role`: normalizer, tester, compiler (coder), assistant, reviewer.
- `by_rule` and `by_norm_rule`: which rule or norm sentence cost what.
- `by_model`: which model and fallback answered.
- For each row: `calls`, `requests`, `input_tokens`, `output_tokens`, `cached_tokens`, `retries`, `fallbacks`, `truncations`, `errors`.
- Compile outcome per rule: valid on the first attempt, after retries, or failed (for example "every model failed").

**Drill-down:** rule → `/rules/{id}/trace` (`normalize_norm → llm_run tester → coder_attempt → llm_run compiler → run_tests → impact_check → activate_rule`), with the exact context each agent saw: instructions, message, answer and tokens.

## Dashboard 3: Execution (published rules on cases)

**Headline:** cases decided; decisions by outcome; escalations by reason; throughput; **0 tokens and 0 €**, shown explicitly as a design guarantee.

**Content** (from `/metrics/execution`):
- `runs`, `instances_decided`, `instances_per_second`, `pending`.
- `decisions_by_outcome`, using the process's own decision types and colours (no hardcoded PAGAR/NO_PAGAR).
- `escalated` and `failures` by reason (`MISSING_DATA`, `RULE_ERROR`, `RULE_CONFLICT`, `RULE_NEEDS_DATA`, `RULE_COMPILE_FAILED`).
- Per rule (`rules[]`): `evaluations`, `fired`, `errors`, `p50_ms`, `p95_ms`.
- Human side: `resolutions`, `open_alerts`.
- `steps[]`: p50/p95 per step (`run_process`, `evaluate_rule`, `decision`, `export_outcomes`).

**Drill-down:** decision → case → the rules that fired and their reason → the process version and rules hash → the source snapshot used.

## Rules for all three dashboards

1. **Keep the planes visible.** The usage explorer can show a combined total when its Sankey immediately decomposes it by plane and then by task or model.
2. **Every number drills down** to the spans behind it. Traceability means a person can go from a total to the exact call.
3. **Each dashboard header shows its plane's health** from `/health/planes`.
4. **Filters:** process, process version and time window. The default is the current process and its latest run.
5. **Live updates:** one SSE subscription per dashboard, filtered by `plane` and `process_id`. Polling is the fallback.
6. **Cost:** show € when the price is known. When it is not, show the count of unpriced requests, never 0.
7. **Separate one-time cost from per-run cost:** the agents plane is spent per norm version, ingestion per new document, and execution never.

## Backend gaps to close

- The agents plane reports tokens but no cost: the Helmcode/DeepSeek price is not configured, so `cost` is `null` in every `llm_run`. Add model prices to the agent configuration and expose `known_cost_usd` and `unpriced_requests` in `/metrics/agents`, as ingestion already does.
- The compiler never hits the prompt cache (`cached_tokens = 0`), because the examples change for every rule. Reducing this is tracked separately. The dashboard only has to show the cache rate.
- `/metrics/{plane}` responses are untyped. Add response schemas so the typed client (phase 0) covers them.

## Usage explorer

The Metrics screen uses `GET /processes/{id}/metrics/breakdown`. Its overview starts with a Sankey: recorded total → plane → task or model.
`flow` contains the complete plane/module/provider/model aggregates in the same snapshot.
Switching tasks/models uses the shared segmented control. A model shared by multiple tasks
merges into one node; selecting it exposes the contributing tasks. Ribbon widths conserve
the selected cost, token or active-time measure, including very small values. Zero and
unpriced amounts never receive fabricated flow widths or a zero-percent label. A note
explains when only one branch has priced usage; token and time views also show activity
without a tariff. Scope is the current process, not
a cross-process product total. Infrastructure spending is not recorded; the cost total is
explicitly labelled as API cost at recorded rates and excludes hardware/deployment until a source is available.
The existing plane cards, distribution and history charts remain under **Detail and evolution**. Selecting a plane shows modules; selecting a module shows its
models/providers and individual operations, with access to each full trace. The shared
segmented control switches cost, tokens and active time. Detailed tables and accounting
notes are collapsed initially so the distribution and history charts remain prominent.

When more than seven task/model branches exist, the six largest remain visible and the
rest are combined into an inspectable node per area. Tasks stay together in source-area
order, with descending amounts within each area. Shared models remain merged and are
positioned between their contributing areas using weighted source positions, reducing
connection crossings. All contributing modules and amounts remain available.

Modules are the recorded agent name (falling back to role) for `llm_run`, the provider's
operation for `provider_call`, and the step name for local work. No fixed list of agents or
providers is needed. Existing records work without a migration or another model call.

Accounting rules:

- Cost is the recorded USD amount on priced/included model calls. Requests without a
  tariff remain explicit, including when a total contains both priced and unpriced work.
  No exchange rate or infrastructure cost is inferred.
- Only `llm_run` and network-attempted `provider_call` records contribute tokens or cost.
  Journal replays retain their operation/time but contribute no new model usage. Cached
  input tokens are part of input, not a third amount to add to input plus output.
- Active time (`self_ms`) subtracts the union of direct child intervals from each timed
  span, clipped to the parent's interval. Children in another plane or outside the filter
  still consume parent time. Concurrent operations accumulate work, so this is not
  wall-clock elapsed time. Untimed point events remain unknown rather than measured zero.
  p50/p95 describe inclusive operation durations and are not additive.
- Evolution attributes the whole operation to its start time in UTC buckets. The API
  returns hourly buckets for windows up to 24 hours, daily buckets thereafter and wider
  buckets for histories longer than 90 days. The chart fills inactive intervals with zero.
  An interval can be selected to inspect the operations contributing to it.
- Filters use `since <= started_at < until`, with explicit timezones. The console offers
  all history (default), the current calendar month (in the browser timezone), 24 hours, 7 days and 30 days. It freezes `until` and the last event ID (`through_id`) while drilling down and
  paginating, so late-finishing operations cannot shift the pages; Refresh takes a new snapshot. Scope and metric selection persist in the URL.

Tests: `backend/app/features/traces/tests/test_breakdown.py` verifies reconciliation,
concurrent timing, cross-plane/time-boundary children, pricing, replay, filters and
pagination against PostgreSQL. `frontend/e2e/metrics.spec.ts` covers browser navigation,
trace details, history selection, metric switching, mobile layout and empty/error states
with deterministic API fixtures.


### Measurement provenance

The screen always uses the audit API. Old `hardcoded` URL parameters are ignored; no
example toggle or production fixture remains. Synthetic values are confined to browser
test fixtures under `frontend/e2e/fixtures/`.

`imported_spans` counts records marked `cached_replay` by the seed restore. These are
original measurements with their original timestamps and saved token/cost data, not
new provider calls. They remain part of historical totals and are identified in the
summary and individual operations. Journal replays are distinct: those represent a
new cache lookup and contribute no new model usage.

Pricing coverage is `(requests - unpriced_requests) / requests`, displayed as counts.
Recorded tariff costs are estimates, not provider invoices. No recorded activity is
shown explicitly instead of presenting an empty group as a measured zero-cost operation.
