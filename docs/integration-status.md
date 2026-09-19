# Integration status

**Date:** 2026-09-19, about 15:30 CEST.
**Audited:** `origin/integration` at 3f7bcc2 (after #112 and #118), and Carlos's stack up to `feat/fe-11-settings` (fe9ef5d).
**Against:** [frontend-handoff.md](frontend-handoff.md) (packages 0-12), [backend-plan.md](backend-plan.md) (B0-B12), [integration.md](integration.md) (the matrix and Martín's decisions) and [observability-dashboards.md](observability-dashboards.md).

This is a snapshot. Update it when the stack lands.

## Frontend packages

The stack is a chain of PRs: #102 → #103 → #106 → #109 → #114 → #116 → #117. Only #102 targets `integration`. The others target the previous `feat/fe-*` branch.

| Pkg | Status | Plan conformance |
|---|---|---|
| 0 Setup | Merged (#91, backend) | Conforms |
| 0b Error states | Merged (#95) | Conforms. Adds 2 new class strings in the Sidebar and the palette (minor) |
| 1 Identity | #97 (login screen) merged. #113 (no login screen, automatic manager) open, CI green | #97 predates Martín's decision. It also has a bug: `state/session.tsx:46` sets `X-User-Id` in a `useEffect`, after the child queries have already fired. A hard reload of a deep link sends its first reads without the header. `GET /processes/{id}/execution` is manager-only, so it answers 401, the session signs out, and the user lands on Procesos. #113 fixes this, because the console renders nothing until it knows the identity. Verified with the pkg 7 e2e step |
| 2 Panel and publish | Merged (#99) | Conforms: `/summary`, p50 from `/metrics/execution`, provider cost from `/metrics`, the `/health/planes` badge, the version chip from `/versions`, and publish with `HistoricalCoverage`. Minor: a new `PublishDraft.tsx` built from existing controls, a raw-JSON `<details>` copied from `ExecutionSettings`, and 1 new class string |
| 3 Upload, run, sources | PR #102 open. **CI e2e red** | Endpoints conform: progress per file, `/extract` when `created:false`, `cut_off_date` required, `syncSource`, `SourceOut`. The red e2e is a test bug, see gap 2 |
| 4 Queue and tabs | PR #103 (stacked) | Conforms: `/queue` with no `type`, the "Revisión del revisor" tab, English statuses |
| 5 Escalation detail | PR #106 (stacked) | The "now" half conforms: "Por qué se escaló", and "Aceptar la propuesta" through `resolve`. **The #93 half is missing**, although #93 merged at 12:38: there is no `POST /instances/{id}/proposal`, no `/proposals/{id}/accept\|reject` and no `ResolveIn.proposal_id` |
| 6 Trace view | PR #109 (stacked) | Conforms: the PDF from `/file`, `/trace` `rule_text` and `exported_decision`, and `documents.generated.ts` deleted. **Deviation:** `lib/symbols.ts:3-8` keeps the 3-entry `FIELD_SYMBOL` map. B1 merged in #100, so it should read `FieldReading.symbol` |
| 7 Run history | PR #114 (stacked) | Conforms: `listRuns`, `getRun`, `?run=` and the notice. The e2e step fails because of a backend defect, see gap 4 |
| 8 Proposals inbox | Not started | – |
| 9 Definition editing | Not started | Hazards still live on the stack: `live.ts:178` sends Spanish `tipo` (`texto`/`numero`/`booleano`, offered by `NewProcess.tsx:359-361`), which B2 now rejects with 422. `live.ts:226` `replaceSymbols` re-posts the whole definition (rows 8 and 9). `live.ts:102` still has `autor: 'tester'` |
| 10 Alerts | PR #116 (stacked) | Conforms: `listAlerts`, `ackAlert` and a 10 s poll |
| 11 Settings | PR #117 (stacked) | Conforms: no `trace.process.*` keys, OCR `local`/`api`/`hybrid` saved through `editDraft`, use-case models. Adds a new `UseCaseModels.tsx` built from existing controls |
| 12 Mock removal | Not started | `mock.ts`, `invoices.generated.ts` and `VITE_API_MODE` remain |
| 3 plane dashboards | Not started, no package | [observability-dashboards.md](observability-dashboards.md) marks them required. B10 serves the data. The Panel shows only the execution p50 and the ingestion provider cost |

Checks across every package:
- **`X-User-Id`:** `http.ts` adds it to every request once `setUserId` has run. The only hole is the boot race in #97.
- **Types:** every response type is an alias of `components['schemas']`. `npm run build` passes on the stack merged with the current `schema.d.ts`, so the fields have not drifted.
- **Mock:** replaced methods throw `noMock`. No PR adds invented data.
- **Visuals:** there is no new CSS or tokens. 6 class strings are new across 11 commits. The rest are copied from existing markup.

## Backend items

| Item | Status | Done check |
|---|---|---|
| B0 e2e | Merged (#104) | Met: `make e2e-integration` is green locally and the CI job exists. Gaps: CI never runs on a push to `integration` (`ci.yml:4-7`, `push: [dev]`), so "CI on integration green" cannot be checked after a merge. The path never loads the workbook with a cut-off, so pkg 3's required input is untested |
| B1 `FieldReading.symbol` | Merged (#100) | Met. It is in the spec |
| B2 symbol type enum | Merged (#100) | Met: `processes/schemas.py:30` has `Literal[text, number, date, boolean]`. The frontend still sends Spanish values (pkg 9) |
| B3 500 as `{code, message}` | Merged (#110) | Met (`tests/test_errors.py`) |
| B4 `Last-Event-ID` and polling timings | Merged (#105) | Met: `traces/router.py:200`, and the timings are in the PR |
| B5 gap check | Merged (#105) | Half met. The table in `backend-plan.md` still lists the #93 endpoints as missing. The re-check after #93 was not done. This audit did it: every endpoint the handoff needs is in `openapi.json` |
| B6 ingestion errors | Merged (#105) | Explained in the PR (18 errors, not 4). Not re-verified here |
| B7, B8 rehearsal and tools | Merged (#112) | Met, according to the PR. The B8 run found the no-workbook bug, which B11 fixes |
| B9 | **The id is used twice** | The plan's B9 (activate and publish in one call) is not built. PR #107 (provider concurrency and 429 backoff, open) also calls itself B9 |
| B10 plane metrics | Merged (#115) | Met: `AgentsMetrics`, `known_cost_usd`/`unpriced_requests`, and the `/traces` filters |
| B11 never-loaded source escalates | Merged (#118) | Not in `backend-plan.md` |
| B12 publish past escalated scans, manager-only rule writes | PR #120 open | Not in `backend-plan.md` |

## E2E results (`make e2e-integration`)

| Step | `integration` 3f7bcc2 | Stack fe-11 + integration + #113, local |
|---|---|---|
| Identity (login, or automatic with #113) | pass | pass |
| Process panel | pass | pass |
| pkg 2 published version | pass | pass |
| Upload 2 text PDFs and run | pass | pass *(a)* |
| pkg 3 progress and `by_decision` | fixme | pass *(a)* (folded into the step above) |
| Upload a scan and run | pass | pass |
| Queue shows the escalated invoices | pass | pass |
| Open the escalation detail | pass | pass |
| pkg 5 why it escalated | fixme | pass *(b)* |
| pkg 5 accept the proposal | fixme | fixme (the #93 half is not built, and it needs a proposal with no LLM, D4) |
| Resolve as the manager | pass | pass |
| Trace view | pass | pass |
| pkg 8 proposals inbox | fixme | fixme (not started) |
| pkg 7 run history | fixme | pass *(c)* |
| **Total** | **9 pass, 5 fixme** | **11 pass, 2 fixme** |

On `integration`, no `fixme` belongs to a package that has already merged, because 0b, 1 and 2 have no `fixme`.

The stack only reaches 11 pass with three local, unpushed changes:
- *(a)* `demo-path.spec.ts:107`: `getByText('2 ESCALAR')` also matches the run-history row "2 ESCALAR · Martín". It needs `{ exact: true }`. This is the red CI on #102.
- *(b)* `demo-path.spec.ts:144`: the reason appears twice, in the notice and in the rule result. It needs `{ exact: true }`.
- *(c)* Two things:
  - Without #113, the `page.goto` reload loses the identity: a 401, then sign-out, then Procesos (pkg 1 bug).
  - With #113, `GET /runs/{id}` lists `factura_41082.pdf` twice, as ESCALAR and as PAGAR. `decisions/runs.py:128` selects every decision with the run's `execution_id`, and a manager's resolve inherits that id (`decisions/service.py:625`). The count path at `runs.py:75` filters on `author == ENGINE`, but `get_run` does not. Adding the same filter makes the step pass.

Merging the stack into `integration` by hand has these problems:
- 6 files conflict (`contracts.ts`, `live.ts`, `mock.ts`, `queries.ts`, `es.ts`, `Process.tsx`), because #99 was squashed while the stack still carries its unsquashed commits.
- The auto-merge silently duplicates `decisionTone` in `lib/process.ts`, which fails the build with TS2300.
- #113 then conflicts with #117 in `Settings.tsx`: the "Salir" button.

## Contract drift (`live.ts` against `openapi.json` on `integration`)

- **Endpoints that no longer exist:** none, on `integration` or on the stack.
- **Fields:** none. The stack typechecks against the current `schema.d.ts`.
- **Values:** `live.ts:178` sends Spanish symbol types. After B2 they get a 422.
- **Endpoints the handoff requires that the frontend never calls, even on the stack:**
  - pkg 5 and pkg 8: `POST /instances/{id}/proposal`, `GET /processes/{id}/proposals`, `POST /proposals/{id}/accept` and `/reject`.
  - pkg 9: `PUT /processes/{id}/draft` for description and symbols (only settings use it), and `/process-drafts` (`startDiscoverySession`, `listDiscoverySessions`, `messageDiscoverySession`, `uploadDraftWorkbook`).
  - The dashboards: `/processes/{id}/metrics/ingestion` and `/processes/{id}/metrics/agents`.

## Top 5 gaps

| # | Gap | Owner |
|---|---|---|
| 1 | The stack (pkgs 3-7, 10, 11) is not in `integration`. It conflicts in 6 files, the auto-merge breaks the build, and stacked PRs never run the e2e job | Carlos (Martín sets the merge order) |
| 2 | The e2e is red on #102, and on the stack, because of two ambiguous assertions (`demo-path.spec.ts:107`, `:144`). The fix (`exact: true`) is verified | Carlos |
| 3 | The merged pkg 1 (#97) loses the identity on a reload, and #97 contradicts the no-login decision. #113 fixes both and is green | Carlos / Martín (merge #113 first) |
| 4 | `GET /runs/{id}` returns the manager's resolutions as run decisions (`runs.py:128`), so run history shows duplicate cases | Backend |
| 5 | Q2 "Proponer" (3 channels) has no UI: the #93 half of pkg 5, pkg 8 and pkg 9 are not started. pkg 9's hazards stay live: Spanish symbol types get a 422 after B2, and the full re-post on Contexto → Guardar. The 3 plane dashboards are not started either | Carlos |

## Next actions

**Carlos**
1. Rebase the stack onto `integration`. Retarget each PR to `integration` in order (3 → 4 → 5 → 6 → 7 → 10 → 11), so every one runs the e2e job.
2. In `demo-path.spec.ts`, add `{ exact: true }` at lines 107 and 144. Then #102 goes green.
3. Merge #113 before the stack, and resolve `Settings.tsx` by dropping "Salir".
4. pkg 6: replace `FIELD_SYMBOL` with `FieldReading.symbol`.
5. pkg 5, second half: the #93 proposal, accept and reject, and `proposal_id`.
6. pkg 9, at least the safe part: `editDraft` for Contexto and Inputs, and a `text`/`number`/`date`/`boolean` `Select`. Then pkg 8 and pkg 12.
7. The 3 plane dashboards, with existing components. Ask Martín where they go, since no package covers them.

**Backend**
1. `decisions/runs.py:128`: filter `get_run` on `Decision.author == ENGINE`, as the count path does, and add a test with a resolved case.
2. `ci.yml`: add `integration` to `push.branches`.
3. `backend-plan.md`:
   - Give #107 an id of its own, or rename the plan's B9.
   - Add B11 (#118) and B12 (#120).
   - Mark the B5 table as re-checked after #93: every endpoint is present.
4. `frontend-handoff.md` package 1 and `integration.md` row 2: record the no-login decision (the automatic manager identity).
5. B0: add a workbook upload with a cut-off to the e2e path, once pkg 3 lands. That way the required cut-off and the B11 behaviour are both covered by the demo path.
