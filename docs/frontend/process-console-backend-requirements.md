# Process console backend requirements

The frontend now models the intended process experience. Some states are optimistic because the current API returns only a final result. This document defines the backend work needed to make every state durable and real without changing the UI.

## Product model

A process has five user-facing areas:

1. Panel: description, health, metrics, latest runs, document drop, and output distribution.
2. Definition: iterate the norm with text, attachments, and AI proposals (add, retire, or update agent context). Accepting a compiled rule and activating it creates a process version. Version snapshots and backtesting live here, not on a separate tab.
3. Knowledge: sources of truth (ERP, workbooks, outcomes, symbols). Operational PDFs belong on the panel.
4. Review: exceptions that require a person. Alerts (compiling rules, waiting queue, contradictory history) surface on the panel, not as a separate tab.
5. Settings: OCR route, model per step, and optional decision reviewer. Space-level identity stays on `/settings`.

The API can use different internal models. These five areas must remain stable in its public contract.

## Process type and initialization

`GET /processes/{process_id}` should add:

```json
{
  "type": "invoice_payment",
  "accepted_document_types": ["application/pdf"],
  "document_label": "Facturas",
  "initialization": {
    "status": "ready",
    "document_count": 500,
    "source_count": 3,
    "last_changed_at": "2026-09-19T08:30:00Z"
  }
}
```

The process type controls upload copy, accepted files, and extraction steps. The frontend should not infer process type from its name.

Upload requirements:

- Batch upload endpoint with per-file status.
- Stable file ID before extraction starts.
- Idempotency by file hash.
- Accepted, rejected, duplicate, and failed states.
- Upload progress when the storage layer supports it.
- A retry endpoint for one failed file.

Suggested endpoint:

`POST /processes/{process_id}/documents`

The response should return one record per file. A partial failure must not fail the whole request.

## Runs

### Start a run

`POST /processes/{process_id}/runs`

Request:

```json
{
  "document_ids": ["doc_123", "doc_124"],
  "rule_set_version": "rsv_18",
  "idempotency_key": "client-generated-uuid"
}
```

Response:

```json
{
  "id": "run_20260919_001",
  "status": "queued",
  "document_count": 2,
  "created_at": "2026-09-19T08:32:10Z"
}
```

Starting a run must return immediately. Processing belongs to a background worker.

### Run history

`GET /processes/{process_id}/runs?cursor=...&limit=20`

Each run needs:

- ID and status.
- Start and finish timestamps.
- Initiating user.
- Document totals by queued, running, decided, review, and failed.
- Decision totals.
- Rule-set version and hash.
- Duration.
- Failure summary.

The process overview uses this endpoint for latest runs. Session-only frontend state should disappear once this exists.

### Live events

Preferred transport: server-sent events.

`GET /runs/{run_id}/events`

WebSocket is acceptable if infrastructure already supports it. Polling is the fallback, not the target.

Every event needs `event_id`, `run_id`, `timestamp`, and a monotonic `sequence`. The frontend must be able to reconnect with `Last-Event-ID`.

Required event types:

```text
run.queued
run.started
document.queued
document.started
step.started
step.completed
step.failed
document.decided
document.review_required
document.failed
run.completed
run.failed
run.cancelled
```

Step events need:

```json
{
  "event_id": "evt_9281",
  "run_id": "run_20260919_001",
  "sequence": 41,
  "type": "step.completed",
  "timestamp": "2026-09-19T08:32:12.481Z",
  "document_id": "doc_123",
  "step": {
    "key": "rules",
    "label": "Reglas",
    "status": "completed",
    "duration_ms": 83
  },
  "data": {
    "evaluated": 8,
    "fired": 1
  }
}
```

The backend defines step keys and labels. Different process types can then expose different pipelines without frontend conditionals.

### Run snapshot and recovery

`GET /runs/{run_id}`

This endpoint returns the current run, all document states, and current step per document. The frontend calls it before connecting to live events and after a reconnect gap.

Event delivery may be at least once. Repeated event IDs must be safe to ignore.

## Rule versions

Rules should be immutable once compiled. Editing a rule creates a new version.

Required model:

```json
{
  "rule_id": "rule_18",
  "version_id": "rule_18_v4",
  "version": 4,
  "text": "El IBAN debe coincidir con el proveedor.",
  "status": "active",
  "hash": "sha256...",
  "created_by": "user_7",
  "created_at": "2026-09-19T08:00:00Z",
  "activated_at": "2026-09-19T08:05:00Z",
  "replaces_version_id": "rule_18_v3"
}
```

Required operations:

- List rules with active version and version count.
- List all versions of one rule.
- Create a draft version.
- Compile and validate a version.
- Preview impact against historical decisions.
- Activate a version atomically.
- Roll back by activating an older valid version.
- Return the exact rule-set version used by every run and decision.

## Pending reviews

`GET /processes/{process_id}/reviews`

Review records should be separate from document state. They need:

- Review ID and status.
- Process, run, and document IDs.
- Proposed decision and confidence when available.
- Reason the process stopped.
- Failed or ambiguous step.
- Assigned user.
- Created, assigned, and resolved timestamps.
- Resolution and resulting rule-version ID.

Add claim and release operations to prevent two operators resolving the same review.

Resolution should support one atomic request that records the human decision and optionally creates a rule draft. The current two-request flow can leave half-complete work.

## Decisions

A decision response should contain:

- Final output and display label.
- Reason in plain language.
- Author, timestamp, and source type.
- Rule-set version and hash.
- Every rule result with duration and evidence references.
- Extracted symbols with provenance.
- Export payload.
- Prior decisions when reprocessed.

The frontend decision panel should not reconstruct this result from several unrelated endpoints.

Suggested endpoint:

`GET /documents/{document_id}/decision`

## Frontend fallback contract

Until these endpoints exist:

- Batch progress advances optimistically through known documents and steps.
- The final API response remains authoritative.
- Optimistic states never claim backend timestamps, durations, or exact step results.
- Latest run data lasts for the browser session only.
- Failed final requests replace optimistic progress with a visible error.
- Mock data uses the same target types planned for production.

Remove each fallback only when its replacement endpoint ships. Keep transport logic behind the API client so route components do not change.

## Delivery order

1. Run creation, run history, and run snapshot.
2. Live run events with reconnect support.
3. Immutable rule versions and rule-set snapshots.
4. Dedicated review records with atomic resolution.
5. Process type and initialization metadata.
6. Consolidated decision endpoint.

Run events unlock the largest product improvement. Build those first.
