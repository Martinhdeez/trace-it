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
| Sources | `GET /processes/{id}/sources` | current load per source: rows count, origin, `loaded_at` |
| Source rows | `GET /processes/{id}/sources/{name}` | same plus `data` |
| Sync the ERP | `POST /processes/{id}/sources/{name}/sync`, `GET .../diff` | |
| Audit trail | `GET /processes/{id}/events?step=&instance_id=&limit=` | newest first. Steps: `decision`, `resolution`, `ingest_document`, `compile_rule`, `normalize_norm`, `suggest_escalation`, `sync_source`, `sync_source_failed` |
| Findings | `GET /processes/{id}/findings` | past decisions a later rule says were wrong |
| Run | `POST /processes/{id}/run` | decides every PENDING instance with symbols; 409 while a rule is `compiling` or when no rule is `active`/`blocked` |
| Reprocess | `POST /processes/{id}/reprocess?dry_run=` (optional `{"names": [...]}`) | decides the DECIDED instances again with the current rules and sources; appends a new engine decision only where it changes; an instance a person decided last is never touched and comes back in `conflicts`. Same 409 as Run |
| Export | `GET /processes/{id}/export` | `outcomes.jsonl`; 409 while anything is undecided or awaiting reviewer-requested approval. One batch only: `make export-batch` (`docs/runbook-batch2.md`) |
| Upload | `POST /processes/{id}/files` (multipart `file`) | stores the PDF and fills declared invoice-payment symbols from verified readings |
| Workbook | `POST /processes/{id}/sources/workbook` (multipart `file`, optional `cut_off_date`) | appends supplier/order snapshots; never replaces ERP |
| Re-extract | `POST /instances/{id}/extract` (JSON `{}` or reader options) | pending documents only; current snapshots, preserved evidence; 409 if already decided |
| Users | `GET /users`, `POST /users`, `POST /login`, `GET /me` | roles `manager`, `operator` |

## Shapes worth knowing

- **Instance status** is `PENDING` or `DECIDED`. The queue and `summary.queue` include
  decisions whose type has `requires_human` and cases with `review_pending: true`.
  Optional review never changes the engine outcome or instance status. Its configuration,
  approval flow, fallback and export semantics are in [decision-review.md](decision-review.md).
- **A decision row** has `decision`, `author`, `reason`, `results` and `created_at`. The
  engine's `results` list one entry per rule: `rule_id`, `hash`, `fires`, `reason`. Join
  `rule_id` with `GET /processes/{id}/rules` for the text. A person's row has no results.
- **Escalation reasons** from the engine start with `RULE_ERROR <id>:` or `RULE_CONFLICT:`
  when a rule could not run or two outcomes tied; otherwise it is the firing rule's reason
  code (e.g. `IMPOSSIBLE_DATE 2026-02-31`, several joined by ` | `), never its text.
- **Symbols** are stored as `{value, origin}`; `origin` says where extraction read it.
- **Names** (`instance.name`) are the exact file names, accents included; they are the
  `file_id` of the export.
