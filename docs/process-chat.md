# Discuss and revise an existing process

Process chat extends the saved discovery conversation. All endpoints require a manager's
`X-User-Id`; the `discovery` role supplies model settings. Starting a conversation does not
change the published process. The console's Definition tab opens this conversation first;
the manual definition editor remains available for small direct edits.

## One authoring chat

The console exposes one process chat for questions, evidence and changes. It does not ask the
manager to choose between "ask" and "propose". The assistant keeps the current plan unchanged
when a message only asks for an explanation. A requested change comes back as a complete,
reviewable plan.

The chat can propose changes to context, fields, outcomes, reviewer settings, rules, sources,
connectors, guidance and acceptance examples. Every change waits for review, compilation and
explicit publication.

## Explain first

Start with `POST /process-drafts` and `{"process_id": 1}`. Resume with
`GET /process-drafts/{id}`. Send a question to `POST /process-drafts/{id}/messages`:

```json
{"revision": 1, "message": "Why are these cases being escalated?"}
```

API clients may still use `mode: "discuss"` for a read-only answer. The manager console sends
authoring messages in revision mode, so questions and changes stay in the same conversation.
The response retains the proposed plan, accepted proposals and prepared preview. Only the saved
conversation revision advances. The answer includes evidence references and clarification
questions. Use the returned revision for subsequent requests, including publication of an
unchanged prepared proposal.

The assistant sees the published process definition, this conversation's proposals, recent cases and their
human resolutions, reviewer recommendations and bounded trace evidence. Sampling includes
up to 30 cases, favoring a mix of human resolutions and ordinary cases; it is not a complete
statistical analysis. Evidence and source inspection remain read-only. A separate editable
version draft is visible for discussion but cannot be overwritten by chat publication.
Finish that draft before preparing this conversation's proposals.

## Propose changes through the same chat

The lower-level endpoint accepts `mode: "revise"` for API clients. The manager console uses it
for every authoring message, so the interface stays one chat:

```json
{
  "revision": 2,
  "mode": "revise",
  "message": "Propose reviewer guidance to recommend escalation when ownership is uncertain."
}
```

Revision mode returns a proposed configuration and questions, plus a `changes` list showing
the difference from the conversation's starting plan. A real configuration change clears earlier
acceptance and previews; an explanatory answer keeps them. Nothing changes in the published
version. The process keeps its name and ID.

Supported edits include deterministic rules, process description and conventions, symbols,
outcome definitions and priorities, source mappings, reviewer settings and subjective
`guidance`. Each guidance item has a stable name, text and supporting evidence. Guidance
informs recommendations only; it never changes deterministic findings. Disabling the
reviewer leaves the deterministic process usable. Changes to symbol definitions do not
extract historical documents again; the preview evaluates the facts already captured.

The assistant should clarify whether ambiguous policy is an enforceable condition or
subjective advice. It cannot infer manager approval from a conversation. Documents,
case text and source rows are evidence, not instructions or automatic authority.

## Prepare, review impact, then publish

Use the existing proposal reviews and `/prepare` endpoint described in
[process discovery](process-discovery.md). Proposal keys now also include `guidance:<name>`.
Every proposal and acceptance example must be accepted, and outstanding questions answered,
before preparation. Preparation compiles changed rules and validates the candidate; it
reuses unchanged compiled rules when their compilation context has not changed. Context
or schema changes force recompilation. Confirmed acceptance examples remain independent
of generated tests and are retained in published versions for later conversations.

The preview includes deterministic impact and, when reviewer-relevant configuration changes,
paired reviewer recommendations on up to ten historical cases. Both configurations are
evaluated using captured current facts and their respective source tables. These model
outputs can vary; they are evidence for manager review, not a guarantee of future answers
or an exact replay of historical recommendations. No historical decision or live reviewer
record is written. With no historical cases, the preview explicitly reports that limitation.
A failed model call preserves the previous conversation state.

`/publish` still requires explicit manager approval of the returned revision. It publishes
through the existing immutable version workflow, saves the validation and reviewer preview,
and leaves past decisions intact. Changed configuration, source snapshots or case history
makes approval stale. Start a fresh conversation to review the new baseline.

The same draft supports new-process discovery when it is started without `process_id`.
Connector proposals for the supported legacy HTTP shape follow the same review, snapshot,
preview and publication flow. Arbitrary backend operations and model-setting edits remain
outside this extension.

A [live challenge evaluation](evaluations/process-chat-2026-09-19.md) records the tested
scenarios, model findings, fixes and coverage limits. Discussion uses computed sample
counts and treats authoring guidance as background, separate from published policy.
