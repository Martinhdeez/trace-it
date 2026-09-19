---
status: accepted
---

# Let the reviewer agent learn a resolved escalation by amending the rule that escalated it

## Context
A manager resolves escalated invoices one by one in Revisión. The same kind of case comes
back, so we want the process to learn from the resolution: next time a similar case should
be decided by the engine. Three facts shape how:

- **Priorities.** In `processes/invoice-payment.json` ESCALAR is 3, NO_PAGAR 2, PAGAR 1, and
  the highest-priority fired rule wins (`decisions/engine.py`, `_combine`). A new PAGAR or
  NO_PAGAR rule never beats the ESCALAR rule that fired. Revisión's old "Resolver y crear la
  regla" did exactly that, so the case escalated again and nothing was learned.
- **Engine codes.** `MISSING_DATA` and `UNVERIFIED_DATA` are returned before any rule runs;
  `SOURCE_UNAVAILABLE`, `RULE_ERROR`, `RULE_NEEDS_DATA`, `RULE_COMPILE_FAILED`,
  `RULE_CONFLICT` and `SCAN_REVIEW` come from data, infrastructure or the combination of
  rules. No single rule's exception can remove them.
- **The old assistant.** `POST /instances/{id}/proposal` ran an LLM as soon as a case was
  opened, before the manager decided, and its `proposed_rule` never used the manager's
  decision. A late answer was stored even if the case had been resolved meanwhile (R04).

## Alternatives considered
- **A new PAGAR / NO_PAGAR rule from the manager's decision (what Revisión did).**
  - Pros: simple; already wired.
  - Cons: loses to the ESCALAR rule by priority; learns nothing.
- **Lower the priority of ESCALAR, or let a rule "override" another.**
  - Pros: any new rule could win.
  - Cons: changes the engine and the meaning of every past decision; "when in doubt,
    ESCALAR" (key decision B) stops being a guarantee.
- **Amend the one ESCALAR rule that fired, with an exception (chosen).**
  - Pros: it can only change cases that rule escalates; the engine stays untouched; it goes
    through the same draft, compile, validate and publish path as any rule.
  - Cons: only rule-based escalations with exactly one escalation rule are learnable; a
    NO_PAGAR that needs a new rejection rule goes to Definición → Normas instead.
- **An LLM explanation of why the case escalated.**
  - Pros: fluent text.
  - Cons: tokens on every opened case, English by default, and not reproducible. The reason
    codes and the rule summaries already say it; the console templates them (FE-2).

## Decision
- **Explain without an LLM.** Each escalation reason code has a Spanish sentence in the
  console, filled with symbol labels and the fired rule's `summary`. Opening a case costs 0
  tokens. The existing decision proposal stays, behind a button only.
- **Suggest after the decision, on a click.** `POST /instances/{id}/rule-proposal`, only on a
  resolved case. A pure gate, `proposals.service.learnable()`, runs first: the engine reason
  must be rule-based, exactly one escalation rule fired, and the other fired rules (or the
  default when none fired) must give the manager's decision. Otherwise 409 with the reason in
  Spanish and 0 tokens spent.
- **The reviewer agent** (role `assistant`, prompt `prompts/reviewer_agent.md`) writes the
  amended rule: `text` in English (it is compiled), `summary` and `rationale` in Spanish. Its
  context is small: the fired rule, the manager's decision and reason, the case's symbols,
  source column names, and people's resolutions of other cases the same rule escalated; no
  file text. An output validator sends back any `text` that names the case (file name,
  `file_id`, `invoice_number`).
- **Stored as a proposal** (ADR 0033): `channel: escalation`, `kind: rule`, payload
  `{decision_id, engine_decision_id, replaces, text, summary, type, decision, resolved_as,
  version_id}`.
- **Accept** creates the rule in the process draft, retires `replaces` there and compiles it
  in the background. It publishes nothing: the manager validates the draft (the source case
  must appear in `resolved_by_person` with `after == resolution`) and publishes it. A
  reprocess then decides similar cases with the new version.
- **Rejected vs ignored.** Rejected is explicit: `status: rejected`, `outcome.reason`, span
  `reject_proposal`. Ignored is what nobody settled: `status: superseded` with
  `outcome.cause` = `ignored` (the manager resolved another case), `version_published`,
  `case_changed` (this case got a new decision) or `superseded` (a newer suggestion on the
  same case), recorded by one `expire_proposal` event. All through `proposals.service
  .supersede(cause)`; no new status, no migration.
- **Stale answers are dropped (R04).** Both proposal kinds re-read the case's latest decision
  after the model answers; if it changed, nothing is stored and the answer is 409.
- **The engine is the baseline (R01 extended).** `decisions/audit.check` (Rule page impact)
  and `learning/validation.impact` compare with the engine's last decision. A case a person
  resolved is a conflict only when the new verdict differs from the engine and from the
  person.

## Consequences
- The manager gets a "learn this" path that can actually change the next decision, and sees
  every other case it would change before publishing.
- Learnable NO_PAGAR is limited to cases where a NO_PAGAR rule also fired.
- The live compile takes minutes and tokens; validate must wait until the rule leaves
  `compiling` (the console guards it, FE-4).
- The amendment is still LLM-written code. The blind tester, the draft validation and the
  manager's publication are the checks, as for any rule (key decision A).
- The demo pair first planned (`factura_41082` + `2026-0233-A_catering`, PO-2026-0492) cannot
  show the flip: both invoices are 1,512.50 and so is the whole order. See
  `docs/reviewer-agent.md` for the verified fallback pair.

## Evidence
- Gate per code and the stored proposal: `proposals/tests/test_reviewer_agent.py`
  (`test_what_no_amendment_can_learn`, `test_the_suggestion_amends_the_rule_that_escalated`,
  `test_a_rule_that_names_the_case_is_sent_back`,
  `test_a_case_no_rule_can_learn_is_409_in_spanish_and_spends_nothing`).
- Ignored vs rejected: `test_ignored_and_rejected_suggestions_differ`;
  `proposals/tests/test_api.py::test_resolving_without_the_proposal_closes_it_as_superseded_with_a_cause`;
  R04: `test_an_answer_that_arrives_after_a_resolution_is_not_stored`.
- The loop, with no LLM key: `test_the_program_learns_from_a_resolved_escalation` (two
  invoices escalated by the VAT-rate rule, one resolved, amended, accepted, validated,
  published, reprocessed: the sibling becomes PAGAR by the engine).
- Engine baseline: `decisions/tests/test_audit.py::test_the_baseline_is_the_engine_and_a_person_only_when_contradicted`,
  `learning/tests/test_api.py::test_a_resolved_escalation_the_norm_leaves_alone_is_no_conflict`.
- Golden 471/471 unchanged (`make test-e2e`).

## Related
Key decisions A, B, C, E. ADR 0001 (reviewed learning), 0002, 0008, 0014, 0031 (impact
before publishing), 0033 (proposal states). `docs/reviewer-agent.md`, `docs/api.md`.

## Update 2026-09-19: concise advice and "no rule" (#165)
Martín asked for shorter advice that proposes rules instead of asking the manager.
- Both agents answer within hard limits: character caps in the output models, sentence
  and single-line limits in the validators (`ModelRetry`), two retries instead of one.
- Every option of the decision assistant carries the English `rule` that justifies it.
- "No rule" is a first-class answer (`no_rule_reason`, Spanish) on both agents. The
  reviewer's is stored as an ordinary open `rule` proposal with an empty `text`, not a
  409. It keeps the proposal states of ADR 0033, it is traced like any agent answer, and
  it survives a reload without a new model call. The 409 stays for the pure `learnable`
  gate (no model called). Accepting it needs the manager's own `text`; otherwise 409.
- The manager's resolution reason is the reviewer's main input.
Evidence: `agents/tests/test_assistant.py` (`test_a_long_answer_is_sent_back`,
`test_every_option_carries_its_rule`, `test_no_rule_is_a_valid_answer`),
`proposals/tests/test_reviewer_agent.py` (`test_no_rule_is_a_proposal_the_manager_dismisses`,
`test_a_long_summary_is_sent_back`), live before/after in `docs/reviewer-agent.md`
("Advice contract").
