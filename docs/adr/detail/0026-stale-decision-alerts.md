---
status: accepted
---

# Flag stale decisions to the manager; never rewrite them silently

## Context
Alberto's data changes after we decide. On Saturday the ERP update marks orders paid or
unpaid, on Sunday a datum of La Caja changes, and norm v4 adds rules. A NO_PAGAR or ESCALAR
decided on Friday may be wrong by Saturday, and nobody finds out unless someone thinks of
running `reprocess?dry_run=true` (ADR 0008) and reads its output. The product owner's rule:
when a decision later turns out to be wrong, the system flags it to the manager, who acts;
decisions are never silently rewritten.

## Alternatives considered
- **Silently reprocess after every change.**
  - Pros: the export is always current; zero manager effort.
  - Cons: a payment decision changes with nobody looking; breaks the product owner's rule
    and ADR 0008's spirit (a person must see what changed and why).
- **Manual reprocess only (today).**
  - Pros: nothing to build; the dry run already says what would change.
  - Cons: depends on someone remembering to ask after each sync or publication; the answer
    is not kept, so nobody can later tell who knew what and when.
- **Alerts (chosen).** After each change, a dry run; every decision that would change
  becomes a stored alert the manager acknowledges and acts on.
  - Pros: nothing is rewritten; the manager learns without asking; the notice, who saw it
    and how it was closed are all on record.
  - Cons: one dry run per sync or publication (cost below); one more list to watch.

## Decision
- **Triggers.** An ERP sync or workbook upload whose rows differ from the previous load
  of the same source (`sources/service.sync`, `sources/workbook.load_workbook`), and the
  publication of a process version (`versions/service.publish`, learning adoption,
  discovery publication in `processes/drafts.publish`). Both run after the change commits,
  in their own session; a failed detection is an error span and never undoes the sync or
  publication.
- **Detection** is `reprocess(dry_run=True)` (no decision written, no reviewer called):
  every decided instance whose outcome would change, engine- or person-decided, is a
  candidate. One exception for data triggers: a decision that was the process default
  (PAGAR) is not flagged, because the new data behind it is usually our own payment (the
  ERP now says PAGADA). A rule change flags PAGAR too: that is the rule saying the
  payment was wrong.
- **The alert** (`alerts` table, migration 0013) stores the instance, the decision flagged
  (`decision_id`, `before`), the would-be outcome (`after`), the trigger (`source_sync`
  with source ids and the changed rows that share a value with the instance, or
  `rule_change` with added, removed and changed rule ids), the evidence (author and reason
  codes before and after), `created_at`, `status`, `acknowledged_by/at` and a note.
- **One table, append-only in content.** What was detected is never edited; only the
  status moves forward (open -> acknowledged), and each move is an `ack_alert` span.
  `resolved` is not stored: it is derived from a later decision of the instance (the
  manager resolved it or reprocessed it). We chose this over `events` plus a status table:
  the same amount of code, but a unique constraint and plain SQL filters instead of JSONB
  queries, and `events` stays a trace, not a work queue.
- **No duplicates.** Unique on (`decision_id`, `after`): the same decision flagged towards
  the same outcome again, by the same trigger or a later one, adds nothing.
- **API.** `GET /processes/{id}/alerts?status=`, `POST /alerts/{id}/ack` (manager only,
  identified by `X-User-Id`; optional note). The manager acts with `POST /instances/{id}/resolve` or `reprocess`.
  Execution metrics carry `open_alerts`. Spans `detect_stale_decisions` (trigger,
  instances, would_change, alerts_created, duration) and `ack_alert`, execution plane.

## Consequences
- Each sync that changes rows and each publication costs one dry run: O(instances x
  rules), one sandbox subprocess per rule over the whole population. Measured below at
  about 1 s for 500 invoices. A sync with no changed rows costs nothing.
- The data-trigger exception is a heuristic: a PAGAR that genuinely new facts contradict
  (say, an IBAN changed after payment) is not alerted on sync. Reprocess dry run and rule
  findings still show it.
- `rows` involved are matched by shared values, not by the rule that read them: good
  evidence, not proof. The reason codes before and after say which rule decided.
- Alerts do not change the export; the manager's action does.

## Evidence
- Live run on 2026-09-19, fresh database `trace_alerts`, hand-written rules (16),
  challenge ERP with one `--lote2` datum changed (`demo-logs/alerts/`):
  - 4 invoices, sync changes AS-00476 PAGADA -> PENDIENTE and AS-00096 PENDIENTE ->
    PAGADA: one alert (`2026-03-28_P002.pdf` NO_PAGAR -> PAGAR), none for
    `2026-01-08_P001.pdf` (PAGAR, its order now paid). Decision unchanged, ack by Martín,
    `reprocess` resolved it, `open_alerts` 1 -> 0. Detection 440 ms (4 instances).
  - 500 invoices: AS-00471 -> PENDIENTE; `detect_stale_decisions` 982 ms, of which
    `reprocess` 963 ms and 16 `evaluate_rule` spans 879 ms (max 101 ms); 2 would change,
    1 alert (`2026-05-28_P003.pdf`), the PAGAR one skipped.
- Tests: `backend/app/features/alerts/tests/test_alerts.py` (sync behind a NO_PAGAR, no
  relevant change, new rule flips, ack author and resolution, no duplicates).
- Code: `backend/app/features/alerts/`, `backend/alembic/versions/0013_alerts.py`.

## Related
ADR 0008 (reprocess, findings), 0015 and 0031 (process versions), 0016 (every instance
gets a decision), 0018 (spans and planes).
