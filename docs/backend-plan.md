# Backend plan for the integration

The backend work that is still needed so the console and the API work together.
The team split on 2026-09-19: the backend team owns `backend/`, `tools/` and the runbook, and Carlos owns `frontend/`.

Inputs:
- [integration.md](integration.md): the matrix. `#n` below is a row of its section 1.
- [frontend-handoff.md](frontend-handoff.md): Carlos's packages 0-12. `pkg n` below is one of them.
- PR #92 (**merged** at c72270c): run history, 401/403 for manager-only writes, required cut-off date. The tools and the runbook already send the manager's id.
- PR #93 (`feat/integration-proposals`, WIP): unified proposals for 3 channels and 4 kinds.

This plan does not repeat anything #92 or #93 already does.
Finishing #93 (the "Missing / next steps" list in its description) belongs to that PR's owner.

## Rules for every item

- `decisions/engine.py`, the rules and the golden test do not change. The golden stays at 471/471.
- Backend only: frontend files and styling are not touched. B0 adds test files and nothing else.
- An item that changes the API runs `make openapi` and commits `frontend/openapi.json` and `frontend/src/api/schema.d.ts`. `backend/tests/test_openapi.py` fails when they are stale.
  - Those two files are generated, so parallel PRs always conflict on them. On a rebase, never merge them by hand. Take either side, then run `make openapi` again.
- One PR per item into `integration`, and CI must be green.
- **Done check, every item:** `make check` is green (the golden included), CI on `integration` is green, and `make e2e-integration` is green (once B0 exists). Each item's own check comes on top of this.

## Coverage of the matrix

The (a) and (c) rows, and who covers them:

| Row | Feature | Dir | Covered by |
|---|---|---|---|
| #3 | Roles and enforcement | c | #92 (done) |
| #7 | Run history | a | #92 (done) |
| #10 | Symbol types | c | **B2** |
| #30 | `FieldReading.symbol` | a | **B1** |
| #35 | Live updates | c | **B4** |
| #39 | Typed contract | c | #91 (merged) |
| #40 | Error shape | a | #91 decided that 422 keeps `{detail}`. **B3** covers what is left (the 500) |

## Items

| Id | What | Depends | Parallel-safe | Size |
|---|---|---|---|---|
| B0 | Automated frontend-backend check (`make e2e-integration`, Playwright) | none | yes | L |
| B1 | `symbol` field on every extraction reading | none | yes | S |
| B2 | Enum for symbol types | D1 | yes | S |
| B3 | A 500 returns `{code, message}` | #93 merged | after #93 | S |
| B4 | Live updates: what polling needs now, and `Last-Event-ID` | none | yes | S |
| B5 | Check the handoff packages for backend gaps | none | yes | S |
| B6 | The 4 ingestion errors in the last demo | none (the fix may need #93) | investigation: yes | M |
| B7 | Batch-2 rehearsal with manager auth and step 1d | #92 (done), B8 | yes | M |
| B8 | Verify `tools/` and `make demo` after #92 | #92 (done) | yes | S |
| B10 | Plane metrics for the three dashboards ([observability-dashboards.md](observability-dashboards.md)): one typed response per plane, agent `known_cost_usd`/`unpriced_requests` priced like ingestion, a `traces` drill-down link on every row, new `/traces` filters | none | yes | S |

### B0. Automated frontend-backend check

**What:** one Playwright script (Chrome) that walks the demo path through the real console and the real API, plus a `make e2e-integration` target.
- **Setup:**
  - A fresh database, `trace_e2e`, with `alembic upgrade head`.
  - The pack loaded and published with no LLM (`make load-frozen MANAGER_ID=1`). The seeded manager is user 1, `martin@trace-it.local`.
  - The ERP stand-in (`make erp`) and the API on that database.
  - The frontend (`npm run dev`) against it, with the mock off (no `VITE_API_MODE`).
  - Playwright's `webServer` starts the frontend, and the make target starts everything else.
- **Demo path:** login and identity, then the process panel, then upload one text PDF and one scan from the challenge corpus, then run. The queue shows ESCALAR with its reason. Then the escalation detail, resolve, the trace view and the run history.
  - Pick the two PDFs from the golden, so both outcomes are known: a text PDF that ends PAGAR and a scan that ends ESCALAR with a known reason.
- **Assertions, on every screen:**
  - The `MOCK DATA` badge is absent, so the data is real.
  - No `ErrorNotice` is shown, found by its text ("El backend no responde", "Endpoint pendiente", or a backend message).
  - The ESCALAR reason on screen equals the one in `GET /instances/{id}`.
- **Scope grows with Carlos's packages:**
  - Steps that work today are live.
  - Each step still waiting for a package is `test.fixme('pkg n')`. It becomes live in the PR that lands package n.
  - Today: login is pkg 1, run history is pkg 7 (#92 is merged, waiting for the package), and escalation accept is pkg 5 (needs #93).
- **No LLM key:** the path never calls a model.
  - The pack is frozen, so nothing compiles.
  - The assistant's proposal is not part of the path (see D4).
- **CI:**
  - Add a job to `.github/workflows/ci.yml` on PRs into `integration`. It uses the same Postgres service, Node, `npx playwright install chromium`, the challenge submodule, and the OCR weights (98 MB) cached with `actions/cache`, keyed on the manifest.
  - If the scan's OCR is too slow or too heavy for CI, the job runs the text PDF only, and the scan step runs locally. `tools/README.md` documents the manual run.
- **Files:** new `tests/integration/` (`package.json`, `playwright.config.ts`, `demo-path.spec.ts`, `README.md`), `Makefile` (`e2e-integration`), `.github/workflows/ci.yml`. `frontend/` is not touched (D3).
- **Why:** Martín's goal, that the frontend and the backend must work well together. It is the done check for every other item and for every package in the handoff.
- **Done check:**
  - `make e2e-integration` passes locally on a fresh database.
  - With the API stopped, it fails on the `ErrorNotice` assertion.
  - With `VITE_API_MODE=mock`, it fails on the badge assertion.
  - The CI job is green, or `tests/integration/README.md` explains why it runs by hand and how.

### B1. `symbol` on every extraction reading

**What:** add `FieldReading.symbol: str | None` (additive). It names the pack symbol that each extraction field feeds, for example `supplier_tax_id` feeds `issuer_nif` and `payment_iban` feeds `iban`.
- **Why:** #30, WP1, pkg 6. Carlos keeps a three-entry map in `DocumentPane.tsx`, marked "remove when `FieldReading.symbol` lands".
- **Files:**
  - `backend/app/features/ingestion/schemas.py`.
  - The code that builds `/instances/{id}/document`: `features/ingestion/process_router.py` or `process_service.py`, wherever the field-to-symbol mapping already lives. Reuse it and do not write a second map.
  - A test beside ingestion.
  - The regenerated OpenAPI files.
- **Done check:** `GET /instances/{id}/document` for a batch-1 invoice has `symbol == "issuer_nif"` on the NIF reading, and every reading that feeds a symbol has its name. The golden is unchanged, because the field only adds data.

### B2. Enum for symbol types

**What:** the type of each symbol becomes `Literal["text", "number", "date", "boolean"]` on the input schemas: `POST /processes/definition` and `PUT /processes/{id}/draft {symbols}`.
- The output schemas stay `str`, so a row already stored with another value still serialises.
- **Why:** #10, WP1, pkg 9. Today `booleano` is stored as it is.
- **Files:** `backend/app/features/processes/schemas.py`, `draft_schemas.py` if symbols are declared there, a test, and the regenerated OpenAPI files.
- **Depends:** D1 (whether `boolean` is on the list).
- **Done check:**
  - Posting a pack with `"type": "booleano"` gets a 422.
  - `processes/invoice-payment.json` and `processes/travel-expenses.json` both load.

### B3. A 500 returns `{code, message}`

**What:** an exception handler for any unhandled `Exception`. It logs the error and returns 500 `{"code": "internal_error", "message": "..."}`, using the existing `TraceError` default. Today an unhandled error returns plain text.
- The 422 keeps FastAPI's `{detail}`, as #91 decided and the handoff documents (D2).
- **Why:** #40, WP1. `http.ts` then never has to handle plain text.
- **Files:** `backend/app/main.py` and `features/ingestion/application.py` (it has its own handler), plus a test.
- **Depends:** #93 merged, because #93 edits `main.py`.
- **Done check:** a test route that raises `RuntimeError` gets JSON `{code: "internal_error"}` with status 500.

### B4. Live updates: polling now, SSE later

**Now (polling, Q3 (b)):** the backend guarantees the following, and B4 adds a test for each point that has none yet.
- `POST /processes/{id}/run` stays synchronous and returns the final `RunSummary`, so nothing needs to be polled during a run.
- `GET /processes/{id}/rules` shows every rule change as soon as it is committed: `compiling`, then `draft` or `blocked`. The console polls it every 2 s while a rule compiles.
- The endpoints the console polls (`/summary`, `/queue`, `/rules`, `/alerts`, `/health/planes`) are reads with no LLM, no network and no writes. Each answers in under about 200 ms on the batch-1 database (500 instances). Measure them once, and write the numbers in the PR.

**SSE later:** `GET /events/stream` already sends `id:` (`events.id`) and accepts `?after=`.
- The only thing missing is reading the `Last-Event-ID` header as a fallback for `after`, so a browser's `EventSource` resumes after a reconnect.
- It is a small change, so do it now even though the frontend uses it later.

- **Why:** #35, and the "Later" list of the integration work order.
- **Files:** `backend/app/features/traces/router.py` and a test in `features/traces/tests/`.
- **Done check:**
  - A stream opened with `Last-Event-ID: n` replays from `n+1`.
  - The latency of each polled endpoint is in the PR.

### B5. Check the handoff packages for backend gaps

A first pass, done while writing this plan:

| Pkg | Backend need | Status |
|---|---|---|
| 0, 0b | Proxy, typed client, `{code, message}` | #91 |
| 1 | Login, 401/403 | `POST /login` exists; 401/403 in #92 |
| 2 | Counts, latency, cost, publish, version | `/summary`, `/metrics/execution`, `/metrics` (`providers[].known_cost_usd`), draft, publish and `/versions` exist |
| 3 | Upload, run, `down_sources`, cut-off | Exists; the cut-off becomes required in #92 |
| 4 | Queue with `review_pending` | Exists |
| 5 | Proposal, then accept or resolve | `/suggestion` exists; accept and reject in #93 |
| 6 | PDF, evidence by symbol, spans, file size | `/file`, `/trace` (`size_bytes`) and `/document` exist; `symbol` is **B1** |
| 7 | Run history | #92 |
| 8 | Proposals inbox | #93 |
| 9 | Draft edits, import, chat | Draft endpoints exist; the type enum is **B2**; chat proposals in #93 |
| 10 | Alerts, ack, resolved when the case is resolved | Exists: `resolved_by_decision_id` gives `resolved` |
| 11 | OCR mode, reviewer and models in the backend | Exists, no new endpoint: `GET /processes/{id}/execution`, `PUT /processes/{id}/draft {execution \| decision_review}`, `GET /use-cases/{id}`, `PUT /use-cases/{id}/agents/{role}`. The handoff's OCR values (`local`/`gemini`/`got`) map to the backend's `local`/`api`/`hybrid` in the frontend |
| 12 | Mock removal | Nothing on the backend |

**What:** confirm the table against `frontend/openapi.json` now for #92's part, and again after #93 merges.
- Every operation id and response field named in the handoff's endpoint tables must exist.
- Open a `backend-gap` issue for each miss, in the handoff's format.
- **Files:** none, or this table.
- **Done check:** every endpoint row of the handoff is matched in `openapi.json`, and the misses are issues or "none" in the PR.

### B6. The 4 ingestion errors in the last demo

**What:** the last demo recorded 4 ingestion spans with an error, out of 2853. They look like provider calls that failed and were retried.
- Find out, for each one:
  - which call it was (`schema_fields.py` `call`/`mark_network_attempt`, `payment_verification.py`, the OCR provider spans from #59);
  - whether the retry succeeded;
  - whether the invoice's evidence and outcome were the same as with no error.
- **Possible outcomes:**
  - A retried call that then succeeded: record it as a retry (a `retried` attribute, or a status that is not `error`), so `/health/planes` does not show the ingestion plane as degraded for a call that recovered.
  - A real failure: its invoice must end ESCALAR with `MISSING_DATA` and never with a wrong value. Add a regression test with a scripted provider.
- **Why:** the traceability rubric, and `/health/planes`, which the sidebar shows (pkg 2).
- **Files:**
  - Investigation: none. Use `make trace-decision FILE=<id>` and `GET /traces?plane=ingestion`.
  - Fix: `features/ingestion/*` and maybe `features/traces/service.py`, which #93 also edits. A fix in that file waits for #93.
- **Done check:** each of the 4 spans is explained in the PR (call, retry, effect on the outcome). On a rerun of the demo, only unrecovered failures are counted as errors, and the golden is unchanged.

### B7. Batch-2 rehearsal with manager auth and step 1d

**What:** rehearse all of [runbook-batch2.md](runbook-batch2.md) on a restored copy of the live database. #92 is merged, so this can start now. Never on the live database itself. The copy comes from `make backup`, restored under another name.
- Check every write against #92's 401/403:
  - `sync` (4b), `reprocess` (5, 5b, 9), `norm` (6), `retire`, `validate` and `publish` (6e), and the rule create in 6d;
  - `files` and `run` in 7'. #92 already added `-H "$MANAGER"` to both.
- Check that `tools/demo_run.py` (7) logs in as the manager and sends the cut-off.
- Run step 1d (compiler `max_tokens` 16000, "Compiler token limit") and confirm the draft shows `compiler 16000`. Then confirm the step-6 compile of one v4-style check comes back `draft`, not `blocked` with `finish_reason` length.
  - Use a short norm text. This step calls the LLM, so it needs keys in `.env`.
- Check step 1's branch: it says `git switch dev`. Set it to whatever branch Saturday runs from.
- **Why:** the Saturday delivery, and #92 changes who may call what.
- **Files:** `docs/runbook-batch2.md` (fixes), and the rehearsal output in `demo-logs/rehearsal-batch2/`.
- **Done check:** every step runs as written on the copy, and each fix is in the runbook. `make check-outcomes` is OK on the rehearsal export, and the batch-1 diff (10b) shows only step 5's changes.

### B8. `tools/` and `make demo` after #92

**What:** #92 already changed the tools: `demo_run.py` logs in as the manager and sends the cut-off, and `bench_scale.py` and `audit_page` use user 1. What is left is to run the driver scripts end to end against a fresh `make setup` with the ERP up, since #92's CI does not run them:
- `make demo` (all 500 invoices);
- `make demo-llm-down`;
- `tools/bench_scale.py` (smoke);
- `tools/audit_page`;
- `make trace-decision`.

Fix any 401, 403 or 422 that is left.
- **Why:** #92 closed writes that the tools used without a header.
- **Files:** `tools/*`, `tools/README.md`.
- **Done check:**
  - `make demo` writes 500 outcomes, and `make check-outcomes` is OK.
  - `demo-llm-down` ends as documented.
  - None of these tools gets a 401 or a 403.

## Waves

**Wave 1, now.** Launch these together:
- **B0 first**, because it is the check every other item must pass. It starts with the steps that work today.
- **B1, B2 (once D1 is answered), B4, B5 (first pass above) and B6 (investigation).**
- **B8, then B7.** #92 is merged, so both can start now. B7's step 7 uses `demo_run.py`, so B8 goes first.
- They touch different files, except the generated OpenAPI files: B1 and B2 both regenerate them. Merge one of them, then rebase the other and run `make openapi` again.
- B0's own done check runs after it merges. B1, B2 and B4 merge after B0, so each one is proven by `make e2e-integration`.

**Wave 2, after #93 merges:**
- **B3** (`main.py`).
- **The B6 fix**, if it touches `traces/service.py`.
- **The B5 confirmation** against the merged `openapi.json`.
- **Grow B0:** turn on its pkg 7 steps (#92 is merged) and its pkg 5 accept steps (after #93) as Carlos's packages land.

Merge order inside a wave: the smallest API diff first, then `make openapi` on each rebase.

## Decisions for Martín

| D | Question | Options | Recommendation |
|---|---|---|---|
| D1 | Which symbol types are allowed? | (1) `text`/`number`/`date`, as the integration vocabulary says. (2) Also `boolean` | **(2).** `processes/travel-expenses.json` declares `has_receipt` as `boolean`, and pkg 9's done check imports that pack. With (1) it would be refused. Add "Booleano" to the vocabulary table in `integration.md` |
| D2 | Should the 422 also become `{code, message, detail}`? | (1) Keep FastAPI's `{detail}` (#91). (2) Wrap it | **(1).** It is documented in `api.md` and the handoff, and `http.ts` already parses it. B3 fixes only the 500, the one shape that is not JSON |
| D3 | Where does the Playwright check live? | (1) `frontend/e2e/`. (2) `tests/integration/` with its own `package.json` | **(2).** `frontend/` is Carlos's, and a new devDependency there conflicts with his lockfile on every package. The check covers both sides, so it sits outside both |
| D4 | Is the assistant's proposal part of B0's path? | (1) Yes, with a scripted model behind a backend setting. (2) No: the path resolves a case directly | **(2).** No test may need an LLM key (AGENTS.md), and a new test-only setting is code for one test. It only holds if the escalation detail does not call the assistant when it opens. If pkg 5 makes that call automatically, Carlos makes it a click, or the check allows an `llm_error` notice on that panel only |
| D5 | Does B0 run the scan in CI? | (1) Yes, with the 98 MB of OCR weights cached. (2) The text PDF only in CI, and the scan run locally | **(1) if the job stays under about 10 minutes, otherwise (2).** Decide after B0's first CI run |

## B5 result: the handoff against `openapi.json` (2026-09-19, integration at fa24f2d)

Every endpoint row of packages 1-11 was checked, by method, path, request fields and response fields, against `frontend/openapi.json`. Package 0, 0b and 12 name no endpoint.

| Pkg | Endpoints | Result |
|---|---|---|
| 1 | `login`, `me` | All present |
| 2 | `getProcess`, `getProcessSummary`, `getProcessPlaneMetrics` (execution), `getProcessMetrics`, `getPlanesHealth`, draft `get`/`validate`/`publish`, `listProcessVersions`, `getExecutionSettings` | All present |
| 3 | `uploadProcessDocument`, `extractInstanceDocument`, `runProcess` (`down_sources`), `uploadProcessWorkbook` (`cut_off_date` required), `listSources`, `getSource`, `syncSource` | All present |
| 4 | `getQueue` (`type`), `listInstances` (`status`, `decision`, `q`), `getInstance` (`reviews[]`) | All present, `review_pending` included |
| 5 | `getInstance`, `getSuggestion`, `resolveInstance`, `createRule` | Present |
| 5 | `POST /instances/{id}/proposal`, `ResolveIn.proposal_id`, `POST /proposals/{id}/accept` and `/reject` | Missing, known: #93 |
| 6 | `getInstance`, `getInstanceTrace` (`file.size_bytes`, `rule_results[].rule_text`, `exported_decision`, `spans[]` tree), `getInstanceFile`, `getInstanceDocument` | Present. `FieldReading.symbol` is missing, known: **B1** |
| 7 | `listRuns`, `getRun` | Present. The handoff said `execution_id` and `escalations`; the API names them `id` and `escalation_reasons`. Fixed in the handoff, no backend change |
| 8 | `analyzeProcessCases`, `getNormProposal` | Present |
| 8 | `GET /processes/{id}/proposals`, accept and reject | Missing, known: #93 |
| 9 | `editProcessDraft` (`description`, `symbols`), `loadDefinition`, rule create, compile, get, impact, activate and retire, `normalizeNorm`, the four `process-drafts` operations | Present. `SymbolIO.type` is a free string, known: **B2** |
| 10 | `listAlerts` (`status`), `ackAlert` | Present, `resolved_by_decision_id` included |
| 11 | `getExecutionSettings`, `editProcessDraft` (`execution`, `decision_review`), `getUseCase`, `configureAgent` | All present |

**Missing endpoints:** none new. Every miss is already #93, B1 or B2. Run this check again after #93 merges.

**Package 2 was missing a sequence, now documented.** In a live demo on v1.0, a process whose rules came from a compiled norm returned 409 on every run. It needs `POST /rules/{id}/activate` for each rule, then `draft/validate`, then `draft/publish`, all as the manager. The handoff's package 2 now lists these steps with their endpoints and errors.

**New item B9, not built: activate and publish in one call.** Today it takes 2 + n calls, and the client must carry `revision` and `validation.hash` from validate to publish.
- **What:** `POST /processes/{id}/draft/publish` with `{rule_ids?, reason}` and no `validation_hash`. It stages the rules, validates, and publishes only if the validation is valid, all under the process lock. It answers 409 with the validation report when it is not valid.
- The two-step flow stays for the Panel, where the manager reviews the coverage before publishing.
- **Why:** the demo's 409, and one call for the tools and the runbook.
- **Size:** S.
