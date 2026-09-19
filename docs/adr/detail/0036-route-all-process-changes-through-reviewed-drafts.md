---
status: accepted
---

# Route every agent-authored process change through a reviewed draft

## Context

A manager may provide a new policy, a replacement reference table, changed extraction fields,
or enough material to define an entirely new process. Treating each input as a special command
would split rule updates, source imports and process creation into separate workflows. Letting
an agent write published configuration directly would also confuse evidence with authority.

## Alternatives considered

- **Add one ingestion endpoint per kind of update.** Simple handlers, but the caller must know
  whether a file changes rules, context or source rows before the agent has inspected it.
- **Let the agent mutate live configuration.** Fast, but removes review, deterministic impact
  checks and an atomic boundary between old and new behavior.
- **Represent every update as a reviewed process draft (chosen).** Reuses discovery, preview,
  immutable versions and source snapshots for both new and existing processes.

## Decision

- Accept format-neutral **evidence assets**. The first supported tabular formats are XLSX, CSV
  and JSON; connectors continue to provide complete record sets. Uploading evidence grants no
  authority and has no runtime effect.
- Let the discovery agent inspect evidence and propose a typed **process change** to the full
  process definition: decision types, symbols, rules, source bindings, extraction hints,
  reviewer settings, guidance and examples.
- Use the existing process draft for both entry points. A draft without `process_id` proposes a
  new process; a draft with `process_id` starts from the active definition and proposes a delta.
- Keep discussion read-only. The caller must explicitly request a revision; attaching evidence
  counts as that request in the manager console. Every revision invalidates prior reviews and
  previews.
- Materialize accepted source bindings in ordinary code. Compile rules, run acceptance examples
  and historical impact, then require manager publication of the exact revision. Publication
  atomically creates or updates the process version and immutable source snapshots.
- Require each source change to declare `replace`, `append`, `upsert` or `delete`. Upserts and
  deletions identify rows with reviewed canonical key fields. Reject missing and duplicate keys
  before preview so an incremental asset cannot silently replace a complete source.
- Keep connector generation, unstructured file readers and unattended publication outside this
  decision. They can extend evidence acquisition without changing the review contract.

## Consequences

The agent can update any modeled part of process behavior without receiving direct write access
to live configuration. New-process inference and existing-process updates share one interface,
audit trail and failure model. Managers still resolve authority and ambiguous policy. Supporting
a new evidence format requires only a deterministic reader that produces the discovery table
representation; it does not require another publication path.

## Evidence

`processes/drafts.py` already starts from either an empty or active definition and publishes
through immutable versions. `sources/discovery.py` now normalizes XLSX, CSV and JSON evidence
before reviewed table mapping. The manager console exposes discussion and proposal modes.
Scripted discovery tests cover creation, update, preview and atomic publication without an LLM
key.

## Related

ADR 0001, 0007, 0008, 0015, 0031, 0024; [domain glossary](../../../CONTEXT.md).
