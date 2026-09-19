# Frontend-backend integration plan

Status: plan only. Checked against `origin/dev` @ cc1c3fb (frontend `frontend/src`, backend `backend/app`).
Inputs: the frontend and backend inventories and `openapi.json` from the same commit.
Work happens on `integration`, branched from `main` once v1.0 is merged (today `main` @ 710d421 is far behind `dev`).
Fixed constraints:
- `decisions/engine.py`, the rules and the golden test (471/471, `make test-e2e`) do not change.
- The frontend is Carlos's. The backend team only changes the contract (schemas, auth, error handlers), never decision logic.

Paths: `FE:` = `frontend/src/`, `BE:` = `backend/app/`.

---

## 1. Inconsistency matrix

Severity:
- **B**: breaks the demo.
- **W**: shows wrong data, or silently does something else.
- **C**: cosmetic, or dead code.

| # | Screen / feature | Frontend expects | Backend provides | Sev | Fix |
|---|---|---|---|---|---|
| 1 | All screens, API mode | `VITE_API_MODE` defaults to `auto` (`FE:api/client.ts:9`). On status 0, 501, 502-504 or 404 `http_error`, it silently answers from `mock.ts`. Vite proxies `/api` to **:8010** by default (`frontend/vite.config.ts:5`) | `make setup` serves on **:8000** (`docker-compose.yml:23`). Out of the box, the proxy gets a 502, so every screen shows the **seeded mock**, and nothing on screen says so | **B** | FE |
| 2 | Definition: Contexto → Guardar, Inputs add/remove symbol, chat `update_context` / `add_symbol` | `loadDefinition` / `replaceSymbols` re-POST `/processes/definition` with only name, description, types and `{name,type,description}` symbols (`FE:api/live.ts:178-239`) | The upsert **sets `decision_review=None`** and merges symbols with `required=false, extraction=None`. It also builds the draft candidate with **`rules=[]`** (`BE:features/processes/definition.py:131-160`). The result is a 409 when a draft exists. Otherwise it stages a draft with no rules and no required symbols, and a manager who publishes it runs a process that has no rules | **B** | FE (use `PUT /processes/{id}/draft`) |
| 3 | Panel → Ejecutar | Upload, then `POST /run`, with a generic error on failure | `run` returns 409 with no published version, while a rule is `compiling`, or when no rule is active. `make setup` loads the pack **without publishing it**. Publishing lives in `ExecutionSettings`, shown to managers at the bottom of the Panel, and its copy is in English | **B** | FE |
| 4 | NewProcess → Importar JSON | Spanish keys (`body.tipos_decision.map`, `FE:api/live.ts:181`) | The API takes the English pack shape, which is what `processes/*.json` use. An English file throws a TypeError that shows as "Algo ha fallado". Rules with `code` files get 409 over HTTP (`definition.py:83`) | **B** | FE |
| 5 | Identity | No login screen. `signIn` is never called. With no user picked in Settings, **no `X-User-Id` is sent** | Upload, workbook, document, resolve and ack need the header. A missing header gives 422 `x_user_id: Field required`, not 401 | **B** | both |
| 6 | Auth enforcement | Client-side gating only on Rule and ExecutionSettings | **No auth** on `run`, `reprocess`, `sources/{name}/sync`, `POST /processes/definition` (which also creates users), `POST /users` and `suggestion`. `resolve` and `ack` accept operators (`BE:features/decisions/router.py:120`, `alerts/router.py:31`) | W (security) | BE |
| 7 | Revisión queue | Tabs = human outcomes, and items are filtered by `decision === tab` (`FE:routes/Queue.tsx:45`) | The queue also returns **reviewer disagreements** (`review_pending`) whose decision is PAGAR or NO_PAGAR (`BE:features/decisions/service.py:526-546`). The UI hides them, so they stay invisible until export fails with 409 | W | FE |
| 8 | Instance status | `PENDIENTE \| REVISION \| DECIDIDA`. `listInstances('REVISION')` returns `[]` without calling the API. "En revisión" counts REVISION plus human outcomes | Status is only `PENDING`/`DECIDED`, plus a `review_pending` flag that `live.ts` drops. REVISION never appears | W | FE |
| 9 | Fuentes → workbook | `cut_off_date` is hardcoded to `'2026-09-18'` (`FE:api/live.ts:497`), with no input | Optional form field. It becomes the `parameters` source that R12 reads | W (decides R12) | FE |
| 10 | Run summary | Maps `decided` and `by_decision` only | `down_sources {name: why}`: those cases escalate `SOURCE_UNAVAILABLE`, and the UI never says why | W | FE |
| 11 | Document viewer | Falls back to the bundled `data/documents.generated.ts` when `/document` has no data. `DocumentPopup` always reads it | `GET /instances/{id}/file` serves the uploaded PDF, and `/instances/{id}/trace` has the evidence and `exported_decision`. Neither is used | W | FE |
| 12 | Run progress | A 190 ms timer walks through fake stages (`FE:components/run/BatchRunPanel.tsx:203-216`) | Uploads are sequential, so per-file progress is knowable. `run` is synchronous | W | FE |
| 13 | Definition chat "Proponer" | Regex heuristics in `proposalsFrom()` (`FE:routes/Definition.tsx:1118-1209`). Attachments are never uploaded | `POST /processes/{id}/norm` (normalizer LLM, manager) splits a norm into rules. Discovery lives in `/process-drafts/*` | W (fake AI) | FE |
| 14 | Ajustes (process) | OCR and "revisor opcional" are kept in **localStorage only** | `PUT /processes/{id}/draft` accepts `execution` and `decision_review`, which the Panel's ExecutionSettings already edits | W | FE |
| 15 | Symbol types | `texto`/`numero`/`booleano` in a free input (`FE:routes/NewProcess.tsx:359`, `Definition.tsx:687`) | `text`/`number`/`date` (`BE:features/processes/schemas.py:19`). Values are sent through untranslated | W | FE |
| 16 | Invoice template, chat chips | `nif_emisor`, `pedido`, `iban_cobro`… (`FE:data/seed.ts:22-32`, `Definition.tsx:85`) | The pack uses `issuer_nif`, `purchase_order`, `iban`… | W | FE |
| 17 | Symbol vs extraction naming | DocumentPane joins fields to symbols | Instance `symbols` use `issuer_nif`/`iban`/`purchase_order`. Extraction `fields` and `verify_fields` use `supplier_tax_id`/`payment_iban`/`purchase_order_ref` (`BE:features/ingestion/schemas.py:7,58-69`) | W | BE (additive) |
| 18 | Rule → Activar | Shown as if it takes effect | It only **stages** into the draft. Status stays `draft` until publish (`BE:features/rules/router.py:117`) | W | FE |
| 19 | Re-upload | Ignores `created:false` | A PENDING re-upload needs `POST /instances/{id}/extract` to refresh its symbols (`tools/demo_run.py` does this) | W | FE |
| 20 | Panel metrics | Latencia and Coste are hardcoded "—". Run history is React state for this session only | `/processes/{id}/summary`, `/metrics/{plane}` and `/health/planes` exist and are unused | W | FE |
| 21 | Alerts | Not called anywhere | `GET /processes/{id}/alerts`, `POST /alerts/{id}/ack` | W (missing feature) | FE |
| 22 | Decision colours | Hardcoded PAGAR/APROBAR = green, NO_PAGAR/RECHAZAR = red, anything else amber (`FE:lib/status.ts:7-22`, `routes/Process.tsx:497,524`, `components/run/TracePane.tsx`) | Decision names are per-process data. `travel-expenses.json` uses APPROVE/REJECT, which renders all amber. `is_default`/`requires_human` are already on each type | C (W for other packs) | FE |
| 23 | Vocabulary | `contracts.ts` uses Spanish keys, and `live.ts` translates both ways. `DocumentEvidence` and `executionApi` stay English, so the UI mixes both | English snake_case everywhere | C (root cause of 4, 8, 15, 16) | FE |
| 24 | 422 errors | `http.ts` parses both shapes | `{detail:[…]}` from Pydantic, and `{code,message}` for `invalid_document`/`sandbox_error`. Unhandled errors return a 500 in plain text | C | BE |
| 25 | OpenAPI for codegen | – | 16 auto-generated `operationId`s (`versions`, `learning`). Two `DraftOut` and two `Evidence` schemas, exported as mangled names. 7 operations return untyped `dict` (`execution`, `replay`, `extraction-plan`, `process-drafts` list and revisions, `/v1/ocr/config`, `/v1/batches*`) | C (blocks clean codegen) | BE |
| 26 | Realtime | Polls rules every 2 s while any rule is compiling. No EventSource | `GET /events/stream` (SSE, no auth). It ignores `Last-Event-ID`, so the client must pass `?after=` | C | FE (+BE 1 line) |
| 27 | Rule detail | Two-compiler fields `codigo_a/b` and `tests_a/b`. `got` is copied into both a and b. `autor:'tester'` is hardcoded | One `code`, `tests` and `report` | C | FE |
| 28 | `executionApi` | A second client that bypasses the contract and the mock. English strings | – | C | FE |
| 29 | Dead code | `routes/Audit.tsx`, `Rules.tsx`, `Sources.tsx`, `components/process/RuleSteps.tsx`, `api.health`, `listFiles` (which invents `hash:''`, `bytes:0`), `uploadSource`, `normalizeNorm` | – | C | FE (delete) |
| 30 | Model settings | ProcessSettings edits the **workspace-wide** use-case agent configs, with an N+1 fetch | The config is per use case, not per process | C | FE |

---

## 2. Decisions to take

### D1. One vocabulary
| Option | For | Against |
|---|---|---|
| **A. English codes end to end. The UI maps codes to Spanish labels only (`FE:i18n/es.ts`)** | One source of truth. Codegen types apply directly. Removes ~550 lines of mappers. Fixes #4, #8, #15, #16 and #23 at the root | Every screen changes its field names (`nombre` → `name`) |
| B. Keep `live.ts` translating at the edge | No screen churn | Every new field needs a mapper. Fields get dropped or invented (#8, #10). Codegen gains little |
| C. Spanish API | – | Breaks the ADR/CONVENTIONS rule "English everywhere", the CLI and the golden fixtures |

**Recommendation: A.**
- Decision-type names (`PAGAR`, `ESCALAR`) are **data**. The UI shows them verbatim and never translates them.
- Colours come from the type's metadata: `is_default` → positive, `requires_human` → amber, anything else → negative. This fixes #22.
- Enums the UI does translate: instance status, rule status, symbol type, role and alert status. Each gets one entry in `es.ts`.

### D2. Typed client
Nothing for codegen is installed today (`frontend/package.json`).
| Option | Deps | Notes |
|---|---|---|
| **A. `openapi-typescript` (dev dependency only), with the existing `http.ts` typed via `components['schemas']`** | +1 devDep, 0 runtime | Types only, no runtime code. Keeps `ApiError` and the header logic. Smallest change |
| B. `openapi-fetch` on top of A | +1 runtime dep (~6 kB) | Path-typed calls. It would replace `http.ts`, which already works |
| C. orval / hey-api generating TanStack hooks | +several | Generates a lot of code and fights the existing `queries.ts` keys |

**Recommendation: A.**
- `make openapi` writes `frontend/openapi.json` from `app.openapi()`, with no server or database, as the inventory already did.
- `npm run api:types` generates `FE:api/schema.d.ts`. Both files are committed.
- A PR that changes a router must regenerate them, and the diff shows up in review.

### D3. Mock policy
| Option | Notes |
|---|---|
| A. Delete the mock now | Honest, but it breaks offline design work in the middle of the migration |
| **B. Opt-in only (`VITE_API_MODE=mock`), `live` by default, `auto` removed, a visible "MOCK" badge. Each mock method is deleted when its screen migrates (Phase 1)** | No silent fallback. The mock dies naturally with the Spanish contracts |
| C. Keep `auto` with a banner | Still shows fake data during the jury demo when a port is wrong (#1) |

**Recommendation: B.**
- Also remove the live-mode fallback to `data/documents.generated.ts` (#11).
- The offline backup for the demo is a DB dump (`make backup`), not the mock.

### D4. Auth scope for the MVP
| Option | Notes |
|---|---|
| **A. Keep the `X-User-Id` identity, add a login screen (`POST /login` by email), and enforce the header plus role on every mutating endpoint. Missing header → 401** | About 1 day in total. It matches the existing `ponytail:` note in `users/dependencies.py`, and demo tooling already sends the header |
| B. Signed tokens (JWT) with a password or magic link | Real security, but it is not needed to judge a hackathon demo, and it touches every test |
| C. Nothing | Anyone can run, re-sync or rewrite a process (#6) |

**Recommendation: A.** The resulting role matrix:
- **Manager:** `run`, `reprocess`, `sources/*/sync`, `POST /processes/definition`, `POST /users`, `resolve`, `ack`, plus the endpoints that are already manager-only.
- **Any identified user:** `createRule`, `compileRule`, `suggestion`, uploads, `/me`.
- **Open reads:** unchanged, because it is a demo.
- The pack says escalations go "to the human queue for a manager" (`DecisionTypeIO`), so `resolve` is manager-only.
- JWT is recorded as a follow-up ADR, not built.

### D5. SSE vs polling
| Option | Notes |
|---|---|
| **A. Phase 1: TanStack `refetchInterval` polling where the data moves (compiling rules, queue, alerts, health). Phase 3: one `EventSource` on `/events/stream?process_id=` that invalidates query families by plane** | Polling already exists and works. SSE only adds live feel |
| B. SSE now | Blocks Phase 1 on the stream: reconnect logic, `after=`, and no auth on the stream |
| C. WebSocket | The backend has none |

**Recommendation: A.**
- Real run progress does not need SSE. Uploads are sequential, so the UI counts files. `run` shows an indeterminate state and then the summary.

### D6. CLI-only steps
| Step | Today | UI now (Phase 1) | Later |
|---|---|---|---|
| Publish the loaded pack (`make activate`) | CLI, or ExecutionSettings validate + publish | **Yes**: a "Publish version" call to action on the Panel whenever there is a draft and no active version (#3) | – |
| Workbook `cut_off_date` | Hardcoded | **Yes**: a required date input (#9) | – |
| Load a pack with rule `code` files / `load-frozen` | CLI | No: `make setup` / `make load-frozen` before the demo | Never over HTTP, by design |
| Bulk compile (`load --compile`) | CLI | No: the UI compiles one rule at a time | A "Compile all drafts" button that loops over `POST /rules/{id}/compile` |
| Batch export (`make export-batch`) | CLI | No | BE: `names` filter on `/export` |
| HTTP connector config (`sources.json`), ERP server | Disk only | No | Only if a second connector appears |
| Create a use case | Implicit | No | – |
| Migrations, OCR models, backup | Make | Never | – |

---

## 3. Phased plan

Effort is in focused hours. FE = Carlos. BE = the backend team.

### Phase 0: the contract (FE 7 h, BE 6 h)
| # | Task | Side | Files | h |
|---|---|---|---|---|
| 0.1 | Explicit `operation_id` on the 16 auto-named routes | BE | `BE:features/versions/router.py`, `BE:features/learning/router.py` | 1 |
| 0.2 | Rename the duplicate schemas: `DraftOut` → `VersionDraftOut` / `DiscoveryDraftOut`, `Evidence` → `ReadingEvidence` / `ProposalEvidence` | BE | `versions/schemas.py`, `processes/draft_schemas.py`, `common/extraction.py` | 0.5 |
| 0.3 | Response models for `GET /processes/{id}/execution`, `POST /decisions/{id}/replay`, `GET /processes/{id}/extraction-plan` and `GET /process-drafts` (+ revisions). `/v1/*` stays as it is: the UI does not use it | BE | `versions/router.py`, `ingestion/process_router.py`, `processes/draft_router.py` | 2 |
| 0.4 | One error shape: a `RequestValidationError` handler returning `{code:"validation_error", message, detail}`, and a catch-all returning 500 `{code:"internal_error"}` | BE | `BE:main.py` | 0.5 |
| 0.5 | Additive: each `FieldReading` gains the `symbol` it feeds (#17). No renames, no pipeline change | BE | `ingestion/schemas.py` and its mapper | 1 |
| 0.6 | A `make openapi` target that dumps `frontend/openapi.json`, plus a unit test: no `__` in any operationId and no duplicate schema names | BE | `Makefile`, `BE:tests` beside `main` | 1 |
| 0.7 | Add `openapi-typescript` (devDep), `npm run api:types`, and commit `api/schema.d.ts`. Type `http.ts` generics with `components['schemas']` | FE | `frontend/package.json`, `FE:api/http.ts`, `FE:api/schema.d.ts` | 1.5 |
| 0.8 | Mock opt-in: delete `withFallback`, default `live`, show a "MOCK" badge in `AppShell` when mock is on. Set the Vite proxy default to `:8000` (#1) | FE | `FE:api/client.ts`, `frontend/vite.config.ts`, `FE:components/shell/AppShell.tsx` | 1 |
| 0.9 | Vocabulary module: label maps for status, rule status, symbol type, role and alert status in `es.ts`, plus `decisionTone(type)` built from the `is_default`/`requires_human` metadata (#22) | FE | `FE:i18n/es.ts`, `FE:lib/status.ts` | 2 |
| 0.10 | Delete the dead code in #29 | FE | `FE:routes/{Audit,Rules,Sources}.tsx`, `FE:components/process/RuleSteps.tsx`, `FE:api/live.ts` | 0.5 |
| 0.11 | Fold `executionApi` into the typed client | FE | `FE:api/execution.ts` | 1 |

**Done when:**
- `make check` is green, and the golden stays at 471/471.
- `npm run build && npm run lint` pass with `VITE_API_MODE` unset.
- With the backend stopped, the UI shows "El backend no responde", not mock data.
- `schema.d.ts` has no `app__` names.

**Risks:**
- Renaming schemas changes nothing on the wire. Check that no test asserts on schema names in the spec.
- An error-handler change can alter a test that asserts `detail`. Update the test, not the behaviour.

### Phase 1: wire the screens, in demo order (FE 36 h, BE 1 h)
Each screen switches to the generated types, deletes its `live.ts` mapper and its `mock.ts` method, and reads English fields.

| # | Screen | Tasks | Files | h |
|---|---|---|---|---|
| 1.1 | Login | Email form → `POST /login` → `setUserId`. Keep the Settings picker as "change user". Redirect to login when there is no user. The role comes from `UserOut.role` | `FE:state/session.tsx`, new `FE:routes/Login.tsx`, `FE:App.tsx` | 2 |
| 1.2 | Process console (Panel) | `GET /processes/{id}/summary` feeds the metrics, pipeline and decision split. Colours from D1. **Publish call to action**: `GET /processes/{id}/draft` → validate → publish, shown when there is a draft (#3, #18). Map run 409 messages. Remove the session-only run history (use `last_run_at`) | `FE:routes/Process.tsx`, `FE:components/process/ExecutionSettings.tsx` | 6 |
| 1.3 | Upload + run | Real per-file progress (n/N, file name, OCR status). `created:false && PENDING` → `/extract`. Then run, with an indeterminate state and the `RunSummary` including `down_sources` (#10, #12, #19). Workbook upload gets a required `cut_off_date` input (#9) | `FE:components/run/BatchRunPanel.tsx`, `FE:components/process/TruthSources.tsx` | 5 |
| 1.4 | Revisión queue + resolve | Tabs = human outcomes **plus "Revisión del revisor"** for `review_pending` (#7, #8). Show the reviewer recommendation from `InstanceDetail.reviews`. Suggestion, then resolve, then optionally create the rule. Invalidate the queue, the instance and the summary | `FE:routes/Queue.tsx`, `FE:components/run/QueueList.tsx` | 4 |
| 1.5 | Trace view | TracePane from `GET /instances/{id}` + `/instances/{id}/trace` (spans, `exported_decision`). The PDF comes from `/instances/{id}/file` in an `<iframe>`. Evidence from `/document` uses `FieldReading.symbol`. Delete the `documents.generated.ts` fallback (#11, #17) | `FE:routes/Instances.tsx`, `FE:components/run/{TracePane,DocumentPane,DocumentPopup}.tsx` | 5 |
| 1.6 | Definition | Contexto and Inputs save through `PUT /processes/{id}/draft` `{description \| symbols, expected_revision}` and never re-post the definition (#2). Symbol type is a `<select>` of `text/number/date`. Import posts the pasted English JSON as it is and shows the 409 text for code files (#4, #15). The invoice template comes from the real pack's names (#16). "Proponer" calls `POST /processes/{id}/norm` (manager) and lists the checks it returns. The regex path and attachment chips are removed (#13) | `FE:routes/{Definition,NewProcess}.tsx`, `FE:data/seed.ts` | 7 |
| 1.7 | Rule | Map `code`/`tests`/`report` as they come. Drop the A/B fields. "Activar" becomes "Añadir a la versión", with a link to the publish call to action (#18, #27) | `FE:routes/Rule.tsx`, `FE:api/contracts.ts` | 2 |
| 1.8 | Alerts | Panel card and list: `GET /processes/{id}/alerts?status=open`, `before → after`, `trigger`, `evidence`, and an Ack button (`POST /alerts/{id}/ack {note}`). Poll every 10 s | `FE:routes/Process.tsx` (card), `FE:routes/Queue.tsx` (tab) | 3 |
| 1.9 | Metrics / health | `/processes/{id}/metrics/execution` (p50/p95, escalated, resolutions) and `/metrics/ingestion` (files/s, OCR calls) replace the "—" placeholders. `/health/planes` becomes a sidebar dot (#20) | `FE:routes/Process.tsx`, `FE:components/shell/Sidebar.tsx` | 3 |
| 1.10 | Settings | Remove the localStorage OCR and reviewer settings. Link to the execution settings, the real ones (#14). Label models as "workspace (use case)" and drop the N+1 fetch (#30) | `FE:routes/{ProcessSettings,Settings}.tsx` | 2 |
| 1.11 | Cleanup | Delete `api/live.ts`, `api/mock.ts`, `data/invoices.generated.ts`, the Spanish types in `api/contracts.ts`, and `api/types.ts`. Mock mode goes away with them | `FE:api/*`, `FE:data/*` | 1 |
| 1.12 | Backend support | Only if 1.2 needs it: expose `draft.revision` to operators read-only. Otherwise none | `BE:features/versions/router.py` | 1 |

**Done when** these flows work against the real API with no mock code left (e2e, manual or Playwright):
- Log in as `martin@trace-it.local`.
- Open "Invoice payment" and publish the pack draft.
- Load the workbook with a chosen cut-off, then upload 20 PDFs and watch real progress.
- Run and see `by_decision`.
- Open an ESCALAR case and see its PDF, symbols, rule results and spans.
- Get a suggestion, then resolve.
- Ack an alert, and see non-"—" latency.
- Export succeeds or shows the 409 modal.
- Editing Contexto keeps the published rules and the `required` symbols: the draft diff shows only the description.

**Risks:**
- #2 is the dangerous one. Until 1.6 lands, **nobody clicks Contexto → Guardar or edits Inputs on the demo DB**.
- `PUT /draft` is manager-only, so operators lose context edits. That is accepted.
- `norm` makes an LLM call that takes seconds, so it needs keys in `.env`. With no key, show the 502 message.
- 36 h is roughly 2 days of Carlos's time. If time runs short, 1.1-1.5 are the jury path. 1.6-1.10 can ship after the demo.

### Phase 2: auth and roles (BE 4 h, FE 3 h)
| # | Task | Side | Files | h |
|---|---|---|---|---|
| 2.1 | `current_user` raises 401 `unauthenticated` on a missing header | BE | `BE:features/users/dependencies.py` | 0.5 |
| 2.2 | Add a manager check on `run`, `reprocess`, `sources/{name}/sync`, `POST /processes/definition`, `POST /users`, `resolve` and `ack`. Add `CurrentUser` on `suggestion`, `createRule` and `compileRule`. Use a single `require_manager` dependency, reusing `rules/router.py:_manager_only` | BE | `decisions/router.py`, `sources/router.py`, `processes/router.py`, `users/router.py`, `alerts/router.py`, `agents/router.py`, `rules/router.py` | 2 |
| 2.3 | Update the API tests to send the header, and add one 401 and one 403 test. The golden tests and `test_frozen_rules` call services directly, so they are untouched | BE | `BE:features/*/tests/test_*api*.py`, `backend/tests/e2e/test_api_flow.py` | 1.5 |
| 2.4 | FE: role from `/me` on boot. Hide or disable manager actions (Ejecutar, Resolver, Ack, Publish, Sincronizar). A 401 goes to Login, a 403 shows a notice | FE | `FE:state/session.tsx`, `FE:components/shell/Notice.tsx`, screens from 1.2-1.8 | 3 |

**Done when:**
- As operator `carlos@trace-it.local`, resolve returns 403 and the button is hidden.
- As manager `martin@…`, the whole Phase 1 flow still passes.
- `curl -X POST /processes/1/run` with no header returns 401.
- `make demo` still works, because `tools/demo_run.py` already logs in as the manager.

**Risks:**
- The CLI and the ERP bridge are unaffected: they do not go through HTTP routes.
- Scripts that call `run`/`sync` without a header break. Grep `tools/` and `docs/runbook-batch2.md`.

### Phase 3: live updates and the rest (FE 20 h, BE 3 h)
| # | Task | Side | h |
|---|---|---|---|
| 3.1 | `useEventStream(processId)`: one `EventSource('/api/events/stream?process_id=…&after=<last id>')`. On `execution`, invalidate instances, summary and queue. On `agents`, invalidate rules. On `ingestion`, invalidate sources and instances. Then remove the 2 s rule polling | FE | 4 |
| 3.2 | Read the `Last-Event-ID` header as `after` on reconnect | BE | 0.5 |
| 3.3 | "Compile all drafts" button (a loop over `compile`) | FE | 1 |
| 3.4 | Reprocess (dry run → confirm) with `conflicts` shown | FE | 3 |
| 3.5 | Version history: `/processes/{id}/versions`, replay a decision | FE | 4 |
| 3.6 | Learning: analyse → proposals → validate → approve/reject | FE | 6 |
| 3.7 | `names` filter on `/export` (the CLI batch export over HTTP) | BE | 2 |
| 3.8 | Move every hardcoded string to `es.ts` (ExecutionSettings is English today) | FE | 2 |
| Later | Discovery sessions UI (`/process-drafts/*`), connector config, JWT | both | – |

**Done when:**
- Running a batch in one tab updates the Panel and the queue in a second tab within 2 s, with no manual refresh and no rule polling in the network log.

**Risks:**
- The SSE stream has no auth and polls the DB every 1 s per client. That is fine for a demo; cap the number of clients if the app is deployed.

---

## 4. Smoke test (after every phase)

Run from the repo root on `integration`. It needs `jq`, the challenge submodule and `make erp` in another terminal.

```bash
# 0. Backend + golden: decision logic untouched
make setup && make check                       # unit + golden 471/471 must stay green

# 1. Contract (Phase 0+)
make openapi && (cd frontend && npm ci && npm run api:types && git diff --exit-code src/api/schema.d.ts openapi.json)
jq -r '.paths[][].operationId' frontend/openapi.json | grep -c '__' | grep -qx 0 && echo "operationIds ok"
(cd frontend && npm run build && npm run lint)
grep -n "withFallback" frontend/src/api/client.ts && echo "FAIL: auto fallback still there" || echo "mock opt-in ok"

# 2. API flow the UI uses (headers as in Phase 2)
API=http://127.0.0.1:8000; J='content-type: application/json'
USER=$(curl -sf -XPOST $API/login -H "$J" -d '{"email":"martin@trace-it.local"}' | jq .id)
H="X-User-Id: $USER"
PID=$(curl -sf $API/processes | jq '.[]|select(.name=="Invoice payment").id')
REV=$(curl -sf -H "$H" $API/processes/$PID/draft | jq .revision)          # 404 = already published
HASH=$(curl -sf -XPOST -H "$H" $API/processes/$PID/draft/validate | jq -r .validation.hash)
curl -sf -XPOST -H "$H" -H "$J" $API/processes/$PID/draft/publish \
  -d "{\"revision\":$REV,\"validation_hash\":\"$HASH\",\"reason\":\"smoke\"}" >/dev/null || true
C=.context/500-sombras-de-alberto
curl -sf -H "$H" -F file=@$C/FINAL_v7_DEFINITIVO_ahorasi.xlsx -F cut_off_date=2026-09-18 \
  $API/processes/$PID/sources/workbook | jq '.sources|length'
for f in $(ls $C/facturas/*.pdf | head -5); do
  curl -sf -H "$H" -F "file=@$f" $API/processes/$PID/files | jq -c '{name,status,created}'; done
curl -sf -XPOST -H "$H" $API/processes/$PID/run | jq -c .                 # decided, by_decision, down_sources?
IID=$(curl -sf $API/processes/$PID/queue | jq '.[0].id // empty')
[ -n "$IID" ] && curl -sf -XPOST -H "$H" -H "$J" $API/instances/$IID/resolve \
  -d '{"decision":"NO_PAGAR","reason":"smoke"}' | jq -c '{id,status,decision}'
curl -s -o /dev/null -w "export %{http_code}\n" $API/processes/$PID/export   # 200 or 409
curl -sf $API/health/planes | jq -c '.[]|{plane,status}'

# 3. Auth (Phase 2+): expect 401 then 403
curl -s -o /dev/null -w "%{http_code}\n" -XPOST $API/processes/$PID/run
OP=$(curl -sf -XPOST $API/login -H "$J" -d '{"email":"carlos@trace-it.local"}' | jq .id)
curl -s -o /dev/null -w "%{http_code}\n" -XPOST -H "X-User-Id: $OP" $API/processes/$PID/run

# 4. UI (every phase): frontend against the real API, mock off
(cd frontend && TRACE_API_URL=$API VITE_API_MODE=live npm run dev)
# Walk: login → Panel → publish → workbook+cut-off → upload 5 → run → queue → resolve → trace (PDF visible) → alerts → export.
# Settings → api must list no "mock" source; stop the backend and the UI must say "El backend no responde".
```

Use a **fresh DB** for this run (`make reset-db && make setup`), never the demo DB: step 2 adds decisions and resolutions, and history is append-only.
