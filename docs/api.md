# API for the console

The backend is the contract; this page is the map. Live and exact: `make setup`, then
http://localhost:8000/docs (OpenAPI). Every response is JSON in English; errors are
`{"code", "message"}`. Identify with `X-User-Id` (from `POST /login`); only resolving and
activating rules need it. CORS is open.

## One screen, one call

| Screen | Call | Notes |
|---|---|---|
| Processes | `GET /processes` | id, name, description |
| Process page | `GET /processes/{id}/summary` | instances, `by_status`, `by_decision`, `queue`, `resolved`, rules with `fires`, current `sources`, `last_run_at` |
| Process setup | `GET /processes/{id}` | decision types (priority, default, requires_human) and symbols |
| Instances | `GET /processes/{id}/instances?status=&decision=&q=` | each row: latest `decision`, `author` (`engine` or a name), `reason`, `decided_at` |
| Queue | `GET /processes/{id}/queue?type=` | instances whose latest decision needs a person |
| Instance | `GET /instances/{id}` | symbols `{name: {value, origin}}`, decision history (each engine row has `results` per rule), events |
| Invoice viewer | `GET /instances/{id}/file` | the PDF bytes, `Content-Disposition: inline` |
| Reading evidence | `GET /instances/{id}/document` | what extraction read, field by field |
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
| Run | `POST /processes/{id}/run` | decides every PENDING instance with symbols |
| Export | `GET /processes/{id}/export` | `outcomes.jsonl`; 409 while anything is undecided |
| Upload | `POST /processes/{id}/files` (multipart `file`) | stores the PDF and creates the instance |
| Users | `GET /users`, `POST /users`, `POST /login`, `GET /me` | roles `manager`, `operator` |

## Shapes worth knowing

- **Instance status** is `PENDING` or `DECIDED`. There is no review state: what needs a
  person is a *decision* whose type has `requires_human` (ADR 0016). The queue and
  `summary.queue` are exactly those.
- **A decision row** has `decision`, `author`, `reason`, `results` and `created_at`. The
  engine's `results` list one entry per rule: `rule_id`, `hash`, `fires`, `reason`. Join
  `rule_id` with `GET /processes/{id}/rules` for the text. A person's row has no results.
- **Escalation reasons** from the engine start with `RULE_ERROR <id>:` or `RULE_CONFLICT:`
  when a rule could not run or two outcomes tied; otherwise it is the firing rule's reason.
- **Symbols** are stored as `{value, origin}`; `origin` says where extraction read it.
- **Names** (`instance.name`) are the exact file names, accents included; they are the
  `file_id` of the export.
