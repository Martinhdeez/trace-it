---
status: proposed  # proposed | accepted | superseded (then add `superseded_by: NNNN`)
---

# State the decision as a short imperative sentence

## Context
What forces the decision: the problem, the constraints (challenge rules, deadline, team)
and what is already true in the code. Link evidence rather than restating it.

## Alternatives considered
- **Option A.** One line on what it is.
  - Pros: ...
  - Cons: ...
- **Option B (chosen).** ...
  - Pros: ...
  - Cons: ...

## Decision
What we do, in a few bullets or short paragraphs. Name the interfaces and invariants that
other code must respect.

## Consequences
What we accept losing or paying for, known gaps, and what becomes easier.

## Evidence
Measured numbers (say how they were measured), tests that pin the behaviour and code
references (`backend/app/features/...`). Keep measurements apart from estimates.

## Related
Other ADRs, pull requests. P-numbers refer to the archived
`.artifacts/archive/application-blueprint.md`.
