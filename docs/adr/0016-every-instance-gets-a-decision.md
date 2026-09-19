---
status: accepted
supersedes: 0009
---

# Decide every instance: a rule that cannot be evaluated escalates the case

## Context
The challenge checks `outcomes.jsonl` with a binary filter: one line per file, every
`result` one of the process's outcomes. ADR 0009 introduced an internal `REVIEW` state for
"our doubt" (a rule that failed, codes A and B disagreeing, extractions disagreeing), kept
it out of the export and made the export refuse while any instance sat in it. ADR 0001 says
something simpler: missing evidence, conflicting sources or an anomaly "sends the case to a
manager", who "must choose one of the process's existing outcomes".

In practice the second state machine cost more than it gave. At 500 invoices a memory limit
in the sandbox failed every rule, every instance went to `REVIEW`, and the run produced no
result at all while every unit test stayed green. A `REVIEW` instance also needed its own
kind of human decision (`review_correction`) to become exportable, a second queue in the
frontend, and a second answer to "what does this case need from me".

## Alternatives considered
- **Keep REVIEW as an internal state (ADR 0009).**
  - Pros: our doubt is never mislabelled as a business outcome.
  - Cons: a run can end with nothing exportable; two queues; two kinds of human decision;
    the export policy machinery (`engine | final`, `unresolved_review`) to make it whole.
- **Fall back to the default outcome when a rule cannot run.**
  - Pros: always a result.
  - Cons: pays an invoice because the code that would have stopped it crashed.
- **Escalate: decide the process's human decision type with the reason (chosen).**
  - Pros: every instance always has a result the reference format accepts; a person sees
    the case and the exact reason (`RULE_ERROR 7: KeyError: 'iban'`); one queue, one kind of
    human decision; the process, not the core, names the outcome (`requires_human`).
  - Cons: our doubt and a rule's "this needs a person" share an outcome. The reason string
    and the per-rule results tell them apart; the export does not.

## Decision
- The engine returns a decision for every instance. Its `Outcomes` are the process's
  priorities, its default type and its **escalation type**: the highest-priority decision
  type marked `requires_human`. A definition must declare at least one.
- A rule whose code fails, returns something malformed or is missing, and a tie between
  different types at the top priority, decide the escalation type. The reason is
  `RULE_ERROR <id>: ...` or `RULE_CONFLICT: ...`; every rule's result is still recorded.
- A symbol marked `required` in the definition is guaranteed by the platform, not by a
  rule: an instance where it is absent, `None` or blank (an instance with no symbols at
  all misses every one) decides the escalation type with the reason
  `MISSING_DATA: <symbol>, ...`. The rules still run and their results are recorded, but
  they cannot pay it. Generated rules follow "a missing symbol does not fire", so without
  this a scan with no text passed every rule and was paid by default.
- A `blocked` rule (its agents answered NeedsData, ADR 0004) has no code on purpose: it
  escalates every instance with `RULE_NEEDS_DATA <id>: missing <what>`, so the manager
  reads what data to add instead of a generic "without code".
- A rule whose compilation on save failed (every LLM down, tokens out, output still
  malformed; ADR 0004, 0020) is `blocked` too, with no code and `report.error`: it
  escalates every instance with `RULE_COMPILE_FAILED <id>: <error>` until it compiles.
  A rule that cannot be applied escalates; the older rules never decide without it.
- A rule that reads a live source whose pre-run sync failed does not run on an older
  snapshot: unless the rules that ran already decide the case, it escalates with the reason
  `SOURCE_UNAVAILABLE: <source>` (added by ADR 0028, which sets the precedence).
- Instance states are `PENDING` (no symbols yet, or not run) and `DECIDED`. There is no
  `REVIEW`, no `review_reason`, no `human_kind`.
- The exported decision is the engine's latest decision for the instance (ADR 0009 kept
  this: the challenge wants the process output, and a person's resolution never changes
  it). A person's decision is exported only for an instance the engine never decided. Export
  refuses (409) while any instance is `PENDING`.
- The engine runs one code per rule, agent A's (ADR 0004 revised): the A/B cross-check
  belongs to compile time, where a disagreement blocks activation.

## Consequences
- After `POST /processes/{id}/run`, every instance with symbols is exportable. The demo
  writes 500 lines for 500 files in one call.
- An escalation caused by a broken rule looks, in the export, like one caused by a rule
  that says "a person must look". The manager's queue shows the reason; a broken rule is a
  bug to fix and re-run, and the instances it touched are re-decided by the next run of a
  new process version (ADR 0015).
- The export policies designed in ADR 0007/0009 (`exported_decision: final`) are not
  implemented; a process that wants the manager's final decision exported would add them.
- The 29 image-only scans of batch 1 carry no symbols and are escalated with
  `MISSING_DATA` (the invoice pack marks the eight symbols R01 checks as required; R01
  stays, redundant), which is the honest answer until OCR fills them
  (`features/ingestion`). A process whose rules were generated from the client's norm gets
  the same guarantee without a completeness rule. OCR now fills them (ADR 0022); ADR 0025
  adds two escalations for scans only: a required value the readers did not confirm
  (`UNVERIFIED_DATA`) and a rejection on scanned data (`SCAN_REVIEW: <rule>`).

## Evidence
- `decisions/engine.py` (`Outcomes`, `decide`); `decisions/service.py` (`outcomes`, `run`,
  `export`); `processes/definition.py` refuses a definition without a `requires_human` type.
- Tests: `test_engine.py` (failed rule → `ESCALAR` with `RULE_ERROR`, tie → `RULE_CONFLICT`,
  malformed answer, rule without code, blocked rule → `RULE_NEEDS_DATA`, failed compile →
  `RULE_COMPILE_FAILED`, a required symbol
  missing or no symbols at all → `MISSING_DATA`), `test_sandbox_integration.py` (the same against
  the real sandbox, including a whole-batch timeout and an invoice missing a symbol the
  rule reads), `test_api.py` (run, queue, resolve, a required symbol missing,
  export; a person's decision exported only when the engine never decided; the real sandbox
  through the service).
- `make demo` on batch 1: `PAGAR 433 / NO_PAGAR 36 / ESCALAR 31`, 500 lines, no instance
  left without a result, identical to the golden reference on all 471 text PDFs.

## Related
ADR 0001, 0002, 0004, 0008, 0009 (superseded), 0014, 0015, 0028 (`SOURCE_UNAVAILABLE`).
