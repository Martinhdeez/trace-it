---
status: accepted  # export change in PR #17 (open)
---

# Treat REVIEW as an internal state and export the engine's decision

## Context
The challenge has a binary filter: exactly one line per file of both batches, and every
`result` must match the private reference (`PAGAR`, `NO_PAGAR` or `ESCALAR`). ESCALAR is a
valid, expected answer for some invoices. Two different situations send a case to a
person, and they must not be confused:
- the process's rules say the case needs a person (a decision type with `requires_human`,
  ESCALAR for invoices); that is the correct outcome;
- the system itself is unsure (the two extractions disagree, a validator fails, codes A and
  B disagree, a rule fails to run); that is our doubt, not an outcome.

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
- **Export the engine's decision; person's resolution kept apart (chosen).**

## Decision
- Instance states: `PENDING`, `REVIEW`, `DECIDED`. REVIEW is internal, carries a reason,
  and is never a decision type of the process.
- Every REVIEW and every decision of a `requires_human` type goes to the manager's queue.
- **Exported decision = the latest engine decision.** A person's **resolution** of an
  escalated case is stored (new row, `resolution`) but never changes the export.
- A person's **correction** of a REVIEW instance (`review_correction`) is exported when
  there is no engine decision: it replaces our doubt with a real answer.
- Export refuses (409) while any instance is PENDING or REVIEW.
- One line per file name: the most recent instance with that name wins, and repeated names
  are reported in a header and a warning; the body stays one JSON object per line.
- Per-process policy (ADR 0007, proposed): `exported_decision: engine | final`,
  `unresolved_review: block | <type>`. The invoice pack uses `engine` and `block`.

## Consequences
- The export may differ from what the business eventually did; the resolution is in the
  history and the trace, not in `outcomes.jsonl`.
- Deciding a PENDING instance by hand counts as a resolution and export still returns 409;
  to decide by hand, move it to REVIEW first.
- The engine today sends a failed rule to the highest `requires_human` type instead of
  REVIEW (`motor.decidir`); it must switch to REVIEW together with ADR 0004's A/B fix.

## Evidence
- PR #17: `Decision.tipo_humana` (`resolucion` | `correccion_revision`), new `exportar`;
  tests `test_ejecutar_revisar_y_exportar` (an escalated instance resolved as NO_PAGAR still
  exports ESCALAR) and `test_exportar_un_nombre_repetido_da_una_sola_linea`; 56 tests green
  on that branch.
- `ingesta/model.py`: `ESTADOS_INSTANCIA = ("PENDIENTE", "REVISION", "DECIDIDA")`.

## Related
ADR 0002, 0007, 0008, 0010. Plan P4, P21; `docs/process-packs.md` (policies); PR #13, #17.
