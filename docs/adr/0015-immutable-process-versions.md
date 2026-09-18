---
status: accepted  # implementation pending
---

# Snapshot the whole process as an immutable version on every activation

## Context
ADR 0001 requires that "published process versions and past decisions are immutable" and
defines `simulate(draft_process_version, historical_cases) -> impact_report`. A process is
more than its rules: decision types (names, priorities, default, `requires_human`), symbols,
the description (context for the compilers) and policies (ADR 0007) all change what the
engine decides or how it is exported.

Today only rules are versioned (states draft/active/retired, a hash of text + both codes),
and each decision stores the hash of the rule set it applied (ADR 0008). Everything else is
edited in place: the pack loader upserts decision types and symbols with `session.merge` and
overwrites the description (`procesos/definicion.cargar_definicion`). Reloading a pack with
a new priority silently changes how every future instance is decided, and no past decision
records which priorities it used.

## Alternatives considered
- **Per-rule versioning only (current draft).**
  - Pros: already implemented; enough for rule changes.
  - Cons: decision types, symbols, description and policies change in place; a past
    decision cannot be replayed with the configuration it was made with.
- **Full event sourcing of every process edit.**
  - Pros: complete history of every field.
  - Cons: overkill for the hackathon; rebuilding state from events adds code and queries
    for no decision we need.
- **Immutable snapshot of the whole process version per activation (chosen).**
  - Pros: one id says exactly what a decision was made with; matches ADR 0001's
    vocabulary; a draft version is what `simulate` runs on.
  - Cons: a snapshot per activation duplicates unchanged data (small at our scale).

## Decision
- Each activation or retirement of rules creates a new **process version**: an immutable
  snapshot of decision types, symbols, description, policies and the active rules with
  their code hashes. Versions are linear per process.
- Every decision references the process version it was made with (replacing the bare
  rule-set hash as the link).
- Edits to decision types, symbols, description or policies, from the app or a pack load,
  go into a **draft process version**. A draft becomes active only through the same path as
  a rule change: impact report over history (ADR 0008) and manager approval.
- The pack loader never overwrites decision types, symbols or the description of an active
  version in place (refines the loader contract in ADR 0007).
- Going back activates an earlier version as a new activation; it is recorded, not undone.

## Consequences
- Replaying a past decision uses its own version, not the current configuration.
- **Known gap:** the loader still uses `session.merge` on decision types and symbols and
  assigns the description directly; there is no process version table yet. Until this is
  implemented, change those fields only through a fresh setup.
- Listing versions and activating an older one in the UI (F9) builds on this.

## Evidence
- `procesos/definicion.py` (`cargar_definicion`): `session.merge(TipoDecision(...))`,
  `session.merge(Simbolo(...))`, `proceso.descripcion = datos.descripcion`.
- `decisiones/model.py`: `Decision.reglas_hash` identifies the rule set only.
- `decisiones/motor.py` (`hash_reglas`): hash over rule id and rule hash.

## Related
ADR 0001, 0007, 0008, 0014. Plan P13, P15; F9.
