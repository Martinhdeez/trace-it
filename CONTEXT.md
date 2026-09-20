# Decision processes

Shared language for configuring processes and reviewing their decisions. Established
terms are also defined in [the conventions](docs/CONVENTIONS.md).

## Language

**Process draft**:
A proposed process definition for a new or existing process, including unresolved questions
and proposed source bindings. A manager reviews it before it becomes active.
_Avoid_: Setup chat, inferred process.

**Process definition**:
The complete behavior proposed or published for a process: its decision types, symbols,
rules, source contracts, extraction hints, reviewer settings and guidance.
_Avoid_: Rules, when referring to the whole configuration.

**Batch**:
A named cohort of instances received or run together. Different batches remain part of the
same process when they use the same decision policy. A later batch may run against newer
source snapshots and an existing batch may then be reprocessed without becoming a new process.
_Avoid_: Process, when referring only to a delivery of documents.

**Evidence asset**:
An uploaded file or connected record set that the agent may inspect when proposing a process
change. An evidence asset is not authoritative until a manager accepts a source binding or
policy proposal supported by it.
_Avoid_: Source of truth, upload source.

**Source binding**:
A reviewed mapping from an evidence asset or connector to a named source contract, including
the selected table, range and output fields. Publication materializes it as a source snapshot.
_Avoid_: Inferred source, live spreadsheet.

**Source snapshot**:
The immutable rows captured for a named source when a process version is published or a live
source is synced. The engine reads snapshots, never evidence assets or live connectors.
_Avoid_: Current data, mutable source.

**Process change**:
An agent-authored, evidence-backed proposal that replaces part of a process definition or its
source bindings. It has no runtime effect until review, preview and manager publication.
_Avoid_: Agent update, automatic edit.

**Source of truth**:
A source accepted as authoritative for specified facts in a process. Finding data in a
evidence asset does not by itself establish that authority.
_Avoid_: Any uploaded document.
