---
status: superseded
superseded_by: 0021
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

The process description (`Process.description`) already has a job: it states the domain
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
  `priority` among them. A tie between different types at the top priority is a
  configuration conflict and is not decided silently: the case escalates with the reason.
- A rule that fails to run escalates the instance too: the case decides the process's
  highest-priority `requires_human` type with `RULE_ERROR` as the reason (ADR 0016). Never
  the default, never silently.
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
- `decisions/engine.py` (`decide`, `Outcomes`): pure function over rule results and the
  process's priorities, default and escalation type; no database, clock, network or LLM.
  `test_engine.py` pins the default, the priority order, the tie and the failed rule.

## Related
ADR 0001 (refined), 0002, 0003, 0004, 0007, 0008, 0015, 0016.
