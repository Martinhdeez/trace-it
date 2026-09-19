---
status: accepted
---

# Turn the client's norm into rules with an autonomous normalizer

## Context
The client's norm is `Norma_Pagos_v3`: six loose Spanish sentences in a workbook sheet
("Pagar solo si el NIF esta en el maestro y el IBAN ... coincide", "Ante duda razonable,
escalar"). Until now the 16 rules of `processes/invoice-payment.json` were our own hand
translation of it. A norm v4 arrives on Saturday in the same style, and the product owner
wants the app fully autonomous for non-technical users: they paste the norm, in any
language, and the system does the rest, with no human review step. The compiler (ADR 0004)
already turns one precise rule text into verified code; what was missing is the step from
a loose sentence to precise rule texts. The client thinks in sentences of their norm, not
in our atomic rules: one sentence ("NIF in the master and IBAN matches") needs several
checks, possibly with different decisions.

## Alternatives considered
- **Hand translation (what we had).**
  - Pros: a person reads every nuance; the texts are exact.
  - Cons: needs one of us for every norm change; not autonomous; the client cannot see
    which of their sentences a rule implements.
- **Normalizer plus human review of the proposed rules.**
  - Pros: a person catches misreadings before any code exists.
  - Cons: the users are not technical and cannot judge a rule text against the data
    model; the product owner ruled out the review step.
- **Fully autonomous normalizer, the norm's own tie-breaker, norm rules as the unit (chosen).**
  - Pros: no person in the loop; every choice is written down with the quote it comes
    from; the client's sentence stays the unit they own and see.
  - Cons: a misreading is not caught by the tester, which reads the same text.

## Decision
- A **norm rule** (`norm_rules`: process, number, the sentence exactly as written,
  `policies`) is the unit the client owns. Its **checks** are ordinary `Rule`s (one code,
  one decision) linked by `rules.norm_rule_id`, compiled and run exactly as before. The
  engine, decisions and results keep referencing the atomic rule; the norm rule is
  resolved through the FK.
- Agent role `normalizer` (`agents/normalizer.py`, platform prompt
  `prompts/normalizer.md`, configured per use case like any role, ADR 0011). Input: the
  norm, the use case description, decision types, symbols, sources with sample rows and
  the active rules. Output per sentence: `checks` `{text, type, decision,
  interpretation}`, `policies` (statements that are not checkable) and `covered` (ids of
  active rules already implementing it).
- Autonomy rules, process-agnostic, in the prompt: one condition per check; English text
  naming exact symbols and columns; never invent data (the compiler answers NeedsData).
- **Decision of a failed check** (revised 2026-09-19, product owner: "a rule not complied
  with rejects; a rule that cannot be applied escalates"). Each check reports
  `decision_source`: `explicit` when its sentence names the outcome of the failure in
  words ("no pagar", "rechazar", "escalar"), with those words in `quote`; `policy` when it
  does not. "Pagar solo si X" states a condition, not an outcome, so it is `policy`. A
  `policy` check gets the use case's `failed_check_decision` (normalizer `AgentSettings`,
  ADR 0011) in code, whatever the model wrote; without one, the model falls back to the
  norm's tie-breaker, then the most conservative type that requires a human. The
  validator rejects an `explicit` check whose `quote` is not in its sentence, and
  `normalize` refuses (409) a policy that is not a decision type of the process or is the
  default (it would pay). The invoice use case sets `NO_PAGAR`. Both fields are kept in
  the check's `report.norm`.
- **Cannot apply is not a failure.** A check whose value is missing or unusable, when
  neither its text nor the description says what to do, is escalated by the platform
  (`MISSING_DATA`, `RULE_ERROR`, `RULE_NEEDS_DATA`, `RULE_CONFLICT`, ADR 0016), never
  decided by the policy. The normalizer prompt says so, and the coder prompt makes such
  code raise instead of returning "does not fire". The invoice description adds that a
  rule comparing an impossible date does not fire (the validity check already fails), so
  the three impossible dates are rejected, not escalated.
- `POST /processes/{id}/run` and `/reprocess` refuse (409) while any rule of the process
  is `compiling`, or when none is `active` or `blocked`: a run started while the norm's
  checks compiled decided 500 invoices with no rule, all paid by default.
- Output validator (`ModelRetry`): decisions exist and are never the default type, check
  texts unique and not already active, `covered` ids exist, no empty sentence.
- `POST /processes/{id}/norm` (manager) creates the norm rules and their checks (status
  `compiling`), compiled in one background job, concurrently, at most
  `TRACE_COMPILE_CONCURRENCY` (default 5) at once; a recompile keeps `report.norm`,
  with the reading in each check's `report.norm`, and records a `normalize_norm` event
  with the whole output. `GET /processes/{id}/norm-rules` lists them with their checks.

## Consequences
- The tester and the coder both read the normalizer's text, so a misreading of the norm
  passes their loop. The external check is `make eval-norm`: norm -> normalizer ->
  compiler -> engine on the 471 text invoices of batch 1 against the golden outcomes.
- Interpretations are auditable per check and per norm rule, but nobody approves them.
- Migration `0004_norm_rules.py` (after `0003`).
- Not built: re-normalizing a changed sentence (a new norm is a new set of norm rules),
  retiring the checks of a replaced norm rule, a concurrency bound shared across jobs.

## Evidence
- `make eval-norm` on `Norma_Pagos_v3` (normalizer and coder `helmcode:deepseek-v4-flash`,
  tester `helmcode:qwen3.6`, temperature 0), two runs on 2026-09-19, no hand-written text:
  - Run 1: 6 norm rules, 11 checks, all 11 compiled valid on the first attempt; 466/471
    agree with the golden; 2.9 min, 23 agent runs. Mismatches: the 3 impossible dates
    escalated instead of NO_PAGAR (the normalizer applied "ante duda, escalar" to
    sentence 4), and the duplicated order PO-2026-0492 (2 files) paid, because "never pay
    the same order twice" was read only as "ERP status PAGADA".
  - Run 2: same 11 checks, all valid first time; **469/471**; 3.0 min, 24 agent runs,
    100k input + 77k output tokens (Helmcode has no price in PydanticAI, so cost reads
    $0). Only mismatch: the duplicated order is NO_PAGAR where the golden says ESCALAR (a
    team decision in the golden, not the norm's wording).
  - Temperature 0 is not deterministic across runs: the decision for a sentence the norm
    leaves open (4) changed between runs. Sentence 6 became two policies, no check.
- Tests: `agents/tests/test_normalizer.py` (context; unknown decision, default decision,
  duplicate text, already active text, bad `covered` id and empty sentence each retried;
  the endpoint creates norm rules whose checks all compile and keep `report.norm`;
  compilations bounded by the limit; operator 403),
  `evals/test_norm_eval.py` (the harness with scripted models: 436/471 with one check).

- Policy runs, `make eval-norm`, 2026-09-19, same models, `failed_check_decision` =
  `NO_PAGAR`, 11 checks, all `policy`, all `NO_PAGAR`, all valid first time:
  - With the new coder principle and no date convention: 466/471. The future-date check
    raised on the 3 impossible dates (`RULE_ERROR`), which escalated them; the duplicated
    order paid (sentence 5 read only as "ERP status PAGADA").
  - With the date convention: **469/471**, 1.3 min, 26 agent runs, 118k input + 51k
    output tokens; 433 PAGAR, 38 NO_PAGAR, 0 ESCALAR. Only mismatch: the duplicated order
    PO-2026-0492 (2 files) is NO_PAGAR (non-compliance with "nunca pagar dos veces") where
    the golden says ESCALAR (a team decision the policy supersedes).
- Tests: `agents/tests/test_normalizer.py` (policy applied to an unstated decision, an
  explicit decision kept, no policy leaves the model's, an unknown or default policy
  refused, a quote not in its sentence retried, the invoice use case sets `NO_PAGAR` and
  disables the share limit), `decisions/tests/test_api.py` (run and reprocess refused
  while compiling or with no enforced rule). The four escalation paths were already covered in
  `decisions/tests/test_engine.py`.

## Related
ADR 0003, 0004, 0006, 0011, 0016.
