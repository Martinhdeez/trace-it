# Discover and revise a process

The backend accepts evidence assets and a conversation to propose a complete process definition.
Every
operation below requires a manager's `X-User-Id`. Discovery never creates live rules;
publication follows review, compilation, acceptance examples and version validation.
Discovery conversations use separate storage from the single editable process version draft.
A separate editable version draft can be discussed, but must be finished before preparing
or publishing discovery proposals. It is never overwritten.

## Start or resume

`POST /process-drafts` accepts `{ "name": "Invoice payments" }` for a new process, or
`{ "process_id": 1 }` to revise an existing one. An optional `use_case_id` supplies existing
agent settings and configured source connections for a new process. Without one, models
use the platform environment settings, including `TRACE_DISCOVERY_MODEL`.

`GET /process-drafts` lists saved conversations. `GET /process-drafts/{id}` returns the
current revision, plan, reviews, messages, evidence inventory, loaded snapshots, available
connectors and preview. `GET /process-drafts/{id}/revisions` preserves earlier proposals
and answers with their authors. Draft state survives restarting the backend.

All mutation requests after creation carry the last returned `revision`. A concurrent
edit or published draft returns 409. Use the returned revision for the next request.

In the console, **New process** opens chat by default and resumes the latest unpublished
new-process conversation. A manager can start another conversation or switch among saved
ones. For an existing process, **Definition** opens the same workflow with the published
version as its baseline. Review, connector sync, preparation, impact and publication stay
inside that screen. Form entry, JSON import and the manual definition editor remain secondary
paths.

Every response carries `trace_id`, the audit trail of the last agent run on this draft
(discovery, discussion or compilation). `GET /traces/{trace_id}` returns that tree: each
model call with its agent, the model that answered, the instructions it saw, its output,
rejected outputs, tokens and latency (ADR 0018). It is null until the first agent run.

Model chains may mix providers. `helmcode:<model>` uses `HELMCODE_API_KEY`; a
`vercel:<provider/model>` entry uses Vercel AI Gateway through `AI_GATEWAY_API_KEY`.
Timeouts and provider errors advance to the next configured model and are retained in the trace.

## Supply evidence and explain the process

- `POST /process-drafts/{id}/evidence`: multipart `file` and `revision`. Accepts XLSX, CSV
  and JSON, up to 20 MB per upload and five evidence assets per draft. CSV accepts UTF-8
  comma, semicolon, tab or pipe-delimited tables. JSON accepts an object, a list, or an
  object of named lists. All formats receive stable sheet and cell references. Excel formula
  cells cannot silently become authoritative source values. The old `/workbooks` path remains
  as a deprecated compatibility alias.
- `POST /process-drafts/{id}/sources/{name}/sync`: `{ "revision": 2 }`. Uses a connector
  already published for the process or a connector proposal the manager accepted in this
  draft. The source is read through the existing client; only a complete download replaces
  the draft snapshot. No live process source changes.
- `POST /process-drafts/{id}/messages`: `{ "revision": 3, "mode": "revise", "message": "Read the workbook
  and ask me about unclear rules. Escalate incorrect VAT rather than rejecting it." }`.
  Revision mode runs discovery and returns the complete proposed plan and outstanding
  questions. Without this mode, messages discuss the proposal without changing it.

Upload and sync retain evidence; send a message to have the agent interpret it. The agent
can read further tabular ranges and search downloaded ERP records. It proposes table
mappings; ordinary code extracts all mapped rows. Source authority, informal notes,
evaluation dates and conflicting policies belong in the clarification conversation.
User instructions can override a document, with the conflict retained for review.
For a new draft with unresolved policy or authority questions, discovery proposes sources
and asks the manager first. Rules and examples can remain empty until those answers arrive.
Answering a question revises the proposal; it does not approve it or publish live rules.

Every proposed source mapping declares how its rows affect the current snapshot: `replace`,
`append`, `upsert` or `delete`. Upsert and delete require canonical key fields; append may
also name keys to reject collisions. Preparation rejects duplicate or missing keys and shows
the operation, key, and before/after row counts. An incremental file must never be interpreted
as a complete replacement merely because its columns match.

## Review and test

`POST /process-drafts/{id}/reviews` accepts:

```json
{
  "revision": 4,
  "proposal": "rule:check-vat",
  "disposition": "accepted",
  "explanation": "Incorrect arithmetic needs a person to investigate."
}
```

Proposal keys are `setup`, `connector:<name>`, `source:<name>`, `rule:<name>`,
`guidance:<name>` and `example:<name>`. Disposition is `accepted` or `rejected`. The
explanation also enters the conversation; follow a
rejection with a message to revise the draft or resolve the ambiguity. Chat revisions,
new uploads and source refreshes clear the reviews and preview. No LLM marks a proposal
accepted. Acceptance examples are reviewed separately and cannot be changed by the coder
or tester during compilation.

`POST /process-drafts/{id}/prepare` with the current revision normalizes confirmed rules,
compiles and tests them in the existing sandbox, evaluates the fixed examples, and runs
version validation against the proposed source rows. It requires all
proposals accepted, no outstanding questions, valid outcomes, rules and examples.
The returned preview includes interpretations, test reports, example results, source row
counts, the active rules being replaced, changed past outcomes and conflicts with manager
decisions. An unexpected rule execution error cannot pass an example merely because
the expected outcome is escalation. A failed test or a
manager conflict, pending reviewer disagreement, or historical execution error prevents publication. Provider failure returns an error and preserves
the previous draft. Calls are synchronous and may take several minutes.

## Publish

`POST /process-drafts/{id}/publish` with the preview's revision is the manager's explicit
approval. For an existing process, it preserves the ID, inserts the compiled rules and
source snapshots, retires the previous active rules, and records audit findings. This is
one transaction through the shared version publication function, including a new immutable
process version and active-version pointer. Previous decisions, rule artifacts, source
snapshots and uploaded files remain.
For a new process, its initial configuration and rules become available together.

The draft records which rules were published and retired. It cannot be published twice.
If the existing process, its source snapshots or case history changed since the draft
started, start a fresh draft so the manager reviews current evidence and impact.

## Initial scope

The manager console and API use this same workflow; it does not replace the lower-level
manual rule endpoints. Existing process identity is preserved. [Process chat](process-chat.md) supports proposing
changes to context, fields, outcomes and reviewer guidance as well as rules and sources.
All configurations remain subject to the existing engine contract.
Tabular evidence currently means XLSX, CSV or JSON plus text pasted in the conversation.
Other unstructured readers can be added behind the same evidence interface. ERP access uses
configured connections and snapshot search, not arbitrary websites or generated connectors.
For the supported legacy HTTP shape, discovery can propose ongoing connector configuration:
XML responses, form-token authentication and numbered pages with reported totals. The manager
must accept the connector before the draft contacts it. Publication stores the connector and
canonical schema in the immutable process version. Other protocols still need adapter code.

The invoice pack supplies a discovery role with the agreed anomaly/escalation guidance.
Loading the pack adds that role's configuration under the existing configuration rules.
The active invoice rules and existing golden outcomes do not change merely by loading it.
