# Optional decision review

Add `decision_review` to a process pack or the body of `POST /processes/definition`:

```json
{
  "decision_review": {
    "guidance": "Recommend escalation when the evidence leaves the consequences of refusal uncertain. Explain the uncertainty and the evidence a manager should check.",
    "timeout_seconds": 30
  }
}
```

Include the rest of the process definition as usual. Omit the field or set it to `null`
to disable review. Guidance is process-specific and does not change rule compilation.
The invoice challenge pack leaves review disabled.

Configure the `decision_reviewer` agent role through the existing use-case agent endpoints
or `agents.decision_reviewer` in `use-case.json`. It supports model, instructions, fallback
models and other existing agent settings. `TRACE_DECISION_REVIEWER_MODEL` supplies the
default model. The process timeout bounds the entire assessment, including retries and
fallbacks; it defaults to 30 seconds and is at most 120 seconds. Missing keys, outages,
timeouts and invalid output produce a stored failure and retain the engine decision.

`POST /processes/{id}/run` assesses each new engine decision when enabled. Rule execution
and the returned `by_decision` counts remain deterministic. The first implementation runs
reviews sequentially inside the decision transaction, so enabled batches take longer;
instances stay locked until their decisions and reviews commit together.

`GET /instances/{id}` returns `reviews`, including the recommendation, reasoning, evidence
references and exact input snapshot. All findings are included, including false and
unevaluated results. Raw file text is limited to 12,000 characters and the snapshot says
whether it was truncated. Source snapshots have the same IDs and rows the engine used.
The model has no tools that can change data or execute downstream actions.

A differing recommendation sets `review_pending: true` on instance responses, adds the
case to `GET /processes/{id}/queue`, and contributes to the summary's queue count. The
instance remains DECIDED and its decision remains the engine's outcome. With a `type`
filter, the queue still filters by current outcome. Without a filter it also includes
reviewer disagreements for outcomes that do not normally require a person.

Resolve through `POST /instances/{id}/resolve` with `decision`, `reason` and the existing
`X-User-Id` header. A person can choose the engine outcome or any other allowed outcome.
The response retains the engine row and review and appends the person's decision.
`review_pending` then becomes false. A human-requiring outcome still remains in the
ordinary escalation queue, even if a person selected it.

Export returns 409 while a selected case has a pending reviewer disagreement. For engine
decisions with a review record, a later human resolution is exported. Without a review
record, the existing challenge export still prefers the engine outcome. Disabling the
reviewer does not remove an existing pending review or alter historical export behavior.
Named batch exports only consider that batch's cases.

Reprocessing runs reviews only for new, changed engine decisions. It preserves existing
pending reviews and reports conflicting engine outcomes in `conflicts`. Human resolutions
are also protected. Dry-run reprocessing and rule-impact checks compare deterministic
outcomes only; they do not preview agent recommendations. Reloading guidance or calling
`run` again does not reassess already-decided cases.

The current frontend uses an older API contract. This flow is available through the
backend API and process packs; console integration is separate.

## Learning guidance

Managers can adopt process-specific subjective norms through the [learning flow](learning.md).
Enabled reviews receive adopted guidance as `norm:<adoption_id>` evidence, alongside the
pack's base guidance. Each review snapshots the text it used. Draft and rejected norms
have no effect, and adopting guidance never grants permission to override an engine decision.
