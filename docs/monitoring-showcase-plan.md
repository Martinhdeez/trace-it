# Monitoring showcase plan

**Status:** plan, no code (2026-09-19). Base: `main` v1.1 (`a71434e`, plus #136).
**Goal:** the manager in the console and the jury in the defense can follow a real decision
and see status, evidence, versions, latency, errors, retries and pending work. The rubric
gives this 20 points.

**Martín's rules:** three separate dashboards (ingestion, agents, execution) and never a
mixed total; every number drills down to its spans; every module is traceable.

**Read for this plan:** [observability-dashboards.md](observability-dashboards.md),
[key-decisions.md](key-decisions.md) C,
[ADR 0018](adr/detail/0018-observability-own-audit-spans-plus-opentelemetry.md),
[api.md](api.md) (metrics, traces, planes, SSE, alerts), [defense.md](defense.md),
[`demo-logs/REPORT-trazabilidad.md`](../demo-logs/REPORT-trazabilidad.md),
`frontend/src` (`PlaneDashboards.tsx`, `TracePane.tsx`, `PdfEvidence.tsx`, `Queue.tsx`,
`api/live.ts`) and the partial v1.1 review (`REVIEW-v1.1.md`, findings N1-N12).

## 1. What exists vs what the rubric asks

### By rubric item

| Item | Backend / CLI today | Console today | Gap |
|---|---|---|---|
| **Status** | `GET /instances/{id}`, `/trace` (`status`, `decisions[]`, `exported_decision`) | Trace pane: final decision, reason, author, rule verdicts | None |
| **Evidence** | Symbols with `origin` (page, offset, `unverified`); `/document/locations` gives rectangles | "Abrir documento" opens the PDF with the field highlighted (`PdfEvidence`) | The source row a rule compared against (ERP entry, supplier row) is not shown. Only `tools/audit_page` shows it |
| **Versions** | `DecisionOut.version_id`, `rules_hash`; per-rule `hash`; `/processes/{id}/versions`; the CLI prints "v1, published by Martín, content 8503b6fc" | Only the 12-character `rules_hash` | No version number, publisher or per-rule code hash in the trace pane |
| **Latency** | `duration_ms` on every span; p50/p95 per step, rule and provider | The "traza" block (collapsed, raw step names); p50/p95 tables | p95 unrounded, e.g. `32.699999999999996 ms` (N9) |
| **Errors** | `status=error` spans; `fires: null` rule results; `failures`; `/health/planes` | Rule "error" chip; error counts per row; a health badge for the selected plane | Execution shows "Degradado" because of assistant spans (N3). The reason chart misses `UNVERIFIED_DATA`, `SOURCE_UNAVAILABLE`, `SCAN_REVIEW` and duplicates (N5) |
| **Retries** | `sync_source` span: requests, retries, 429s, logins, timeouts. `llm_run`: `retries`, `failed_attempts`. `provider_call`: `http_status_code`, `retry_after_s`, `fallback` | Agents table: "Reintentos · fallback" | **The biggest gap.** The trace pane shows no retry: sync spans are not in the instance trace. Ingestion shows no 429s per provider and no ERP sync rows |
| **Pending work** | `/queue`, `/alerts?status=open`, `/proposals?status=open`, `pending` and `open_alerts` in execution metrics | Panel "Atención", Revisión tabs, Alertas tab | The trace pane does not say what is pending on this case. "N propuestas" links to Definición instead of Revisión (N6) |

### By plane

| Plane | Dashboard today (`PlaneDashboards.tsx`) | Unused data the API already returns | Gaps |
|---|---|---|---|
| **Ingestion** | 5 cells (documents, OCR, cache, abstentions, cost) and a provider table (calls, tokens, errors, cost, p50/p95) | `traces` link on each row, `abstentions_by_field`, `steps[]`, `blocked`, `fallbacks` | No drill-down. No 429 count. No ERP sync rows. Cost reads "N sin precio" only when nothing is priced |
| **Agents** | 5 cells (calls, tokens, cache rate, first-try compile, cost), plus `by_role` and `by_rule` (rule links to the Rule screen) | `by_model`, `by_norm_rule`, `norms[]` (`seconds_to_active`), `per_hour[]`, `traces` links | No `by_model` table, although the rule asks for "by role, rule and model". No drill-down to the `llm_run` and its prompt. Helmcode is unpriced |
| **Execution** | 5 cells (runs, per second, escalated, alerts, "0 tokens · 0 €"), by outcome, by reason, per rule, per step | `rules[].instances`, `resolutions_by_author`, `resolution_p50_s`/`p95_s`, `traces` links | N3 (assistant spans inflate p95 to 8.2 s). N4 ("Evaluaciones" counts batch spans). N5 (reasons). N8 (the outcome total counts human resolutions: 31 for 30). N9. Outcome counts link to an unfiltered list |
| **All** | Polling every 10 s | `GET /events/stream` (SSE per plane and process) | **No SSE consumer in the frontend.** Nothing drills down to spans. The Panel's "Coste" card is ingestion only but reads as a total |

## 2. The story for the defense (about 2:50)

It replaces the CLI demo in step 3 of [defense.md](defense.md) (2:15-4:00). `make
trace-decision` stays as the fallback, and its saved outputs are in `demo-logs/defense/`.

**The case:** `scan_002.pdf`. It is a scan, so it has OCR evidence. The engine escalates
it, the assistant has left a proposal, and the manager resolves it live. The ERP sync of
its run has real retries: the challenge ERP returns `ORA-00600` on every 10th query and a
429 on bursts.

### A. Follow one decision (1:30)

| # | Time | Screen and click | What the jury sees (rubric item) | Endpoint |
|---|---|---|---|---|
| 1 | 0:00 | **Panel** `/processes/{P}`. Point at the three plane badges, then click "En revisión" | Three planes, all `ok`. 4 cases waiting for a person: 5 escalated, 1 already resolved (**pending work**) | `/summary`, `/health/planes` |
| 2 | 0:10 | **Revisión** → tab ESCALAR → `scan_002.pdf` | ESCALAR with its reason (in the 500 run, `MISSING_DATA: issuer_nif, iban`), decided by the engine (**status**) | `/queue`, `/instances/{id}`, `/instances/{id}/trace` |
| 3 | 0:20 | "Abrir documento", then click `total` and `iban` | The scan page with the box the OCR read, the value marked `unverified` and the empty IBAN (**evidence**) | `/document/locations`, `/document/pages/1` |
| 4 | 0:35 | "reglas" block, then the new version line, then click the rule that fired | R1 fired with its text; process **v1, published by Martín**, rules hash, rule code hash. On the Rule screen, its code and the compile trace (**versions**) | `/trace`, `/versions`, `/rules/{id}/trace` |
| 5 | 0:50 | "traza" block | `upload_document` about 1.2 s → `ocr` about 0.3 s (primary) and 0.8 s (secondary) → `run_process` → `decision` → `export_outcomes` 27 ms (**latency**) | `/trace` |
| 6 | 1:00 | The new "fuentes leídas" block | ERP sync `ok`: 31 requests, 3 retries, 429s (**errors and retries**). Say: "the ERP failed during the sync, the client retried, and the decision read a complete snapshot" | `/trace` (`sources_read`, B3) |
| 7 | 1:10 | The new "pendiente" block, then "Proponer" | An open assistant proposal. Say: "the assistant proposes, a person decides" | `/proposals?status=open` |
| 8 | 1:20 | Resolve with a reason ("IBAN confirmado por teléfono") | A new decision by **Martín**; the engine's stays in "histórico" (append-only). The export line changes | `POST /instances/{id}/resolve`, `/trace` |

### B. The three dashboards (0:50)

| # | Time | Screen and click | What the jury sees | Drill-down |
|---|---|---|---|---|
| 9a | 1:30 | Panel → Trazabilidad → **Ejecución** | 30 decided, "0 tokens · 0 €", outcomes add up to 30, escalations by reason, p95 per rule | Click the `evaluate_rule` row of R1 → the span drawer (F1) → one span with `instances`, `fired`, ms |
| 9b | 1:45 | **Lectura** | Documents, OCR calls, tokens and cost per provider, 429s, the ERP sync row with its retries | Click the Gemini or Helmcode row → the `provider_call` spans with `http_status_code` and tokens |
| 9c | 2:00 | **Agentes** | Tokens by role (normalizer, tester, compiler, assistant) and by model, one fallback, first-try compile rate | Click the compiler row → the `llm_run` span → the exact instructions, prompt and answer |

### C. Live (0:30)

| # | Time | Action | What the jury sees |
|---|---|---|---|
| 10 | 2:20 | Drop `scan_004.pdf` and `2026-01-12_P002.pdf` on the Panel, then "Ejecutar" | The live strip (F10) scrolls `upload_document → ocr → provider_call → run_process → decision`, one line per span, with the plane's colour. Dashboard counts change without a reload |

**Optional resilience beat** (+20 s, only if time allows): Ctrl+C on `make erp`, then
Fuentes → "Sincronizar". A `sync_source` error span appears in the strip, and the Lectura
badge turns "Degradado · sources down". Restart `make erp`, sync again, and it goes back
to `ok`. Do not click "Ejecutar" while the ERP is down: the cases would escalate
`SOURCE_UNAVAILABLE`.

**Demo data needed:** the seed in section 5, with `scan_002` escalated and an open proposal,
one resolution by Martín (`factura_41082`), one open alert, agent activity (one compiled
norm sentence plus one fallback), two PDFs held back for step 10, and `make erp` running.

## 3. Fixes before the story works

P0 blocks the story, P1 weakens it, P2 is polish. **Owners:** Backend (Martín or a backend
agent) and Carlos (frontend), following the owners in
[integration-status.md](integration-status.md).

### Backend

| id | P | Size | Fix | Done when |
|---|---|---|---|---|
| B1 | P0 | S | Move `suggest_escalation` and `propose_decision` to the agents plane in `traces/service.py` `PLANES` (N3, BE2). Update the plane table in ADR 0018 (line 168) | After the seed, `/health/planes` shows execution `ok` and its p95 is under 5 s. `test_planes.py` is green |
| B2 | P0 | S | In `_outcomes`, count only the **latest** decision per instance (N8, BE3). Add `escalation_reasons: {code: n}` over the instances whose latest decision is ESCALAR, grouped with the existing `decisions/runs.reason_codes`, plus `OTHER` (N5) | `decisions_by_outcome` adds up to 30 and matches `/summary.by_decision`. `escalation_reasons` adds up to `escalated`. A test with one resolved case |
| B3 | P0 | S | Add `sources_read` to `InstanceTrace`: the latest `sync_source` span of each source before the latest decision, with `status`, `requests`, `retries`, `rate_limited`, `timeouts` and `duration_ms`. This is the logic of `tools/trace_decision.py:159`, moved into the API | `/instances/{scan_002}/trace` lists `erp` with `retries > 0`. A unit test |
| B4 | P1 | S | Ingestion metrics: `rate_limited` per provider (`provider_call` spans with `http_status_code = 429`), and `sources[]` per source (syncs, errors, requests, retries, `rate_limited`, p95, `traces` link) from the `sync_source` spans | `/metrics/ingestion` has an `erp` row with retries and a 429 column per provider. The schema is typed |
| B5 | P1 | S (config) | Set `TRACEPAY_HELMCODE_BILLING_MODE` in the demo `.env` to the real contract (`included`, or `metered` with its rates). **Martín decides.** Recommendation: `included`, if the hackathon covers Helmcode. It is honest and turns "sin precio" into "incluido" | `unpriced_requests` is 0 in both planes. `included_requests > 0` |

### Frontend

| id | P | Size | Fix | Done when |
|---|---|---|---|---|
| F1 | P0 | M | **Span drawer.** Every dashboard row with a `traces` link, and every headline cell, opens a side panel with `GET <traces>`. Each span reuses `SpanBlock` from `TracePane` and opens its tree (`/traces/{trace_id}`). An `llm_run` shows its instructions, prompt, answer and tokens. Add `listSpans(url)` to `api/live.ts` | From each of the three dashboards, one click on a number reaches a span with its data |
| F2 | P0 | S | Execution table: "Evaluaciones" reads `rules[].instances` (N4, FE4). `formatMs` rounds to one decimal (N9, FE3), fixing every caller | "Evaluaciones" is 30 per rule with 30 invoices. No long decimals anywhere |
| F3 | P0 | S | The reason chart reads `escalation_reasons` (B2). An outcome count links to Instances filtered by that decision (a `?d=` parameter read on load) | The reasons add up to the escalated count. Clicking "10 NO_PAGAR" lists 10 cases |
| F4 | P0 | S | Cost (N7): `cost()` shows the known amount **and** "N sin precio" together, never 0. The Panel's "Coste" card becomes "Coste de lectura" (ingestion only), or three chips, one per plane. Keep USD: there is no exchange rate in the system, and inventing one is worse than the currency | With unpriced Helmcode calls, no screen shows `0,00` |
| F5 | P0 | S | Trace pane, version line: `vN`, publisher and date from `/versions` (by `version_id`), the rules hash, and each rule's code hash in the "reglas" block | Step 4 of the story shows "v1 · Martín · cf741d48f1e4" |
| F6 | P0 | S | Trace pane, two blocks. "Fuentes leídas" from `sources_read` (B3). "Pendiente": whether a person is waiting, the open proposal, and the alerts of this instance (`/alerts` filtered by `instance_id`), each linking to Revisión with `?i=` | Steps 6 and 7 of the story work on `scan_002` |
| F7 | P0 | S | Atención: "N propuestas" links by proposal kind. A decision goes to Revisión with the case open; a rule or context change goes to Definición (N6, FE2) | The seeded `scan_002` proposal opens in Revisión |
| F8 | P1 | S | Agents: add the `by_model` table and `norms[]` (tokens, `seconds_to_active`) | The Agentes tab shows role, rule **and** model |
| F9 | P1 | S | Ingestion: a 429 column, the `sources[]` rows (B4) and `abstentions_by_field` | The ERP row shows its retries and 429s |
| F10 | P1 | M | **SSE.** A `useLiveSpans(plane?, processId)` hook on `EventSource('/events/stream?...')`. Each event invalidates that plane's metrics and the summary, and polling stays as the fallback. A live strip on the Panel shows the last 6 spans (time, plane, step, status, ms). Check that the Vite proxy streams without buffering | During step 10, the strip moves and the counts change within 2 s, with no reload |
| F11 | P1 | S | Keep the Panel's first screen for the story. Move the "Models and execution effort" form to process settings (N2, FE6) and cut the description to two lines (N1) | Atención, metrics and the plane badges fit without scrolling |
| F12 | P2 | S | Health badges for all three planes in the dashboard header, as a dot on each segment | You can see the other planes' health without switching tabs |

**Out of scope here:** N10 (landing figures), N11 (Spanish rule texts), N12 (process list
chips). They matter for the product, not for this story.

**Order:** B1, B2 and B3 first (one backend PR, about 2 h). Then F2 to F7 (one PR, about
3 h), F1 (about 2 h) and F10 (about 2 h). B4 with F9, and F8 and F11, only if time allows.

## 4. Optional extras (only if cheap)

| Extra | Cost | Value for the jury | Recommendation |
|---|---|---|---|
| Live strip from `/events/stream` | Included in F10 | High: it shows the system working, not a static screen | Do it (F10) |
| "Descargar traza" button in the trace pane (the `/instances/{id}/trace` JSON, or the `make trace-decision` text) | S | Medium: a per-invoice audit file an auditor can keep | Do it if F5 and F6 are done |
| Per-batch audit page (`tools/audit_page/build.py`) | 0 (it exists) | Medium: the PDF, decision, rules and source rows for all 500 invoices, offline | Mention it with one screenshot |
| Phoenix view (`docker compose --profile observability up -d`, `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:6006`) | S (config) | Low to medium: the same spans in a standard OTel tool. It proves the mirror in ADR 0018, but it adds nothing the console lacks | One screenshot on a slide, not live |
| Stacked bar "tokens by plane" (never one total) | S | Medium: it makes "deciding costs 0" visible at a glance | Only after F1 to F10 |

## 5. Demo data script

Base: `local-seed.sh` in the `main-local` worktree (a fresh `trace_local_test`, frozen pack
v1 published, workbook with cut-off 2026-09-18, ERP sync, 30 invoices with 5 scans, one
run, one resolution, one assistant proposal and one stale alert; it takes 1:52). Result
from the review: 5 ESCALAR, 10 NO_PAGAR and 15 PAGAR.

**Changes:**

| # | Change | Why |
|---|---|---|
| 1 | The ERP is not started by `local-stack.sh`. Start it by hand: `ERP_PORT=8309 make erp` (no `--rapido`). The seed first checks `curl -sf localhost:8309` and stops with "run make erp first" | Martín's rule. The real latency, `ORA-00600` and 429 give the sync real retries |
| 2 | Keep the `factura_41082` resolution and the `scan_002` proposal. Never resolve `scan_002` | `resolutions_by_author` is not empty, and step 8 happens live |
| 3 | After the run, `POST /processes/$P/norm` with one sentence (for example "Invoices above 50,000 EUR need a second approval"). Wait until `GET /processes/$P/rules?status=compiling` is empty, and never activate the rule | The agents plane gets normalizer, tester and compiler `llm_run` spans with tokens. Decisions do not change. Runs return 409 while a rule compiles, so wait |
| 4 | Run `make demo-llm-down` with `TRACE_DATABASE_URL` pointing at `trace_local_test` | One real fallback (`failed_attempts`) in the agents plane |
| 5 | Stale alert: the seed writes `logs/erp_lote2.csv` and **pauses** with "restart make erp with `--lote2 logs/erp_lote2.csv`, then press Enter", then syncs | The ERP is manual, so the seed cannot restart it. It leaves one open alert. Skip it with `ALERT=0` if defense step 7 raises the alert live |
| 6 | Hold back `scan_004.pdf` and `2026-01-12_P002.pdf` | Step 10 (live upload and run) |
| 7 | Close with a check: every line below must pass, or the seed prints the failure | The dashboards show meaningful numbers before the jury arrives |

**Seed check** (after B1-B3):

| Call | Expected |
|---|---|
| `/health/planes` | three planes `ok`, or ingestion `degraded` only while the ERP is down |
| `/processes/$P/metrics/execution` | `decisions_by_outcome` adds up to 30; `escalation_reasons` adds up to `escalated`; `resolutions` = 1; `open_alerts` = 1 (or 0 with `ALERT=0`) |
| `/processes/$P/metrics/ingestion` | 30 files; `ocr_calls > 0`; at least one provider row with tokens; an `erp` source row with `retries > 0` (B4) |
| `/processes/$P/metrics/agents` | the roles normalizer, tester, compiler and assistant; `fallbacks >= 1` |
| `/instances/{scan_002}/trace` | ESCALAR; the OCR spans; `sources_read.erp.retries > 0` |
| `/processes/$P/proposals?status=open` | 1 (`scan_002`) |

**Before the jury:** run the seed about 15 minutes before and open the Panel in the demo
browser. Rehearse once with the two held-back PDFs, then reseed: the OCR journal may
replay them. Replays cost 0 tokens, which is also worth saying.
