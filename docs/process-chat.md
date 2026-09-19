# Discuss and revise an existing process

Process chat extends the saved discovery conversation. All endpoints require a manager's
`X-User-Id`; there is no new frontend or agent role. The `discovery` role supplies model
settings. Starting a conversation does not change the published process.

## Explain first

Start with `POST /process-drafts` and `{"process_id": 1}`. Resume with
`GET /process-drafts/{id}`. Send a question to `POST /process-drafts/{id}/messages`:

```json
{"revision": 1, "message": "Why are these cases being escalated?"}
```

Messages default to `mode: "discuss"`. The response retains the proposed plan, accepted
proposals and prepared preview. Only the saved conversation revision advances. The answer
includes evidence references and clarification questions. Use the returned revision for
subsequent requests, including publication of an unchanged prepared proposal.

The assistant sees published rules, this conversation's proposals, recent cases and their
human resolutions, reviewer recommendations and bounded trace evidence. Sampling includes
up to 30 cases, favoring a mix of human resolutions and ordinary cases; it is not a complete
statistical analysis. Workbook and source inspection remain read-only. A separate editable
version draft is visible for discussion but cannot be overwritten by chat publication.
Finish that draft before preparing this conversation's proposals.

## Propose changes explicitly

Use `mode: "revise"` when asking for edits:

```json
{
  "revision": 2,
  "mode": "revise",
  "message": "Propose reviewer guidance to recommend escalation when ownership is uncertain."
}
```

Revision mode returns a proposed configuration and questions, plus a `changes` list showing
the difference from the conversation's starting plan. It clears earlier acceptance and
previews. Nothing changes in the published version. The process keeps its name and ID.

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

New-process discovery remains available through its existing endpoints. Conversational
connector generation, arbitrary backend operations and model-setting edits are outside
this extension.
