---
status: accepted
---

# Build process drafts through documents and conversation before approval

## Context

Users need to create a process from scratch or revise an existing process by supplying
documents, connected sources and explanations of their work. A workbook can contain
policy, reference tables and informal notes together; its contents alone do not establish
which sources are authoritative or how ambiguous cases should be decided.
The current normalizer assumes decision types, symbols and sources already exist.
Its coder and tester share the interpreted rule text, so both can accept a misreading.

## Alternatives considered

- **Require a manually configured process pack.**
  - Pros: uses the existing implementation and makes configuration explicit.
  - Cons: requires technical help to discover tables, relationships and business rules.
- **Infer and activate everything from documents automatically.**
  - Pros: minimal user effort.
  - Cons: silently invents authority and policy where documents are incomplete or conflict.
- **Discover a draft through documents and conversation, then approve it (chosen).**
  - Pros: combines source evidence with user knowledge and exposes consequential choices.
  - Cons: requires persistent drafts, clarification and a manager's activation decision.

## Decision

- Support both entry points through one workflow: create a new process or start a draft
  from an existing process. A new process asks what decision is being made and proposes
  its decision types and symbols; an existing process retains its configuration as the
  starting point and presents changes. The first import implementation revises rules and
  sources in an existing process; it preserves its fields, outcomes and description.
  New processes establish their initial setup through the same conversation.
- Use one discovery agent to propose sources, table mappings, relationships, symbols,
  decision types and plain-language rules. Documents and chat both contribute evidence.
  Domain names and policies belong to process configuration; the workflow also supports
  other processes, such as hiring, without invoice-specific discovery logic.
- Persist a **process draft** with revisions, evidence references, questions, answers and
  proposal dispositions. Its interface supports starting discovery, answering or revising
  proposals, and approving a specific revision. Keep it separate from active configuration.
- Let users accept or reject proposals and explain their process in free text. Rejection
  prompts clarification when dropping the proposal would leave a required rule unresolved.
  Show what each answer changes. Reopen an accepted choice if new evidence contradicts it.
- Ask focused business questions about missing requirements, source authority, conflicting
  evidence and interpretations that change outcomes. Show the relevant passage or cells
  and the proposed effect. A table's existence does not make it a source of truth.
  Explicit user instructions override document rules for the draft, with the conflicting
  passage, instruction and justification retained for manager review.
- Read workbook cells, formulas and locations deterministically. Let the agent propose
  table ranges and mappings, then extract and validate complete tables in ordinary code.
  Retain provenance and surface unsupported or unreadable material as unresolved questions.
- Let discovery inspect the configured ERP through bounded read-only tools and its
  documentation. Reuse the existing connector for complete immutable snapshots. The
  agent searches those snapshots, and the engine reads snapshots only. Initially support
  the current ERP; arbitrary browser
  automation and generated connectors are outside this implementation.
- Feed confirmed plain-language rules and source definitions into the existing normalizer,
  tester, coder and sandbox. Record user-confirmed example outcomes as acceptance tests
  that compilation agents cannot revise. Invoice text remains case evidence and cannot
  override process policy. Unresolved requirements must be answered or assigned an explicit
  escalation behavior before activation.
- Show a concise summary of the draft, compilation results and preview outcomes. For an
  existing process, include impact against historical evidence. A manager approves the
  exact revision before activation; changing it invalidates that approval. Compilation
  success or low historical impact cannot bypass approval. Publish the revision together
  so cases cannot run against a partially installed process. Preserve past decisions.
- For the invoice rollout, encode the agreed examples: incorrect VAT, impossible dates,
  unreadable invoices, amount mismatches and disputed order ownership escalate; already
  paid orders and established absence from the supplier master reject. Duplicate invoices
  claiming one order both escalate until an approved selection rule exists. A missing or
  incomplete supplier source does not prove that a supplier is absent. Keep these choices
  in invoice configuration and acceptance examples, not platform policy.

## Consequences

The discovery module belongs with agents, reusing source readers and compilation; drafts
belong with processes. No agent per sheet or separate orchestration framework is needed.
Source coverage and authority remain reviewable rather than inferred silently.
The user clarified that this is a rule import workflow, not a new versioning subsystem.
Publication keeps the process identity and uses existing rule history and backtesting.
The confirmed draft revision identifies the imported rule set; changed rules are new rows,
old rules retire, and past decisions remain untouched. Structural revisions to existing
processes remain the separate concern of ADR 0015.
This workflow requires review instead of ADR 0017's autonomous import and ADR 0004's
automatic activation. Their existing endpoints and compilation mechanisms remain available.

## Evidence

The user confirmed both entry points, accept/reject plus chat, a summary before activation,
recorded user overrides and escalation for duplicate invoices on 2026-09-19.
`sources/excel.py` already retains workbook cells; `sources/workbook.py` maps fixed invoice
tables. `sources/http_connector.py` supplies ERP snapshots. `agents/normalizer.py` requires
existing process context; `agents/compiler.py` generates tests and code from that context.
These paths are under `backend/app/features/`. `processes/drafts.py` stores revisions and
publishes reviewed imports; `processes/draft_compilation.py` reuses the normalizer, compiler,
engine and audit. Scripted tests cover both entry points, manager conflicts, stale approval,
fixed acceptance examples, failed compilation and ERP sync, workbook precision and
preservation of history. A synthetic hiring process exercises the same interface.
This implementation is backend-only, as requested; no frontend is included.
**Update (2026-09-19).** The console's Definition screen now drives discovery sessions
(`/process-drafts`). Publication also carries the plan's description, decision types and
symbols for an existing process (`draft_compilation.candidate`), as one version.

## Related

ADR 0001, 0003, 0004, 0007, 0008, 0013, 0015, 0016, 0017; [domain glossary](../../../CONTEXT.md).

## Integration with process versions

Discovery sessions and their append-only revisions live in `discovery_sessions` and
`discovery_revisions`, introduced after versioning by migration 0012. A session is the
conversation and evidence record, not a second editable runtime version. Publication
uses the shared versions module and validates proposed source rows with the same
historical-error and human-review guards. Existing version drafts must be finished
before discovery can publish; they are never silently overwritten.
