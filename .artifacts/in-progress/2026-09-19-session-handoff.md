# Session handoff — 2026-09-19 (orchestrator)

Resume as ORCHESTRATOR: never code; delegate to agents (worktree, PR into target branch, do not merge); merge only with CI green + golden 471/471. Talk to Martín in Spanish, concise, tables, a recommendation with every question. Memory: `~/.claude/projects/-Users-apple-orca-projects-trace-pay/memory/` (see project-integration, project-decision-policy).

## State
- **main = v1.0** at 65bd45b (merge of release/v1.0 = dev ef3e079). Verified from a clean clone: 443/36/21, golden 471/471, compose + demo + frontend build OK. Only main is frozen; dev stays open.
- **integration** (from main): b9534a7 = #90 (docs/integration.md reconciliation matrix + docs/integration-plan.md) + #91 (phase 0: contract, operationIds, `make openapi` + `npm run gen:api`, mock opt-in `VITE_API_MODE=mock`, proxy :8000 / `VITE_API_TARGET`, CI on integration).
- Split: our team = BACKEND; Carlos = FRONTEND. Integration = functionality only, never aesthetics.

## In flight (saved as draft PRs into integration; check `gh pr list --base integration`)
1. **Draft PR #92** `feat/integration-backend-runs-auth` (NOT green: ~28 failing unit tests, mostly tests creating users/processes without a manager header; runs/401/403/cut-off tests unwritten; must merge integration #91, add listRuns/getRun operationIds, `make openapi`, docs): `GET /processes/{id}/runs`, `GET /runs/{id}` (history timeline, compare escalations across reruns); manager-only (401/403) on run, reprocess, sync, definition, publish, resolve, alert ack, POST /users; cut-off date required on workbook upload; "Decisions (Martín)" section in docs/integration.md.
2. **Draft PR #93** `feat/integration-proposals` (NOT green: migration 0015 `proposals` table + endpoints + `POST /instances/{id}/proposal` + resolve `proposal_id` done; test `test_only_a_manager_settles` fails (creates user with invalid role `user`), 4 new tests never ran; must merge integration #91, `make openapi`, docs/api.md, live Helmcode run; schema named `ManagerProposalOut`): unified proposals (kind decision|rule|context|input|source) through 3 channels: escalation assistant (why + options + proposed decision; accept = resolve), definition chat (accept = stage into draft), learning agent (promotions from traces). `GET /processes/{id}/proposals`, `POST /proposals/{id}/accept|reject`.
3. `docs/frontend-handoff.md` (branch `docs/frontend-handoff`): Carlos's package-by-package frontend plan. **DONE: merged as #94 (integration 55b8c42) and sent to Carlos by WhatsApp 2026-09-19** (contact "Carlos Hackspain", 34615799708@s.whatsapp.net): the file plus a short message, signed `MartinBot🤖`.

For each: finish (merge integration, `make openapi`, CI green, golden 471/471), then merge into integration.

## Martín's integration decisions
Run history timeline with easy going back; "Proponer" = the 3 channels above for all 4 kinds; runs stay synchronous; cut-off date is a required input; single manager role (the app user replaces the intern and handles only escalations); learning is shown via reruns in the run history (no new UI).

## Delivery (pending the team)
`delivery/outcomes_system.jsonl` (443/36/21, generated and traceable) vs `delivery/outcomes_mateo_review.jsonl` (452/40/8, hand review). My recommendation: option C = enter Mateo's review as traced human resolutions and export the final decision. Also open: the 4 scan IBAN cases (NO_PAGAR vs ESCALAR). The final delivery file should carry only file_id + result.

## Other notes
- Key ADRs A-E: docs/key-decisions.md; preview artifact https://claude.ai/artifact/FirnvywWuEUdsaR6mLt5JL ; PDF demo-logs/delivery/albertitos_plan.pdf (team name/members/teamId still missing).
- Saturday runbook: docs/runbook-batch2.md (step 1d: refresh draft agents so compiler max_tokens 16000 applies).
- Keep worktree agent-a30cad90bd2b8e611 (delivery run .data). Data backup: /Users/apple/orca/projects/trace-pay/worktree-data-backup-2026-09-19/.
- Minor: 4 ingestion errors out of 2853 spans in the last demo (retried provider calls); 946 kB frontend bundle.

## Local files (untracked in the pelican checkout, not in git)
- `.artifacts/specs/2026-09-19-frontend-inventory.md`, `2026-09-19-backend-inventory.md`, `2026-09-19-openapi-dev-cc1c3fb.json` (integration inventories), `.artifacts/specs/2026-09-19-frontend-backend-integration-plan.md` (same content as docs/integration-plan.md on integration), `.artifacts/pages/2026-09-19-live-monitor.html`.
- `demo-logs/api*.log` and `dashboard/server.log` show as modified only because of runtime writes: do not commit them.
- Still running locally: demo API :8010, dashboard :8020, ERP :8009, monitor :8021.
- The other session (peer "assitant") saved everything: no running agents, nothing pushed.

## Update (after account switch)
- integration head moved: #92 runs+auth, #93 proposals, #95/#97 Carlos (error states, login), #100 B1+B2, #104 B0 e2e (`make e2e-integration`, CI job `e2e-integration`).
- Plans: docs/backend-plan.md (B0-B10), docs/frontend-handoff.md (sent to Carlos), docs/observability-dashboards.md (PR #108: THREE dashboards, one per plane — ingestion (tokens+cost per provider), agents (by role/rule/model), execution (0 tokens); every number drills down to spans; v1.0 demo 214,734 tokens = 24% ingestion / 76% agents / 0 execution).
- Agents running: integrator for `integration` (#105, Carlos stack #99/#102/#103/#106, #108, then new PRs), integrator for dev/main (#88, #101 dev->main VPS deploy: review, secrets, golden, demo before merge commit), B3 (500 JSON + llm_error 502), B8->B7 (tools + batch-2 rehearsal + P001-without-workbook check), B9 (Gemini 429 limit/backoff + Helmcode fallback), B10 (typed /metrics/{plane}, known_cost_usd, unpriced_requests, drill-down).
- Open decision for Martín: drop the login screen (my recommendation: auto-identity as the pack manager, keep X-User-Id for authorship). If yes: tell Carlos by WhatsApp and adjust the e2e.

## Saturday OCR config (B9, PR #107)
Gemini free quota exhausted (500/day). Use Helmcode vision primary: `TRACEPAY_OCR_PROFILE=experimental` + `TRACEPAY_VISION_PROVIDERS=helmcode,gemini`, set BEFORE `make load-frozen` (a published version pins its image reader); run `make ocr-check` by hand. Live: 62x200, 0x429; 29 scans 11 PAGAR / 18 ESCALAR; only diff vs outcomes_system is scan_004 -> PAGAR (correct: PO-2026-0480 matches all sources). No misread pays.
Also open: B11 (never-loaded source -> ESCALAR), B12 (norm v4 publish blocker + rule writes manager-only), #101 dev->main re-review at new head (accept scan_004 diff).

## STATE AT ACCOUNT SWITCH (latest, read this first)
- **main = v1.1** at a71434e (tag v1.1): full frontend-backend integration (Carlos packages 0-13 + backend B0-B12) + dev fixes. Deployed to VPS OK (run 35448525648): https://gex-dashboard.hopto.org/nexia/trace-it/ (basic auth; creds in /opt/trace-it/secrets/access.env on the VPS). dev = 73727ff. integration = b301af9 (merged into dev). CI deploy now requires e2e-integration.
- **Local stack of main RUNNING**: worktree /Users/apple/orca/projects/trace-pay/.claude/worktrees/main-local — console http://localhost:5300, API :8300, ERP :8309, DB trace_local_test; `./local-stack.sh stop|start|status`, `./local-seed.sh` reseeds; PIDs in logs/pids.txt. Old stacks: demo :8010/:8020/:8009/:8021; integration-local stopped.
- **In progress**: Playwright review of main (all screens/flows) -> `REVIEW-v1.1.md` in main-local worktree (paused as PARCIAL at switch; resume the remaining screens). Martín's next step: use that list to split work Carlos (FE) / backend.
- **Known findings to include**: FE1 opening an escalation auto-calls the assistant (spends tokens per click); FE2 "N propuestas esperan" links to Definition instead of Review; FE3 unrounded ms in run history; FE4 execution dashboard "Evaluaciones" counts runs not invoices; FE5 alerts screen copy + blank "Ahora (motor)"; FE6 English block in Spanish UI; FE7 production offline notice shows a developer hint "make setup (:8000)"; BE1 assistant can take 218 s and hit token limit; BE2 assistant spans counted in execution plane (shows "Degradado", contradicts 0 tokens); BE3 decisions_by_outcome counts human resolution (31 for 30).
- **Deployment security still open**: protect env trace-it-production, scope SSH secrets to it, make production-stack required on main, CORS * on 500 responses -> restrict to real domain.
- **Cleanup pending**: worktree /Users/apple/orca/workspaces/trace-pay/promote; many *_test DBs on trace-pay-db-1.
- **Resume phrase**: "lee la nota de traspaso y continúa como orquestador".
- Review PARCIAL saved (main-local/REVIEW-v1.1.md): ~1/3 covered (landing, process list, Panel, Atención links, Ejecuciones list + one case detail, Definición→Normas). 12 findings (6 important, 6 minor; 7 FE, 4 BE, 1 both), no blocker, no console errors/failed /api/slow >3s. New: Panel opens with ~20 lines of English pack description; "Models and execution effort" form in English on the Panel (belongs in Ajustes); escalation-reason chart sums 2 for 5 escalations (missing UNVERIFIED_DATA / duplicate order) [BE]; cost "0,00 USD" hides unpriced Helmcode calls; landing says "once reglas" and 433/36/31 (should be 12 rules, 443/36/21). Remaining: upload+run, run compare, Revisión + Proponer + resolve, trace PDF, alerts, Lectura/Agentes dashboards drill-down, rest of Definición (chat->draft->publish), inbox, Ajustes, ERP-down and API-down cases, update LOCAL-TEST.md. Headless Chrome on :9333 (+ recorder) left open; PIDs in logs/pids.txt.

## Update 2026-09-19 evening (latest)
- Dashboards: NO redesign (Martín). Carlos only improves how existing data is shown. Traceability canvas shelved.
- main: #143 (dev->main) merged 0cbe3b7; Mateo fixed e2e on main (#147, 006b66a), deployed OK (run 35452689147). #148 (Mateo, dev->main) conflicting on demo-path.spec.ts, his to resolve.
- dev: #149 e2e fix, #150 B1-B4 metrics data, #151 ADR refinement (A-E restructured, 0022 dup -> 0031, new 0032-0034, 34 detail ADRs), #152 reviewer agent backend (1efd480, ADR 0035, docs/reviewer-agent.md).
- Mateo's 1704cbe on dev removed tests/integration + e2e-integration job; Martín: restore it -> agent on `ci/restore-e2e-integration` (PR pending).
- In flight: `fix/reviewer-agent-quality` (hallucinated rationale, rejection feedback, output token cap, llm_run span instance id, tools/reviewer_demo_pdfs.py).
- #153 mail ingestion (Mateo): review verdict HOLD until after Sunday (draft, conflicts, no ADR, untraced mail steps, real mailbox hardcoded in public repo, IMAP abort kills worker). Not yet told to Mateo.
- Reviewer agent verified end to end via API on local stack :5400/:8400/:8409 (DB trace_reviewer_test, X-User-Id 2), guide TRY-REVIEWER.md in worktree agent-acfd92c787df45063. Demo pair = two 10% VAT invoices (PO-2026-0726, PO-2026-0717); catering/41082 is a real duplicate.
- Next: when Carlos ships FE-3/FE-4, run the full loop from the console with Playwright (Playwright Chrome currently held by another session on s003).
- Slides (5 ADRs, Spanish, 14): https://claude.ai/artifact/H1GiAiA6cpKMhZYvvrVgb8
- Open for Martín: Helmcode 444/36/20 log (else drop), OCR fallback wording, TRACE_DECISION_WORKERS=1 in deploy, B5 billing mode (recommend included), regenerate albertitos_plan.pdf.

## Update 2026-09-19 night (all agents stopped by Martín: token budget)
- dev = main = 7b5c336 (team promoted #164/#167/#169), then dev += #170 (d38dded, advice quality). Reviewer agent FE+BE complete (#152 #157 #161 #162 #165 #170); traceability gaps #163. CI now manual (workflow_dispatch).
- Live demo (headed Chromium script .scratch/reviewer-demo-live.mjs, runs in .scratch/demo-run-*): UI OK, loop failed on reviewer rule quality -> fixed in #170 (data-grounded rules). Re-run demo on current dev still pending (stack :5400 worktree agent-aab68a0d317e3a2bd, currently on PR161 branch; use pull-and-restart.sh + local-seed.sh).
- Open: duplicate-pair advice names wrong "first" invoice (date validator, ~30 min). UI: card silent on compile failure; Validar not blocked for rule without code; English error.
- Latency audits (OCR parallelization; flash model for advice, target p95 2-3 s) were started and STOPPED before reporting. Resume only on Martín's OK; worktrees agent-ae809783597d7dce7 (OCR) and agent-ae75374488cf5f375 (advice).
- Martín prefers speed: no required checks on dev. Genericity: core generic, no more work (GDPR pack in agent-a7aa261aa57a33376/.scratch).
