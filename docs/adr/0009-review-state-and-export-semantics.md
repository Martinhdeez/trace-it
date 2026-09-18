---
status: accepted  # `engine` export merged in PR #17; `final` and REVIEW on rule failure pending
---

# Treat REVIEW as an internal state and export the decision the process policy names

## Context
The challenge has a binary filter: exactly one line per file of both batches, and every
`result` must match the private reference (`PAGAR`, `NO_PAGAR` or `ESCALAR`). ESCALAR is a
valid, expected answer for some invoices. Two different situations send a case to a
person, and they must not be confused:
- the process's rules say the case needs a person (a decision type with `requires_human`,
  ESCALAR for invoices); that is the correct outcome;
- the system itself is unsure (the two extractions disagree, a validator fails, codes A and
  B disagree, a rule fails to run); that is our doubt, not an outcome.

ADR 0001 also requires that the manager owns the final decision for every escalated case,
and that the decision record keeps the rule findings, the recommendation and the final
decision apart. The challenge reference, however, expects the process output: an ESCALAR
invoice must export ESCALAR even after the manager resolves it.

Before PR #17, export took the latest decision of each instance, including a person's: an
ESCALAR case the manager later resolved as PAGAR exported PAGAR, while the reference
expects ESCALAR. Two files with the same name also produced two lines.

## Alternatives considered
- **REVIEW as a decision type (e.g. mapped to ESCALAR).**
  - Pros: no extra state.
  - Cons: our doubt would be exported as a business outcome; wrong whenever the reference
    expects PAGAR or NO_PAGAR for that file.
- **Export the latest decision, person's included.**
  - Pros: reflects what the business finally did.
  - Cons: turns a correct ESCALAR into something else; fails the filter.
- **Always export the engine's decision.**
  - Pros: passes the filter.
  - Cons: hardcodes the invoice challenge's expectation; a business that wants the
    manager's final decision exported cannot have it.
- **Record the final decision; export per process policy `exported_decision` (chosen).**
  - Pros: satisfies ADR 0001 (the final decision is recorded) and the challenge (the
    invoice pack exports the engine's decision) without hardcoding either.
  - Cons: one more policy to configure and test.

## Decision
- Instance states: `PENDING`, `REVIEW`, `DECIDED`. REVIEW is internal, carries a reason,
  and is never a decision type of the process.
- Every REVIEW and every decision of a `requires_human` type goes to the manager's queue.
- A rule whose code fails, or whose codes A and B disagree, sends the instance to REVIEW
  with the reason. It never produces a decision type such as ESCALAR (ADR 0004, 0014).
- The manager's **resolution** of an escalated case is recorded as the **final decision**
  (new row, `resolution`), as ADR 0001 requires. The engine's decision stays in the history.
- **Exported decision** follows the per-process policy `exported_decision` (ADR 0007):
  - `engine`: the latest engine decision (the process output). The invoice pack uses it
    because the challenge reference expects the process output.
  - `final`: the final decision, i.e. the manager's resolution when there is one, otherwise
    the engine decision.
- A person's **correction** of a REVIEW instance (`review_correction`) is exported when
  there is no engine decision: it replaces our doubt with a real answer.
- Export refuses (409) while any instance is PENDING or REVIEW.
- One line per file name: the most recent instance with that name wins, and repeated names
  are reported in a header and a warning; the body stays one JSON object per line.
- Per-process policies (ADR 0007): `exported_decision: engine | final`,
  `unresolved_review: block | <type>`. The invoice pack uses `engine` and `block`.

## Consequences
- With `engine`, the export may differ from what the business eventually did; the final
  decision is in the history and the trace, not in `outcomes.jsonl`.
- Deciding a PENDING instance by hand counts as a resolution and export still returns 409;
  to decide by hand, move it to REVIEW first.
- **Known gaps** (fixes pending in a PR for Mateo): the engine sends a failed rule to the
  highest `requires_human` type (ESCALAR) instead of REVIEW, runs only code A, and starts
  one subprocess per instance and rule (`engine.decide`, ADR 0004). `export` implements
  only the `engine` policy; `final` is not implemented.

## Evidence
- PR #17 implements the `engine` case: `Decision.human_kind` (`resolution` |
  `review_correction`), new `export`; tests `test_run_review_and_export` (an
  escalated instance resolved as NO_PAGAR still exports ESCALAR) and `test_export_a_duplicate_name_gives_a_single_line`; 56 tests green
  on that branch.
- `ingestion/model.py`: `INSTANCE_STATUSES = ("PENDING", "REVIEW", "DECIDED")`.

## Related
ADR 0001, 0002, 0004, 0007, 0008, 0010, 0014. Plan P4, P21; `docs/process-packs.md`
(policies); PR #13, #17.
