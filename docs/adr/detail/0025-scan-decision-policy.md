---
status: accepted
---

# Decide scans only on confirmed data, and escalate a scan the rules would reject

## Context
Batch 1 holds 29 PDFs with no text layer. Since ADR 0022 they are read by local OCR, Gemini
and Jev, and the rules decide them like any other invoice. Two kinds of result are unsafe:

- **A rejection on scanned data.** The rules reject a scan when a value fails a check (the
  IBAN is not the supplier master's, the VAT does not add up). On OCR data such a mismatch
  cannot be told apart from a misread digit.
- **A decision on unconfirmed data.** Only a null field escalated (`MISSING_DATA`, ADR
  0016). A value the readers disagreed on (`ambiguous`), or that one reader alone proposed
  (`unverified`), was still used. The freeze rehearsal (PR #65) decided eight scans that
  way: scan_002, 010, 012, 013, 014, 015 and 022 `PAGAR`, scan_008 `NO_PAGAR`.

Gemini and Jev are called live, so the readings of a scan can change between runs, and
with them the decision. The product owner decided (2026-09-19, `docs/mentor-questions.md`):
scans are read and decided; a null field, a field we would have to check, or a failed check
on scanned data means `ESCALAR`. Text PDFs are unaffected.

## Alternatives considered
- **Escalate every scan.**
  - Pros: trivial; never wrong on a misread.
  - Cons: throws away the readings; 10 clean, fully confirmed scans go to a person.
- **Decide scans like text (before this ADR).**
  - Pros: no special case.
  - Cons: rejects on a possible misread; pays on a value one reader guessed; the decision
    changes between runs.
- **Decide only when the readers agree and the data matches the ERP.**
  - Pros: strongest confirmation.
  - Cons: turns the ERP into a reader of the document. A mismatch with the ERP is exactly
    what the rules check, so this hides real anomalies behind "unreadable".
- **Decide, but escalate on unconfirmed data and on a rejection (chosen).**
  - Pros: a scan is paid only when every required value is confirmed and every rule
    passes; a person sees every doubt, with the reason; deterministic over the stored
    readings.
  - Cons: a genuinely wrong invoice that arrives scanned is escalated, not rejected.

## Decision
- **A scan is a document with no page of native text** (`metrics.native_pages == 0`). This
  is decided per document, not per symbol: a text PDF where OCR helped on one field stays
  a text PDF. Ingestion records it in each symbol's origin (`payment_symbols`):
  `scan:<extraction id>`, and `scan:<extraction id>:<verification>` for a value its readers
  did not confirm (`unverified`, `ambiguous`). A text PDF keeps `document:<extraction id>`.
- The service passes the engine, per scanned instance, the symbols its readers did not
  confirm (`symbols.scan`); the engine (`_combine`) applies, in this order:
  1. a required symbol missing -> escalate, `MISSING_DATA: <symbols>` (unchanged);
  2. a scan with a required symbol not confirmed -> escalate,
     `UNVERIFIED_DATA: <symbols>`, whatever the rules say, `PAGAR` included;
  3. failed rules and ties -> escalate (unchanged);
  4. a scan whose winning decision is neither the default nor the escalation type ->
     escalate, `SCAN_REVIEW: <the firing rules' reason codes>`.
- Rule results are recorded as always, so the evidence still names the rule; the reason is
  in the decision row and the `decision` span, and `run_process` counts both causes.
- The escalation type is hardcoded (`ponytail:` note in `engine.py`). A process setting
  (`scan_rejection_decision`) would need a new process column and migration; it waits for
  a process that wants another outcome.

## Consequences
- Only fully confirmed scans are decided by the rules, which also removes most of the
  variance of live readers: both batch-1 runs below end at the same 10 `PAGAR` / 19
  `ESCALAR`. The delivery still keeps the `outcomes.jsonl` of one run.
- Symbols stored before this change carry `document:` for scans too, so they are not
  treated as scans until they are extracted again. Replay and reprocess of old executions
  are unaffected.
- A `NO_PAGAR` the reference expects on a scan becomes `ESCALAR` (5-6 files in batch 1).

## Evidence
- Recount of `demo-logs/scan-review/report.json` (29 scans, one full-OCR run): today 18
  `PAGAR` / 5 `NO_PAGAR` / 6 `ESCALAR`; with `SCAN_REVIEW` 18 / 0 / 11; with
  `UNVERIFIED_DATA` as well 10 / 0 / 19.
- Recount of the frozen rehearsal (`trace_freeze`, process 3, read-only): the stored rule
  results re-combined by `_combine` reproduce all 580 stored decisions; the 29 batch-1
  scans at their first decision go from 17 / 6 / 6 to 17 / 0 / 12 (`SCAN_REVIEW`) and 10 / 0 /
  19 (both). No text PDF changes.
- Golden: 471/471 (`make check`).
- Tests: `test_engine.py` (a rejected scan -> `SCAN_REVIEW`, a clean scan -> `PAGAR`, the
  same mismatch on a text PDF -> `NO_PAGAR`, a null field -> `MISSING_DATA`, a conflicting
  total -> `UNVERIFIED_DATA`), `test_payment_verification.py` (origins),
  `decisions/tests/test_api.py` (a scanned already-paid invoice through `run`).

## Related
ADR 0008, 0016, 0017, 0022; `docs/mentor-questions.md` (answers of 2026-09-19).
