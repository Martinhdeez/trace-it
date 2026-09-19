# Learning from past cases

A manager can request learning analysis for one process. The learner sees past decisions,
rule findings, human resolutions and their reasons, reviewer recommendations, and selected
operational spans. It proposes norms with supporting references, counterexamples and
limitations. It can also conclude that the history does not justify a proposal.

Analysis and validation never change rules, guidance or decisions. A manager must approve
each norm separately before it affects future cases. Approval of guidance does not approve
any individual decision: departures from the engine still need a person's resolution.

## Request, inspect, validate, approve

All learning endpoints require `X-User-Id` for a user with role `manager`.

| Method and path | Body | Result |
|---|---|---|
| `POST /processes/{id}/learning` | `{"case_limit": 30}` or `{}` | 201: analysis, captured context and up to five proposals |
| `GET /processes/{id}/learning?limit=20` | | Analyses, newest first; limit 1–100 |
| `GET /learning/{id}` | | Analysis and its proposals, validations and manager resolutions |
| `GET /norm-proposals/{id}` | | One proposal with the complete validation and adoption history |
| `POST /norm-proposals/{id}/validate` | | 201: a new immutable validation, including `report.valid` |
| `POST /norm-proposals/{id}/approve` | `{"validation_id": 12, "reason": "Reviewed the evidence and impact."}` | 201: manager adoption and published configuration snapshot |
| `POST /norm-proposals/{id}/reject` | `{"reason": "This is an isolated exception."}` | 201: manager rejection; no process change |

A proposal has `kind` (`deterministic` or `guidance`), `text`, `reasoning`, `evidence`,
`counterexamples` and `limitations`. Evidence references name `case:<id>` or `span:<id>`
entries in the analysis snapshot. Unknown references and exact duplicate proposal texts
are rejected by the learner's output validator. Semantic overlap still needs manager review.

Validation may return 201 with `report.valid: false`. Inspect the report before approval.
Model failures during validation are recorded as failed validations, so retrying adds a new
record without losing the previous attempt. Analysis failures return 502 and create no
partial analysis. Analysis requires at least one decided case; otherwise it returns 409.

Approval requires the latest successful validation ID. It returns 409 if the proposal was
already resolved, validation failed, or captured inputs changed. New decisions, source
loads, symbol corrections, rule/config changes and other norm adoptions require validation
again. Concurrent approvals of the same proposal publish it once. Approving a different
proposal changes the process, so other prepared proposals must be validated again.

## Deterministic norms

Validation reuses the existing normalizer, blind tester, coder and sandbox. It saves the
normalization, generated code, tests and reports in the validation record. It does not call
the live rule-creation path, which can automatically activate rules or enforce missing-data
rules by escalating cases.

A deterministic proposal must normalize to 1–8 checks and no subjective policies. Mixed
proposals need separate deterministic and guidance proposals. Missing data, failed tests,
runtime errors, conflicts with human decisions, or changed outcomes for cases awaiting
reviewer-requested approval prevent adoption.

The proposed checks run together with the enforced rules over decided instances using
stored symbols, the complete population for `others`, and sources captured at validation.
The impact report distinguishes engine outcome changes from human/review conflicts.
This is a simulation with current captured evidence, not a reconstruction of the original
historical inputs. Rules use temporary negative IDs in this preview only.

Approval publishes the exact tested code as ordinary active rules linked to one norm rule.
It also records findings for affected historical automatic outcomes, as the existing rule
adoption path does. Original decisions stay untouched. Future runs use the new rules;
reprocessing existing cases remains an explicit action through the existing endpoint.

## Subjective guidance

Guidance validation requires the process's optional `decision_review` to be enabled. For
up to ten sampled cases it calls the existing reviewer twice with the same captured
engine findings and evidence, once with current guidance and once with the proposed norm.
The report contains both recommendations, reasoning, evidence and model names, alongside
the case's final decision. These comparisons help a manager assess the guidance; they are
not deterministic tests or proof that the new recommendation is correct.

Approval records the guidance as an immutable adopted norm. Future reviews receive it as
`norm:<adoption_id>` in their evidence map, in addition to the base process guidance.
They can cite that reference in their reasoning. Their snapshots preserve the exact text.
Drafts and rejected proposals never enter live reviews. Guidance does not enable a disabled
reviewer, and disabling review retains its existing deterministic fallback behavior.

Guidance is process-specific. It does not modify the shared use-case agent instructions.
Reloading a process pack does not overwrite adopted guidance.

## Scope and operation

Set `TRACE_LEARNER_MODEL` or configure the `learner` role through the existing use-case
agent configuration endpoints. The role uses the same model fallback and trace recording
as other agents. No scheduler, worker queue or frontend is involved.

Analysis defaults to 30 cases, with an allowed range of 2–100. It reserves half the sample
for recent human-resolved cases and half for ordinary cases, filling unused slots from
either group. It includes up to three operational spans per requested case in total,
three sample rows per source and the latest 100 proposal texts. The analysis records the
sampling method; a sample is not a claim about the whole process.

Analysis has a two-minute deadline. Validation has a five-minute deadline, with the
existing per-case review timeout inside it. Both endpoints wait for their result. At this
MVP scale, validations store the captured process inputs, sources and history for audit;
large histories will need a separate batching/storage design.

Analyses, proposals, validations and manager resolutions are append-only. Each adoption
stores its exact norm, linked validation, generated rule IDs and a configuration snapshot
of the process, rules, guidance and agent settings at publication. Decision rule hashes
and reviewer norm references connect later execution to the adopted artifacts. Approval also publishes a complete immutable process version through the shared path
in ADR 0022. Existing drafts remain separate and must be rebased after publication. Guidance replacement/retirement
and editing a proposed sentence are not part of this initial flow; reject unsuitable
proposals rather than altering their evidence or text in place.
