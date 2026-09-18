---
status: proposed  # pending Mateo's confirmation (owner of ADR 0001)
---

# Combine rule findings by decision-type priority only; process context never enters the automatic decision

## Context
ADR 0001 says: "A separate decision step then considers those findings together with
approved process context. Context can influence the recommendation or expose uncertainty,
but it cannot alter a deterministic rule finding." It does not say how context would be
considered. The only way to weigh free-text context against rule findings at runtime is a
model, and ADR 0002 already keeps LLMs out of the decision path: the challenge has a binary
filter, every decision must be replayable in a retroactive audit (ADR 0008), and a case can
carry text that tries to steer its reader (`factura_1936`).

The process description (`Proceso.descripcion`) already has a job: it states the domain
conventions every rule inherits (normalisation, units, tolerances, missing values), and the
compiler agents receive it as shared context (ADR 0003, 0004, 0007).

## Alternatives considered
- **Context-aware decision step with an LLM.** A model reads the rule findings and the
  process context and returns one of the process's decision types, or flags uncertainty.
  - Pros: closest literal reading of ADR 0001; could catch situations no rule covers.
  - Cons: non-deterministic; cannot be replayed from stored symbols, so audits and shadow
    backfills lose their meaning; exposed to prompt injection from the case; spends tokens
    per instance; its reasoning cannot be audited like a rule.
- **Rules only, combined by decision-type priority (chosen).**
  - Pros: deterministic and replayable; zero tokens per decision; every outcome traces back
    to the rules that fired.
  - Cons: a situation no rule covers falls to the default decision type; context helps
    only through better rules.

## Decision
- The automatic decision is a pure function of the rule findings and the process's decision
  types: no rule fires → the default type; one or more fire → the type with the highest
  `priority` among them. A tie between different types at the top priority, or a rule that
  names an unknown type, is a configuration conflict and is not decided silently.
- A rule that fails to run, or whose two codes disagree, sends the instance to REVIEW
  (ADR 0004, 0009); it is never mapped to a decision type such as ESCALAR.
- Process context (the description) feeds the compiler agents and the escalation assistant
  (explaining a case to the manager, proposing a rule). It never enters the automatic
  decision.
- This refines the ADR 0001 paragraph on "a separate decision step that considers findings
  together with approved process context": the decision step is the priority combination
  above, and context reaches it only through the rules it helped compile. The rest of ADR
  0001 stands.

## Consequences
- Gaps in the rules show up as default decisions, not as flagged uncertainty. The manager
  closes them by adding rules from escalations (the ADR 0001 learning loop), each checked
  against history before activation (ADR 0008).
- A system recommendation for an escalated case comes from the assistant, is stored apart
  from the decision, and never changes the exported result (ADR 0009).
- Changing the description changes future compilations, not past decisions; it is part of
  the process version (ADR 0015).

## Evidence
- `decisiones/motor.py` (`decidir`): pure function over rule results, priorities and the
  default type; no database, clock, network or LLM.
- Known gap: `decidir` sends rule failures, unknown types and priority ties to the highest
  `requires_human` type (ESCALAR for invoices); failures must go to REVIEW (ADR 0004).

## Related
ADR 0001 (refined), 0002, 0003, 0004, 0007, 0008, 0009, 0015.
