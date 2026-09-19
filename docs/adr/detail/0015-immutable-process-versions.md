---
status: accepted
---

# Snapshot the whole process as an immutable version on every activation

Amended by ADR 0031: a version is created only when a manager publishes a validated draft.

## Context
ADR 0001 requires that "published process versions and past decisions are immutable" and
defines `simulate(draft_process_version, historical_cases) -> impact_report`. A process is
more than its rules: decision types (names, priorities, default, `requires_human`), symbols,
the description (context for the compilers) and policies (ADR 0007) all change what the
engine decides or how it is exported.

Today only rules are versioned (states draft/active/retired, a hash of text + code),
and each decision stores the hash of the rule set it applied (ADR 0008). Everything else is
edited in place: the pack loader upserts decision types and symbols with `session.merge` and
overwrites the description (`processes/definition.load_definition`). Reloading a pack with
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

**Update (2026-09-19).** Rule activation and retirement now only stage changes in the
process draft (`rules/service.py`, `activate`, `retire`). A new version is created by
`POST /processes/{id}/draft/validate` followed by a manager's
`POST /processes/{id}/draft/publish`. Going back restores an earlier version into the
draft (`restore_version_id`) and publishes it (ADR 0031).

## Consequences
- Replaying a past decision uses its own version, not the current configuration.
- Implemented through complete published snapshots and captured execution inputs in ADR
  0031. Legacy authoring tables no longer determine a published process's runtime behavior.
- Existing decisions retain unknown historical configuration rather than receiving a
  fabricated migration version. Replay is available for new captured engine executions.
- Listing versions and activating an older one in the UI (F9) builds on this.

## Evidence
The state before this decision:
- `processes/definition.py` (`load_definition`): `session.merge(DecisionType(...))`,
  `session.merge(Symbol(...))`, `process.description = data.description`.
- `decisions/model.py`: `Decision.rules_hash` identifies the rule set only.
- `decisions/engine.py` (`hash_rules`): hash over rule id and rule hash.

Today: `load_definition` stages its result in the process draft
(`processes/definition.py`); `Decision.version_id` references `process_versions`
(`decisions/model.py`); `features/versions/` holds drafts, publication and replay.

## Related
ADR 0001, 0007, 0008, 0014.
