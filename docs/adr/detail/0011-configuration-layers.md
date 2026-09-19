---
status: accepted
---

# Separate bootstrap files, versioned runtime configuration and secrets

## Context
Agent behaviour (models, prompts, limits) must be tuned while the app runs, without
restarts and without losing a good experiment. Every LLM result must say which
configuration and prompt produced it, so configurations can be compared with data. A fresh
machine must reproduce a known setup with one command. API keys and ERP credentials must
never reach git or the database.

The app must also serve any use case, not only invoices. Until now the model per role was a
setting (`TRACE_<ROLE>_MODEL`), the prompts were Python constants with invoice wording, and
the domain conventions lived in `processes.description`, one copy per process.

## Alternatives considered
- **Environment variables / settings file only.**
  - Pros: simple; twelve-factor.
  - Cons: a change needs a restart; no history; no link from a result to its config.
- **Mutable config row per role (the first version, `llm_config`).**
  - Pros: editable through the API.
  - Cons: overwriting loses experiments; old traces point to a config that no longer
    exists. Removed.
- **Prompts stored only in the database.**
  - Pros: editable at runtime.
  - Cons: the contract the code relies on (output shape, rule contract) becomes editable
    and unreviewed; lost on a reset.
- **Configuration per process.**
  - Pros: no new concept.
  - Cons: every process of the same domain repeats the conventions and the tuning.
- **Platform prompts as files + append-only agent config versions per use case (chosen).**

## Decision
A **use case** (`use_cases`) is what the app is used for (e.g. "Invoice payment"). It holds
the domain `description` (conventions) and the agent configuration, shared by all its
processes. A **process** is one set of rules inside a use case (`processes.use_case_id`).
A definition without `use_case` gets a use case of its own, with the process's name and
`description`.

| Layer | Where | Holds | Changed by |
|---|---|---|---|
| Bootstrap | git: `agents/prompts/*.md`, `processes/<pack>/use-case.json` | platform prompts, seed config | pull requests |
| Runtime | PostgreSQL `agent_configs` | versions per (use case, role), traces | managers, while it runs |
| Secrets | `.env` (never committed) | API keys, ERP credentials | each deployment |

- **Platform prompt**: the role's contract, the same for every use case, in a file.
- **Agent config** (`AgentSettings`), per use case and role (`compiler`, `tester`,
  `assistant`): model, `instructions` (domain guidance appended to the platform prompt under
  "## Guidance for this use case"), `model_settings`, `limits` (compiler: `max_attempts`,
  `auto_activate_max_change`; tester: `min_tests`, `max_reviews`) and `examples`
  (approved rule/code pairs; the rule being compiled never sees its own). Empty fields
  fall back to `TRACE_<ROLE>_MODEL` and the constants in `compiler.py`.
- Versions are append-only; at most one active per (use case, role) (partial unique
  index). `PUT /use-cases/{id}/agents/{role}` adds an active version,
  `POST /agent-configs/{id}/activate` rolls back. Manager only.
- Loading a pack never overrides runtime: a role with no versions gets v1 active; a file
  config that differs from every stored version becomes a new inactive version.
- Every agent event records `config_id` and `prompt_hash` (sha256[:12] of the effective
  instructions). Case data goes in the user message, so the hash means something.
- Secrets are referenced by variable name (e.g. in `sources.json`), never stored inline.

Model fallback chains and a per-request timeout were added later (ADR 0019).
Not implemented: presets (`quality`, `cheap`, `fast`), per-role
retry and request limits, exporting a version back to a file, and an event for each
activation (the version row keeps author, note and time).

## Consequences
- Results are comparable per configuration with one query over `events`.
- `processes.description` is gone; `ProcessOut.description` is the use case's. Migration
  0002 moves each description into a use case of its own, so no `make reset-db`.
- A process can only join an existing use case: loading the pack loads it first.
- Invoice wording left the prompts; it lives in the invoice use case.

## Evidence
- Code: `features/use_cases/`, `agents/llm.py` (`run`, `Setup`), `agents/prompts/`,
  `processes/invoice-payment/use-case.json`.
- Migration: `alembic/versions/0002_use_cases.py` (upgrade with backfill, downgrade,
  `alembic check` clean).
- Tests: `use_cases/tests/test_service.py` (idempotent load, changed config enters
  inactive, example code read), `use_cases/tests/test_api.py` (new active version,
  operator 403, rollback), `agents/tests/test_llm.py` (guidance, `config_id`,
  `prompt_hash`, model override), `agents/tests/test_compiler.py` (examples of other rules
  only, limits honoured), `processes/tests/test_definition.py` (422, 409).

## Related
ADR 0004, 0006, 0007, 0012.
