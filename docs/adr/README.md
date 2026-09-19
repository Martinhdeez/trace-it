# Architecture Decision Records

Each file records one architecture decision: its context, the alternatives we weighed, what
we decided, what we accept losing, and the evidence. ADR 0001 is the founding decision and
wins over any other document. Superseded plans live in `.artifacts/archive/`.

## Index

| # | Decision | Status | Summary |
|---|---|---|---|
| [0001](0001-configurable-decision-process.md) | Build a configurable decision process with reviewed learning | accepted | Reusable decision system; invoices are the first configured process; managers approve every rule change |
| [0002](0002-deterministic-engine-llm-never-decides.md) | Decide with a deterministic engine; the LLM never decides at runtime | accepted | All active rules run as code, combined by decision-type priority; LLMs only compile, extract, explain and propose |
| [0003](0003-rules-compiled-to-python-by-agents.md) | Compile each rule's text to free Python code with agents | accepted | No closed DSL; one contract `evaluate(instance, sources, others) -> {fires, reason}`; the decision comes from the approved rule |
| [0004](0004-blind-tester-and-autonomous-coder.md) | Verify generated rule code against a blind tester, and activate it by impact | accepted | Tester writes tests from the text only; coder iterates against them and may dispute a test; NeedsData instead of invented fields; auto-activation when impact on history is small |
| [0005](0005-in-house-sandbox-for-rule-code.md) | Run rule code in an in-house sandbox | accepted | AST allowlist, restricted builtins/imports, separate process with timeouts and rlimits, one subprocess per rule over the whole dataset |
| [0006](0006-pydanticai-agent-framework.md) | Build every agent on PydanticAI | accepted | Typed output, output validators with bounded retries, one run entry point that traces cost; models per role from settings; scripted models in tests |
| [0007](0007-declarative-process-packs.md) | Keep all domain knowledge in declarative process packs | accepted | `<name>.json` holds decision types, symbols, rules (with optional hand-written code), users; `<name>/sources.json` the connectors; idempotent loader |
| [0008](0008-immutable-history-and-retroactive-audit.md) | Never rewrite history | accepted | Content-hashed files, append-only decisions, audits over stored symbols that only produce findings; linear rule versions |
| [0009](0009-review-state-and-export-semantics.md) | Treat REVIEW as an internal state and export the decision the process policy names | superseded by 0016 | Kept for why the export is the engine's decision and one line per file name |
| [0010](0010-double-extraction-with-deterministic-validators.md) | Extract symbols with two readings and deterministic validators | superseded by 0022 | Historical double-LLM proposal; the production OCR committee and its evidence contract are recorded in 0022 |
| [0011](0011-configuration-layers.md) | Separate bootstrap files, versioned runtime configuration and secrets | accepted | Use case holds the domain description and append-only agent config versions (model, guidance, limits, examples); platform prompts as files; `config_id` + prompt hash in every trace. No presets; fallback chains in 0019 |
| [0012](0012-stack-and-feature-based-structure.md) | Use FastAPI, PostgreSQL and a feature-based layout | accepted | Async FastAPI + SQLAlchemy + Alembic on Postgres, Docker Compose, uv; one folder per feature; English conventions |
| [0013](0013-fault-tolerant-erp-client.md) | Read the ERP only through a fault-tolerant client | accepted | Token renewal, backoff with jitter, Retry-After, client rate limiter, validation, paginated snapshot, diff between snapshots; connectors belong to the use case |
| [0019](0019-llm-fallback-chain.md) | Move to the next model of a per-role chain when a provider fails | accepted | `fallback_models` and `timeout_seconds` per use case and role; only provider errors switch, validation retries never; `llm_run` records the chain, each failed attempt and the model that answered |
| [0014](0014-rules-only-decision-step.md) | Combine rule findings by decision-type priority only | superseded by 0021 | Refines ADR 0001: process context feeds compilers and the assistant, never the automatic decision; a failed rule or a tie escalates |
| [0015](0015-immutable-process-versions.md) | Snapshot the whole process as an immutable version on every activation | accepted | Complete approved configuration snapshots; decisions reference versions and captured execution inputs; see 0022 |
| [0016](0016-every-instance-gets-a-decision.md) | Decide every instance: a rule that cannot be evaluated escalates the case | accepted | No REVIEW state; failure or tie decides the process's `requires_human` type with the reason; export is the engine's decision; code A alone at runtime |
| [0017](0017-autonomous-norm-normalizer.md) | Turn the client's norm into rules with an autonomous normalizer | accepted | Each norm sentence is a norm rule the client owns; the normalizer splits it into atomic checks (ordinary rules) with the norm's own tie-breaker; no human review; batch-1 golden eval as the external check |
| [0018](0018-observability-own-audit-spans-plus-opentelemetry.md) | Trace every step as spans in our own database, and mirror them to OpenTelemetry | accepted | `events` holds hierarchical spans (the audit, with prompts, tokens and durations); the same spans go to Logfire or a local Phoenix by env; trace, journey, rule and metrics endpoints |
| [0020](0020-deployment-and-scaling-plan.md) | Deploy as one small server with a remote LLM, and scale by measured triggers | proposed | Baseline one server, LLM remote; ten scaling steps each gated by a metric of our spans; the quadratic `others` fix first; a failed norm-check compile escalates instead of leaving the old rules to decide |
| [0021](0021-optional-decision-review.md) | Review engine decisions with optional advice and human approval | accepted | Off by default; disagreements enter the human queue; failed reviews retain the engine outcome; reviewed exports respect approval |
| [0022](0022-ocr-evidence-and-provider-tracing.md) | Preserve OCR evidence and trace each provider operation | accepted | Production demo uses OCR; immutable attached readings; model/request provenance, journal replay, sanitized provider spans and network-only usage totals |
| [0023](0023-fal-visual-fallback-evaluation.md) | Evaluate fal.ai visual readers before selecting a production fallback | proposed | Compare Moondream and a fixed OpenRouter model; bounded opt-in queue/journal adapter only after measured evaluation |
| [0024](0024-discover-processes-through-documents-and-conversation.md) | Build process drafts through documents and conversation before approval | accepted | Create or revise through workbook discovery and chat; review proposals, compile and backtest, then publish under the same process identity |
| [0025](0025-scan-decision-policy.md) | Decide scans only on confirmed data, and escalate a scan the rules would reject | accepted | A scan (no native text) with a required value its readers did not confirm escalates `UNVERIFIED_DATA`; one the rules would reject escalates `SCAN_REVIEW: <rule>`; text PDFs unaffected |
| [0026](0026-stale-decision-alerts.md) | Flag stale decisions to the manager; never rewrite them silently | accepted | After a source sync that changes rows or a version publication, a dry run; each decision that would change is an alert (trigger, reason codes before/after) the manager acknowledges and acts on; about 1 s per 500 invoices |
| [0027](0027-ocr-execution-modes-and-provider-fallback.md) | Configure local/API/hybrid OCR and bounded provider fallback | accepted | Preserve the invoice default; distinct visual corroboration, Helmcode fallback, network-only usage, latency and explicit billing basis |
| [0028](0028-live-sources-sync-before-run.md) | Live sources: sync before every run, fail closed when a source is down, canonical schema | accepted | Runs and reprocess sync live sources first; a failed sync is down, its snapshot unused; rules that read it escalate `SOURCE_UNAVAILABLE` unless the other rules already reject; synced rows checked against the pack's canonical schema |

| [0022](0022-publish-approved-process-versions.md) | Require manager publication of complete process versions | accepted | One draft, validated approval, atomic publication and deterministic replay; replaces automatic rule activation |

## Glossary
- **Rule finding:** the result of one rule on one instance (`fires`, `reason`).
- **Audit finding:** a past decision that a newer process version would decide
  differently. Stored in the table `findings`.
- **Manager:** the human role that approves rule and process changes and owns the final
  decision of escalated cases. Not "approver" or "responsable".
- **Engine decision / final decision / exported decision:** the process output; the
  manager's decision for an escalated case; the one written to the export, which is the
  engine's (ADR 0016).
- **Process version:** an immutable, published configuration approved for future executions.
- **Process draft:** proposed configuration awaiting validation and manager publication.
- **Execution:** one evaluation of cases using a fixed process version and captured evidence.

## Adding an ADR
1. Copy [`template.md`](template.md) to `NNNN-kebab-title.md` with the next free number.
2. Title it with the decision itself, in the imperative ("Use X", "Never do Y").
3. Fill Context, Alternatives considered (pros and cons for each), Decision, Consequences
   (what we accept losing), Evidence (measured numbers, tests, code references) and
   Related. Aim for 40-90 lines.
4. Start as `status: proposed`. Switch to `accepted` in the PR that implements it.
5. Every PR that takes an architecture decision adds or updates its ADR. Do not rewrite an
   accepted ADR's decision: write a new one and mark the old one `superseded`
   (with `superseded_by: NNNN`).
6. Add a row to the index above.

English only. Use the domain names above.

## Selected for `albertitos_plan.pdf`
Five decisions that best explain the system to the jury:

1. **Deterministic engine with compiled rules** (0002 + 0003 + 0014): no LLM in the
   decision path, findings combined by decision-type priority only, zero tokens per
   decision, every decision replayable.
2. **Blind tester and autonomous coder** (0004): how we trust LLM-written code without reading it.
3. **Process packs** (0007): the invoice challenge is configuration, not code; a second
   pack runs on the same code.
4. **Immutable history and export semantics** (0008 + 0016): rule and process changes are
   checked against every past decision and never rewrite it; every instance ends with a
   decision, and a rule we cannot trust sends the case to a person instead of paying.
5. **Resilience** (0013 + 0019 + 0005 + 0006): fault-tolerant ERP client into versioned
   snapshots, a fallback model chain per agent role (`make demo-llm-down`),
   a sandbox that runs 500 invoices in a second, agents that fail closed; an outage never
   becomes a wrong decision.
