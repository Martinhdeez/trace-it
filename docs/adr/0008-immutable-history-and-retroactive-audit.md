---
status: accepted
---

# Never rewrite history: content-addressed files, append-only decisions, audits that only report

## Context
Rules change during the challenge (norma v3 → v4, ERP update, a live change on Sunday) and
the manager keeps adding rules from escalations. Every past decision must stay explainable
with the rules and data it was taken with, and a new rule must show its effect on the past
before it is adopted. ADR 0001 requires immutable published versions and past decisions,
and a shadow backfill that never overwrites history.

## Alternatives considered
- **Mutable decisions (update the row when rules change).**
  - Pros: simple queries; the table always shows "the truth now".
  - Cons: loses what was decided and why; an invoice already paid silently changes.
- **Version files and sources in place.**
  - Pros: one row per document.
  - Cons: two contents behind one id; a decision cannot say which bytes it saw.
- **Re-run extraction and ERP calls during an audit.**
  - Pros: always "fresh" data.
  - Cons: slow, costs tokens, non-deterministic, and depends on a live ERP.
- **Append-only history plus replay over stored symbols (chosen).**

Terminology (glossary in the README): a **rule finding** is the result of one rule on one
instance (`fires`, `reason`); an **audit finding** is a past decision that a newer process
version would decide differently. This ADR stores the first per decision and produces the
second; the table named `hallazgos` stores audit findings.

## Decision
- **Files** are identified by the SHA-256 of their content and never modified. A modified
  file is a new file. Each load of a source is stored apart; the current one is the latest
  by name.
- **Decisions** are append-only rows (engine or person); an instance's current decision is
  its latest row. Each row keeps per-rule results (rule id, rule hash, fires, reason) and
  the hash of the rule set applied.
- **Retroactive audit / shadow backfill:** before a rule is activated or retired, the
  proposed rule set is replayed over the **stored symbols** of every decided instance.
  Results: unchanged; changed (engine decisions); conflict (a person's decision would be
  contradicted), which blocks the change until the manager resolves it. Adopting the change
  records **audit findings** ("old → new: reason"; for invoices, paid wrongly or unpaid
  but due) for past decisions the engine concluded alone (not those that went to a
  person). Findings are notices; the past is never edited, and acting on them
  (claim money back, pay what is owed) happens outside the system.
- **Rule versions** are linear: one active rule set per process; going back activates an
  earlier version and is itself recorded. Processes do not share rules or history. ADR 0015
  extends this to a snapshot of the whole process version.

## Consequences
- The audit is fast, free and deterministic, but only as good as the stored symbols: a new
  rule that needs a symbol never extracted requires extracting it from the stored text
  first (P10, open).
- Full linear versioning (list of versions, activate an older one) is iteration 2 (F9).
  Today rules have states draft/active/retired, a hash of text + both codes, and every
  decision stores the rule-set hash, enough to map old decisions to versions later.
- History grows without bound; acceptable at hackathon scale.

## Evidence
- `ingesta/model.py`: `Fichero` keyed by hash ("a modified file is a new file").
- `decisiones/model.py`: `Decision` append-only, `Hallazgo` (table `hallazgos`) stores audit findings and never changes the past.
- `decisiones/auditoria.py` (`comprobar`, `registrar_hallazgos`) and
  `reglas/service._aplicar` (conflicts refuse the change); 5 tests in
  `decisiones/tests/test_auditoria.py`.
- `decisiones/service.resolver`: a person's decision is a new row, never an edit.

## Related
ADR 0001, 0004, 0009, 0010, 0015. Plan P2, P13, P14, P15, P16; PR #16.
