# Branch history

Every feature branch was merged into `dev` through a pull request and then deleted. To restore one, run `git fetch origin pull/<PR>/head:<branch>`. GitHub keeps each PR's head ref.

| Branch | PR | Merged | Title |
|---|---|---|---|
| `chore/trace-it` | #12 | 2026-09-18 | chore: rename product to trace-it and make docs and code process-agnostic |
| `docs/agents-md` | #22 | 2026-09-18 | docs: add AGENTS.md as the shared assistant guide |
| `docs/guia-equipo` | #1 | 2026-09-18 | docs: add team guide and update team split |
| `docs/reparto-core` | #3 | 2026-09-18 | docs: assign core backend between agents and rules owners |
| `docs/exportacion-y-compilacion` | #13 | 2026-09-18 | docs: define exported decision and rule compilation trigger |
| `docs/process-packs` | #20 | 2026-09-18 | docs: explain process packs and configuration layers |
| `docs/tipos-decision` | #7 | 2026-09-18 | docs: make decision types fully configurable per process |
| `docs/agentes-pydantic-ai` | #19 | 2026-09-18 | docs: plan agents on PydanticAI |
| `docs/erp-scope` | #25 | 2026-09-18 | docs: scope the ERP connector before H1 |
| `docs/english` | #29 | 2026-09-18 | docs: translate documentation to English |
| `docs/adr-registry` | #21 | 2026-09-18 | docs(adr): add architecture decision records 0002-0013 |
| `docs/adr-decisions` | #24 | 2026-09-18 | docs(adr): record decision step, export policy, process versions and terminology |
| `feat/compilador` | #6 | 2026-09-18 | feat(agentes): compile rules with two blind agents and cross-tests |
| `feat/contexto-proceso` | #14 | 2026-09-18 | feat(agentes): give agents the process description as shared context |
| `feat/sandbox` | #4 | 2026-09-18 | feat(agentes): run generated rule code in an isolated sandbox |
| `feat/asistente` | #5 | 2026-09-18 | feat(agentes): suggest decision and new rule for escalated cases |
| `feat/esqueleto-backend` | #2 | 2026-09-18 | feat(backend): add FastAPI skeleton with users, processes and rules |
| `feat/decisiones-api` | #10 | 2026-09-18 | feat(decisiones): add the decisions API |
| `feat/motor` | #8 | 2026-09-18 | feat(decisiones): add the rule engine |
| `feat/auditoria` | #16 | 2026-09-18 | feat(decisiones): check a rule change against every past decision |
| `feat/ingestion` | #33 | 2026-09-18 | feat(ingestion): integrate document readings with the process API |
| `feat/activar-reglas` | #23 | 2026-09-18 | feat(procesos): let a rule ship with its code, and activate from the CLI |
| `feat/setup-rapido` | #11 | 2026-09-18 | feat(procesos): procesos declarativos en JSON y arranque con un comando |
| `feat/erp-connector` | #30 | 2026-09-18 | feat(sources): add configurable HTTP connector with ERP snapshotting |
| `feat/demo-run` | #31 | 2026-09-18 | feat(tools): run the whole invoice process over the real corpus |
| `fix/contexto-duplicado` | #15 | 2026-09-18 | fix(decisiones): drop contexto, a rule's cut-off date is a source row |
| `fix/exportar-decision-motor` | #17 | 2026-09-18 | fix(decisiones): export the engine decision, not a person's resolution |
| `fix/engine-fail-closed` | #28 | 2026-09-18 | fix(decisions): fail closed to REVIEW, run both rule codes, batch the sandbox |
| `fix/symbol-format` | #32 | 2026-09-18 | fix(decisions): pass flat symbol values to rule code |
| `chore/english` | #26 | 2026-09-18 | refactor!: translate code, API and schema to English |
| `test/e2e-golden` | #27 | 2026-09-18 | test: golden outcomes, end-to-end tests, compiler eval and CI |
| `feat/reglas-v3-manuales` | #18 | 2026-09-18 | test(decisiones): hand-write the sixteen v3 rules as a fixture |
| `chore/freeze-and-rehearsal` | #65 | 2026-09-19 | chore: freeze norm-compiled rules for delivery, rehearse batch 2 with full OCR |
| `chore/outcomes-names-compiler-tokens` | #84 | 2026-09-19 | chore: name delivery outcomes by origin; compiler max_tokens 16000 |
| `chore/mvp-polish` | #72 | 2026-09-19 | chore: polish the MVP for the jury (fresh clone, trace-decision, defense script) |
| `chore/demo-logs` | #52 | 2026-09-19 | chore: publish demo-logs run logs and throwaway dashboard |
| `chore/delivery` | #73 | 2026-09-19 | chore(delivery): record what we hand in and what the hand review found |
| `dev` | #40 | 2026-09-19 | Dev |
| `docs/scale-capacity-plan` | #63 | 2026-09-19 | docs: capacity limits, cost formula, deployment scenarios and scaling plan (ADR 0020) |
| `docs/feature-ideas` | #60 | 2026-09-19 | docs: feature ideas seen in the track |
| `docs/key-decisions` | #79 | 2026-09-19 | docs: five key decisions (A-E); detailed ADRs to docs/adr/detail |
| `docs/traceability-report` | #54 | 2026-09-19 | docs: per-module traceability report (Spanish) |
| `docs/resilience-evidence` | #75 | 2026-09-19 | docs: resilience evidence, verified live; retry refused OCR provider calls |
| `docs/scale-cost` | #47 | 2026-09-19 | docs: scale, token cost model and evolution per input type |
| `feat/batch2-runbook` | #43 | 2026-09-19 | feat: batch 2 runbook, reprocess and per-batch export |
| `feat/resilience-sources` | #45 | 2026-09-19 | feat: use-case source connectors and LLM fallback chain (ADR 0019) |
| `feat/doubt-checks` | #46 | 2026-09-19 | feat(agents): doubt checks escalate; engine reason is the rule's reason code |
| `feat/escalate-policy` | #44 | 2026-09-19 | feat(agents): failed-check decision policy for the normalizer |
| `feat/norm-normalizer` | #39 | 2026-09-19 | feat(agents): normalize the client's norm into norm rules and checks |
| `feat/autonomous-compiler` | #36 | 2026-09-19 | feat(agents)!: blind tester + autonomous coder, auto-activation by impact, Helmcode |
| `feat/stale-decision-alerts` | #68 | 2026-09-19 | feat(alerts): stale decision alerts after source syncs and rule changes |
| `feat/console-endpoints` | #35 | 2026-09-19 | feat(api): endpoints for the console, one call per screen |
| `feat/optional-decision-review` | #51 | 2026-09-19 | feat(decisions): add optional reviews with human approval |
| `feat/scan-mismatch-escalates` | #67 | 2026-09-19 | feat(decisions): escalate scans on unconfirmed data or a rejection (ADR 0025) |
| `feat/export-reason` | #80 | 2026-09-19 | feat(decisions): export the engine's reason beside the result |
| `feat/required-symbols` | #41 | 2026-09-19 | feat(decisions): required symbols escalate with MISSING_DATA |
| `feature/web-setup` | #50 | 2026-09-19 | feat(frontend): console landing and live API adapter |
| `feature/frontend-update` | #74 | 2026-09-19 | feat(frontend): process console tabs and definition chat |
| `feature/frontend-cleanup` | #83 | 2026-09-19 | feat(frontend): slide the segmented switcher instead of jumping |
| `feat/rule-driven-extraction` | #76 | 2026-09-19 | feat(ingestion): add dynamic fields and OCR modes with Helmcode fallback |
| `fix/ocr-integration-review` | #59 | 2026-09-19 | feat(ingestion): trace OCR providers and preserve decision evidence |
| `feat/ocr-force-recompute` | #82 | 2026-09-19 | feat(ingestion): TRACEPAY_OCR_FORCE_RECOMPUTE forces every read and provider call |
| `feat/learning-norms` | #56 | 2026-09-19 | feat(learning): propose norms from past cases with manager approval |
| `feat/process-execution-settings` | #81 | 2026-09-19 | feat(processes): configure models and execution effort per process |
| `feat/process-discovery` | #58 | 2026-09-19 | feat(processes): discover and review rule imports through documents and chat |
| `feat/process-chat` | #69 | 2026-09-19 | feat(processes): discuss and revise process configuration through chat |
| `feat/process-versions` | #66 | 2026-09-19 | feat(processes): publish approved versions and replay decisions |
| `feat/autonomous-rules` | #38 | 2026-09-19 | feat(rules): compile on save, block rules that need data, check coder keys |
| `feat/erp-live-sources` | #78 | 2026-09-19 | feat(sources): sync live sources before every run, fail closed when one is down (ADR 0028) |
| `feat/audit-page` | #70 | 2026-09-19 | feat(tools): audit page to review a decided batch by hand |
| `feat/trace-coverage` | #49 | 2026-09-19 | feat(traces): full trace coverage, author on every config and rule change |
| `feat/monitoring-planes` | #57 | 2026-09-19 | feat(traces): monitoring planes (ingestion, agents, execution), plane health and live stream |
| `feat/observability` | #42 | 2026-09-19 | feat(traces): own audit spans plus OpenTelemetry (ADR 0018) |
| `feat/use-cases` | #37 | 2026-09-19 | feat(use-cases)!: use cases with versioned agent configuration |
| `fix/agent-limits` | #48 | 2026-09-19 | fix(agents): cap output tokens, fall back on truncated answers, give the assistant a model |
| `fix/ocr-incremental-cache` | #62 | 2026-09-19 | fix(ingestion): reuse OCR evidence and refresh stale pending documents |
| `docs/ocr-reproducible-setup` | #53 | 2026-09-19 | fix(ingestion): run demo through production OCR and document setup |
| `fix/failed-compile-fails-closed` | #64 | 2026-09-19 | fix(rules): a rule whose compile fails is blocked and escalates |
| `fix/iban-near-miss` | #77 | 2026-09-19 | fix(rules): an IBAN a few characters from the master escalates instead of refusing |
| `fix/verified-ocr-outcomes` | #71 | 2026-09-19 | Pin the verified OCR profile and refresh the shared 500-invoice outcomes |
| `dev` | #34 | 2026-09-19 | Release: cleanup for the hackathon deliverable |
