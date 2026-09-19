---
status: accepted
---

# Live sources: sync before every run, fail closed when a source is down, canonical schema

## Context
The ERP changes under us: on Saturday the batch 2 update marks orders paid, and a person had
to remember `POST /sources/erp/sync` before each run (runbook step 4b). A run decided on
whatever snapshot was last stored, however old. When a sync failed, the previous snapshot
"stayed current", so an ERP outage silently became decisions on stale data: an order paid
yesterday could be paid again today. Separately, rules read ERP rows by field name
(`purchase_order`, `status`, `amount`...), and nothing checked that a connector delivered
those names. A connector mapping `order_ref` instead of `purchase_order` made every ERP rule
pass silently ("no entry found"), which pays. Mateo's discovery agent will produce more
mappings, so the contract must be checked by code, not by the prompt.

Product owner decision (Martín, 2026-09-19): sync before every run; when a source is down,
never use the last snapshot; escalate only what depends on it.

## Alternatives considered
- **Manual sync (today).**
  - Pros: nothing to build; a run never waits on the ERP.
  - Cons: freshness depends on someone remembering; a forgotten sync decides on old data
    with no trace of it.
- **Sync before the run, and use the last snapshot when the sync fails.**
  - Pros: every run produces the usual outcomes.
  - Cons: an outage becomes wrong decisions. "Never pay twice" (R15) reads a stale
    `PENDIENTE` and pays.
- **Refuse the run while a source is down.**
  - Pros: never wrong.
  - Cons: nothing is decided, including the invoices a non-ERP rule already rejects (wrong
    IBAN, impossible date); ADR 0016 says every instance gets a decision.
- **Escalate only what depends on the down source (chosen).**
  - Pros: never decides on stale data; rejections that do not need the ERP still stand; the
    manager sees exactly which cases need the ERP (`SOURCE_UNAVAILABLE: erp`).
  - Cons: during an outage every otherwise clean invoice goes to a person; a run waits for
    the connector's retries (about 15 s with the ERP unreachable, measured below).

## Decision
- **Live sources.** `processes/<pack>/schema.json` declares, per source, the canonical
  fields and `sync_before_run`. The invoice pack marks `erp` live. No file, or the flag off,
  means no pre-run sync (offline packs, tests). The connector stays in `sources.json`.
- **Sync before every run.** `POST /processes/{id}/run` and `reprocess` (not a dry run)
  call `sources.sync_before_run` first: the existing `sources.sync` for each live source,
  one `sync_source` span each, children of `run_process` / `reprocess`. A sync that changes
  rows triggers the stale-decision alerts as any sync does (ADR 0026). The dry run (the
  alerts' own detection, and `?dry_run=true`) never syncs: that would loop sync -> alert ->
  dry run -> sync, and a dry run writes nothing.
- **Down.** A source whose pre-run sync fails for any reason (network, auth, a broken
  configuration, a snapshot not in the canonical schema) is down for that run: its load is
  left out of the captured execution inputs (`source_ids`), and the inputs record
  `down: {name: why}` so a replay decides the same. The run answers `down_sources`; the
  source's status in `GET /processes/{id}/sources` is `down` with the error until a sync
  succeeds; `GET /health/planes` reports ingestion `degraded` with `sources down:
  <process>:<source>` while any source's latest sync in the window failed.
- **Which rules read which source** is found deterministically from each rule's code by
  `compiler.source_reads`: the literal keys `read_keys` already finds on the second
  parameter, plus literal names passed with it to a helper (`rows(sources, "erp")`, the form
  of the hand-written and frozen rules). Any other use of the parameter means "every
  source". It is computed from the code at run time, so hand-written, frozen and compiled
  rules are covered alike; a compiled rule's report also stores it (`report.sources`).
- **Engine.** Stays pure: the caller passes `down` (rule id -> unavailable sources it reads).
  Such a rule does not run; its result is `SOURCE_UNAVAILABLE <rule id>: erp`. Precedence:
  1. `MISSING_DATA`; 2. `UNVERIFIED_DATA` (ADR 0025); 3. any other rule failure
  (`RULE_ERROR`, `RULE_NEEDS_DATA`, `RULE_COMPILE_FAILED`); 4. the rules that ran decide
  when no rule that could not run could outrank their outcome or tie it with another type:
  `RULE_CONFLICT`, `SCAN_REVIEW` or the rejection; 5. otherwise the escalation type with
  `SOURCE_UNAVAILABLE: <sources>`; 6. the default.
- **Canonical schema.** For invoices (`processes/invoice-payment/schema.json`, documented in
  `docs/sources-http.md`): `erp` entry_id, date, supplier_id, purchase_order, amount,
  status required, nif optional; `suppliers` id, nif, iban; `orders` purchase_order,
  total_amount, status; `parameters` cut_off_date. These are the names the rules already
  read. A sync fails loudly (502, error span, nothing written) when the connector maps no
  field to a required name, or when any row lacks one (absent, null or blank).

## Consequences
- The Saturday ERP update needs no manual step: the next run syncs it.
- An ERP outage costs escalations, never wrong payments. The manager resolves them or
  reprocesses once the ERP is back (reprocess syncs too).
- A run with a live source takes the sync's time (5 s for 516 entries at the challenge
  ERP's latency; 15 s to give up when it is unreachable).
- Status is read from the latest `sync_source` span, not a table: pruning spans would lose
  it (a `ponytail:` note marks it).
- A process with `sync_before_run` off keeps today's behaviour: manual syncs, last snapshot.
- The heuristics in `source_reads` over-approximate: code that iterates `sources` is taken
  to read everything and escalates on any outage. Never under-approximates for the shapes
  the sandbox allows.

## Evidence
- Tests: `backend/app/features/decisions/tests/test_live_sources.py` (a run syncs first and
  uses the fresh rows; ERP down: non-ERP rejection kept as NO_PAGAR, the other case
  `ESCALAR SOURCE_UNAVAILABLE: erp`, no stale snapshot in the inputs, replay matches,
  source `down`, ingestion `degraded`; a row missing `status` and a connector without
  `purchase_order` fail the sync; precedence; the ERP readers among the 16 hand-written and
  12 frozen rules), `tests/e2e/test_api_flow.py` (the API flow against the real challenge
  ERP, synced by the run), golden 471/471 (`test_engine_golden.py`, `test_frozen_rules.py`).
- Live run on 2026-09-19, fresh database `trace_erp_live`, frozen rule set, own challenge
  ERP on :8032 (`demo-logs/erp-live/`): ERP up, 4 PDFs, the run's trace holds one
  `sync_source` (516 rows, 26 pages, 2 `ORA-00600` retried, 5.1 s) and decides as the
  golden says; ERP stopped, 4 more PDFs: `down_sources.erp` after 15.4 s, the clean invoice
  and the ERP_PAID one `ESCALAR SOURCE_UNAVAILABLE: erp`, the IBAN and date rejections
  `NO_PAGAR`, source `down`, ingestion `degraded` (`sources down: 2:erp`).
- Code: `sources/service.py` (`sync_before_run`, `nonconforming`, `sync_status`),
  `decisions/engine.py`, `decisions/service.py` (`_inputs`), `versions/execution.py`,
  `agents/compiler.py` (`source_reads`), `traces/service.py` (`health`).

## Related
ADR 0013 (fault-tolerant ERP client), 0016 (every instance gets a decision; new reason code),
0025 (scan policy precedence), 0026 (alerts on sync), 0018 (spans and planes).
