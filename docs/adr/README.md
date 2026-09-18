# Architecture Decision Records

Each file records one architecture decision: its context, the alternatives we weighed, what
we decided, what we accept losing, and the evidence. ADR 0001 is the founding decision and
wins over any draft document (`docs/plano-aplicacion.md`, `docs/plan-agentes.md`,
`.artifacts/`).

## Index

| # | Decision | Status | Summary |
|---|---|---|---|
| [0001](0001-configurable-decision-process.md) | Build a configurable decision process with reviewed learning | accepted | Reusable decision system; invoices are the first configured process; managers approve every rule change |
| [0002](0002-deterministic-engine-llm-never-decides.md) | Decide with a deterministic engine; the LLM never decides at runtime | accepted | All active rules run as code, combined by decision-type priority; LLMs only compile, extract, explain and propose |
| [0003](0003-rules-compiled-to-python-by-agents.md) | Compile each rule's text to free Python code with agents | accepted | No closed DSL; one contract `evaluate(instance, sources, others) -> {fires, reason}`; the decision comes from the approved rule |
| [0004](0004-dual-blind-compilation-with-cross-tests.md) | Verify generated code with two blind compilers and cross-tests | accepted | A and B write code + tests blind; all tests on both codes; agreement on history; disagreement at runtime → REVIEW |
| [0005](0005-in-house-sandbox-for-rule-code.md) | Run rule code in an in-house sandbox | accepted | AST allowlist, restricted builtins/imports, separate process with timeouts and rlimits, batch execution; container next |
| [0006](0006-pydanticai-agent-framework.md) | Build every agent on PydanticAI | accepted | Typed output, bounded retries, fallback chains and offline tests without handing flow control to a framework |
| [0007](0007-declarative-process-packs.md) | Keep all domain knowledge in declarative process packs | accepted | `process.json` holds decision types, symbols, rules, description and policies; idempotent loader never overrides runtime |
| [0008](0008-immutable-history-and-retroactive-audit.md) | Never rewrite history | accepted | Content-hashed files, append-only decisions, audits over stored symbols that only produce findings; linear rule versions |
| [0009](0009-review-state-and-export-semantics.md) | Treat REVIEW as an internal state and export the engine's decision | accepted | REVIEW is our doubt, not an outcome; a person's resolution never changes the export; one line per file name |
| [0010](0010-double-extraction-with-deterministic-validators.md) | Extract symbols with two readings and deterministic validators | accepted | Readings must agree; IBAN/NIF/arithmetic validators send to REVIEW and never retry the model; cache by file hash |
| [0011](0011-configuration-layers.md) | Separate bootstrap files, versioned runtime configuration and secrets | accepted | Repo presets → append-only agent config versions in the DB; prompt hash in every trace; secrets only in `.env` |
| [0012](0012-stack-and-feature-based-structure.md) | Use FastAPI, PostgreSQL and a feature-based layout | accepted | Async FastAPI + SQLAlchemy + Alembic on Postgres, Docker Compose, uv; one folder per feature; English conventions |
| [0013](0013-fault-tolerant-erp-client.md) | Read the ERP only through a fault-tolerant client | proposed | Token renewal, backoff with jitter, Retry-After, client rate limiter, validation, paginated snapshot, circuit breaker |

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

English only. Use the domain names above; mention Spanish code identifiers in parentheses
only to locate code until the rename lands.

## Selected for `albertitos_plan.pdf`
Five decisions that best explain the system to the jury:

1. **Deterministic engine with compiled rules** (0002 + 0003): no LLM in the decision path,
   zero tokens per decision, every decision replayable.
2. **Dual blind compilation** (0004): how we trust LLM-written code without reading it.
3. **Process packs** (0007): the invoice challenge is configuration, not code; a second
   pack runs on the same code.
4. **Immutable history and export semantics** (0008 + 0009): rule changes never rewrite
   the past, and our own doubt (REVIEW) is never exported as a business outcome.
5. **Resilience** (0013 + 0006): fault-tolerant ERP client and model fallback chains; an
   outage fails closed, never into a wrong decision.
