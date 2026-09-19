# Reviewer agent (agente revisor)

After a manager resolves an escalated invoice, the reviewer agent suggests how the process
can decide similar cases by itself next time. It amends the escalation rule that fired,
never adds a PAGAR or NO_PAGAR rule, because a new rule would lose to ESCALAR by priority.
No LLM decides: the manager accepts, validates and publishes, and the engine decides.
Why it works this way: [ADR 0035](adr/detail/0035-learn-from-resolved-escalations.md).
Endpoints and payloads: [api.md, Proposals](api.md#proposals).

Status: backend done (#152). Frontend: FE-1, FE-2, FE-3 and FE-6 built on Carlos's patterns
(see [Frontend implementation and merge notes](#frontend-implementation-and-merge-notes));
FE-4 and FE-5 in #162 ([their merge notes](#fe-4fe-5-merge-notes)).

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
   `channel: escalation`, `kind: rule`. Spans: `suggest_rule`, `llm_run` (both carry the
   instance id, so `GET /instances/{id}/trace` shows the model call).
   What the agent is given, besides the rule and the resolution: the case's symbols, the
   fired rule's own reason (`escalation.rule_evidence`), the other cases that reason names
   with their symbols and `same_as_case` (`escalation.related_cases`: the other invoice of
   a duplicate order), and the suggestions the manager already rejected on this case with
   their reason (`rejected_suggestions`). Its answer is sent back (up to twice) when it names the
   case or a related one, repeats a rejected rule, or quotes an identifier (a nif, an iban,
   an order) that is none of the values it was shown. It runs on the `assistant` role's
   settings with reasoning off and `max_tokens` 1500: about 450 output tokens a call,
   against 3.5k per call (9-15k with the fallbacks) when reasoning ran into the cap.
   The manager's own reason (`resolution.reason`) is its main input. Its answer is short
   by contract: `summary` one line (180 characters), `rationale` at most two sentences (320),
   `text` at most 600 characters; a longer answer is sent back, up to two retries.
   **"No rule" is a valid answer**: when the reason rests on something outside the data (a
   call, a document) or no condition separates the cases, the agent answers
   `no_rule_reason` instead of forcing a rule. It is stored as an ordinary open proposal
   with `payload.text: ""`, `payload.no_rule_reason`, the reason as `rationale` and a
   `summary` that starts `Sin regla:`. It uses the existing statuses: the manager dismisses
   it with Rechazar, or writes a rule in the textarea and accepts that. Accepting it with no
   text is 409. Why a stored proposal and not a 409: it is traced and auditable like any
   agent answer, it survives a reload without a second model call, and the current card
   already renders it (summary and rationale, an empty textarea, Aceptar disabled).
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

## Advice contract (#165)

Both agents that advise on an escalation are short on purpose, propose rules instead of
asking the manager what they think, and may answer that no rule should learn the case.
Code: `backend/app/features/agents/assistant.py`; prompts: `prompts/assistant.md`,
`prompts/reviewer_agent.md`. ADR 0035, update 2026-09-19.

**Length limits.** Characters and list sizes are capped in the output models
(`Field(max_length)`). Sentences and single lines are checked by the output validators
(`too_long` → `ModelRetry`). A violation sends the answer back; both agents have 2 retries,
then 502.

| Field | Limit |
|---|---|
| assistant `why` | 1-2 items, each one line, one sentence, ≤ 180 chars |
| assistant `reasoning`, `no_rule_reason` | ≤ 2 sentences, ≤ 320 chars |
| assistant `options[].consequence` | one line, one sentence, ≤ 180 chars |
| assistant `options[].rule`, `proposed_rule` | ≤ 600 chars (the longest rule of the invoice pack is 423) |
| reviewer `summary` | one line, one sentence, ≤ 180 chars |
| reviewer `rationale`, `no_rule_reason` | ≤ 2 sentences, ≤ 320 chars |
| reviewer `text` | ≤ 600 chars |
| `evidence` (both) | 1-6 references |

**Every option has a concrete rule.** Each assistant option pairs a decision with the
English `rule` that would justify it. The rule is new, or the escalating rule amended with
an exception (an escalation rule beats PAGAR and NO_PAGAR by priority), or `"Rule <id>"`
for an active rule that already gives that decision. Its Spanish `consequence` reads like
"Sí se podría pagar si se añade la regla: … (casos como este pasarían a PAGAR)" or
"No se debería pagar por la regla 9: …". Without `no_rule_reason`, a missing option rule,
`proposed_rule` or `proposed_type` is sent back.

**"No rule, always a person" is a valid answer.**
- Assistant: `no_rule_reason` (Spanish), with `proposed_rule` and `proposed_type` null.
  `decision` is still a final type (never `ESCALAR`). The prompt makes a missing or
  unverified datum always "no rule".
- Reviewer: `no_rule_reason`, stored as an ordinary open `rule` proposal. It has
  `payload.text: ""`, `payload.no_rule_reason`, the reason as `rationale`, a `summary`
  starting "Sin regla:", and `payload.type` taken from the old rule. The manager dismisses
  it (Rechazar → `rejected`), or writes a rule and accepts it with `text`. Accepting with
  no text is 409 "Esta sugerencia no trae regla: …". After a rejected "no rule", a second
  "no rule" is sent back. Span `suggest_rule` records `no_rule`.

**The manager's reason is the main input.** The reviewer generalises `resolution.reason`,
not what it would have decided. When that reason rests on something outside the data (a
call, a document) or no condition separates the cases, it answers "no rule".

### Before / after (live, deepseek-v4-flash, 2026-09-19)

Contexts built in the exact shape `_context` / `suggest_rule` produce, from the pack rules,
the golden symbols and the demo invoices. The full outputs are in PR #165.

**10 % VAT, rule 9 (`hosteleria_A_F26-0726.pdf`).**
- Before, assistant: 5 `why` paragraphs, a 10-line `reasoning`, and options like "Se aprueba
  el pago de la factura F26-0726 por 2.480,50 EUR al proveedor B96233419 en la cuenta …; el
  caso se cierra sin más revisiones." (892 tokens).
- After, assistant (601 tokens):
  - why: "Se escaló por la regla R09: el IVA de la factura es del 10 % en vez del 21 % habitual…"
    and "Los importes cuadran (base 2255,00 + IVA 225,50 = total 2480,50)…".
  - PAGAR: "Sí se podría pagar si se añade la regla: IVA del 10 % en hostelería no escala (casos
    como este pasarían a PAGAR)." with a rule amending R09.
  - NO_PAGAR: "No se debería pagar por la regla 9: el tipo de IVA impreso (10 %) no es el 21 %
    exigido." with rule `Rule 9`.
- Reviewer, after "La hostelería tributa al 10 %…":
  - text: "`vat_rate` is other than 21, unless `vat_rate` is 10 and the order of `purchase_order`
    exists with `total_amount` matching (±0.01) `total`."
  - summary: "Se exceptúa del escalado por IVA distinto de 21 % cuando el tipo es 10 % (hostelería)
    y el pedido cuadra."

**Duplicate order, rule 16 (`factura_41082.pdf` / `2026-0233-A_catering.pdf`, B96233419).**
- Before, assistant: PAGAR ("es una simple coincidencia de pedido"), with a 12-line
  reasoning and a 560-character rule.
- After, assistant: NO_PAGAR with **no rule**. no_rule_reason: "El mismo pedido
  PO-2026-0492 aparece en otra factura del proceso (2026-0233-A_catering.pdf) y no hay
  datos de esa instancia en el caso: una persona debe comparar ambas facturas y decidir si
  el pedido ya está cubierto." The options still pair PAGAR with a candidate amendment,
  and NO_PAGAR with `Rule 16`.
- Reviewer, after "Es la primera de las dos…": still a rule, the earliest invoice of the
  group (before and after). The reason states a data condition.
- Reviewer, after "He llamado a Catering Hermanos Pico: confirman que la buena es esta y
  anulan la otra.": **no rule**.
  - summary: "Sin regla: la duplicidad de purchase_order con importes idénticos sigue yendo
    a una persona; la anulación de la otra factura no consta en los datos."
  - no_rule_reason: "La decisión se basa en una llamada al proveedor que confirma cuál
    factura es válida y anula la otra: esa información no está en ninguna columna ni
    símbolo. Ninguna condición sobre purchase_order, importes o NIF distingue los
    duplicados que se pagan de los que se retienen, así que la regla 16 debe seguir
    escalando."

**MISSING_DATA (`sin_pedido_F26-0999.pdf`).**
- Before, assistant: NO_PAGAR plus a new rule "If `purchase_order` is empty … must not be
  paid", which goes against the policy that missing data goes to a person.
- After, assistant: NO_PAGAR with **no rule**. no_rule_reason: "Falta el purchase_order,
  un dato obligatorio que ninguna regla puede suplir: una persona debe obtenerlo del
  proveedor o del expediente antes de decidir."
- Reviewer: unchanged. The gate answers 409 before any model call.

Known gap: on the VAT case, the assistant's `proposed_rule` once named the file. The
reviewer's identifier check does not cover the decision assistant yet.

### Frontend integration notes (after Carlos's refactor)

No component changed in #165; `tsc -b` passes on the current `Queue.tsx`.

**Response fields that changed**
- `Suggestion` (`GET /instances/{id}/suggestion`), and the `payload` of a `kind: decision`
  proposal:
  - `options[].rule: string | null`: new.
  - `proposed_rule`: now nullable. In the payload, `proposed_rule` is `{text, type} | null`.
  - `proposed_type`: now nullable.
  - `no_rule_reason: string | null`: new.
- `payload` of a `kind: rule` proposal (`POST /instances/{id}/rule-proposal`):
  - `no_rule_reason: string | null`: new, always present.
  - `text`: may be `""` (a "no rule" answer).
  - `type`: always set (falls back to the old rule's).
- `POST /proposals/{id}/accept` on a rule proposal with empty `payload.text` and no `text`:
  409, Spanish `message`.

**Render**
- Decision proposal: `why` (≤ 2 lines), then each option's `consequence`, with its `rule`
  (English, small/monospace) under it. When `no_rule_reason` is set, show it as a line
  "Sin regla: {no_rule_reason}" and do not prefill any rule textarea from `proposed_rule`
  (it is null).
- Rule proposal with a rule: as today (summary, rationale, editable `payload.text`,
  "Sustituye a la regla N", Aceptar / Rechazar).
- Rule proposal with `payload.no_rule_reason`: show it as an answer, not a form:
  - the `summary` ("Sin regla: …") and the reason (`rationale`);
  - hide "Sustituye a la regla N" and the textarea;
  - "Entendido" = Rechazar with reason "Sin regla";
  - an optional "Escribir yo la regla" that opens the textarea, then Aceptar sends `text`.
  - Until then, the current card already works: empty textarea, Aceptar disabled.

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
- The rule text is editable before Aceptar (the textarea "Regla que entra con esta
  decisión", prefilled with `payload.text`); the edit goes as `text`.
- Aceptar → `POST /proposals/{id}/accept` `{reason?, text?}` → `outcome.rule_id` (plus
  `edited: true, original_text` when the text was edited): link to the Rule
  page (`/rules/{rule_id}`, status `compiling` → `draft`) and to Panel → Publicar.
- Rechazar → `POST /proposals/{id}/reject` `{reason}`.
- A "no rule" answer (`payload.no_rule_reason` set, `payload.text` empty) already renders
  sensibly in the current card: `summary` ("Sin regla: ..."), the reason as `rationale`, an
  empty textarea and Aceptar disabled until the manager writes a rule. When Carlos styles
  it: show it as an answer, not a form. Title "Sin regla: que lo siga decidiendo una
  persona", the reason below, hide "Sustituye a la regla N" and the textarea, and offer
  "Entendido" (Rechazar with reason "Sin regla") plus an optional "Escribir yo la regla"
  that opens the textarea (Aceptar with `text`).
- The decision proposal (`Suggested`) can show each option's `rule` under its
  `consequence`, and `payload.no_rule_reason` as a line "Sin regla: ..." when set; today
  it shows the consequence only, which already pairs the decision with its rule in Spanish.
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

### FE-4/FE-5 merge notes
Done in `feat/reviewer-agent-publish-impact`, functionality only, in Carlos's existing UI:
`components/process/ValidationImpact.tsx`, `components/process/PublishDraft.tsx`,
`routes/Process.tsx` (Panel alerts), `api/contracts.ts` (`ResolvedByPerson`),
`lib/paths.ts` (`reviewCase`), `i18n/es.ts` (`reviewerAgent` block). Each changed block has a
`reviewer-agent FE-n` comment. When merging a newer version, keep his UI and preserve:
- publish is blocked while a rule compiles (Validar and Publicar disabled, reason shown);
- the manager sees agree/contradict counts before publishing (`after === resolution`);
- escalation proposals link to their case (`review?i=<instance_id>`).

### FE-6. Client
- `api/contracts.ts` + `api/live.ts`: add
  `proposeRule(instanceId: number): Promise<Proposal>` →
  `post(`/instances/${instanceId}/rule-proposal`)`. `schema.d.ts` is regenerated here;
  re-run `make openapi` if the backend changes.

## Frontend implementation and merge notes

Built for Carlos, on his patterns: react-query through the typed client (`api/live.ts`,
`api/queries.ts` keys, `families` invalidation), his components (`Notice`, `ErrorNotice`,
`Button`, `Textarea`, `StatusBadge`, `TerminalLoader`), his classes only, no new styling.
The rule suggestion card follows #159's "preview, then accept" (`NormProposal`) and the
Definition inbox's "Rechazar needs a reason" (`InboxCard`). Every changed block carries a
`// reviewer-agent FE-n (docs/reviewer-agent.md)` comment with the invariants below.

| Package | Files | Components and what they do |
|---|---|---|
| FE-1 | `frontend/src/routes/Queue.tsx` | `Resolve`: the open decision proposal is listed (`listProposals`, `status=open`, `instance_id`, `kind === 'decision'`); `ask` mutation behind "Pedir propuesta al asistente", hidden on `SOURCE_UNAVAILABLE`; `Suggested` options clickable only while `open`; the Decisión dropdown lists only final types (no ESCALAR); one "Resolver" button |
| FE-2 | `frontend/src/routes/Queue.tsx`, `frontend/src/i18n/es.ts` (`escalationWhy`) | `explain()` and `WhyEscalated`: one Spanish sentence per code from the engine's decision (also on a resolved case), `symbols.*` labels and the fired rules' `rule_summary`; the raw reason stays as a chip |
| FE-3 | `frontend/src/routes/Queue.tsx`, `frontend/src/api/queries.ts` (`caseRuleProposal`), `frontend/src/api/contracts.ts` (`RuleProposalPayload`, `ProposalOutcome`), `frontend/src/i18n/es.ts` (`proposalCause`) | `Queue` keeps a resolved case open through `?i=`; `SuggestRule`: "Sugerir regla" → `proposeRule`; 409 `message` in a `Notice`; 502 `ErrorNotice` with Reintentar; the card (summary, rationale, `payload.text` in the editable "Regla que entra con esta decisión" textarea, "Sustituye a la regla N", Aceptar with the edited `text` / Rechazar with a reason; an edited accepted rule shows the agent's original); accepted shows the new rule and its status with links to the rule and Panel → Publicar; `rejected` shows its reason, `superseded` its `outcome.cause` |
| FE-6 | `frontend/src/api/contracts.ts`, `frontend/src/api/live.ts` | `proposeRule(instanceId)`; `make openapi` left `openapi.json` and `schema.d.ts` unchanged |
| Test | `tests/integration/demo-path.spec.ts` | no POST /proposal on opening a case; resolve; 409 on a MISSING_DATA scan; a rule suggestion stored with `tests.support.proposals rule`, shown, rejected, `Rechazada`; another edited then accepted: the created rule has the edit and `outcome.edited` |
| Backend | `backend/app/features/proposals/{schemas,router,service}.py`, `tests/test_reviewer_agent.py` | `AcceptIn.text`: accepting an escalation rule suggestion with an edited text creates that rule; `outcome` and the `accept_proposal` span record `edited`, `original_text` |

**Behaviour invariants a merge must preserve**

- Opening a case makes no LLM call: no `POST /instances/{id}/proposal` (nor `/suggestion`)
  until the manager presses the button.
- Resolving never waits on the rule suggestion; "Sugerir regla" only appears after it.
- A 409 from `/rule-proposal` shows the backend's Spanish `message` as is.
- Aceptar stages the rule in the process draft and does not publish; publishing stays in
  Panel → Publicar.
- `rejected` (the manager's no, with a reason) is shown apart from `superseded` and its
  `outcome.cause` (`ignored`, `version_published`, `case_changed`, `superseded`).
- Publish is blocked while a rule is compiling (FE-4, #162).
- The manager can edit the rule before accepting; the edit is what compiles, and the
  outcome records `edited` and `original_text`.
- The existing decision accept/reject stays: the assistant's decision proposal keeps
  Aceptar / Rechazar as on main, only asked for by the button.

**Endpoints and operationIds used**

| Call | operationId | Where |
|---|---|---|
| `GET /processes/{id}/proposals[?status=open]` | `listProposals` | `Resolve`, `SuggestRule` |
| `POST /instances/{id}/proposal` | `proposeDecision` | `Resolve` (button only) |
| `POST /instances/{id}/resolve` | `resolveInstance` (existing) | `Resolve` |
| `POST /instances/{id}/rule-proposal` | `proposeRule` | `SuggestRule` |
| `POST /proposals/{id}/accept` `{reason?, text?}`, `/reject` `{reason}` | `acceptProposal`, `rejectProposal` | `Resolve`, `SuggestRule` (`text` = the edited rule) |
| `GET /rules/{id}` | `getRule` | `SuggestRule` (the accepted rule compiling) |

**If this conflicts with Carlos's branch:** prefer his markup and styling, then re-apply
these invariants.

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
`changes` `ESCALAR → PAGAR`), Publicar, Reprocesar: B becomes `PAGAR` by the engine. The
PDFs are not in the repository; `make reviewer-demo-pdfs [OUT=<folder>]`
([`tools/reviewer_demo_pdfs.py`](../tools/reviewer_demo_pdfs.py), default
`output/reviewer-demo/`) writes A (`hosteleria_A_F26-0726.pdf`), B
(`hosteleria_B_F26-0717.pdf`) and `sin_pedido_F26-0999.pdf`, an invoice without a purchase
order that escalates `MISSING_DATA` and shows the 409 of a case no rule can learn. Upload
them like any invoice. The backend loop test
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
