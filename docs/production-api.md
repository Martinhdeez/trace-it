# Trace-it production API

## URLs and quick start

- Interactive documentation: https://gex-dashboard.hopto.org/nexia/trace-it/api/docs
- Complete OpenAPI 3.1 contract: https://gex-dashboard.hopto.org/nexia/trace-it/api/openapi.json
- This guide: https://gex-dashboard.hopto.org/nexia/trace-it/api/guide
- Base URL: https://gex-dashboard.hopto.org/nexia/trace-it/api

The documentation is public. Reading or modifying production data requires credentials.
In Swagger, click **Authorize**, enter the API token (without the word `Bearer`), then use
**Try it out**. Ask the deployment owner for the token; it is not published in this guide.
Swagger does not persist authorization after a page reload.

```bash
export TRACE_API_BASE='https://gex-dashboard.hopto.org/nexia/trace-it/api'
read -rs TRACE_API_TOKEN  # enter the token, then press Enter
export TRACE_API_TOKEN
curl --fail-with-body "$TRACE_API_BASE/processes" \
  -H "Authorization: Bearer $TRACE_API_TOKEN"
curl --fail-with-body "$TRACE_API_BASE/me" \
  -H "Authorization: Bearer $TRACE_API_TOKEN"
```

The same administrative Bearer token works on the business endpoints in the OpenAPI contract, including
uploads, process creation, rule compilation, publishing, running decisions, source sync,
learning, proposals, configuration, traces, metrics and exports. It acts as the dedicated
**Trace-it API** manager (`trace-it-api@localhost`). No login or `X-User-Id` is needed;
`X-User-Id` cannot override a Bearer caller's identity. This is a shared administrative
credential, not a separate identity for each person. Application permissions, validation,
revision checks and workflow prerequisites still apply.

Mail ingestion is an exception: `/mail-ingestion/{process_id}` requires its own mailbox
service token, limited to a single assigned process. Never configure the worker with the
administrative token. See [mail-ingestion.md](mail-ingestion.md) for gathering settings,
read-only IMAP, recovery and disabled installation.

Existing browser access continues to use HTTP Basic at the proxy, with `X-User-Id` for
application actions. The database administration API ALWAYS requires Bearer, even for a
caller with valid Basic credentials. Incorrect or disabled Bearer tokens return 401 and
never fall back to browser identity. With no configured token, Bearer access is disabled.

Use HTTPS. The production owner chose a short shared token; anyone who knows or guesses
it can read and change this application's data. The token is not protection from its own
holders. Rotating it means changing `TRACE_API_TOKEN` in the private runtime environment
and recreating the backend. Never put credentials in URLs, Git, screenshots or shared logs.

## Business operations

Prefer business endpoints for normal work: they preserve application validation, evidence,
process versions and append-only history. Expand an operation in Swagger for the precise
request, response, required parameters and schemas. The generated catalog below lists all
operations; OpenAPI is the authoritative, current contract.

Typical sequence:

1. `GET /processes`, then `GET /processes/{id}` and `/summary` to inspect a process.
2. Create a process with `POST /processes/definition`, or use `/process-drafts` for discovery.
3. Inspect extraction settings; upload documents with `POST /processes/{id}/files`.
4. Add rules or a norm, review compilation, edit the process draft, validate and publish it.
5. `POST /processes/{id}/run` decides pending instances. Reprocess is an explicit operation.
6. Read instances, decisions, queues and traces; resolve escalations through the business API.
7. Export outcomes with `GET /processes/{id}/export` when the workflow permits it.

```bash
# Upload one document. The API selects the published process configuration.
curl --fail-with-body "$TRACE_API_BASE/processes/1/files" \
  -H "Authorization: Bearer $TRACE_API_TOKEN" -F 'file=@invoice.pdf'

# Run pending instances (this modifies production and may call configured providers).
curl --fail-with-body -X POST "$TRACE_API_BASE/processes/1/run" \
  -H "Authorization: Bearer $TRACE_API_TOKEN"

# Read the full trace of one instance.
curl --fail-with-body "$TRACE_API_BASE/instances/1/trace" \
  -H "Authorization: Bearer $TRACE_API_TOKEN"
```

Processing and agent operations can take minutes and use paid providers. An HTTP timeout
on a mutation does not prove that it failed: inspect its current state before retrying.
Read Swagger's body schema before calling an action; not every POST uses the same body.
SSE (`GET /events/stream`) works with `curl -N -H "Authorization: Bearer ..."`; browser
EventSource cannot supply custom headers, so use a fetch-based SSE client.

## Database administration

The `/db` endpoints expose all registered Trace-it application tables in PostgreSQL's
`public` schema. They do not expose arbitrary SQL, DDL, server settings, credentials,
PostgreSQL system catalogs, migration control, other schemas/databases, shell commands or
host files. The table list is an application allowlist, not user-provided SQL.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /db/tables | Tables, primary keys and write capability |
| GET | /db/tables/{table}/schema | Columns, defaults, generated values, keys, checks and indexes |
| GET | /db/tables/{table}/rows | Filtered, paginated rows and etags |
| GET | /db/tables/{table}/row?key={...} | One row by its complete primary key |
| GET | /db/tables/{table}/export | A page of raw values as JSONL |
| POST | /db/tables/{table}/rows | Create one row |
| PATCH | /db/tables/{table}/row | Update one row with a matching etag |
| DELETE | /db/tables/{table}/row | Delete one row with a matching etag |

`events` and `database_api_changes` are readable but cannot be inserted, edited or deleted
through the database API. The API manager account is also reserved. Other registered
application tables, including historical business records, are writable. Direct writes
are administrative overrides: they bypass business workflows and ORM-only validation,
and do not automatically recompile rules, publish versions, reprocess decisions, sync
sources or invalidate document caches. Use business endpoints unless a direct correction
is intentional. PostgreSQL not-null, unique, check and foreign-key constraints still apply.
Deletions do not disable constraints or request cascades; any schema-defined cascade still
applies. Take a backup before making substantial corrections.

### Discover and read

```bash
curl --fail-with-body "$TRACE_API_BASE/db/tables" \
  -H "Authorization: Bearer $TRACE_API_TOKEN"
curl --fail-with-body "$TRACE_API_BASE/db/tables/users/schema" \
  -H "Authorization: Bearer $TRACE_API_TOKEN"
curl --fail-with-body --get "$TRACE_API_BASE/db/tables/users/rows" \
  -H "Authorization: Bearer $TRACE_API_TOKEN" \
  --data-urlencode 'filters={"role":"operator"}' --data-urlencode 'limit=50'
curl --fail-with-body --get "$TRACE_API_BASE/db/tables/users/row" \
  -H "Authorization: Bearer $TRACE_API_TOKEN" --data-urlencode 'key={"id":123}'
```

Filters are a JSON object of exact column-value equalities combined with AND; null means
SQL IS NULL. No filter expression, function, wildcard column or raw SQL is accepted.
Responses contain `rows`, `limit`, `offset`, and `next_offset`. Follow `next_offset` until
null. Each row contains `key`, `values`, and `etag`. Ordering is by the complete primary
key; the maximum page size is 200 and large pages stop at approximately 48 MiB. An individual
row over that budget returns 413. Pages are separate reads, not a consistent snapshot:
concurrent writes can move offsets. For a full consistent PostgreSQL backup, use pg_dump.
JSONL exports return plain row values and `X-Next-Offset` if another page exists.

Column encoding: integers/booleans/text/null use JSON native types; JSON/JSONB keeps its
structure; dates/timestamps use ISO 8601; exact decimals and UUIDs are strings; binary
`bytea` values use `{"$base64":"..."}`. Use the same representation for writes. Inspect
`/schema` for required fields and defaults. Database defaults apply; Python/ORM defaults
do not. Omit generated columns. Partial updates leave omitted columns unchanged; explicit
null writes null. Primary keys cannot be changed.

### Create, update and delete

```bash
curl --fail-with-body -X POST "$TRACE_API_BASE/db/tables/users/rows" \
  -H "Authorization: Bearer $TRACE_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"values":{"name":"Integration operator","email":"operator@example.com","role":"operator"},"reason":"Create integration operator"}'
```

Save the returned `key` and `etag`. For the following examples replace 123 and
`<etag-from-the-latest-read>` with the actual values:

```bash
curl --fail-with-body -X PATCH "$TRACE_API_BASE/db/tables/users/row" \
  -H "Authorization: Bearer $TRACE_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"key":{"id":123},"values":{"name":"Updated operator"},"expected_etag":"<etag-from-the-latest-read>","reason":"Correct display name"}'

curl --fail-with-body -X DELETE "$TRACE_API_BASE/db/tables/users/row" \
  -H "Authorization: Bearer $TRACE_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"key":{"id":123},"expected_etag":"<etag-from-the-latest-read>","reason":"Remove unused operator"}'
```

Writes require a nonempty reason (up to 1,000 characters); updates and deletions require
the complete primary key and the latest SHA-256 row etag. Composite keys are JSON objects
containing every key column. The server locks the row and returns 409 on a stale etag.
Read again and reconsider the correction before retrying. Each successful write returns
`change_id`; its before/after values, key, operation, reason and shared actor are committed
in `database_api_changes` in the same transaction. If auditing fails, the change rolls back.
A delete response contains the removed row. One request changes one row, not a bulk filter.

The database API body limit is 2 MiB. Business document uploads retain their own limits.
Statements time out after 10 seconds and lock waits after 3 seconds. Error responses omit
SQL and database connection details. 401 = missing/invalid token; 403 = reserved resource;
404 = unknown table/row; 409 = constraint or etag conflict; 413 = size limit; 422 = invalid
input; 503 = database unavailable or timed out. Business errors retain their existing
`{"code","message"}` format; framework/admin errors use `{"detail":...}`.

## Isolation and operations

The backend runs as a non-root container with a read-only root filesystem, dropped Linux
capabilities, no Docker socket or host project mounts, a read-only OCR model mount, and a
Trace-it-only data volume. PostgreSQL is not published to the host network. The API token
has no meaning on other applications, Caddy administration, the ERP login, SSH or Docker.
The proxy only accepts Bearer for Trace-it's `/api/` path; the web interface remains Basic.
Public docs contain the contract and examples, not production records or credentials.

When Bearer access is enabled, caller-selected local/compatible model URLs must match the
operator-configured endpoints. OCR model paths must remain under the deployment's model
directory. These checks also apply to direct JSON snapshot writes and execution, preventing
API callers from redirecting configured credentials to arbitrary model servers or choosing
host paths. Approved provider integrations and the configured ERP remain part of normal
Trace-it operation. Rule code still runs through the existing constrained rule runner.

The production runtime uses `trace_app`, a non-superuser PostgreSQL role with no role/database
creation or replication privileges, only DML on registered application tables, sequence
access, and read/insert permission for audit tables. It cannot run migrations or read server
files. Migration and backup credentials stay in the operator's private Compose environment,
not in the running backend. `TRACE_API_TOKEN` stays in the private runtime environment.

Deployment procedure (operator only): pull dev, run make check against an isolated test
database, build both production images with their Git revision labels, back up production,
run Alembic with the database owner, provision the restricted runtime role using
`python -m app.features.database_api.provision` with `TRACE_APP_DATABASE_PASSWORD` supplied
privately, then set `TRACE_DATABASE_USER=trace_app` and `TRACE_DATABASE_PASSWORD` in private
Compose configuration. Recreate backend/frontend, verify `/ready`, Basic browser access,
Bearer reads/writes and rejection tests. Preserve the previous image identifiers for code
rollback. Never restore an older database automatically. A token rotation requires backend
recreation, not only a container restart.

Schema migration 0017 is additive. A code rollback can leave its audit table and manager in
place. Future deployments must run migrations with the owner, then refresh grants for new
application tables before starting the restricted runtime. The checked-in deploy script
does this when `TRACE_DATABASE_USER=trace_app` is configured.

## Complete endpoint catalog

The following catalog is generated from this release's OpenAPI contract. Swagger includes
all request/response schemas and examples and is updated together with the deployed code.

<!-- endpoint-catalog -->

- `GET /health` — Health
- `GET /ready` — Ready
- `GET /processes/{process_id}/gathering` — Read the process gathering email
- `PUT /processes/{process_id}/gathering` — Assign the supported gathering email exclusively
- `GET /processes/{process_id}/mail-ingestion` — Mail provenance and processing status
- `GET /mail-ingestion/{process_id}` — Scoped worker state and protocol version
- `POST /mail-ingestion/{process_id}/initialize` — Persist the first-activation UID boundary
- `POST /mail-ingestion/{process_id}/discover` — Persist discovered work and cursor atomically
- `POST /mail-ingestion/{process_id}/poll-failure` — Record bounded polling failure/backoff
- `POST /mail-ingestion/{process_id}/claim` — Reserve recoverable work
- `PUT /mail-ingestion/{process_id}/messages/{message_id}/manifest` — Save bounded MIME metadata
- `PUT /mail-ingestion/{process_id}/messages/{message_id}/attachments/{attachment_id}` — Import a validated PDF
- `POST /mail-ingestion/{process_id}/messages/{message_id}/attachments/{attachment_id}/failure` — Record attachment rejection
- `POST /mail-ingestion/{process_id}/messages/{message_id}/finish` — Evaluate only owned imports
- `POST /mail-ingestion/{process_id}/messages/{message_id}/failure` — Record retryable or terminal failure
- `GET /db/tables` — Tables
- `GET /db/tables/{table_name}/schema` — Schema
- `GET /db/tables/{table_name}/rows` — Rows
- `POST /db/tables/{table_name}/rows` — Create
- `GET /db/tables/{table_name}/row` — Row
- `PATCH /db/tables/{table_name}/row` — Update
- `DELETE /db/tables/{table_name}/row` — Delete
- `GET /db/tables/{table_name}/export` — Export
- `GET /processes/{process_id}/versions` — Versions
- `GET /process-versions/{version_id}` — Version
- `GET /processes/{process_id}/draft` — Draft
- `PUT /processes/{process_id}/draft` — Edit
- `DELETE /processes/{process_id}/draft` — Discard
- `POST /processes/{process_id}/draft/validate` — Validate
- `POST /processes/{process_id}/draft/publish` — Publish
- `POST /decisions/{decision_id}/replay` — Replay
- `GET /processes/{process_id}/execution` — Execution Settings
- `GET /users` — All users
- `POST /users` — Create a user
- `POST /login` — Find the user by email. Send its id as `X-User-Id` afterwards
- `GET /me` — The current user
- `GET /processes` — All processes
- `POST /processes/definition` — Create or update a whole process from its JSON definition (idempotent)
- `GET /processes/{process_id}` — A process with its setup
- `GET /process-drafts` — List Drafts
- `POST /process-drafts` — Start
- `GET /process-drafts/{draft_id}` — Get
- `GET /process-drafts/{draft_id}/revisions` — History
- `POST /process-drafts/{draft_id}/messages` — Message
- `POST /process-drafts/{draft_id}/workbooks` — Workbook
- `POST /process-drafts/{draft_id}/sources/{name}/sync` — Sync
- `POST /process-drafts/{draft_id}/reviews` — Review
- `POST /process-drafts/{draft_id}/prepare` — Prepare
- `POST /process-drafts/{draft_id}/publish` — Publish
- `PUT /process-drafts/{draft_id}/execution` — Configure Execution
- `GET /processes/{process_id}/rules` — Rules
- `POST /processes/{process_id}/rules` — Add a rule as text. It is compiled in the background (status `compiling`)
- `POST /processes/{process_id}/norm` — Turn a norm in natural language into norm rules and their checks. The checks compile in the background, concurrently (status `compiling`)
- `GET /processes/{process_id}/norm-rules` — The sentences of the client's norm, each with its atomic rules
- `GET /rules/{rule_id}` — A rule with its code
- `POST /rules/{rule_id}/compile` — Recompile a draft or blocked rule: tests, code, validation; waits for it
- `GET /rules/{rule_id}/impact` — What activating (or retiring) this rule would change, without doing it
- `POST /rules/{rule_id}/activate` — Stage a validated rule in the process draft; publish the draft to activate
- `POST /rules/{rule_id}/retire` — Stage removal of a rule; validate and publish the process draft to retire it
- `POST /processes/{process_id}/run` — Decide every pending instance with the active rules
- `POST /processes/{process_id}/reprocess` — Decide the decided instances again with the current rules and sources
- `GET /processes/{process_id}/runs` — Run history, newest first: each run and reprocess with its outcome
- `GET /runs/{run_id}` — One past run with the decisions it appended, read-only
- `GET /processes/{process_id}/summary` — The numbers of a process page: instances, decisions, queue, rules, sources
- `GET /processes/{process_id}/instances` — Instances with their latest decision, oldest first
- `GET /processes/{process_id}/events` — The trace of a process, newest first
- `GET /processes/{process_id}/queue` — Instances waiting for a person: escalations and reviewer disagreements
- `GET /instances/{instance_id}` — An instance with its symbols, decision history and trace
- `POST /instances/{instance_id}/resolve` — A person decides. Adds a decision, never edits the engine's
- `GET /processes/{process_id}/export` — outcomes.jsonl, one line per instance
- `GET /processes/{process_id}/findings` — Past decisions a later rule says were wrong
- `GET /instances/{instance_id}/suggestion` — Assistant's suggested decision, reasoning and new rule for an escalated case. Only a suggestion: the person resolves the instance and creates the rule (POST /processes/{id}/rules) themselves
- `GET /processes/{process_id}/extraction-plan` — Inspect the current fields and rule dependencies used for document extraction
- `POST /processes/{process_id}/files` — Store a PDF and its reading evidence as an instance of a process
- `GET /instances/{instance_id}/document` — Read persisted document evidence from PostgreSQL
- `GET /instances/{instance_id}/document/locations` — Get Document Locations
- `GET /instances/{instance_id}/document/pages/{page_number}` — Get Document Page
- `POST /instances/{instance_id}/extract` — Re-extract a pending document using current symbols, rules and source snapshots
- `POST /processes/{process_id}/sources/workbook` — Load supplier and order snapshots from an XLSX workbook
- `GET /instances/{instance_id}/file` — The file the instance was made from, byte for byte (usually a PDF)
- `GET /processes/{process_id}/sources` — The current load of each source of truth
- `GET /processes/{process_id}/sources/{name}` — The current load of one source, rows included
- `POST /processes/{process_id}/sources/{name}/sync` — Download an HTTP source (e.g. the ERP) into a new snapshot
- `GET /processes/{process_id}/sources/{name}/diff` — The latest snapshot of a source against the one before it
- `GET /use-cases` — All use cases
- `GET /use-cases/{use_case_id}` — A use case with the active configuration of each agent role
- `GET /use-cases/{use_case_id}/agents/{role}/versions` — Every version of an agent role's configuration, oldest first
- `PUT /use-cases/{use_case_id}/agents/{role}` — Save a new version of an agent role's configuration and activate it
- `POST /agent-configs/{config_id}/activate` — Activate an existing version (rollback, or adopt one loaded from the pack)
- `GET /traces` — Recent spans, newest first
- `GET /traces/{trace_id}` — One trace as a tree of spans
- `GET /instances/{instance_id}/trace` — The journey of one instance: file, reading, symbols, decisions, people, export
- `GET /rules/{rule_id}/trace` — How a rule was produced (norm, tests, attempts, reviews, activation) and its runtime stats
- `GET /processes/{process_id}/metrics` — Aggregates of a process: runs, throughput, step durations, LLM tokens, outcomes
- `GET /processes/{process_id}/metrics/ingestion` — The ingestion plane of a process
- `GET /metrics/ingestion` — The ingestion plane across every process
- `GET /processes/{process_id}/metrics/agents` — The agents plane of a process
- `GET /metrics/agents` — The agents plane across every process
- `GET /processes/{process_id}/metrics/execution` — The execution plane of a process
- `GET /metrics/execution` — The execution plane across every process
- `GET /health/planes` — Each plane now: ok, degraded or down
- `GET /events/stream` — Every new span, live (server-sent events)
- `POST /processes/{process_id}/learning` — Analyze past cases and propose norms; changes no decisions or rules
- `GET /processes/{process_id}/learning` — List Analyses
- `GET /learning/{analysis_id}` — Get Analysis
- `GET /norm-proposals/{proposal_id}` — Get Proposal
- `POST /norm-proposals/{proposal_id}/validate` — Prepare isolated code/tests or paired guidance previews; waits up to five minutes
- `POST /norm-proposals/{proposal_id}/approve` — Publish the exact latest validated norm after checking for stale evidence
- `POST /norm-proposals/{proposal_id}/reject` — Reject
- `GET /processes/{process_id}/alerts` — Past decisions that newer data or rules would decide otherwise
- `POST /alerts/{alert_id}/ack` — The manager has seen the alert; records who and an optional note
- `POST /instances/{instance_id}/proposal` — The assistant proposes a decision for an escalated instance; a manager settles it
- `GET /processes/{process_id}/proposals` — Proposals from the escalation assistant, the process chat and learning
- `POST /proposals/{proposal_id}/accept` — The manager accepts a proposal; its channel's own workflow applies it
- `POST /proposals/{proposal_id}/reject` — The manager rejects a proposal; nothing it proposed is applied
- `GET /v1/ocr/config` — Ocr Config
- `POST /v1/extractions` — Extract
- `GET /v1/extractions/{extraction_id}` — Get Result
- `POST /v1/batches` — Submit Batch
- `GET /v1/batches/{batch_id}` — Get Batch
