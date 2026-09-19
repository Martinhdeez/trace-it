---
status: accepted
---

# Review engine decisions with optional advice and human approval

A process may supply guidance for an optional decision reviewer after all deterministic
rules have run. The reviewer recommends an existing decision type and explains its choice
with evidence references. It cannot change a rule finding or finalize a different outcome.
A recommendation that differs from the engine outcome puts the case in the human queue.
A person may accept it, reject it, or choose another allowed outcome, with a justification.

Review is disabled by default. Missing model configuration, provider failure, timeout or
invalid output records a failed review and leaves the engine outcome in force. Agreement
records an explanation without adding a review obligation. Existing engine escalations
continue to require a person, regardless of the reviewer's recommendation.

A decision review is append-only and belongs to one engine decision. It records its
recommendation, reasoning, evidence references, model, and an input snapshot including
process guidance, agent settings, all rule findings and the source loads used by the
engine. Review completion and the engine decision commit together. Review status is
separate from the instance's PENDING/DECIDED status and from the outcome. A later human
decision resolves the pending review without editing it. Reprocessing cannot replace a
pending review or a person's decision. Dry runs and rule-impact checks remain deterministic
and do not call the reviewer. Only newly appended engine decisions receive reviews;
changing guidance does not rerun reviews of unchanged historical decisions.

Export refuses cases with a pending reviewer disagreement. When the latest engine decision
has a review record, export uses a later human resolution when present. Otherwise it uses
the engine outcome, including when the review failed. Decisions made without the optional
step retain the challenge's existing engine-first export behavior. The stored record,
not the current setting, determines this behavior, so disabling review cannot bypass an
outstanding approval or undo an approved resolution.

This extends ADR 0001's separation of findings, recommendation and final decision, and
refines ADR 0002, 0009, 0014 and 0016 for processes opting into review. The deterministic
engine and its sandbox contract are unchanged. Re-running a model is a new assessment,
not deterministic replay. Full immutable process publication remains the work in ADR 0015.
