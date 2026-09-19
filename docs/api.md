> Configuration publication now follows [process versions](process-versions.md).
> Rule activation and retirement stage edits; manager-approved draft publication makes
> them effective. Compilation no longer auto-activates rules.

# API for the console

The backend is the contract; this page is the map. Live and exact: `make setup`, then
http://localhost:8000/docs (OpenAPI). Every response is JSON in English; errors are
`{"code", "message"}`. Identify with `X-User-Id` (from `POST /login`); resolving,
activating rules, document extraction and source uploads need it. CORS is open.

## One screen, one call

| Screen | Call | Notes |
|---|---|---|
| Processes | `GET /processes` | id, name, description |
| Process page | `GET /processes/{id}/summary` | instances, `by_status`, `by_decision`, `queue`, `resolved`, rules with `fires`, current `sources`, `last_run_at` |
| Process setup | `GET /processes/{id}` | decision types (priority, default, requires_human), symbols and optional `decision_review` guidance |
| Extraction plan | `GET /processes/{id}/extraction-plan` | current fields, enforced rule references, warnings and content fingerprint; [configuration and caching](dynamic-extraction.md) |
| Instances | `GET /processes/{id}/instances?status=&decision=&q=` | each row: latest `decision`, `author` (`engine` or a name), `reason`, `decided_at` |
| Queue | `GET /processes/{id}/queue?type=` | human-requiring outcomes and pending reviewer disagreements; `type` filters the current outcome |
| Instance | `GET /instances/{id}` | symbols `{name: {value, origin}}`, decision history, `review_pending`, append-only `reviews` with recommendations and reasoning, events |
| Invoice viewer | `GET /instances/{id}/file` | the PDF bytes, `Content-Disposition: inline` |
| Reading evidence | `GET /instances/{id}/document` | what extraction read, field by field |
| Instance trace | `GET /instances/{id}/trace` | reading/provider spans, stored evidence, decisions and the current export result |
| Provider activity | `GET /traces?process_id={id}&name=provider_call` | model, HTTP status, request fingerprint, replay/network outcome and reported tokens |
| Metrics | `GET /processes/{id}/metrics` | stage timings, agent `llm` usage and separate reader `providers` totals; replay does not count as network usage |
| Assistant | `GET /instances/{id}/suggestion` | decision, reasoning and a proposed rule. 409 if not escalated, 502 if the model failed |
| Resolve | `POST /instances/{id}/resolve` `{decision, reason}` | adds a decision; the engine's stays |
| Rules | `GET /processes/{id}/rules?status=` | compiling, draft, active, blocked, retired |
| Rule | `GET /rules/{id}` | `code`, `tests`, `report` (`valid`, `tests`, `discrepancies`, `attempts`, `reviews`; `needs_data` when blocked) |
| Norm | `POST /processes/{id}/norm`, `GET /processes/{id}/norm-rules` | the client's norm split into norm rules, each with its rules |
| Rule lifecycle | `POST /processes/{id}/rules` (compiles in the background), `POST /rules/{id}/compile`, `GET /rules/{id}/impact`, `POST /rules/{id}/activate`, `POST /rules/{id}/retire` | impact = `unchanged`, `changes`, `conflicts`; activate/retire need a manager |
| Learning | `POST /processes/{id}/learning`, `GET /processes/{id}/learning` | Manager-only analysis and proposed norms; [full flow](learning.md) |
| Norm proposal | `GET /norm-proposals/{id}`, `POST .../validate`, `POST .../approve`, `POST .../reject` | Isolated previews; explicit manager adoption with a validation ID |
| Sources | `GET /processes/{id}/sources` | current load per source: rows count, origin, `loaded_at`, and from its latest sync `status` (`ok`/`down`, null if never synced), `error`, `checked_at`. A `down` load is not read by runs until a sync succeeds (ADR 0028) |
| Source rows | `GET /processes/{id}/sources/{name}` | same plus `data` |
| Sync the ERP | `POST /processes/{id}/sources/{name}/sync`, `GET .../diff` | 502 when the download fails or the rows miss a canonical field (`processes/<pack>/schema.json`); nothing is written. Runs sync live sources themselves |
| Audit trail | `GET /processes/{id}/events?step=&instance_id=&limit=` | newest first. Steps: `decision`, `resolution`, `ingest_document`, `compile_rule`, `normalize_norm`, `suggest_escalation`, `sync_source`, `sync_source_failed` |
| Findings | `GET /processes/{id}/findings` | past decisions a later rule says were wrong |
| Alerts | `GET /processes/{id}/alerts?status=open\|acknowledged\|resolved` | past decisions that newer data or rules would decide otherwise (ADR 0026): `before`, `after`, `trigger` (`source_sync` with the rows involved, or `rule_change` with rule ids), `evidence` (reason codes before and after), `acknowledged_by`, `resolved_by_decision_id`. Raised after a sync that changes rows and after a version is published |
| Acknowledge | `POST /alerts/{id}/ack` `{note?}` | needs `X-User-Id`; 409 if already acknowledged. Act with Resolve or Reprocess; the later decision marks the alert `resolved` |
| Run | `POST /processes/{id}/run` | first syncs every live source (`sync_before_run` in the pack's `schema.json`), then decides every PENDING instance with symbols; `down_sources` (`{name: why}`, omitted when none) lists sources whose sync failed: their rules do not run and those cases escalate `SOURCE_UNAVAILABLE: <source>` unless a rule that ran already rejects (ADR 0028); 409 while a rule is `compiling` or when no rule is `active`/`blocked` |
| Reprocess | `POST /processes/{id}/reprocess?dry_run=` (optional `{"names": [...]}`) | decides the DECIDED instances again with the current rules and sources; appends a new engine decision only where it changes; an instance a person decided last is never touched and comes back in `conflicts`. Syncs live sources first like Run (`down_sources`), except with `dry_run=true`. Same 409 as Run |
| Export | `GET /processes/{id}/export` | `outcomes.jsonl`; 409 while anything is undecided or awaiting reviewer-requested approval. One batch only: `make export-batch` (`docs/runbook-batch2.md`) |
| Upload | `POST /processes/{id}/files` (multipart `file`) | stores the PDF and fills symbols from the current extraction plan; existing invoice defaults are retained |
| Workbook | `POST /processes/{id}/sources/workbook` (multipart `file`, optional `cut_off_date`) | appends supplier/order snapshots; never replaces ERP |
| Re-extract | `POST /instances/{id}/extract` (JSON `{}` or reader options) | pending documents only; current symbol schema, rules and source snapshots, preserved evidence; 409 if already decided |
| Locate readings | `GET /instances/{id}/document/locations` | needs `X-User-Id`; source quotes and normalized rectangles per candidate, including dynamic fields; see [PDF traceability](ingestion/pdf-traceability.md) |
| Original page | `GET /instances/{id}/document/pages/{page}` | needs `X-User-Id`; PNG of the original PDF page (one-based), including its rotation; 404 for a missing page |
| Users | `GET /users`, `POST /users`, `POST /login`, `GET /me` | roles `manager`, `operator` |
| Metrics | `GET /processes/{id}/metrics?since=` | runs, step durations, LLM tokens by model and role, outcomes (unchanged) |
| Monitoring: ingestion | `GET /processes/{id}/metrics/ingestion?since=`, `GET /metrics/ingestion` (all processes) | `files`, `files_per_second`, `pages`, `ocr_calls`, `vision_calls`, `judge_calls`, `focused_reads`, `cache_hits`, `abstentions`, `abstentions_by_field`, `steps[]` |
| Monitoring: agents | `GET /processes/{id}/metrics/agents?since=`, `GET /metrics/agents` | tokens in/out/cached, requests, retries, fallbacks, truncations `by_model`, `by_role`, `by_rule`, `by_norm_rule`, `by_use_case`; `per_hour[]`; `compile` (success rate, attempts); `norms[]` (tokens, `seconds_to_active`) |
| Monitoring: execution | `GET /processes/{id}/metrics/execution?since=`, `GET /metrics/execution` | `runs`, `instances_per_second`, `rules[]` (p50/p95 per rule), `decisions_by_outcome`, `failures`, `escalated`, `pending`, `resolutions_by_author`, `resolution_p50_s`/`p95_s`, `open_alerts` |
| Plane health | `GET /health/planes` | per plane `status` `ok`/`degraded`/`down`, `error_rate`, `p95_ms`, `reason` (thresholds `TRACE_HEALTH_*`); ingestion is at least `degraded` (`sources down: <process>:<source>`) while a source's latest sync in the window failed |
| Live feed | `GET /events/stream?plane=&process_id=&after=` | server-sent events: `event` = plane, `id` = span id, `data` = a span as in `GET /traces`; `: ping` every idle second. Use `EventSource` |

## Shapes worth knowing

- **Instance status** is `PENDING` or `DECIDED`. The queue and `summary.queue` include
  decisions whose type has `requires_human` and cases with `review_pending: true`.
  Optional review never changes the engine outcome or instance status. Its configuration,
  approval flow, fallback and export semantics are in [decision-review.md](decision-review.md).
- **A decision row** has `decision`, `author`, `reason`, `results` and `created_at`. The
  engine's `results` list one entry per rule: `rule_id`, `hash`, `fires`, `reason`. Join
  `rule_id` with `GET /processes/{id}/rules` for the text. A person's row has no results.
- **Escalation reasons** from the engine start with `RULE_ERROR <id>:` or `RULE_CONFLICT:`
  when a rule could not run or two outcomes tied, `SOURCE_UNAVAILABLE: <source>` when a
  source the case needed was down (ADR 0028); otherwise it is the firing rule's reason
  code (e.g. `IMPOSSIBLE_DATE 2026-02-31`, several joined by ` | `), never its text.
- **Symbols** are stored as `{value, origin}`; `origin` says where extraction read it.
- **Names** (`instance.name`) are the exact file names, accents included; they are the
  `file_id` of the export.
