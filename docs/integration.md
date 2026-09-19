# Frontend-backend reconciliation

This page lists what the team agrees to build to join the console (`frontend/`) and the API (`backend/`).
Each feature gets one direction.
It is based on `origin/integration` @ 65bd45b (v1.0).
The detailed inconsistency matrix, the phases and the smoke test are in [integration-plan.md](integration-plan.md).
Numbers such as #2 refer to its matrix.

Sources:
- Backend: [api.md](api.md), [key-decisions.md](key-decisions.md), [adr/](adr/README.md), [process-versions.md](process-versions.md), [process-chat.md](process-chat.md), [decision-review.md](decision-review.md) and the OpenAPI spec.
- Frontend: `frontend/README.md`, [frontend/process-console-backend-requirements.md](frontend/process-console-backend-requirements.md) (the frontend's proposals to the backend), `frontend/src/api/*`, routes and UI text.
- The code was read only where these documents contradict each other. The frontend README says the proxy targets `:8000`, but `vite.config.ts` targets `:8010`. The README also says the API sends Spanish keys, but `live.ts` translates them.

**How the direction was chosen**
- **(a)** The backend adopts a frontend idea. Used when the frontend offers UX the backend lacks and the demo or the jury gains from it.
- **(b)** The frontend adopts the backend. Used when the backend already has the capability and the frontend fakes it or ignores it.
- **(c)** Both sides change and meet in the middle.
- **(d)** Drop or defer.

The backend owns business logic, data and decisions. The frontend never invents data.

Constraints from the plan:
- `decisions/engine.py`, the rules and the golden test (471/471) do not change.
- The backend changes only the contract: schemas, auth and errors.

---

## 1. Feature reconciliation matrix

| # | Feature | Frontend today | Backend today (endpoint) | Gap | Dir | Why | Effort | Owner |
|---|---|---|---|---|---|---|---|---|
| 1 | API mode and proxy | `VITE_API_MODE=auto` answers from the mock without warning when a call fails. The proxy targets `:8010` | Serves on `:8000` (`make setup`) | The demo can show seeded mock data and nothing says so (#1) | b | Only the backend has data. The mock becomes opt-in with a visible badge | S | FE |
| 2 | Login and identity | No login screen. A user is picked from a list in Settings. `signIn` is never called, so no user means no `X-User-Id` header | `POST /login {email}`, `GET /me`, header `X-User-Id` | Uploads and resolve fail with 422 when no user is picked (#5) | b | The backend already has login | S | FE |
| 3 | Roles and enforcement | Role checks only on Rule and ExecutionSettings | **Done (Q5).** A manager is required on `run`, `reprocess`, `sources/*/sync`, `POST /processes/definition`, draft publish, `resolve`, `ack` and `POST /users`. A missing or unknown `X-User-Id` returns 401 `unauthenticated`, a non-manager 403 `permission_denied`. Reads stay open | The frontend must send the manager's `X-User-Id` on every write | c | The backend enforces 401/403. The frontend hides what the role cannot do | M | BE+FE |
| 4 | Process list | Works. Fields mapped to Spanish (`nombre`) | `GET /processes` | Only the mapper | b | Read the English fields | S | FE |
| 5 | Process type and initialization metadata | Its requirements doc asks for `type`, `accepted_document_types`, `document_label` and `initialization` | None. `GET /processes/{id}/summary` has the counts | New fields for a second process type that does not exist yet | d | One process type today. The summary covers the counts | – | – |
| 6 | Process console (Panel) metrics | Latencia and Coste are hardcoded "—". The counts are derived on the client | `GET /processes/{id}/summary`, `/metrics/execution`, `/metrics/ingestion` | Placeholders and client-side maths (#20) | b | The backend already measures this | M | FE |
| 7 | Run history ("Ejecuciones") | Runs kept in React state for this browser session only | **Done (Q1).** `GET /processes/{id}/runs` (newest first: author, version, `rules_hash`, `by_decision`, `escalated`, `escalation_reasons`, `down_sources`, `trace_id`) and `GET /runs/{id}` (the decisions of that run), read from `executions`, `decisions.execution_id` and the run's span. No migration | The history is lost on reload. The frontend reads it from the backend | **a** | The frontend's run list is good UX. Add a thin read endpoint over data the backend already stores (Q1) | S | BE (+FE S) |
| 8 | Context (description) editing | Contexto → Guardar re-posts the whole process to `POST /processes/definition` | `PUT /processes/{id}/draft {description, expected_revision}` | The re-post stages a draft with `rules=[]` and resets `required` and `decision_review` (#2) | b | The draft API is the only safe way to write. The re-post breaks the demo | S | FE |
| 9 | Symbols (inputs) editing | Adding or removing a symbol re-posts `POST /processes/definition` | `PUT /processes/{id}/draft {symbols, expected_revision}` | Same data loss as #8 | b | Same reason as #8 | S | FE |
| 10 | Symbol types | Free text: `texto`/`numero`/`booleano` | `type: str`, with examples `text`/`number`/`date` | Spanish values are stored as they are, and `booleano` has no meaning in the backend (#15) | c | The backend declares an enum. The frontend shows a `<select>` with Spanish labels | S | BE+FE |
| 11 | Invoice template and chat chips | Spanish symbol names (`nif_emisor`, `pedido`) | The pack uses `issuer_nif`, `purchase_order`… | Rules written from the template name symbols that do not exist (#16) | b | The pack is the source of truth | S | FE |
| 12 | Rule detail | Two-compiler fields `codigo_a/b` and `tests_a/b`. `autor:'tester'` is hardcoded | One `code`, `tests` and `report` | Fake A/B data (#27) | b | The backend has one compiler and a blind tester (ADR 0004) | S | FE |
| 13 | Rule "Activar" | Presented as if it takes effect | `POST /rules/{id}/activate` only stages the rule into the draft | The manager thinks the rule is live (#18) | b | Publishing is what makes it effective (ADR 0015). Relabel it "Añadir a la versión" | S | FE |
| 14 | "Proponer" chat | Regular expressions in `proposalsFrom()`. Attachments are never uploaded | `POST /processes/{id}/norm` (normalizer). Discuss and revise under `/process-drafts/*` ([process-chat.md](process-chat.md)) | Fake AI in the headline flow (#13) | b | The normalizer is ADR A, the core of the pitch. "Proponer" covers rules and context, inputs and sources of truth, through three channels (Q2 decision below) | M | FE |
| 15 | Chat attachments | Shown as chips, never sent | Workbooks through `sources/workbook` or discovery `/workbooks` | Promises something that does not happen | d | Remove the chips. Workbooks go through Fuentes | S | FE |
| 16 | Create a process (form) | Spanish keys. The client checks one default and one human outcome | `POST /processes/definition` (English pack shape) | Mapper only. The backend validates too | b | One shape, the pack's | S | FE |
| 17 | Import JSON | Accepts only a Spanish shape. The repo's own packs throw a TypeError | `POST /processes/definition`. Rules with `code` files get 409 over HTTP | The import breaks on `processes/*.json` (#4) | b | Post the English pack as it is and show the 409 text | S | FE |
| 18 | Publish and versions | Validate and publish sit at the bottom of the Panel, with English copy. The version chip is computed on the client (`v{n}` = activation dates) | `GET/PUT /processes/{id}/draft`, `/validate`, `/publish`, `GET /processes/{id}/versions`, `active_version_id` | `make setup` leaves the pack unpublished, so Ejecutar returns 409. The version number is invented (#3) | b | Versions are the backend's (ADR 0015). Add a publish call to action and a real version chip | M | FE |
| 19 | Per-rule versions and rollback | Its requirements doc asks for immutable versions of each rule | Whole-process versions, and `PUT /draft {restore_version_id}` restores one | A different model | d | Process versions already cover rollback (ADR 0015, E) | – | – |
| 20 | Upload | One request per file, in sequence. `created:false` is ignored | `POST /processes/{id}/files`, `POST /instances/{id}/extract` | A re-uploaded PENDING file keeps stale symbols (#19). The requirements doc asks for a batch `/documents` endpoint | b | A per-file loop gives real progress. No batch endpoint is needed | S | FE |
| 21 | Run and progress | A 190 ms timer walks through fake stages. Its requirements doc asks for async runs, `GET /runs/{id}` and a per-run SSE | Synchronous `POST /processes/{id}/run` (~5 s ERP sync plus ~0.8 s for 500 invoices) → `RunSummary` | Invented progress (#12) | b | Upload progress is real per file. The run is short enough for an indeterminate state (Q3) | S | FE |
| 22 | Run errors | Generic error | 409 when nothing is published, while a rule is compiling, or when no rule is active | The manager cannot tell why a run failed | b | Show the backend's message | S | FE |
| 23 | `down_sources` and source status | `RunSummary.down_sources` is dropped. Source `status`/`error`/`checked_at` are not shown | `RunSummary.down_sources`, `GET /processes/{id}/sources` (ADR 0028) | Cases escalate `SOURCE_UNAVAILABLE` and the screen never says why (#10) | b | Resilience is on the rubric (E). The data already exists | S | FE |
| 24 | ERP sync | Calls `sources/erp/sync`. The URL `127.0.0.1:8009` is hardcoded as a label | `POST /processes/{id}/sources/{name}/sync`, `GET …/diff` | A made-up label. The diff is unused | b | Connectors live in the pack. Show the rows diff after a sync | S | FE |
| 25 | Cut-off date | `cut_off_date='2026-09-18'` is hardcoded in `live.ts` | **Done (Q4).** A required workbook form field (422 when missing, no default). It becomes the `parameters` source that R12 reads | The frontend decides R12's input (#9) | b | Business data belongs to the manager and the backend, never to a constant (Q4) | S | FE |
| 26 | Queue and tabs | Tabs are human outcomes, and items are filtered by `decision === tab` | `GET /processes/{id}/queue` also returns reviewer disagreements (`review_pending`) | Those cases are invisible until export returns 409 (#7) | b | The backend defines the queue | S | FE |
| 27 | REVISION vs `review_pending` | A `REVISION` state that never occurs (`listInstances('REVISION')` returns `[]`) | Status is `PENDING`/`DECIDED`, plus a `review_pending` flag and `reviews[]` (ADR 0016, 0021) | A state the backend dropped (ADR 0009 is superseded) (#8) | b | Show the flag and the reviewer's recommendation | S | FE |
| 28 | Resolve | `resolve`, then an optional `createRule` (two calls). No role check | `POST /instances/{id}/resolve`. Manager only (Q5) | Its requirements doc asks for an atomic resolve plus rule, review records and claim/release | d | `createRule` only stages a draft, so a half-done pair is harmless. One manager in the demo. Only a manager resolves (Q5) | – | – |
| 29 | Trace view | Built from `/instances/{id}`. `documents.generated.ts` is the fallback, and `DocumentPopup` always reads it | `GET /instances/{id}/trace` (spans, evidence, `exported_decision`), `/file` (PDF), `/document` | Bundled data in live mode (#11). Its requirements doc asks for `GET /documents/{id}/decision` | b | `/instances/{id}/trace` is that consolidated endpoint. Traceability is 20 points of the rubric | M | FE |
| 30 | Extraction fields vs symbol names | DocumentPane joins fields to symbols | Symbols use `issuer_nif`/`iban`. Extraction fields use `supplier_tax_id`/`payment_iban` | The evidence cannot be joined to its symbol (#17) | **a** | The trace view needs it. Add `FieldReading.symbol` (additive) | S | BE |
| 31 | Alerts | Not called. The Panel "alerts" card counts compiling rules, waiting cases and findings | `GET /processes/{id}/alerts`, `POST /alerts/{id}/ack` (ADR 0026) | A missing feature (#21) | b | Stale-decision alerts are part of key decision E | S | FE |
| 32 | Metrics and plane health | "—" placeholders. No health indicator | `/processes/{id}/metrics/{plane}`, `/health/planes` | Unused (#20) | b | The three traceability planes (C) become visible | S | FE |
| 33 | OCR and reviewer settings | Ajustes keeps them in localStorage, never sent | `GET /processes/{id}/execution` (presets), `PUT /processes/{id}/draft {execution, decision_review}` | Two UIs for one concern, and only one of them works (#14) | b | Configuration is versioned in the backend (ADR 0011) | S | FE |
| 34 | Model settings | Ajustes edits the workspace-wide use-case agents, with N+1 fetches | `GET /use-cases/{id}`, `PUT /use-cases/{id}/agents/{role}` | It looks like a per-process setting (#30) | b | Label it "caso de uso". Per-process models are not needed | S | FE |
| 35 | Live updates | Polls rules every 2 s while one compiles. No EventSource | `GET /events/stream` (SSE). It ignores `Last-Event-ID` | Its requirements doc prefers SSE with reconnect | c | Poll now. Then one `EventSource` per process. The backend reads `Last-Event-ID` (Q3) | M | FE+BE |
| 36 | Export | Works. A 409 opens a modal. The file is always named `outcomes.jsonl` | `GET /processes/{id}/export`. Batch export is CLI only (`make export-batch`) | No batch filter over HTTP | d | Batch 2 runs through the runbook's CLI | – | – |
| 37 | Decision types and colours | Colour hardcoded by name (PAGAR/APROBAR green…) | Names are per-process data, with `is_default`/`requires_human` on each type | Another pack renders all amber (#22) | b | Derive the tone from the backend's metadata | S | FE |
| 38 | Vocabulary | Spanish keys in `contracts.ts`, translated both ways in `live.ts`. `executionApi` and `DocumentEvidence` stay English | English snake_case everywhere | The root cause of #4, #8, #15 and #16 (#23) | b | English codes end to end. Spanish only as labels in `es.ts` (section 2) | L | FE |
| 39 | Typed contract | Hand-written types, and casts on every response | 16 auto-generated `operationId`s, duplicate `DraftOut`/`Evidence`, 7 untyped responses (#25) | No clean code generation | c | The backend cleans up the spec. The frontend generates types with `openapi-typescript` | M | BE+FE |
| 40 | Error shape | `http.ts` parses both shapes | `{code,message}`, plus Pydantic `{detail:[…]}` on 422 and plain text on 500 (#24) | Two shapes on the same status | **a** | One `{code,message,detail?}` shape, which the frontend already expects | S | BE |
| 41 | `executionApi` | A second client that bypasses the contract and the mock | – | Duplicate client (#28) | b | Fold it into the typed client | S | FE |
| 42 | Dead code | `routes/{Audit,Rules,Sources}.tsx`, `RuleSteps.tsx`, `listFiles` (invents `hash:''`), `uploadSource` | – | Fabricated fields (#29) | d | Delete it | S | FE |
| 43 | Reprocess | None | `POST /processes/{id}/reprocess?dry_run=` | Needed to act on an alert, besides Resolve | d | After the demo path. The API and CLI are enough for now | – | – |
| 44 | Learning | None | `/processes/{id}/learning`, `/norm-proposals/*` ([learning.md](learning.md)) | No UI for the bonus feature | d | Q6: no new UI. Learning shows in the run history (row 7): a rerun of the same invoices has fewer escalations | – | – |
| 45 | Discovery (new process by conversation) | Chat is the primary New process path; form and JSON remain secondary | `/process-drafts/*` ([process-discovery.md](process-discovery.md)) | Done | b | The saved conversation now includes review, preparation, impact and explicit publication | S | FE |
| 46 | User administration | Picker only | `POST /users`, manager only (#3) | – | d | Users come from the pack. The first manager is loaded by `make setup` | – | – |
| 47 | "Proponer": proposals to accept or reject | Regular expressions in `proposalsFrom()` | `GET /processes/{id}/proposals`, `POST /proposals/{id}/accept\|reject`, `POST /instances/{id}/proposal` ([api.md](api.md#proposals)) | Three channels (escalation, chat, learning), each with its own endpoints | c | One contract lists every proposal (decision, rule, context, input, source), and the manager settles each one | M | BE done, FE |

**Already aligned** (only the mapper changes, under #38):
- Assistant suggestion (`GET /instances/{id}/suggestion`).
- Rule create, compile and impact (`/rules/*`).
- Findings count (`/processes/{id}/findings`).
- Export with the 409 modal.
- Source list (`GET /processes/{id}/sources`).
- The static landing page.

**Counts per direction:** (a) 3, (b) 29, (c) 4, (d) 10. Total 46.

---

## 2. The contract: shared vocabulary

The API and the code use the English codes. The UI shows the Spanish label, from `frontend/src/i18n/es.ts` only.

**Decision-type names are data and are never translated.** `PAGAR`, `NO_PAGAR` and `ESCALAR` come from the pack, and the UI shows them as they are.
The tone of a decision type comes from its metadata:

| Metadata | Tone |
|---|---|
| `is_default` | positive (green) |
| `requires_human` | attention (amber) |
| anything else | negative (red) |

| Domain | API code | UI label (es) |
|---|---|---|
| Decision type (invoice pack) | `PAGAR` · `NO_PAGAR` · `ESCALAR` | PAGAR · NO_PAGAR · ESCALAR (verbatim) |
| Instance status | `PENDING` · `DECIDED` | Pendiente · Decidida |
| Instance flag | `review_pending: true` | Revisión del revisor |
| Decision author | `engine` · a person's name | Motor · the name |
| Rule status | `compiling` · `draft` · `active` · `blocked` · `retired` | Compilando · Borrador · Activa · Bloqueada · Retirada |
| Rule type | `requirement` · `prohibition` | Requisito · Prohibición |
| Symbol type | `text` · `number` · `date` | Texto · Número · Fecha |
| Role | `manager` · `operator` | Responsable · Operador |
| Alert status | `open` · `acknowledged` · `resolved` | Abierta · Vista · Resuelta |
| Alert trigger | `source_sync` · `rule_change` | Cambio en la fuente · Cambio de reglas |
| Source status | `ok` · `down` · `null` | Al día · Caída · Sin sincronizar |
| Plane | `ingestion` · `agents` · `execution` | Lectura · Agentes · Ejecución |
| Plane health | `ok` · `degraded` · `down` | Bien · Degradado · Caído |
| Review status | `completed` · `failed` | Completada · Fallida |
| Escalation reason prefix | `SOURCE_UNAVAILABLE:` · `RULE_ERROR` · `RULE_CONFLICT:` | Fuente no disponible · Error en la regla · Reglas en conflicto (the code stays visible) |

These are the invoice pack's symbol names (`processes/invoice-payment.json`).
The UI shows the Spanish label and the code in monospace:

| API code | Type | UI label (es) | Old frontend name |
|---|---|---|---|
| `file_id` | text | Fichero | – |
| `issuer_nif` | text | NIF del emisor | `nif_emisor` |
| `issuer_name` | text | Emisor | – |
| `iban` | text | IBAN | `iban` / `iban_cobro` |
| `invoice_number` | text | Número de factura | `numero_factura` |
| `date` | text (YYYY-MM-DD) | Fecha de emisión | `fecha` |
| `purchase_order` | text | Pedido | `pedido` / `numero_pedido` |
| `base` | number | Base imponible | `base` |
| `vat_rate` | number | Tipo de IVA | `tipo_iva` |
| `vat_amount` | number | Cuota de IVA | `cuota_iva` |
| `total` | number | Total | `total` |
| `free_text` | text | Texto libre | – |
| `parameters.cut_off_date` | date (source row) | Fecha de corte | hardcoded `'2026-09-18'` |

---

## Decisions (Martín, 2026-09-19)

These settle the open questions in section 3. Where a decision differs from the recommendation there, the decision wins.

- **Scope.** Integration changes functionality only. It never changes how the frontend looks.
- **Q1: run history.** It is a timeline of runs that makes going back easy. Any past run opens read-only and shows what it decided.
  - Backend: `GET /processes/{id}/runs` and `GET /runs/{id}` ([api.md](api.md)).
  - `by_decision` and `escalated` cover every instance a run evaluated. A rerun of the same invoices therefore compares directly with the run before it.
- **Q2: "Proponer".** The assistant proposes rules and also context, inputs and sources of truth. It does so through three channels:
  1. The escalation assistant explains why a case escalated and proposes decisions.
  2. The definition chat proposes changes, which the manager accepts.
  3. The learning agent proposes promotions from traces.
- **Q3: runs.** Runs stay synchronous. There is no worker and no per-run stream.
- **Q4: cut-off date.** The cut-off date is a required input on the workbook upload. There is no default value. The backend answers 422 when it is missing.
- **Q5: one role.** The app's user is the manager, who handles only escalations.
  - Every write needs a manager: run, reprocess, source sync, `POST /processes/definition`, draft publish, resolve, alert ack and `POST /users`.
  - A missing or unknown `X-User-Id` answers 401. A user who is not a manager gets 403. Reads stay open.
- **Q6: learning.** Learning gets no new UI. It shows in the run history: a rerun of the same invoices has fewer escalations.

## 3. Open questions for the team

Only the rows where the direction is a product choice. Each has a recommendation.

| Q | Row | Question | Options | Recommendation |
|---|---|---|---|---|
| Q1 | 7 | Should run history survive a reload? | (a) The backend adds `GET /processes/{id}/executions`, with each run's `created_at`, author, version and `by_decision`, taken from `decisions.execution_id`. (d) Show only `last_run_at` | **(a)**. It is a small read over stored data. The jury sees each run tied to a version, which fits traceability (C) |
| Q2 | 14 | What does "Proponer" call? | (b1) `POST /processes/{id}/norm`: the manager pastes norm text and gets checks that compile in the background. (b2) Process chat (`/process-drafts/*` discuss/revise → prepare → publish). (d) Remove the chat | **(b1) now, (b2) later**. `/norm` is one call, and it demos key decision A. Process chat needs sessions, reviews and a prepare step that takes minutes |
| Q3 | 21, 35 | Async runs with a per-run event stream, as the frontend's requirements doc asks? | (a) The backend adds `/runs`, a worker and per-run SSE. (b) The run stays synchronous: real upload progress, an indeterminate run, then the summary. Polling, then the existing `/events/stream` | **(b)**. A run takes about 6 s. An async runner is L effort and touches the decision path, which is frozen. Defer (a) until runs take minutes (ADR D triggers) |
| Q4 | 25 | What does the frontend send as the cut-off? | Required date input. Optional input. Its own endpoint to set `parameters` | **A required date input on the workbook form, with no default value.** It shows the current `parameters.cut_off_date` from `GET /processes/{id}/sources/parameters` when one exists. No new endpoint |
| Q5 | 3, 28 | Who may resolve and acknowledge alerts? | Manager only. Any identified user | **Manager only.** The pack says escalations go "to the human queue for a manager", and one manager runs the demo |
| Q6 | 44 | Learning in the UI for the jury? | (b) A Learning tab: analyse, proposals, validate, approve. (d) Demo it through `/docs` or curl | **(d) for the demo, (b) after.** It is about 6 h of frontend work, and validation waits up to 5 minutes. Show it with the commands in [learning.md](learning.md) |

---

## 4. Work order

The packages below are in demo priority order. Each one is a single PR into `integration`.

Every package has the same **done check**:
- `make check` is green, and the golden stays at 471/471.
- `npm run build && npm run lint` pass.
- The listed flow works with `VITE_API_MODE=live` against `make setup` (`:8000`), on a fresh database.

| WP | Rows | Owner | Files | Done check (flow, mock off) |
|---|---|---|---|---|
| 1. Backend contract | 10, 30, 39, 40 | BE | `backend/app/main.py`, `features/versions/{router,schemas}.py`, `features/learning/router.py`, `features/processes/{schemas,draft_schemas}.py`, `common/extraction.py`, `features/ingestion/{schemas,process_router}.py`, `Makefile` (`make openapi`), a unit test beside `main` | The spec has no `__` in any operationId and no duplicate schema name. A 422 validation error returns `{code:"validation_error",…}`. `/document` fields carry `symbol`. `symbols[].type` rejects `booleano` |
| 2. Frontend base | 1, 37, 38 (module), 39, 41, 42 | FE | `frontend/vite.config.ts`, `frontend/README.md`, `src/api/{client,http,execution}.ts`, new `src/api/schema.d.ts`, `src/i18n/es.ts`, `src/lib/status.ts`, `src/components/shell/AppShell.tsx`, and deletes the dead routes | With the backend stopped, the UI says "El backend no responde", not mock data. A MOCK badge appears only with `VITE_API_MODE=mock` |
| 3. Login and roles | 2, 3, Q5 | BE+FE | `backend/app/features/users/dependencies.py`, `features/{decisions,sources,processes,users,alerts,agents,rules}/router.py`, the API tests; `src/state/session.tsx`, new `src/routes/Login.tsx`, `src/App.tsx`, `src/components/shell/Notice.tsx` | Log in as `martin@trace-it.local` and reach the Panel. As `carlos@…`, Resolver is hidden and a direct `POST /resolve` returns 403. With no header, `POST /processes/1/run` returns 401. `make demo` still passes |
| 4. Panel and publish | 6, 7 (Q1), 18, 32 | FE (+BE `executions` list) | `src/routes/Process.tsx`, `src/components/process/ExecutionSettings.tsx`, `src/components/shell/Sidebar.tsx`; `backend/app/features/versions/router.py` | Open "Invoice payment", publish the draft from the call to action, and see `vN` from `/versions`. Latencia shows p50 from `/metrics/execution`. The sidebar dot follows `/health/planes`. Run history survives a reload |
| 5. Upload, run and sources | 20, 21, 22, 23, 24, 25 | FE | `src/components/run/BatchRunPanel.tsx`, `src/components/process/TruthSources.tsx`, `src/api/live.ts` (the workbook call) | Load the workbook with a typed cut-off date. Upload 20 PDFs and see n/20 with file names. Run and see `by_decision`. With `make erp` stopped, the summary shows `down_sources` and the source shows as "Caída" |
| 6. Queue and resolve | 26, 27 | FE | `src/routes/Queue.tsx`, `src/components/run/QueueList.tsx`, `src/lib/process.ts` | An ESCALAR case appears in its tab, and a `review_pending` case appears under "Revisión del revisor" with the reviewer's recommendation. Suggestion, then resolve: the queue count drops and export returns 200 or its 409 modal |
| 7. Trace view | 29 | FE | `src/routes/Instances.tsx`, `src/components/run/{TracePane,DocumentPane,DocumentPopup}.tsx`, and deletes `src/data/documents.generated.ts` | Open a case: the PDF from `/file` is visible, the evidence is joined by `symbol`, and spans and `exported_decision` come from `/trace`. The bundle does not contain `documents.generated` |
| 8. Definition | 8, 9, 10, 11, 12, 13, 14 (Q2), 15, 16, 17 | FE | `src/routes/{Definition,NewProcess,Rule}.tsx`, `src/data/seed.ts`, `src/api/contracts.ts` | Editing Contexto changes only `description` in the draft diff, and the rules and `required` symbols stay. Pasting `processes/travel-expenses.json` imports it. "Proponer" with norm text lists the checks from `/norm`, and they compile. "Añadir a la versión" links to publish |
| 9. Alerts | 31 | FE | `src/routes/Process.tsx` (card), `src/routes/Queue.tsx` (tab) | After an ERP sync that changes rows, an open alert shows `before → after`. Ack with a note, and it leaves the open list |
| 10. Settings | 33, 34 | FE | `src/routes/{ProcessSettings,Settings}.tsx` | An OCR mode or reviewer change appears in `GET /processes/{id}/draft`. `localStorage` holds no `trace.process.*` key. Models are labelled by use case, with one fetch |
| 11. Mock removal | 38 (finish) | FE | Deletes `src/api/{live,mock,types}.ts`, `src/data/invoices.generated.ts` and the Spanish types in `src/api/contracts.ts` | Repeat the WP3-WP9 flows. `grep -r "nombre\|tipos_decision" frontend/src` finds only labels |

**Later**, after the demo:
- `EventSource` on `/events/stream`, with the backend reading `Last-Event-ID` (row 35).
- Reprocess (row 43).
- Learning (Q6).
- An HTTP batch export (row 36).

If time runs short, WP1-WP7 are the jury path.
Until WP8 lands, **nobody clicks Contexto → Guardar or edits Inputs on the demo database** (row 8).
