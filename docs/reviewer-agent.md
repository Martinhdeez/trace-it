# Reviewer agent (agente revisor)

After a manager resolves an escalated invoice, the reviewer agent suggests how the process
can decide similar cases by itself next time. It amends the escalation rule that fired,
never adds a PAGAR or NO_PAGAR rule, because a new rule would lose to ESCALAR by priority.
No LLM decides: the manager accepts, validates and publishes, and the engine decides.
Why it works this way: [ADR 0035](adr/detail/0035-learn-from-resolved-escalations.md).
Endpoints and payloads: [api.md, Proposals](api.md#proposals).

Status: backend done (this PR). Frontend: work packages FE-1 to FE-6 below.

## Target flow

1. **Engine run** (exists). An invoice ends `ESCALAR`, with `reason` and `results`.
   Spans: `run_process`, `evaluate_rule`, `decision`.
2. **The manager opens the case in Revisión.** The console explains why it escalated with a
   Spanish sentence per reason code, built from `reason`, the fired rules' `summary` and
   the `symbols.*` labels (FE-2). No LLM call, no new span. The decision proposal
   (`POST /instances/{id}/proposal`) is still there, behind a button (FE-1).
3. **The manager resolves** with `POST /instances/{id}/resolve` (exists). It never waits for
   a suggestion. It now closes every other open proposal on the case (`case_changed`) and
   every open rule suggestion on other cases (`ignored`). Spans: `resolution`, then
   `expire_proposal` `{proposal_ids, cause}` when something was open.
4. **Nudge.** After resolving, Revisión offers "¿Quieres que esto se decida solo la
   próxima vez? [Sugerir regla]" (FE-3). The backend's gate decides whether it can help;
   the console shows its 409 message when it cannot.
5. **Sugerir regla** → `POST /instances/{id}/rule-proposal`. The pure gate
   `learnable()` runs first: 409 with a Spanish reason and 0 tokens when the case cannot be
   learned. Otherwise the reviewer agent writes the amended rule, stored as a proposal
   `channel: escalation`, `kind: rule`. Spans: `suggest_rule`, `llm_run`.
6. **The manager decides on the suggestion:**
   - **Accept** → `POST /proposals/{id}/accept`. The new rule is created in the process
     draft and `payload.replaces` is retired there; the rule compiles in the background.
     `outcome: {reason, rule_id, retired, draft_revision}`. Spans: `accept_proposal`,
     `save_rule`, `retire_rule`, `compile_rules`, `compile_rule`, `coder_attempt`,
     `run_tests`.
   - **Reject** → `POST /proposals/{id}/reject` `{reason}`. Status `rejected`. Span
     `reject_proposal`.
   - **Ignore**, by doing nothing: status `superseded` with `outcome.cause`.
7. **Panel → Publicar** (exists: `PublishDraft`). Validate only once the new rule left
   `compiling` (FE-4). `POST /processes/{id}/draft/validate` shows `changes` (other
   escalations that would now be decided by the engine) and `resolved_by_person` (the
   manager's own cases: agree when `after == resolution`). The source case appears there
   with `after == resolved_as`. Publishing records `publish_process_version` and closes open
   rule suggestions (`version_published`).
8. **Next time** (exists: `ReprocessAfterPublish`). `POST /processes/{id}/reprocess?dry_run=true`,
   then without `dry_run`: the sibling escalated invoice gets a new engine row with the new
   decision. The manager's own case is never re-decided. Spans: `reprocess`, `decision`.

## Rejected vs ignored

| | Status | `outcome` | Event | Who |
|---|---|---|---|---|
| Accepted | `accepted` | `{reason, rule_id, retired, draft_revision}` | `accept_proposal` | the manager |
| Rejected | `rejected` | `{reason}` | `reject_proposal` | the manager, explicitly |
| Ignored | `superseded` | `{cause: "ignored"}` | `expire_proposal` | the manager resolved another case |
| Out of date | `superseded` | `{cause: "version_published"}` | `expire_proposal` | a version was published |
| Case changed | `superseded` | `{cause: "case_changed"}` | `expire_proposal` | the case got a new decision |
| Replaced | `superseded` | `{cause: "superseded"}` | `expire_proposal` | a newer suggestion on the same case |

A settled proposal never changes again; accept or reject on it is 409.

## Frontend work packages (Carlos)

Functionality only; styles and components follow the console's existing patterns. The
typed contract is already regenerated (`frontend/openapi.json`, `src/api/schema.d.ts`).

### FE-1. No LLM when a case opens (R03, R13)
- `routes/Queue.tsx` (the `proposal` `useQuery` that calls `api.proposeDecision`): list
  the open proposals instead, `GET /processes/{id}/proposals?status=open`, filtered by
  `instance_id` and `kind === 'decision'`.
- "Pedir propuesta al asistente" becomes a button (a mutation on
  `POST /instances/{id}/proposal`), hidden when `reason` starts with
  `SOURCE_UNAVAILABLE`.
- A proposal's options are clickable only while `status === 'open'`.
- Remove `ESCALAR` from the resolve dropdown (only the final types).
- Done when opening a case makes 0 `POST /proposal` calls (Playwright `stack.spec.ts`).

### FE-2. Templated explanation
- `i18n/es.ts`: one sentence per code, and `WhyEscalated` fills it with
  `t('symbols.<name>')` and the fired rules' `rule_summary`. The code stays as a chip.

  | Code (`reason` prefix) | Sentence |
  |---|---|
  | `MISSING_DATA: a, b` | Falta {X}; sin ese dato el proceso nunca decide solo |
  | `UNVERIFIED_DATA: a` | Es un escaneo y no pudimos confirmar {X} |
  | `SOURCE_UNAVAILABLE: s` | No pudimos consultar {fuente}; vuelve a ejecutar cuando responda |
  | `RULE_ERROR n: ...`, `RULE_NEEDS_DATA`, `RULE_COMPILE_FAILED` | La regla {n} falló al evaluarse: es un fallo técnico, no de la factura |
  | `RULE_CONFLICT: ...` | Dos reglas piden decisiones distintas con la misma prioridad |
  | `SCAN_REVIEW: ...` | Las reglas lo rechazarían, pero es un escaneo y podría ser un error de lectura |
  | anything else (rule-based) | La regla «{summary}» pide revisión humana: {reason} |

### FE-3. Nudge and suggestion card
- Replace "Resolver y crear la regla" (it creates a PAGAR/NO_PAGAR rule, which never beats
  the ESCALAR rule) with a "Sugerir regla" button shown after the resolution.
- Click → `POST /instances/{id}/rule-proposal` (`operationId: proposeRule`, no body).
  - 201: a `ManagerProposalOut` with `channel: "escalation"`, `kind: "rule"`,
    `status: "open"`. Show `summary`, `rationale`, `payload.text` (English, what gets
    compiled), "Sustituye a la regla {payload.replaces}", and Aceptar / Rechazar (with a
    reason).
  - 409: show `message` as is: it is the Spanish reason why no rule can learn this case.
  - 502: the model failed; offer to retry.
- On reopening a resolved case, find its open suggestion with
  `GET /processes/{id}/proposals?status=open` (`instance_id`, `kind === 'rule'`,
  `channel === 'escalation'`).
- Aceptar → `POST /proposals/{id}/accept` `{reason?}` → `outcome.rule_id`: link to the Rule
  page (`/rules/{rule_id}`, status `compiling` → `draft`) and to Panel → Publicar.
- Rechazar → `POST /proposals/{id}/reject` `{reason}`.
- A suggestion that comes back `superseded` shows why from `outcome.cause`: `ignored`,
  `version_published`, `case_changed`, `superseded`.
- Done when resolve works with the card untouched and Aceptar stages the rule.
- Seed one with no LLM key for Playwright:
  `python -m tests.support.proposals rule <instance_id> "<rule text>"` (the case must be
  resolved and learnable; it prints the proposal id, or exits with the Spanish reason).

### FE-4. Impact line and compile guard
- `components/process/ValidationImpact.tsx`: add `validation.resolved_by_person`: "Tus
  decisiones: N — coinciden K, contradicen J" (agree when `after === resolution`), next
  to `changes` ("N escalados se decidirían solos").
- `components/process/PublishDraft.tsx`: disable Validate while any draft rule is
  compiling: `GET /processes/{id}/rules?status=compiling` is non-empty.

### FE-5. Panel links (R18)
- Proposals with `channel === 'escalation'` link to `review?i={instance_id}`; count open
  rule suggestions (`kind === 'rule'`).

### FE-6. Client
- `api/contracts.ts` + `api/live.ts`: add
  `proposeRule(instanceId: number): Promise<Proposal>` →
  `post(`/instances/${instanceId}/rule-proposal`)`. `schema.d.ts` is regenerated here;
  re-run `make openapi` if the backend changes.

## Demo pair

**Verdict: the planned pair cannot show the "learned" flip.** `factura_41082.pdf` and
`2026-0233-A_catering.pdf` both carry PO-2026-0492, both from P005 (Catering Hermanos Pico,
`B96233419`), both `total` 1,512.50 (`tests/golden/batch1_symbols.jsonl`). The order's
`total_amount` in `Pedidos_2026` is 1,512.50 and the ERP entry `AS-00492` is 1,512.50
`PENDIENTE`. Together the invoices are 3,025.00, twice the order: it is a real double
invoice. The expected amendment ("unless the invoices on that order together do not exceed
the order amount") keeps 41082 `ESCALAR`, which is correct, so nothing looks learned. The
rule "`total` matches `orders.total_amount`" also means two invoices of one order can never
both pass, so no sane amendment of the duplicate-order rule flips this pair. Batch 1 has no
other rule-based escalation among its text PDFs (the other 29 are scans, `MISSING_DATA`, not
learnable), and no text PDF has a VAT rate other than 21 %.

**Verified fallback: two hotel/catering invoices at 10 % VAT (rule "`vat_rate` is other than
21").** The workbook has open orders whose totals are exactly base × 1.10, unused by
batch 1, for example:

| Invoice | Supplier | Order | Base | VAT 10 % | Total = order = ERP (`PENDIENTE`) |
|---|---|---|---|---|---|
| A | P005 `B96233419`, IBAN `ES18 0081 5290 0700 0123 4567` | PO-2026-0726 | 2,255.00 | 225.50 | 2,480.50 |
| B | P001 (IBAN from the master) | PO-2026-0717 | 1,804.00 | 180.40 | 1,984.40 |

Checked with the hand-written v3 rule code in the real sandbox and the real sources
(workbook + ERP export), dated 2026-09-10:

- Current rules: both `ESCALAR`, reason `VAT rate 10`, only rule 9 fires.
- Rule 9 amended to "other than 21 and other than 10": both `PAGAR`, no rule fires.
- Batch 1 under the amended rule set: 0 of 471 decisions change (golden stays 471/471).

Script: resolve A as `PAGAR` with "La hostelería tributa al 10 %", Sugerir regla, Aceptar,
wait for the compile, Validar (A in `resolved_by_person` with `after: PAGAR`, B in
`changes` `ESCALAR → PAGAR`), Publicar, Reprocesar: B becomes `PAGAR` by the engine. The two
PDFs are not in the repository; generate them for the rehearsal with those values (any
invoice number and date up to 2026-09-18). The backend loop test
`proposals/tests/test_reviewer_agent.py::test_the_program_learns_from_a_resolved_escalation`
runs the same shape with no LLM key.

## Risks

- The live compile takes minutes and tokens: accept early in the demo; `POST
  /rules/{id}/compile` recompiles.
- Validating while the new rule is still `compiling` fails ("has no validated code"), so
  the draft cannot be published yet; FE-4 disables Validate until the compile ends.
- The process has one draft: discard or publish other staged edits before the demo.
- The model may write an exception that is too narrow or too broad: the validation numbers
  show it; reject and ask again.
