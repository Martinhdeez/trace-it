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
| [0010](0010-double-extraction-with-deterministic-validators.md) | Extract symbols with two readings and deterministic validators | proposed | Readings must agree; IBAN/NIF/arithmetic validators never retry the model; cache by file hash. Ingestion today reads documents; the double LLM reading is not built |
| [0011](0011-configuration-layers.md) | Separate bootstrap files, versioned runtime configuration and secrets | accepted | Use case holds the domain description and append-only agent config versions (model, guidance, limits, examples); platform prompts as files; `config_id` + prompt hash in every trace. No presets or fallback chains |
| [0012](0012-stack-and-feature-based-structure.md) | Use FastAPI, PostgreSQL and a feature-based layout | accepted | Async FastAPI + SQLAlchemy + Alembic on Postgres, Docker Compose, uv; one folder per feature; English conventions |
| [0013](0013-fault-tolerant-erp-client.md) | Read the ERP only through a fault-tolerant client | accepted | Token renewal, backoff with jitter, Retry-After, client rate limiter, validation, paginated snapshot, diff between snapshots |
| [0014](0014-rules-only-decision-step.md) | Combine rule findings by decision-type priority only | accepted | Refines ADR 0001: process context feeds compilers and the assistant, never the automatic decision; a failed rule or a tie escalates |
| [0015](0015-immutable-process-versions.md) | Snapshot the whole process as an immutable version on every activation | proposed | Decision types, symbols, description and active rules; decisions reference their version; loader writes drafts |
| [0016](0016-every-instance-gets-a-decision.md) | Decide every instance: a rule that cannot be evaluated escalates the case | accepted | No REVIEW state; failure or tie decides the process's `requires_human` type with the reason; export is the engine's decision; code A alone at runtime |
| [0017](0017-autonomous-norm-normalizer.md) | Turn the client's norm into rules with an autonomous normalizer | accepted | Each norm sentence is a norm rule the client owns; the normalizer splits it into atomic checks (ordinary rules) with the norm's own tie-breaker; no human review; batch-1 golden eval as the external check |
| [0018](0018-observability-own-audit-spans-plus-opentelemetry.md) | Trace every step as spans in our own database, and mirror them to OpenTelemetry | accepted | `events` holds hierarchical spans (the audit, with prompts, tokens and durations); the same spans go to Logfire or a local Phoenix by env; trace, journey, rule and metrics endpoints |

## Glossary
- **Rule finding:** the result of one rule on one instance (`fires`, `reason`).
- **Audit finding:** a past decision that a newer process version would decide
  differently. Stored in the table `findings`.
- **Manager:** the human role that approves rule and process changes and owns the final
  decision of escalated cases. Not "approver" or "responsable".
- **Engine decision / final decision / exported decision:** the process output; the
  manager's decision for an escalated case; the one written to the export, which is the
  engine's (ADR 0016).
- **Process version:** an immutable snapshot of a process (ADR 0015).

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
5. **Resilience** (0013 + 0005 + 0006): fault-tolerant ERP client into versioned snapshots,
   a sandbox that runs 500 invoices in a second, agents that fail closed; an outage never
   becomes a wrong decision.
