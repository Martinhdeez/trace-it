# Mail ingestion for a process

Status: implemented for local verification; **disabled by default**. No production mailbox
credentials have been validated and no real reception test has been performed. Development
does not access the VPS, Stalwart, Roundcube, SMTP, DNS, certificates or production data.
This integration targets Trace-it, not the ERP simulator.

## Process assignment and behavior

In **Process → Ajustes → Correo de recepción (gathering)**, a manager can assign
`migration-test@j-aautomation.com` or leave the field empty. Only this address is accepted
in this first release; a database uniqueness constraint and serialized API updates prevent
assigning it to two processes. Assignment is audited and does not enable the worker.
An active account must be halted before its assignment can change. The service credential,
configured process, mailbox identity and process gathering email must all agree.

A separate worker uses verified TLS on IMAP port 993, opens INBOX with EXAMINE, and reads
only candidate PDF parts with BODY.PEEK. It has no SMTP or mailbox write commands.
The command guard also refuses SELECT, CLOSE, STORE, MOVE, COPY, APPEND and EXPUNGE.
See [Python's IMAP API](https://docs.python.org/3/library/imaplib.html) and
[the IMAP specification](https://www.rfc-editor.org/rfc/rfc3501.html).

The worker discovers UIDs without filtering on unread flags or trusting the sender's Date.
It inspects BODYSTRUCTURE and RFC822.SIZE first, then bounded headers and candidate parts.
PDF and octet-stream attachments with PDF filenames are supported. Message attachments,
ZIPs, executables and links are not followed. Original filenames are preserved separately
from safe, unique internal names. A PDF signature alone is insufficient: EOF, readability,
encryption and page count (maximum 500) are checked before ingestion. Recoverable PDF
structure damage is accepted when the reader can open its pages. The original bytes go
through the same process extraction pipeline as uploaded documents, including its configured
OCR and verification; the mail worker does not replace that pipeline or rewrite the PDF.

All ready attachments from a message are imported before evaluation. The existing extraction
configuration, published rules, source synchronization, captured inputs, sandbox, parallel
rule evaluation and optional decision review remain in use. Selected documents are evaluated
with the full process population as `others`. No LLM chooses the outcome.
`PAGAR` records an application decision; it performs no payment, transfer or external
accounting operation. `ESCALAR` remains the normal human-review outcome.

## Persistence and recovery

Migration 0018 is additive: `processes.gathering_email`, `mail_accounts`, `mail_messages`,
`mail_attachments` and `run_operations`. All durable state resides in PostgreSQL.
The worker has no direct database access.

Explicit initialization stores the account/folder identity, UIDVALIDITY and UIDNEXT in
one transaction. **Initialization is the activation boundary**: earlier UIDs are excluded;
messages arriving after the sampled UIDNEXT, including during initialization, are eligible.
Starting or restarting the worker never initializes or resets the boundary.

Discovery searches bounded numeric UID windows (20 initially). An empty window cannot use
reversed wildcard semantics. Every discovered message is inserted in the same transaction
that advances the cursor. Sparse/expunged UIDs are safe; a disappeared discovered message
is recorded as `message_missing`. A UIDVALIDITY change halts the account without scanning
the replacement mailbox. Missing or inconsistent persisted state fails closed.

Messages are leased for five minutes using row locking and SKIP LOCKED. Each request
checks the lease token; an expired worker cannot overwrite a replacement worker's work.
Database transactions keep the message locked during an import. Crashed work becomes
claimable after expiry. There is one processing worker initially.

Identity is account + folder + UIDVALIDITY + UID + MIME part, with the content hash and
links to instance, execution and decision. Message-ID and attachment filename are metadata,
not idempotency keys.

* Same part retried: its ledger row returns the original import. The instance, PDF evidence
  and ledger link commit together.
* Same PDF in another message: record a new provenance row with `duplicate_content` and
  link to the existing instance/result. Do not evaluate it again.
* Same content as a manual pending instance: record `manual_pending_conflict`; leave
  that instance pending for a person.
* Previously decided instances: never call reprocess or modify decision history.
* Run response lost: a stable operation key returns the response committed alongside the
  decisions. A changed selection with the same key is rejected. Human keys are namespaced.

Attachment states are `discovered`, `imported`, `completed`, `duplicate` or `failed`.
Message states include `discovered`, `importing`, `evaluating`, `completed`, `partial`,
`ignored`, `retry_wait` and `failed`. Attempts, next retry and lease expiry are durable
on the parent message. No-PDF mail is `ignored`; mixed success/failure is `partial`.
Invalid PDFs and size violations are permanent errors. Technical errors never manufacture
an ESCALAR decision. Message attempts are capped at six; poll failures back off to one hour
and halt after six. Invalid credentials halt immediately. Backend unavailability backs off
in the worker and exits after six failures; the service has no automatic restart loop.

The Settings view shows last successful poll, sender, subject, message identity, attachment
status/error and instance/execution/decision links. Document traces identify mail provenance.
No body, attachment content, password or token is included in worker logs.

## API and permissions

`GET/PUT /processes/{id}/gathering` is the human configuration API (writes require a manager).
`GET /processes/{id}/mail-ingestion` is the human status view. Neither exposes a token hash.

`/mail-ingestion/{process_id}` and its initialize/discover/claim/message operations use
HTTP Bearer authentication against a SHA-256 service-token hash. A credential is bound to
one process and mailbox. Mail-token requests to human or administrative endpoints are denied
even with X-User-Id. The existing administrative Bearer retains its separate API permissions
and cannot substitute for the scoped mailbox credential.
The worker can neither publish rules nor resolve/reprocess instances nor change providers.
Automatic run authors are `mail_ingestion:<account_id>`, not a person's identity.

`POST /processes/{id}/run` still accepts no body to run all pending instances manually.
An optional body selects instances:

```json
{"instance_ids": [123, 124], "idempotency_key": "a-client-generated-operation-id"}
```

An empty list is rejected, as are missing/foreign IDs before any source sync or execution.
The mail endpoint derives selection from its own imported attachment rows; the worker
cannot submit arbitrary IDs. Selected responses include execution and decision IDs.
`GET /runs/{id}` remains the immutable execution/result read API.
Regenerate contracts using `make openapi`.

## Configuration

See [the example](../deploy/mail.env.example). The worker does not load a backend .env.
Secret values are read only from files. Never use VITE variables for service credentials.

| Setting | Initial value |
| --- | --- |
| MAIL_INGESTION_ENABLED | false |
| MAIL_IMAP_HOST / MAIL_IMAP_PORT | mx1.j-aautomation.com / 993 |
| MAIL_IMAP_USERNAME / MAIL_IMAP_FOLDER | migration-test@j-aautomation.com / INBOX |
| MAIL_IMAP_PASSWORD_FILE | /run/secrets/mail_password |
| MAIL_API_BASE_URL | http://backend:8000 (private Compose network) |
| MAIL_API_TOKEN_FILE | /run/secrets/mail_token |
| MAIL_PROCESS_ID | required, verified by operator |
| MAIL_POLL_INTERVAL_SECONDS | 60 |
| MAIL_MAX_PDF_BYTES | 20971520 |
| MAIL_MAX_MESSAGE_BYTES | 52428800 |
| MAIL_MAX_PDFS_PER_MESSAGE | 10 |
| MAIL_MAX_MESSAGES_PER_POLL | 20 |
| MAIL_WORKER_CONCURRENCY | 1 |
| MAIL_TIMEOUT_SECONDS | 30 |

PDF and MIME byte limits can be lowered; this release has hard ceilings of 20 MiB and
50 MiB. The backend independently enforces its ingestion limits. Candidate and discovery
limits are configurable up to 100. Downloads use partial FETCH and incremental decoding:
both encoded and decoded sizes are bounded before the full part can be accumulated.
TLS certificate and hostname verification cannot be disabled through configuration.

## Future operator installation — do not run during development

These are separate, reviewable steps for a later root intervention.

1. **Install disabled.** Review migration 0018, take the normal backup, and install the
   reviewed backend/frontend images and additive migration through the normal release
   procedure. Do not change mail services. Install only the reviewed
   `compose.mail.yml`, `mail-service.sh` and the small mail-stop patch in `deploy.sh`;
   compare against the VPS's current files rather than replacing them with old copies.
   Do not include the mail overlay in ordinary deployment Compose commands.
   Leave MAIL_INGESTION_ENABLED=false and the service stopped.
2. **Introduce credentials.** In root-owned `/opt/trace-it/secrets/`, create
   `mail-password` containing only the mailbox password and `mail-token` containing a
   new cryptographically random token (at least 32 characters). Use owner root, group 10001,
   mode 0640, and a protected parent directory. Do not echo credentials or pass them as
   command arguments. The backend does not receive the mailbox password. Copy
   `mail.env.example` to `secrets/mail.env` and fill the verified process ID.
   Keep the three path overrides in `secrets/mail-compose.env`, including
   TRACE_MAIL_ENV_FILE=./secrets/mail.env.
3. **Verify destination.** Open Trace-it, confirm the intended Invoice payment process,
   its published version and source configuration, and assign the gathering email in
   Settings. Production was previously observed as ID 1, but that is not a universal ID.
   Provision the credential using the backend image with only the token file temporarily
   mounted read-only, then remove that temporary mount:
   `python -m app.features.mail_ingestion.admin provision --process-id <verified-id> --token-file /run/secrets/mail_token`.
   This checks assignment and publication; it does not contact IMAP.
4. **Verify the immutable image.** Set TRACE_MAIL_IMAGE in the protected
   `mail-compose.env` to the *same* registry digest as TRACE_BACKEND_IMAGE in current.env,
   e.g. `ghcr.io/martinhdeez/trace-it/backend@sha256:<64-hex>`. The wrapper refuses tags or
   a different backend digest. Set TRACE_MAIL_PASSWORD_FILE and TRACE_MAIL_TOKEN_FILE to
   the files above. `mail-service.sh check` verifies the command/dependencies exist in that
   exact image. CI also runs the command and disabled default in its tested backend image.
   A local image ID is validation evidence, not a published production release digest.
5. **Initialize explicitly.** With the service still stopped, run
   `mail-service.sh initialize`. This contacts IMAP read-only and persists UIDNEXT without
   importing history. Inspect status afterward. If the response was lost, inspect state;
   do not clear the cursor or repeat initialization against an existing boundary.
6. **Activate explicitly.** Set MAIL_INGESTION_ENABLED=true in the operator file, then run
   `mail-service.sh start`. Check compatibility, assignment and last-poll status. The worker
   uses protocol version 2 and fails closed on mismatched account/host/folder/process.
   No additional port, Docker socket, OCR key or administrative mailbox credential is used.
7. **Verify a user-supplied email.** Ask the user to supply a new message after initialization.
   Inspect each attachment, its stored original PDF/evidence, execution and decision.
   Verify the mailbox's flags/content stayed unchanged. Do not send a synthetic or real
   email to production as part of this development task.
8. **Stop/recover.** `mail-service.sh stop` stops discovery and allows up to five minutes for
   in-flight work. Lease expiry and atomic imports/runs recover interrupted work. For
   credential correction, stop, use the backend operator command `halt`, correct the
   secret, then `resume` with the same process ID and existing cursor. Resume refuses a
   UIDVALIDITY change; investigate/restore state separately rather than scanning history.
   Final failed messages remain visible for review; this release has no automatic historical
   replay or unlimited retry command.

The worker runs as UID 10001, with no capabilities, no published ports, a read-only
filesystem, bounded memory/CPU/PIDs and separate secret mounts. The main deployment script
stops this project's mail containers **before** backend shutdown, backup and migration.
Success and rollback both leave mail stopped; resuming needs explicit operator action.
PostgreSQL backups include the cursor, provenance, operation responses and decisions.
Disabling or reverting the worker must retain those tables; do not downgrade this migration
or restore a stale cursor to make a worker start.

## Local validation

`make check` runs unit/database/mail tests and golden outcomes without real providers.
`make e2e-mail` runs Chromium against a separate test database, real API and loopback TLS
IMAP fixture. It sets the email in Settings, starts the test worker, delivers a synthetic
.eml into the local fixture, and verifies PAGAR/NO_PAGAR/ESCALAR and visible provenance.
No browser API responses are mocked. Native PDF extraction and published deterministic
test rules produce decisions through the production engine.

The fixture generates its own temporary CA, synthetic credentials, .eml and PDFs. It records
the actual wire commands with LOGIN arguments removed. Tests assert unchanged flags/content,
old-mail exclusion, initialization races, bounded downloads, duplicates, manual conflicts,
lease recovery, concurrent workers, lost responses, UIDVALIDITY halt, credential scope,
missing sources, infrastructure failure and preserved `others` context.
CI runs this test in addition to the existing integration and production-image checks.


## Reception console and activity (migration 0019)

Open a process and choose **Reception** ("Recepción" in the console). The overview also
has a mailbox summary; Settings retains mailbox assignment. Reception lists messages,
PDF attachments, reading/evaluation stages, outcomes and links to documents, review and
executions. Review-required outcomes are distinct from technical failures. It refreshes
every five seconds; filters apply to the current page and older messages remain paginated.
Activity links open their exact message, including messages outside the first page.

The worker sends a heartbeat every 15 seconds, independently of document extraction.
A heartbeat older than 60 seconds displays a warning, not a claim that the mailbox is
connected. The last successful mailbox poll and worker heartbeat are displayed separately.
A stopped/halted worker is visibly stopped. Heartbeat indicates worker liveness, not that
an individual PDF is making progress. Stages reflect committed state, never invented
percentages; document evidence explains whether native text, OCR or vision was used.

New mail transitions generate grouped in-app notices (at most three message cards per poll)
while the process is open. Existing history never generates startup toasts. Read state is
stored per user and process; **Mark as read** acknowledges it across browser sessions.
Notifications are in-app only. Message details retain reception, reading, evaluation,
failure and retry transitions, plus earlier operator recovery events where available.
No historical transition timestamps are fabricated for messages predating this release.

A manager may retry an eligible failed PDF using **Retry reading** and the inline
confirmation. Only that MIME part is reset; successful attachments, past decisions,
manual pending instances and mailbox cursor remain intact. The message must be terminal,
have no active lease, match the current UID boundary and have fewer than six total claims.
Only invalid_pdf, infrastructure_error and operator_retry_failed without an imported
instance/decision/execution are eligible. Stale or concurrent clicks return 409. The previous
failure and requesting manager are recorded before the transition. Permanent size/MIME
issues require a corrected new email; exhausted attempts require operator investigation.
Imported-but-undecided documents use existing lease recovery, not a reset of their identity.

### API additions

Console endpoints use the existing human authentication and process boundaries:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /processes/{id}/mail-ingestion | Overview; limit, before_id and optional message_id |
| GET | /processes/{id}/mail-ingestion/activity | Recent activity; after_id for ascending catch-up, limit <= 200 |
| POST | /processes/{id}/mail-ingestion/activity/read | Monotonic per-user receipt: {"through_id": 123} |
| GET | /processes/{id}/mail-ingestion/messages/{message_id}/history | Stage and legacy operator history |
| POST | /processes/{id}/mail-ingestion/attachments/{attachment_id}/retry | Manager only: {"expected_attempts": 1} |

The scoped worker token alone can call POST /mail-ingestion/{id}/heartbeat with
{"phase":"polling"}, "processing", "waiting" or "stopped", and POST
/mail-ingestion/{id}/messages/{message_id}/attachments/{attachment_id}/reading with
its current X-Mail-Lease. Worker credentials cannot acknowledge human notifications or
request manager retries. Activity is an audit table and is read-only through the database
API. OpenAPI includes the complete request/response schemas.

### Upgrade an already active mailbox

Release backend, frontend and worker from the same reviewed revision. Back up first;
apply additive migration 0019 and run the standard database privilege provisioning.
The normal deploy script stops mail before migrating and intentionally leaves it stopped.
Point TRACE_MAIL_IMAGE at the new backend digest, run mail-service.sh check (protocol=2),
verify the persisted account/process/UIDVALIDITY/initial_uid/next_uid, then start the worker.
**Do not run initialize again and do not import history.** Verify a fresh heartbeat, a new
successful poll and unchanged cursor boundaries except normal discovery of new mail.
Existing messages/decisions are preserved. Old workers fail closed against protocol 2;
rollback requires a matching worker/backend pair and retaining the additive database state.
