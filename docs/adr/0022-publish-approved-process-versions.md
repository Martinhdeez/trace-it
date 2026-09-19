---
status: accepted
---

# Require manager publication of complete process versions

## Context

ADR 0015 proposed immutable process versions, but rule status, outcome definitions,
symbols and shared use-case settings still independently controlled execution. Learning
adoption captured its own configuration without covering other mutation paths. The user
confirmed that every configuration publication requires manager approval and requested
captured inputs for deterministic replay on 2026-09-19.

## Alternatives considered

- Record configuration hashes without changing execution: smaller, but a hash cannot stop
  a pack reload or concurrent update from changing part of a running process.
- Version each configuration entity separately: precise, but assembly and publication need
  many relationships and consistency checks for small configurations.
- Publish a complete immutable snapshot: duplicates configuration, but supplies one unit
  for approval, execution, historical interpretation and rollback. Chosen.

## Decision

- Keep one editable draft and linear immutable published versions per process. Every
  publication requires a manager, the exact validated candidate, and unchanged preview
  evidence. Publish the whole candidate atomically.
- Include outcome definitions, symbols, description, exact rule artifacts, reviewer
  settings, approved guidance and pinned agent settings. Shared settings are authoring
  defaults; they do not silently update published processes.
- Compilation prepares artifacts only. Missing-data rules also stay outside execution
  until the missing inputs are addressed. This supersedes automatic activation in ADR
  0004 and the no-review adoption workflow in ADR 0017. Their compilation and normalization
  mechanisms remain in use. This also replaces ADR 0020's automatic enforcement of failed
  draft compilations. Failures in already published rules still escalate at runtime.
- Learning approval publishes its exact validated additions through the same module,
  without another approval and without including unrelated draft edits.
- Every new engine decision references a version and a batch execution. Capture source
  snapshot references, case symbols and the comparison population once per execution.
  Source refreshes are evidence changes, not process publications.
- Replay uses saved code and inputs through the current deterministic engine and sandbox.
  It never writes a decision or repeats optional LLM review.
- Historical queue classification and human resolution retain the decision's original
  outcome definitions. Reprocessing is explicit and never replaces human resolutions.
- Rollback republishes a prior configuration after current impact validation. Migration
  establishes a labeled current baseline; it does not invent versions for old decisions.

## Consequences

A process lock serializes execution, publication and evidence writes. Optional reviews
can delay publication; this is acceptable at current scale and avoids a worker framework.
Configuration and batch evidence occupy additional storage. Replay does not preserve the
Python runtime or promise reproducibility across future engine contract changes.

Existing rule activation/retirement endpoints now stage edits. CLI approval identifies a
manager and publishes once. `make demo` no longer implicitly approves configuration.
No frontend changes are included.

## Evidence

`features/versions/tests/test_api.py` exercises publication, changed preview evidence,
rollback, captured-input replay, concurrent approvals and historical resolution. Existing
learning and review tests cover adoption and optional review behavior. The golden API flow
now explicitly validates and publishes before deciding cases.

## Related

ADR 0001, 0004, 0008, 0015, 0017, 0021; [operation guide](../process-versions.md).
