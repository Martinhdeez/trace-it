# Frontend handoff: wiring the console to the real API

For Carlos, who owns `frontend/`. The backend team owns `backend/`.
This page lists what to change in the console, package by package, in demo priority order.
Each package is one PR from `feat/fe-<package>` into `integration`.

Where this comes from:
- [integration.md](integration.md): the reconciliation matrix and vocabulary. "Row N" in this page means a row of its matrix.
- [integration-plan.md](integration-plan.md): the inconsistency list and the smoke test.
- [api.md](api.md) and `frontend/openapi.json` on `integration` after phase 0 (PR #91, merged at b9534a7). Operation ids are the ones in that spec.
- The frontend code on `origin/integration` @ b9534a7.
- The descriptions of the open backend PRs #92 (run history and manager auth) and #93 (proposals).

Paths: `FE:` is `frontend/src/`. `BE:` is `backend/app/`.

---

## Ground rules

**Functionality only, never aesthetics.**
- Allowed:
  - Replace fake or hardcoded values with real data in the slots that already exist.
  - Change copy (labels, hints, error text).
  - Add an element only by reusing an existing component with the props it already takes: `Button`, `Field`, `Input`, `Select`, `Textarea`, `Segmented`, `CountChip` (`components/shell/Controls.tsx`), `Notice`, `ErrorNotice`, `Empty` (`Notice.tsx`), `StatusBadge`, `DataTable`, `NestedCard`, `PageIntro`, `Overlay`, `DropZone`, and the route-local `ProposalCard`, `Suggested`, `Runs`, `Alerts` and `Metrics`.
- Not allowed:
  - New or edited `className`s, CSS, tokens, colours, spacing, icons, or layout grids.
  - A new screen design.
- If a feature cannot fit an existing component, stop and ask Martín before building anything.

**One user: the manager.**
- The person using the app is a manager, and a manager only handles escalations.
- Every write needs the manager's id in `X-User-Id`. `http.ts` already adds it to every request once `setUserId` has run, so the only work is to make sure a user is signed in (package 1).
- What changes when PR #92 (`feat/integration-backend-runs-auth`) merges:
  - A missing or unknown `X-User-Id` returns **401** `unauthenticated`.
  - A user who is not a manager gets **403** `permission_denied` on run, reprocess, source sync, `POST /processes/definition`, resolve, alert ack and `POST /users`.
  - The draft, publish, norm, chat, learning and rule activate/retire endpoints are already manager-only today.
  - PR #93's proposal endpoints are all manager-only too.
- Until #92 merges, most writes accept any user. A missing header returns **422** (`loc: ["header","x-user-id"]`), and an unknown id returns 404 on `/me`.
- The UI handles them like this:
  - 401, or a 422 on `x-user-id`: sign out and go to Login.
  - 403: show `ErrorNotice` with the backend's message.

**Vocabulary.**
- The code uses the English API codes end to end.
- `FE:i18n/es.ts` is the only place that turns a code into a Spanish label.
- Decision-type names (`PAGAR`, `NO_PAGAR`, `ESCALAR`) are data, and the UI shows them verbatim.
- A decision type's tone comes from its metadata: `is_default` is positive, `requires_human` is attention, and anything else is negative (see [integration.md §2](integration.md#2-the-contract-shared-vocabulary)).

**Types.**
- Type every response with `components['schemas']['<Name>']` from `FE:api/schema.d.ts`, which `npm run gen:api` generates.
- When a screen moves to the English types:
  - Delete its Spanish mapper in `live.ts`.
  - Replace its `mock.ts` method with `throw new ApiError(501, 'not_implemented', 'Sin mock')`. The existing `ErrorNotice` shows "Endpoint pendiente".
  - The mock shrinks screen by screen, until package 12 deletes it.

**Errors.**
- Domain errors are `{code, message}`:
  - `not_found` 404
  - `conflict` 409
  - `permission_denied` 403
  - `invalid_document` and `sandbox_error` 422
  - `llm_error` and `source_unavailable` 502
  - `internal_error` 500
- Request validation keeps FastAPI's 422 `{detail: [...]}`.
- `http.ts` `fail()` already parses both. Show `error.message` through `ErrorNotice`, and never a generic text when the backend sent one.

**Estimates.** S is half a day or less. M is about a day. L is about two days.

---

## 0. Setup

**Story:** As Carlos, I run the real backend locally and point the console at it, with the mock off.

**Depends on:** available now. Phase 0 (PR #91) is merged into `integration` at b9534a7. It gives you:
- **Proxy:** `/api` goes to `:8000` by default, and `VITE_API_TARGET` overrides it.
- **Mock:** the `auto` mode and its silent fallback are gone, so the real API is the default. The mock runs only with `VITE_API_MODE=mock`, and then a MOCK DATA badge (the existing `StatusBadge`) stays next to the logo.
- **Errors:** a failed call reaches `ErrorNotice`. When the backend is down (status 0, or a Vite 502/503/504 with no `{code}`), it says "El backend no responde".
- **Types:** `make openapi` writes `frontend/openapi.json`, then `npm run gen:api` writes `src/api/schema.d.ts`. Both files are committed.
- **Schema names:** `VersionDraftOut` (the process draft), `DiscoveryDraftOut` (the chat or discovery conversation) and `ProposalEvidence`. No `app__…` names are left.

### Backend

```bash
git switch integration && git pull
cp .env.example .env            # add LLM keys to use the assistant, norm, chat and learning
make setup                      # Postgres + API on :8000; loads processes/invoice-payment.json as an unpublished draft
make erp                        # another terminal: the challenge ERP on :8009. Every run syncs it first

# Your manager id (the pack's manager is Martín; the app user is always a manager)
MANAGER=$(curl -s -XPOST localhost:8000/login -H 'content-type: application/json' \
  -d '{"email":"martin@trace-it.local"}' | jq .id)

# Publish a runnable version. Pick one:
make load-frozen MANAGER_ID=$MANAGER    # no LLM keys: publishes "Invoice payment - frozen 2026-09-19"
make compile && make activate MANAGER_ID=$MANAGER   # with LLM keys: compiles and publishes "Invoice payment"
```

- Leave one process unpublished if you want to test the publish button (package 2): `make setup` alone leaves "Invoice payment" as a draft.
- OpenAPI docs: http://localhost:8000/docs.
- A fresh database: `make down`, then remove the `db` volume and run `make setup` again. Ask before you drop a shared database.

### Frontend

```bash
cd frontend && npm ci
npm run dev                                         # :5173, /api -> http://127.0.0.1:8000
VITE_API_TARGET=http://127.0.0.1:8001 npm run dev   # the API on another port
VITE_API_MODE=mock npm run dev                      # offline only; a "MOCK DATA" badge stays on screen
```

| Variable | Where | Default | Use |
|---|---|---|---|
| `VITE_API_TARGET` | shell or `frontend/.env.local` | `http://127.0.0.1:8000` | Vite proxy target. `TRACE_API_URL` is a legacy alias |
| `VITE_API_URL` | same | `/api` | Base path the client calls (`FE:api/http.ts`) |
| `VITE_API_MODE` | same | unset = real API | `mock` is opt-in only |
| `BACKEND_PORT`, `DB_PORT`, `ERP_PORT` | repo shell | 8000, 5432, 8009 | When a port is taken |
| `ANTHROPIC_API_KEY`, `HELMCODE_API_KEY`… | repo `.env` | empty | The assistant, norm, chat and learning. Without keys they return 502 `llm_error`, which the UI shows as a message |

### Typed API

- Every backend PR commits `frontend/openapi.json` and `src/api/schema.d.ts`. `backend/tests/test_openapi.py` fails when they are stale.
- After you pull, the types are current.
- If you ever need to regenerate them: `make openapi` from the repo root (it needs `uv`). It runs `npm run gen:api` too.
- `package.json` has an `overrides` entry. `openapi-typescript` 7.13 declares TypeScript `^5` as a peer dependency, and we use TypeScript 6. The override lets it use ours, because it only uses the printer API. Keep the entry. If `npm ci` complains about peers, check that the entry is still there, rather than adding `--legacy-peer-deps`.

**Done check:**
- `npm run dev` with the backend up: Procesos lists the real processes, with no badge.
- Stop the API: every screen says "El backend no responde".
- `npm run build && npm run lint` pass.

**Estimate:** S.

---

## 0b. Error states where there are none

**Story:** As the manager, when the API fails anywhere, I see why instead of an empty area.

**Today:** these components run queries but never read `isError`, so a failure shows nothing:
- `FE:components/shell/Sidebar.tsx`: the process list (`listProcesses`) stays empty.
- `FE:components/shell/CommandPalette.tsx`: the process and instance search (`listProcesses`, `listInstances`) shows no results.
- `FE:components/run/DocumentPane.tsx`: evidence (`getDocument`) quietly falls back to the bundled facsimile. After package 6, it would show a blank paper.
- `FE:components/process/ProcessScreen.tsx` (`ProcessTabs`): the tab header (`getProcess`, `listInstances`) shows "…" forever.

**Endpoints:** none new. These are the same queries.

**Changes:**
- In each component, when `query.isError`, render the existing `ErrorNotice error={query.error}` in the slot where the data would go:
  - Sidebar: in place of the process list.
  - CommandPalette: in place of the results list.
  - DocumentPane: in place of the paper, with no fallback to bundled data.
  - ProcessTabs: in place of the counts.
- If `ErrorNotice` is too large for the Sidebar or the palette, use `Empty` with `error.message`. Both exist, so there is no new styling.
- Keep TanStack's default retry (one retry for errors other than 4xx), and do not add polling.
- A 401 goes to Login through the `http.ts` callback from package 1, so these components never handle auth themselves.

**Vocabulary:** –

**Depends on:** available now.

**Done check (mock off):**
1. Open a process, then stop the API and reload.
2. The sidebar, the process tabs and ⌘K each say "El backend no responde" instead of staying empty.
3. Open `/processes/9999`: the tabs show the 404 message.
4. On a case with no stored document, the document pane shows the 404 message.

**Estimate:** S.

---

## 1. Login and identity

**Story:** As the manager, I sign in with my email, and every action I take carries my identity.

**Today:**
- There is no login screen. `session.tsx` `signIn` exists, but nothing calls it.
- A user is picked from a list in `routes/Settings.tsx`, and nothing is sent when none is picked. That gives 422s on upload and resolve (row 2).
- `isManager` compares with the Spanish `rol === 'responsable'`.

**Endpoints:**

| Method, path (operationId) | Headers | Body | Response fields used | Errors |
|---|---|---|---|---|
| `POST /login` (`login`) | – | `LoginIn {email}` | `UserOut {id, name, email, role}` | 404 unknown email, 422 |
| `GET /me` (`me`) | `X-User-Id` | – | `UserOut` | 404 stale id (for example after a database reset); later 401 |

**Changes:**
- `FE:api/live.ts`:
  - `login` returns `UserOut` as it is.
  - Add `me()`.
  - Drop the `user()` mapper.
- `FE:state/session.tsx`:
  - Store `UserOut`.
  - `isManager = user?.role === 'manager'`.
  - On boot, when a user is stored, call `me()`. On 404 or 401, run `signOut()`.
  - Keep the `trace.usuario` key. It only holds identity.
- `FE:api/http.ts`: after `fail()`, when the status is 401, or 422 with `x-user-id` in `detail[].loc`, call a registered `onUnauthenticated` callback. `session.tsx` sets it to `signOut` plus a redirect to `/login`.
- A new `FE:routes/Login.tsx`:
  - `PageIntro`, a `Field` with an `Input type="email"`, and a primary `Button` "Entrar", which calls `signIn`, then navigates to `/processes`.
  - Errors go through `ErrorNotice`.
  - Copy the layout wrapper from an existing simple route, such as `Processes.tsx`. Do not create new styles.
- `FE:App.tsx`:
  - Add `/login`.
  - The `Console` wrapper redirects to `/login` when there is no user.
  - `/` (Landing) stays public.
- `FE:routes/Settings.tsx`: the user picker stays as "Cambiar de usuario" and uses `signIn(email)`.
- Only a manager uses the app. Once 403s arrive, an operator who signs in still sees read-only screens. Do not build per-role layouts.

**Vocabulary:** `manager` → Responsable, `operator` → Operador (`es.ts`, `roles`).

**Depends on:**
- Available now: `/login` and `/me`.
- 401 and 403 enforcement is pending: PR #92 (`feat/integration-backend-runs-auth`). Code for them now, because the 422 path covers today.

**Done check (mock off):**
1. Clear site data and open http://127.0.0.1:5173/processes. You land on Login.
2. Enter `martin@trace-it.local`. You see Procesos.
3. In devtools, every `/api` request carries `X-User-Id`.
4. Reset the database, then reload the app. You are sent back to Login, with no crash.
5. `nobody@x.y` shows the backend's 404 message.

**Estimate:** S.

---

## 2. Panel and publish with a real version

**Story:** As the manager, I open a process, see real counts, latency and cost, and publish its draft as a numbered version.

**Today (`FE:routes/Process.tsx`, `FE:components/process/ExecutionSettings.tsx`, `FE:routes/Definition.tsx` `VersionChip`):**
- The counts are computed on the client from `listInstances`, twice.
- `Metrics` shows "—" for Latencia and Coste.
- `Alerts` counts compiling rules and findings only.
- `make setup` leaves the pack unpublished, so Ejecutar gets a 409 that nobody explains (row 18).
- Publishing sits at the bottom of the Panel, in English copy, through `executionApi`, a second client that bypasses `api`.
- `VersionChip` invents `v{n}` from activation dates and a hash from concatenated rule hashes.

**Endpoints:**

| Method, path (operationId) | Headers | Body | Response fields used | Errors |
|---|---|---|---|---|
| `GET /processes/{id}` (`getProcess`) | – | – | `name`, `description`, `active_version_id`, `decision_types[] {name, priority, is_default, requires_human}`, `symbols[]`, `decision_review` | 404 |
| `GET /processes/{id}/summary` (`getProcessSummary`) | – | – | `instances`, `by_status`, `by_decision`, `queue`, `resolved`, `rules[] {status, fires}`, `sources[]`, `down_sources`, `last_run_at` | 404 |
| `GET /processes/{id}/metrics/execution` (`getProcessPlaneMetrics`, plane=`execution`) | – | – | `steps[]` (`step == "run_process"` → `p50_ms`), `escalated`, `pending`, `resolutions`, `open_alerts` | 404 |
| `GET /processes/{id}/metrics` (`getProcessMetrics`) | – | – | `providers[].known_cost_usd` (sum), `llm[]` | 404 |
| `GET /health/planes` (`getPlanesHealth`) | – | – | `[{plane, status, reason}]` | – |
| `GET /processes/{id}/draft` (`getProcessDraft`) | manager | – | `VersionDraftOut {revision, base_version_id, validation}` | 404 when there is no draft; 403 |
| `POST /processes/{id}/draft/validate` (`validateProcessDraft`) | manager | – | `validation.valid`, `validation.hash`, `validation.coverage`, `validation.conflicts`, `validation.errors` | 404, 409 |
| `POST /processes/{id}/draft/publish` (`publishProcessDraft`) | manager | `PublishIn {revision, validation_hash, reason}` | `VersionOut {id, number, created_at, author, reason}` | 409 stale revision or hash, or a human conflict |
| `GET /processes/{id}/versions` (`listProcessVersions`) | – | – | `[{id, number, content_hash, author, reason, created_at}]` | 404 |
| `GET /processes/{id}/execution` (`getExecutionSettings`) | manager | – | `ExecutionOut {settings, revision, version_id, presets, decision_review}` | 403 |
| `POST /rules/{id}/activate` (`activateRule`) | manager | – | `RuleDetail {id, status}`; the rule is staged in the draft, not yet active | 409 not compiled or discrepancies unresolved, or it contradicts a human decision; 403 |

**From compiled rules to a runnable process.** Rules that come from a norm (`POST /processes/{id}/norm`, package 9) or from `POST /processes/{id}/rules` are compiled, but no run uses them until they are published. Until then `POST /processes/{id}/run` returns 409 "Publish an approved process version before running cases" (no version yet), or runs with the old version's rules. The sequence, all as the manager:
1. Wait until each rule is compiled: `GET /processes/{id}/rules` shows `status` `draft` (compiled, valid), not `compiling`. A `blocked` rule cannot go on (its `report` says why).
2. `POST /rules/{id}/activate` for each rule. It adds the rule to the process draft. 409 if the rule is not compiled or has discrepancies.
3. `POST /processes/{id}/draft/validate`. Read `validation.valid`, `validation.hash` and `revision` from the answer. `valid: false` is a 200 with `validation.errors`, not an error. 404 no draft; 409 "The active version changed; rebase the draft before validation".
4. `POST /processes/{id}/draft/publish` with `{revision, validation_hash: validation.hash, reason}`. 201 `VersionOut`. 409 "Approve the latest successful validation of this exact draft revision" (stale revision or hash, or an invalid validation), or "Configuration or execution evidence changed; validate again" (a source or setting changed after step 3: validate again).
5. Now `POST /processes/{id}/run` works.

Every step is manager-only: 401 without `X-User-Id`, 403 for an operator. The publish flow below covers steps 3 and 4. The rule page covers step 2 (package 9).

**Changes:**
- `live.ts`:
  - Add `summary`, `planeMetrics(processId, plane)`, `processMetrics`, `planesHealth`, `getDraft`, `validateDraft`, `publishDraft` and `listVersions`, typed with the generated schemas.
  - Fold `FE:api/execution.ts` `executionApi` into `live.ts` (`getExecution`, `saveDraft`), and delete `execution.ts` (row 41).
- `Process.tsx`:
  - `Metrics`:
    - Documentos = `summary.instances`.
    - Decididos = `by_status.DECIDED`.
    - En revisión = `summary.queue`.
    - Latencia = `formatMs(p50_ms of run_process)`.
    - Coste = the sum of `known_cost_usd`, in euros through `formatEuro`, as reported USD. Keep the note text, and change it to "coste conocido de proveedores".
  - Drop the double `listInstances` query and `countsOf`.
  - `Split` reads `summary.by_decision`, and the tone comes from the type's metadata.
  - `Alerts`:
    - Add an item "Borrador sin publicar · Publicar vN+1" when `getDraft` returns 200.
    - It opens the publish `Overlay` described below.
  - Publish flow:
    - It reuses `SettingsForm`'s validate-then-publish logic from `ExecutionSettings.tsx`, inside an `Overlay`.
    - Show the validation result with the existing `HistoricalCoverage` component.
    - Use a `Textarea` for `reason` (required) and a primary `Button` "Publicar".
    - On 201, invalidate everything and show `Notice` "Versión vN publicada".
- `ExecutionSettings.tsx`: keep it where it is. It stops using `executionApi`. Moving its English copy to `es.ts` is copy, not style.
- `Definition.tsx` `VersionChip`:
  - `label = "v" + versions[0].number`.
  - `hash = content_hash.slice(0, 8)`.
  - `stamp = created_at`.
  - Delete `versionName()` and the concatenated-hash logic.
- `FE:components/shell/Sidebar.tsx`: the existing `StatusBadge` next to the process list shows the worst `/health/planes` status. It is the same badge the MOCK badge uses, so there is no new element.
- Map run 409s (package 3) here too: "Publica una versión antes de ejecutar" when the message says nothing is published.

**Vocabulary:**
- Plane `ingestion`/`agents`/`execution` → Lectura/Agentes/Ejecución.
- Health `ok`/`degraded`/`down` → Bien/Degradado/Caído.
- Instance status `PENDING`/`DECIDED` → Pendiente/Decidida.

**Depends on:** available now. The draft endpoints are manager-only today.

**Done check (mock off, "Invoice payment" left unpublished):**
1. Open the process. ATENCIÓN shows "Borrador sin publicar".
2. Click it, then Validar: the coverage shows.
3. Enter a reason and click Publicar. The notice says `v1`, and the Definición chip says `v1` with the hash from `/versions`.
4. After one run (package 3), Latencia shows milliseconds, not "—".
5. Stop `make erp` and run: the sidebar badge goes Degradado.

**Estimate:** M.

---

## 3. Upload, run and sources: real progress, cut-off date and `down_sources`

**Story:** As the manager, I load the reference workbook with its cut-off date, upload a batch, watch real progress, run it, and see which sources were down.

**Today:**
- `BatchRunPanel.tsx` `Progress` walks a 190 ms timer through fake stages (row 21).
- `live.ts` `uploadFiles` loops over the files but reports nothing per file. It ignores `created:false`, so a re-uploaded PENDING file keeps stale symbols (row 20).
- `run` drops `down_sources` (row 23).
- `uploadWorkbook` hardcodes `cut_off_date = '2026-09-18'` (row 25).
- `TruthSources.tsx` shows a hardcoded `http://127.0.0.1:8009` and never shows a source's `status`, `error` or `checked_at`. `syncErp` fakes `cargada = now()`.

**Endpoints:**

| Method, path (operationId) | Headers | Body | Response fields used | Errors |
|---|---|---|---|---|
| `POST /processes/{id}/files` (`uploadProcessDocument`) | `X-User-Id` | multipart `file` | `DocumentUpload {instance_id, name, status, created, extraction.warnings}` | 422 `invalid_document`, 404 |
| `POST /instances/{id}/extract` (`extractInstanceDocument`) | `X-User-Id` | `{}` | `DocumentUpload` | 409 already decided |
| `POST /processes/{id}/run` (`runProcess`) | manager (PR #92) | – | `RunSummary {decided, by_decision, down_sources?}` | 409 nothing published, a rule compiling, or no active rule |
| `POST /processes/{id}/sources/workbook` (`uploadProcessWorkbook`) | `X-User-Id` | multipart `file`, `cut_off_date` (`YYYY-MM-DD`; optional today, required once PR #92 merges) | `WorkbookUpload {sources[] {name, rows}, warnings}` | 422 `invalid_document`; 422 with no `cut_off_date` (PR #92) |
| `GET /processes/{id}/sources` (`listSources`) | – | – | `[{name, origin, rows, loaded_at, status, error, checked_at}]` | 404 |
| `GET /processes/{id}/sources/parameters` (`getSource`) | – | – | `data[0].cut_off_date` (the current value) | 404 when not loaded yet |
| `POST /processes/{id}/sources/{name}/sync` (`syncSource`) | manager (PR #92) | – | `SyncResult {origin, rows, diff {added, removed, changed}}` | 502 `source_unavailable` |

**Changes:**
- `live.ts`:
  - `uploadFiles(processId, files, onProgress)` calls `onProgress({done, total, name, status})` after each file.
  - When `created === false && status === 'PENDING'`, it calls `POST /instances/{id}/extract` before moving on.
  - `run` returns `RunSummary` as it is.
  - `uploadWorkbook(processId, file, cutOffDate)` has no default value.
  - Replace `syncErp` with `syncSource(processId, name)`.
  - `listSources` returns `SourceOut`.
  - Delete `uploadSource` and `listFiles` (row 42).
- `BatchRunPanel.tsx` `Progress`:
  - Delete the timer.
  - `progress = done / total` comes from the `onProgress` state that `Process.tsx` holds.
  - The row markers use the real per-file state: a file is done once its upload returns. The current row shows the file name.
  - While `run` is pending, use the current `stages` row as it is: an indeterminate state on "Decisión".
  - On success, show `by_decision`. When `down_sources` is not empty, add an `ErrorNotice`-style `Notice`: "Fuentes caídas: erp (why). Esos casos se escalan".
- `Process.tsx` `startRun` passes the progress callback, and maps run 409 messages to `ErrorNotice`.
- `TruthSources.tsx`:
  - Add a `Field` "Fecha de corte" with `Input type="date" required` above the `DropZone`. Its initial value comes from `GET …/sources/parameters`, and it is empty when there is none.
  - Disable the `DropZone` until a date is set. Martín's decision: the cut-off is a required input on upload.
  - `DataTable` gets an "Estado" column, rendered with `StatusBadge` and the label from `es.ts`. Show `error` as the cell's `title`.
  - "Cargada" reads `loaded_at`.
  - Replace the hardcoded ERP URL with the `origin` of the `erp` source row.
  - After a sync, show the `diff` counts in a `Notice`: "+N −M ~K filas".

**Vocabulary:**
- Source status `ok` → Al día, `down` → Caída, `null` → Sin sincronizar.
- Escalation reason `SOURCE_UNAVAILABLE:` → Fuente no disponible, with the code visible.
- Symbol `parameters.cut_off_date` → Fecha de corte.

**Depends on:** available now. The 401/403 on `run` and `sync` is pending on PR #92, and package 1 already handles it.

**Done check (mock off, a published version, `make erp` running):**
1. Definición → Fuentes. The drop zone is disabled until you pick 2026-09-18.
2. Drop the challenge `.xlsx`. The table shows `suppliers`, `orders` and `parameters` with Al día.
3. Panel → Ejecutar. Drop 20 PDFs and start: the bar goes 1/20 … 20/20, with each file name.
4. Then it shows `by_decision`.
5. Stop `make erp` and run again with one new PDF. The summary lists `erp`, and Fuentes shows `erp` as Caída with the error on hover.
6. Upload the same PENDING PDF twice: the network tab shows `/extract` on the second upload.

**Estimate:** M.

---

## 4. Decisions queue and tabs, including `review_pending`

**Story:** As the manager, I see every case waiting for me, including the ones the reviewer disagreed with.

**Today:**
- `FE:routes/Queue.tsx` builds its tabs from the human outcomes and filters items by `decision === tab`. `review_pending` cases whose decision is `PAGAR` never show, and export fails with 409 later (row 26).
- The Spanish status `REVISION` never happens. `listInstances('REVISION')` returns `[]` without calling the API (row 27).
- `lib/process.ts` `waitingOnPerson` counts it anyway.

**Endpoints:**

| Method, path (operationId) | Headers | Body | Response fields used | Errors |
|---|---|---|---|---|
| `GET /processes/{id}/queue` (`getQueue`) | – | query `type` (optional) | `[{id, name, status, decision, author, reason, decided_at, review_pending}]` | 404 |
| `GET /processes/{id}/instances` (`listInstances`) | – | query `status`, `decision`, `q` | same `InstanceOut` | 404 |
| `GET /instances/{id}` (`getInstance`) | – | – | `reviews[] {status, recommendation, reasoning, evidence}` | 404 |

**Changes:**
- `live.ts`:
  - `queue(processId)` returns `InstanceOut[]` with no `type` parameter.
  - `listInstances(processId, {status, decision, q})` passes the filters to the server, for the command palette and Instances.
  - Delete the `REVISION` short-circuit.
- `Queue.tsx`:
  - Tabs = the human outcomes by priority, **plus** a `review` tab, "Revisión del revisor", shown only when any item has `review_pending`.
  - An outcome tab filters `decision === tab && !review_pending`. The review tab filters `review_pending`.
  - `CountChip` counts come from the same split.
  - Same `Segmented`, no new markup.
- `lib/process.ts`: `waitingOnPerson` is replaced by `summary.queue` (package 2), and `countsOf` is deleted.
- `lib/status.ts`:
  - `INSTANCE_STATES = ['PENDING', 'DECIDED']`.
  - `tone()` takes the decision type's metadata.
  - `RULE_STATES` uses the English codes and gains `blocked`. `rechazada` is removed.

**Vocabulary:** `review_pending: true` → Revisión del revisor. Review status `completed`/`failed` → Completada/Fallida.

**Depends on:** available now.

**Done check (mock off):**
1. Enable a reviewer in Ajustes (package 11), or publish a pack with `decision_review`, then run a batch.
2. Revisión shows ESCALAR with its count.
3. A case the reviewer disagreed with appears under "Revisión del revisor", even though its decision is PAGAR.
4. The total across the tabs equals `summary.queue`.

**Estimate:** S.

---

## 5. Escalation detail: the assistant's proposal, then resolve

**Story:** As the manager, on an ESCALAR case I read why it escalated and what the assistant proposes, and accepting a proposal resolves the case.

**Today:**
- `Queue.tsx` `Resolve` loads `api.suggestion`, maps it to Spanish, and pre-fills the form.
- Resolve then `createRule` are two calls, and the rule text is required for the primary button.
- The case does not show *why* it escalated: the engine's `reason` and which rule fired. For a `review_pending` case, the reviewer's recommendation is not shown.

**Endpoints:**

| Method, path (operationId) | Headers | Body | Response fields used | Errors |
|---|---|---|---|---|
| `GET /instances/{id}` (`getInstance`) | – | – | `reason` (engine escalation reason), `decisions[-1].results[] {rule_id, fires, reason}`, `reviews[-1] {recommendation, reasoning}` | 404 |
| `GET /instances/{id}/suggestion` (`getSuggestion`) | `X-User-Id` after PR #92 | – | `Suggestion {decision, reasoning, proposed_rule, proposed_type}` | 409 not in the queue, 502 `llm_error` |
| `POST /instances/{id}/resolve` (`resolveInstance`) | manager | `ResolveIn {decision, reason}` | `InstanceDetail` (`status`, `decision`, `review_pending`) | 409 unknown decision type, 403 operator (after PR #92) |
| `POST /processes/{id}/rules` (`createRule`) | `X-User-Id` | `RuleIn {text, type, decision}` | `RuleDetail {id, status}` | 422 |
| **Pending, PR #93:** `POST /instances/{id}/proposal` | manager | – | `payload {proposed, why[], options[{decision, consequence}], escalation_reason, fired_rules}`, `evidence` | 502 `llm_error` |
| **Pending, PR #93:** `POST /instances/{id}/resolve` with `ResolveIn.proposal_id` | manager | `{decision, reason, proposal_id}` | the proposal is accepted when `decision` equals the proposed one, and rejected otherwise | 409 |
| **Pending:** `POST /proposals/{id}/accept`, `POST /proposals/{id}/reject` | manager | `{reason}` | the accepted proposal; for `decision`, the resolved instance | 409 already decided |

**Changes, now (on today's endpoints):**
- `live.ts`:
  - `suggestion` returns `Suggestion` as it is.
  - `resolve` returns the POST body and stops re-fetching.
  - Delete their mappers.
- `Queue.tsx` `Resolve`:
  - Above `Suggested`, show "Por qué se escaló" inside the same card, using `Notice`:
    - The instance `reason`, with its prefix translated.
    - The firing rules' text, looked up from `listRules`.
    - For a `review_pending` case, the reviewer's `recommendation` and `reasoning`.
  - `Suggested` reads `reasoning`, `proposed_rule` and `proposed_type`.
  - On 502, show `ErrorNotice`, and resolving by hand stays available.
  - The primary `Button` becomes "Aceptar la propuesta": `resolve({decision: suggestion.decision, reason: note || suggestion.reasoning})`.
  - The soft `Button` "Resolver sin regla" stays, for the manager's own choice in the `Select`.
  - "Resolver y crear la regla" stays as a soft `Button`. It sends `createRule` with `{text, type, decision}` in English.
  - On success, invalidate `queue`, `instance`, `summary` and `alerts`. The case leaves the list.

**Changes, when PR #93 lands:**
- Opening the case calls `POST /instances/{id}/proposal`. `Suggested` shows `payload.why[]` as the explanation and `payload.options[]` as the choices, each with its `consequence`. The proposed option comes first.
- Each option reuses the card, with "Aceptar" (`Button primary`) and "Rechazar" (`Button soft`).
- Accept calls `POST /proposals/{id}/accept`, which resolves the case. Choosing another decision in the `Select` sends `resolve` with `proposal_id`, and the backend rejects the proposal. Reject asks for a reason in the existing `Textarea`.
- `getSuggestion` stays only as a fallback, if the backend keeps it.

**Vocabulary:**
- Rule type `requirement` → Requisito, `prohibition` → Prohibición.
- Decision author `engine` → Motor.
- Escalation prefixes `RULE_ERROR` → Error en la regla, `RULE_CONFLICT:` → Reglas en conflicto, `SOURCE_UNAVAILABLE:` → Fuente no disponible.

**Depends on:**
- Available now: suggestion and resolve.
- Pending: PR #93 (`feat/integration-proposals`, draft), for the explained options and accept/reject.

**Done check (mock off, LLM keys set):**
1. Revisión → select an ESCALAR case. "Por qué se escaló" shows the engine reason, for example `SOURCE_UNAVAILABLE: erp`, and the rule text.
2. The assistant card shows a decision and its reasoning.
3. Click "Aceptar la propuesta". The case leaves the list, the tab count drops by 1, and `GET /instances/{id}` shows a new decision whose author is Martín.
4. Without keys, the card shows the 502 message, and "Resolver sin regla" still works.

**Estimate:** M.

---

## 6. Trace view with the real document

**Story:** As the manager, I open any case and see the real PDF, the evidence for each symbol, the rule results and the spans, all from the backend.

**Today:**
- `FE:routes/Instances.tsx` → `TracePane` reads `getInstance`.
- `DocumentPane.tsx` falls back to the bundled `data/documents.generated.ts` (8,956 lines), and `DocumentPopup.tsx` always reads it (row 29).
- `/instances/{id}/file` and `/instances/{id}/trace` are never called.

**Endpoints:**

| Method, path (operationId) | Headers | Body | Response fields used | Errors |
|---|---|---|---|---|
| `GET /instances/{id}` (`getInstance`) | – | – | `symbols {name: {value, origin}}`, `decisions[]`, `events[]`, `reviews[]` | 404 |
| `GET /instances/{id}/trace` (`getInstanceTrace`) | – | – | `file {name, size_bytes, ingested_at}`, `decisions[].rule_results[] {rule_id, fires, reason, rule_text}`, `exported_decision`, `spans[]` (`SpanNode` tree: `step`, `status`, `duration_ms`, `data`, `children`) | 404 |
| `GET /instances/{id}/file` (`getInstanceFile`) | – | – | PDF bytes, `inline` | 404 |
| `GET /instances/{id}/document` (`getInstanceDocument`) | `X-User-Id` | – | `ExtractionResult {fields {name: FieldReading}, text, sha256, pipeline_version, cache_hit}` | 404 |

**Changes:**
- `live.ts`:
  - Add `getTrace(id)` and `fileUrl(id) => BASE + '/instances/' + id + '/file'`. Export `BASE` from `http.ts`.
  - `getDocument` returns `ExtractionResult`.
  - `getInstance` returns `InstanceDetail` as it is.
- `DocumentPane.tsx`:
  - Delete the `extractedDocuments` import and `InvoicePaper`.
  - Inside the existing paper container, render `<iframe src={fileUrl(id)} title={name}>` sized to that container.
  - `EvidencePaper` (text and search) stays and reads `/document`.
  - The "download" action links to `fileUrl`.
  - Zoom and rotate keep working, because they transform the container.
- `DocumentPopup.tsx`:
  - Origin, pages and size come from `trace.file` and `/document`.
  - Cost comes from the `provider_call` spans' `data` in `trace.spans`, not from event `datos`.
- `TracePane.tsx`:
  - Rule results come from `trace.decisions[].rule_results` and use `rule_text`. This drops the `listRules` lookup in `Instances.tsx`.
  - The export line uses `exported_decision`.
  - The event list renders the span tree through the existing `Block` component, one level per `children`.
- The evidence join:
  - Symbols are keyed `issuer_nif`, `iban` and `purchase_order`. Extraction fields are keyed `supplier_tax_id`, `payment_iban` and `purchase_order_ref` (row 30).
  - Until the backend adds `FieldReading.symbol`, keep a three-entry map in `DocumentPane.tsx`, marked `// remove when FieldReading.symbol lands`. The other fields already share the symbol's name.
- Delete `FE:data/documents.generated.ts`, and `api/types.ts` `InvoiceDocument` once nothing imports it.

**Vocabulary:**
- The symbol labels from [integration.md §2](integration.md#2-the-contract-shared-vocabulary): `issuer_nif` → NIF del emisor, and so on. Show the code in monospace next to the label.
- Plane labels as in package 2.

**Depends on:**
- Available now: `/trace`, `/file` and `/document`.
- Pending: `FieldReading.symbol`, which is integration-plan task 0.5 and is **not** in #91. The workaround above unblocks you.

**Done check (mock off):**
1. Ejecuciones → select any decided case. The real PDF renders in the paper area.
2. Every rule result shows its text, and the export line matches `GET /instances/{id}/trace` `exported_decision`.
3. The popup shows the file size from the backend.
4. `npm run build && grep -rl extractedDocuments dist/` prints nothing.

**Estimate:** M.

---

## 7. Run history timeline, with easy going back

**Story:** As the manager, I see every run of this process on a timeline (when, which version, what it decided), and I can open any past run's cases and come back. After the learning agent adopts a norm, a rerun shows fewer escalations.

**Today:**
- `Process.tsx` `Runs` lists "Las de esta sesión", which is React state lost on reload (row 7).
- "Historial" links to Instances unfiltered.

**Endpoints (PR #92, `feat/integration-backend-runs-auth`, draft):** the shape below comes from the PR description, and the planned operation ids are `listRuns` and `getRun`. Confirm it in `schema.d.ts` when the PR merges; if they differ, the OpenAPI wins.

| Method, path | Headers | Body | Response fields to use | Errors |
|---|---|---|---|---|
| `GET /processes/{id}/runs` (`listRuns`) | – | – | a list, newest first. Each run has its `id` (the `execution_id` its decisions carry), `started_at`, `version_number`, `author`, `by_decision`, `escalated`, `escalation_reasons` and `rules_hash`. `by_decision` and `escalated` count every instance the run evaluated, so a reprocess can be compared with the run before it | 404 |
| `GET /runs/{id}` (`getRun`) | – | – | the same run plus the decisions it appended (instance id, name, decision) | 404 |

**Changes:**
- `live.ts`: add `listRuns(processId)` and `getRun(id)`.
- `Process.tsx`:
  - `Runs` reads `listRuns` instead of `runs` state, and `setRuns` is deleted.
  - Each existing `<li>`:
    - Its title is "{decided} decisiones · vN".
    - Its subtitle is the `by_decision` split with the ESCALAR count first.
    - Its time comes from `formatRunDate(created_at)`.
  - The intro copy loses "Las de esta sesión…".
  - `run.onSuccess` invalidates `['runs', processId]`.
- `lib/paths.ts`: `instances(processId, runId?)` adds `?run=`.
- `Instances.tsx`:
  - When `?run=` is present, the list comes from `getRun(id).instances`, and a `Notice` says "Ejecución del {date} · vN". Its action is a link back to the Panel ("Volver").
  - Browser Back works, because the filter lives in the URL.
- A rerun after learning:
  - Show whatever runs the backend returns. The split makes "fewer ESCALAR" visible, and no Learning screen is needed (Martín's decision).
  - PR #92 counts a reprocess as a run, so it appears with no extra frontend work. After a learning norm is adopted, a reprocess shows the drop in `escalated`.

**Vocabulary:** version as `v{number}`. Decision names verbatim.

**Depends on:** pending: PR #92 (`feat/integration-backend-runs-auth`, draft).

**Done check (mock off):**
1. Run twice, then reload the Panel. Both runs are listed with their version and split.
2. Click the older one: Ejecuciones shows only its cases, with the notice.
3. Browser Back returns to the Panel.
4. After a learning norm is adopted and the batch is rerun, the newest row shows fewer ESCALAR than the one before it.

**Estimate:** S (M if the shape changes).

---

## 8. Proposals inbox: chat and learning, accept or reject

**Story:** As the manager, I see every open proposal (from the escalation assistant, the definition chat and the learning agent) and accept or reject each one. Nothing changes without my click.

**The model (Martín's decision):**
- A proposal has a `kind`: `decision`, `rule`, `context`, `input` or `source`.
- It comes from one of 3 channels:
  1. `escalation`: on an ESCALAR case, the assistant proposes decisions. Accepting one resolves the case (package 5).
  2. `chat`: the definition chat proposes changes. Accepting one **stages** it into the process draft. Publishing stays separate (package 2).
  3. `learning`: the learning agent proposes promotions from traces.

**Today:**
- The Definition chat's proposals are regular expressions (`Definition.tsx` `proposalsFrom()`) applied on the client (row 14).
- There is no learning UI.
- `ProposalCard` has "Aplicar" only.

**What exists in the backend today:**
- The escalation suggestion: `GET /instances/{id}/suggestion`. One proposal, no accept endpoint.
- Process chat (#69): `/process-drafts` with `{process_id}`, messages in `discuss` or `revise` mode, then `POST …/reviews` `{proposal, disposition: accepted|rejected}`, `…/prepare` and `…/publish`. **Its publish goes straight to a new version, not into the draft.** So do not wire accept through `…/prepare` or `…/publish`: that contradicts "accept stages into the draft".
- Learning (#56): `POST /processes/{id}/learning`, then `GET /norm-proposals/{id}`, `…/validate` (up to 5 min), and `…/approve {validation_id, reason}` or `…/reject {reason}`. Its approve publishes directly.
- PR #93 (`feat/integration-proposals`) wraps these in one inbox API. Build against it, not against the three above.

**Endpoints (PR #93, `feat/integration-proposals`, draft):** the shape below comes from the PR description, and the response schema is `ManagerProposalOut`. Confirm it in `schema.d.ts` when the PR merges; if they differ, the OpenAPI wins. Every endpoint needs the manager's `X-User-Id`. Without it you get 401, and a non-manager gets 403.

| Method, path | Headers | Body | Response fields to use | Errors |
|---|---|---|---|---|
| `POST /instances/{id}/proposal` | manager | – | creates the escalation proposal: `payload {proposed, why[], options[{decision, consequence}], escalation_reason, fired_rules}` and `evidence` | 409, 502 `llm_error` |
| `GET /processes/{id}/proposals?status=open` | manager | – | `[{id, channel, kind, summary, rationale, evidence, payload, status, author, created_at, resolved_by, resolved_at, outcome}]` | 403 |
| `POST /proposals/{id}/accept` | manager | `{reason?}` | the proposal with `status: accepted` and what it changed (the resolved instance, or the new draft `revision`) | 409 already decided, or a stale draft |
| `POST /proposals/{id}/reject` | manager | `{reason}` | the proposal with `status: rejected` | 409 |

**Changes:**
- `live.ts`: add `listProposals(processId, status)`, `acceptProposal(id, reason?)` and `rejectProposal(id, reason)`.
- `FE:api/queries.ts`: `keys.proposals(processId)`. Accept and reject invalidate `proposals`, `summary` and `draft`, plus `queue` and `instance` for `decision`.
- `Definition.tsx`, left column:
  - Above the turns, list the open `chat` and `learning` proposals with the existing `ProposalCard`. Change its prop type to the generated proposal type.
  - The card's `label` maps `kind` through `es.ts`.
  - "Aplicar" becomes "Aceptar" (`acceptProposal`).
  - Add "Rechazar": a `Button tone="soft"` next to it that opens the existing `Textarea` for the reason.
  - "Aplicada" becomes "Aceptada", or "Rechazada".
  - Show `reasoning`, and `evidence` as monospace references, in the card's existing text slot.
- `Process.tsx` `Alerts`: an item "{n} propuestas esperan tu decisión" that links to Definición.
- `Queue.tsx`: the `decision` proposals of the current case, as in package 5.
- Nothing in this package publishes. After a `chat` or `learning` accept, the Panel's "Borrador sin publicar" item (package 2) is the way to publish.

**Vocabulary:**
- Kind `decision`/`rule`/`context`/`input`/`source` → Decisión/Regla/Contexto/Input/Fuente.
- Channel `escalation`/`chat`/`learning` → Asistente/Chat/Aprendizaje.
- Status `open`/`accepted`/`rejected` → Abierta/Aceptada/Rechazada.

**Depends on:** pending: PR #93 (`feat/integration-proposals`, draft).

**Done check (mock off, LLM keys set):**
1. In the chat (package 9), ask for a rule. A `rule` proposal appears as a card.
2. Accept it. `GET /processes/{id}/draft` shows the rule, the active version has not changed, and the Panel shows "Borrador sin publicar".
3. Reject another proposal with a reason. It leaves the list, and `GET …/proposals?status=rejected` holds it with that reason.
4. A learning proposal appears with channel Aprendizaje.

**Estimate:** M.

---

## 9. Definition editing: safe draft edits, English import and the chat

**Story:** As the manager, I edit the context and inputs without losing rules, import a pack as it is in the repo, and talk to the chat to get real proposals.

**Today:**
- **Dangerous:** Contexto → Guardar and Inputs add or remove call `loadDefinition` or `replaceSymbols`. They re-post the whole process to `POST /processes/definition`, which stages a draft with `rules=[]` and resets `required` and `decision_review` (rows 8 and 9). Until this package lands, nobody clicks them on the demo database.
- The symbol type is a free `Input` (`texto`/`numero`/`booleano`) (row 10).
- The invoice template and the chat chips use Spanish symbol names (row 11).
- The JSON import only accepts the Spanish shape, and the repo's own `processes/*.json` throw a TypeError (row 17).
- `Rule.tsx` shows fake A/B compiler fields and `autor: 'tester'` (row 12), and "Activar" reads as if it takes effect (row 13).
- The chat is regular expressions, and attachments are never sent (rows 14 and 15).

**Endpoints:**

| Method, path (operationId) | Headers | Body | Response fields used | Errors |
|---|---|---|---|---|
| `GET /processes/{id}/draft` (`getProcessDraft`) | manager | – | `revision`, `snapshot` (current candidate) | 404 no draft |
| `PUT /processes/{id}/draft` (`editProcessDraft`) | manager | `DraftIn {expected_revision, description?}` or `{expected_revision, symbols: SymbolIO[]}`. Omitted fields keep their values | `VersionDraftOut {revision, snapshot}` | 409 stale revision: reload and retry |
| `POST /processes/definition` (`loadDefinition`) | manager (after PR #92) | `Definition` (the English pack shape, sent as it is) | `LoadResult {process.id, new_rules, new_users}` | 409 rules with `code` files, or a draft exists; 422 |
| `POST /processes/{id}/rules`, `POST /rules/{id}/compile`, `GET /rules/{id}`, `GET /rules/{id}/impact`, `POST /rules/{id}/activate`, `/retire` | manager for activate and retire | `RuleIn {text, type, decision}` | `RuleDetail {code, tests, report {valid, tests[], discrepancies, attempts, reviews, needs_data}}` | 409 |
| `POST /processes/{id}/norm` (`normalizeNorm`) | manager | `NormIn {text}` | `NormOut.norm_rules[] {text, checks[] {text, type, decision, rule_id}}` | 502 `llm_error` |
| `POST /process-drafts` (`startDiscoverySession`) | manager | `{process_id}` | `DiscoveryDraftOut {id, revision, messages}` | 409 |
| `GET /process-drafts` (`listDiscoverySessions`) | manager | – | `[{id, process_id, published_process_id}]`, to resume this process's open conversation | – |
| `POST /process-drafts/{id}/messages` (`messageDiscoverySession`) | manager | `MessageIn {revision, message, mode: "discuss"}` | `revision`, `messages[-1]` (the answer) | 409 stale revision, 502 |
| `POST /process-drafts/{id}/workbooks` (`uploadDraftWorkbook`) | manager | multipart `file`, `revision` | `revision`, `documents` | 422 |

**Changes:**
- `live.ts`:
  - Add `getDraft` (shared with package 2) and `editDraft(processId, body)`.
  - `loadDefinition(body: Definition)` posts the object as it is. Delete `definitionBody()`, `replaceSymbols` and `createProcess`'s Spanish mapper.
- `Definition.tsx` `ContextPane`:
  - Save = `getDraft` (404 means no draft yet, so omit `expected_revision`), then `editDraft({expected_revision, description})`.
  - On 409, show `ErrorNotice` with "Recarga: alguien cambió el borrador".
  - The textarea shows the draft's description when a draft exists.
- `InputsPane`:
  - Add or remove = `editDraft({expected_revision, symbols})`, where `symbols` is the **full** current `SymbolIO` list with `required` and `extraction` kept.
  - The type `Input` becomes the existing `Select` with `text`/`number`/`date`, labelled Texto/Número/Fecha.
  - The placeholder becomes `issuer_nif`.
- `Definition.tsx` `Definition()`:
  - `saveContext` and `addSymbol` use the same `editDraft` path.
  - Delete `proposalsFrom()`.
  - The `Composer` send:
    - Starts or resumes the process conversation (`listDiscoverySessions`, then `startDiscoverySession` when none is open).
    - Posts `mode: "discuss"`.
    - Renders the answer as a turn, using the existing turn markup.
  - `.xlsx` attachments go to `uploadDraftWorkbook`. Other file types show a `Notice` ("Solo Excel"). The chip UI stays.
  - Proposals in the chat come from package 8, not from the chat response.
  - A norm pasted in the Normas pane goes to `POST /processes/{id}/norm`, and the returned checks are listed with `ProposalCard`, already created as draft rules that compile in the background (row 14, Q2).
- `PANE_CHAT` chips and `FE:data/seed.ts` `invoiceSymbols` use the pack's names: `issuer_nif`, `iban`, `invoice_number`, `date`, `purchase_order`, `base`, `vat_rate`, `vat_amount` and `total`.
- `NewProcess.tsx`:
  - `FromDefinition` does `JSON.parse`, then `loadDefinition` as it is. A 409 shows the backend's text.
  - The `EXAMPLE` becomes `processes/travel-expenses.json`'s shape.
  - `ByHand` builds a `Definition` with English keys.
- `Rule.tsx`:
  - Read `code`, `tests` and `report` as they come, and drop `codigo_a/b` and `tests_a/b`.
  - "Activar" → "Añadir a la versión", and "Retirar" → "Quitar de la versión".
  - After either one, show a `Notice` that links to the Panel's publish item.

**Vocabulary:**
- Symbol type `text`/`number`/`date` → Texto/Número/Fecha.
- Rule status `compiling`/`draft`/`active`/`blocked`/`retired` → Compilando/Borrador/Activa/Bloqueada/Retirada.
- Symbol labels as in [integration.md §2](integration.md#2-the-contract-shared-vocabulary).

**Depends on:**
- Available now: the draft edits, the import, rules, norm, and discuss-mode chat.
- Pending: PR #93, for the chat's proposals (package 8). With #93, every revise-mode message on an existing process becomes proposals, one per changed kind, and a new revision supersedes the open ones.
- Pending, integration-plan row 10: the backend rejecting `booleano` (not started). The `Select` already prevents it.

**Done check (mock off):**
1. Contexto: edit one word and click Guardar. `GET /processes/{id}/draft` → `snapshot.description` changed, the `rule_ids` are identical, and every symbol keeps `required`.
2. Inputs: add `iban_check`, `text`. The draft has it, and the other symbols are intact.
3. Nuevo proceso → Importar: paste `processes/travel-expenses.json`. The process is created. Pasting `invoice-payment.json` a second time shows the 409 text.
4. Chat: "¿Por qué se escalan estos casos?" returns an answer that cites cases.
5. Normas: paste a norm sentence. The checks are listed and move from Compilando to Borrador.

**Estimate:** L.

---

## 10. Alerts with acknowledge

**Story:** As the manager, I see past decisions that newer data or rules would decide differently, and I acknowledge them with a note.

**Today:** alerts are never called. The Panel's "ATENCIÓN" card lists client-side counts only (row 31).

**Endpoints:**

| Method, path (operationId) | Headers | Body | Response fields used | Errors |
|---|---|---|---|---|
| `GET /processes/{id}/alerts?status=open` (`listAlerts`) | – | – | `[{id, instance_id, name, before, after, trigger {type: source_sync or rule_change, …}, evidence, status, created_at}]` | 404 |
| `POST /alerts/{id}/ack` (`ackAlert`) | manager (after PR #92) | `AckIn {note?}` | `AlertOut {status, acknowledged_by, acknowledged_at, note}` | 409 already acknowledged |

**Changes:**
- `live.ts`: add `listAlerts(processId, status)` and `ackAlert(id, note)`.
- `Process.tsx` `Alerts`: an item "{n} decisiones podrían cambiar" that links to `paths.review(processId) + '?tipo=alertas'`. Poll every 10 s with `refetchInterval`.
- `Queue.tsx`:
  - A `Segmented` option "Alertas" with a `CountChip`.
  - Its list uses the same `<ul>` markup: `name` plus `StatusBadge before` → `StatusBadge after`, with the trigger label.
  - The detail panel uses the `Resolve` card layout:
    - The evidence (reason codes before and after) in a `Notice`.
    - A `Textarea` note, and a primary `Button` "Marcar como vista" that calls `ackAlert`.
    - A link "Ver traza".
  - Resolving the case (package 5) marks the alert `resolved` on the backend.

**Vocabulary:**
- Alert status `open`/`acknowledged`/`resolved` → Abierta/Vista/Resuelta.
- Trigger `source_sync`/`rule_change` → Cambio en la fuente/Cambio de reglas.

**Depends on:** available now. The manager-only ack is pending on PR #92, and package 1 handles it.

**Done check (mock off):**
1. Load the workbook with a different cut-off, or sync the ERP after changing a supplier's row, so some decided rows change.
2. The Panel shows "N decisiones podrían cambiar".
3. Revisión → Alertas lists them with `before → after`.
4. Acknowledge one with a note: it leaves the open list, and `GET …/alerts?status=acknowledged` holds it with your name and note.

**Estimate:** S.

---

## 11. Settings: from localStorage to the backend

**Story:** As the manager, the OCR mode, the reviewer and the models I choose are real, versioned settings, not browser-only values.

**Today:**
- `FE:routes/ProcessSettings.tsx` keeps OCR (`local/gemini/got`) and the reviewer in `localStorage` (`trace.process.{id}.ocr` and `.reviewer`), and never sends them (row 33).
- The models are workspace-wide use-case agents, fetched N+1 and labelled as if they were per process (row 34).

**Endpoints:**

| Method, path (operationId) | Headers | Body | Response fields used | Errors |
|---|---|---|---|---|
| `GET /processes/{id}/execution` (`getExecutionSettings`) | manager | – | `settings.extraction.mode` (`local`/`api`/`hybrid`), `decision_review`, `revision` | 403 |
| `PUT /processes/{id}/draft` (`editProcessDraft`) | manager | `{expected_revision, execution}` or `{expected_revision, decision_review: {guidance, timeout_seconds} or null}` | `revision` | 409 stale |
| `GET /use-cases/{id}` (`getUseCase`) | – | – | `agents[] {role, config.model, version}` | 404 |
| `PUT /use-cases/{id}/agents/{role}` (`configureAgent`) | manager | `AgentConfigIn {config: AgentSettings, note}` | `AgentConfigOut {version, config.model}` | 403 |

**Changes:**
- `ProcessSettings.tsx`:
  - Delete `OCR_KEY`, `REVIEWER_KEY` and `localStorage`.
  - The OCR `OCR_OPTIONS` become `local`/`api`/`hybrid`, labelled from `es.ts`, in the same control. Save them through `editDraft({expected_revision, execution: {...settings, extraction: {...settings.extraction, mode}}})`.
  - The reviewer checkbox saves `decision_review`: the current guidance, or a `Textarea` default when enabling, or `null` when disabling.
  - After a save, show a `Notice`: "Queda en el borrador. Publica para que se aplique", with a link to the Panel.
  - Models: read `getProcess(id).use_case_id`, then one `GET /use-cases/{use_case_id}`. Label the section "Modelos del caso de uso (compartidos)".
- `Settings.tsx`: the models section uses the same single fetch. The theme stays in `localStorage`, because it is per viewer.
- `live.ts`:
  - `listLlmConfig(useCaseId)` makes one call.
  - `setLlmConfig` sends the full `config` with the new `model`, and a `note`.

**Vocabulary:**
- Extraction mode `local`/`api`/`hybrid` → Local/API/Híbrido.
- Preset `lowest_cost`/`fastest`/`balanced`/`highest_quality` → Más barato/Más rápido/Equilibrado/Máxima calidad.

**Depends on:** available now.

**Done check (mock off):**
1. Ajustes → OCR: Híbrido. `GET /processes/{id}/draft` → `snapshot.execution.extraction.mode == "hybrid"`.
2. Enable the reviewer: `snapshot.decision_review` is set.
3. DevTools → Application → Local Storage has no `trace.process.*` key.
4. The Network tab shows one `/use-cases/{id}` request.

**Estimate:** S.

---

## 12. Mock removal

**Story:** As the team, we ship a console that can only show backend data.

**Today:** `api/mock.ts` (27 kB), `api/types.ts`, `data/invoices.generated.ts`, the Spanish types in `api/contracts.ts`, and the `ApiClient` indirection in `api/client.ts`.

**Endpoints:** none new.

**Changes:**
- Delete `FE:api/mock.ts`, `FE:api/types.ts` and `FE:data/invoices.generated.ts`, plus `data/documents.generated.ts` if package 6 left it.
- Delete the Spanish types in `contracts.ts`: `contracts.ts` keeps only aliases of `schema.d.ts`, or goes away.
- `client.ts` exports `liveClient` as `api`, and `VITE_API_MODE` goes away.
- The Sidebar `StatusBadge` MOCK branch and the `Settings.tsx` mode line go away.
- `frontend/README.md` drops the mock row.
- `Notice.tsx` status-0 text drops the `VITE_API_MODE=mock` hint.

**Vocabulary:** –

**Depends on:** packages 1-11.

**Done check (mock off, it is the only mode):**
1. `grep -rn "nombre\|tipos_decision\|mockClient\|VITE_API_MODE" frontend/src` finds only `es.ts` labels.
2. `npm run build && npm run lint` pass.
3. Repeat the done checks of packages 1-10 on a fresh database.

**Estimate:** M.

---

## Checklist

| # | Package | Depends on | Status | Estimate |
|---|---|---|---|---|
| 0 | Setup | #91 (merged) | Can start | S |
| 0b | Error states where there are none | available now | Can start | S |
| 1 | Login and identity | available now (401/403: PR #92) | Can start | S |
| 2 | Panel and publish with version | available now | Can start | M |
| 3 | Upload, run and sources | available now | Can start | M |
| 4 | Queue and tabs (`review_pending`) | available now | Can start | S |
| 5 | Escalation detail and resolve | available now; explained options and accept/reject: PR #93 | Can start | M |
| 6 | Trace view with the real document | available now; `FieldReading.symbol` (plan 0.5) has a workaround | Can start | M |
| 7 | Run history timeline | PR #92 | Waits | S |
| 8 | Proposals inbox | PR #93 | Waits | M |
| 9 | Definition editing and chat | available now; chat proposals: PR #93 | Can start | L |
| 10 | Alerts with ack | available now | Can start | S |
| 11 | Settings to the backend | available now | Can start | S |
| 12 | Mock removal | 0b-11 | Last | M |

Demo path if time runs short: 0 → 0b → 1 → 2 → 3 → 4 → 5 → 6.
Until package 9 lands, nobody clicks Contexto → Guardar or edits Inputs on the demo database.

## What the backend team delivers and when

| Delivery | Branch or PR | What it gives the frontend | Unblocks | Status |
|---|---|---|---|---|
| Contract, typed client, mock opt-in | PR #91 | Proxy to `:8000` and `VITE_API_TARGET`; the mock only with `VITE_API_MODE=mock`; `npm run gen:api` and `schema.d.ts`; clean operation ids; typed `ExecutionOut` and `ReplayOut` | 0, and every typed package | **Available now** (merged at b9534a7) |
| Manager auth, run history, required cut-off | PR #92 `feat/integration-backend-runs-auth` | 401 `unauthenticated` with no or an unknown `X-User-Id`; 403 for a non-manager on run, reprocess, sync, definition, resolve, ack and `POST /users`; `GET /processes/{id}/runs` and `GET /runs/{id}`; `cut_off_date` required on the workbook upload (422 without it) | 7; hardens 1, 3, 5, 10 | Draft, in progress |
| Unified proposals | PR #93 `feat/integration-proposals` | `POST /instances/{id}/proposal`, `GET /processes/{id}/proposals?status=`, `POST /proposals/{id}/accept` and `/reject`, `ResolveIn.proposal_id`; the chat and learning channels create proposals | 8; the rest of 5 and 9 | Draft, in progress |
| `FieldReading.symbol` | none yet (integration-plan task 0.5) | Evidence joined to its symbol with no frontend map | Removes the workaround in 6 | Not started |
| Symbol type enum | none yet (row 10) | `symbols[].type` rejects anything but `text`/`number`/`date` | Nothing (the `Select` covers it) | Not started |
| `Last-Event-ID` on `/events/stream` | later (row 35) | Live updates without polling | Post-demo | Later |

After each backend PR merges into `integration`, pull. The regenerated `schema.d.ts` is in the PR, and the provisional shapes in packages 7 and 8 must be checked against it.

## How to report a backend gap

When a screen needs a field or an endpoint the backend does not give, open a GitHub issue labelled **`backend-gap`**:
- Title: `<METHOD> <path>: <what is missing>`.
- Body:
  - The package number.
  - The endpoint, or "new endpoint".
  - The exact fields you expected, with their types.
  - What the response gives today: paste it, or the relevant part of `schema.d.ts`.
  - Whether it blocks the demo path.

Do not work around a gap by inventing data on the client. A labelled "—" is better than a fake number.
