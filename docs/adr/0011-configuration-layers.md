---
status: accepted  # agent config versions: implementation in progress (agents-plan task 1)
---

# Separate bootstrap files, versioned runtime configuration and secrets

## Context
Agent behaviour (models, fallback chain, retries, limits, prompts) must be tuned while the
app runs, during the challenge, without restarts and without losing a good experiment. Every
LLM result must say exactly which configuration and prompt produced it, so configurations
can be compared with data. A fresh machine must reproduce a known setup with one command.
API keys and ERP credentials must never reach git or the database.

Today `config_llm` holds one model per role and is overwritten in place; the prompts are
Python constants (`SISTEMA`) in each agent module.

## Alternatives considered
- **Environment variables / settings file only.**
  - Pros: simple; twelve-factor.
  - Cons: a change needs a restart; no history; no link from a result to its config.
- **Mutable config row per role (current `config_llm`).**
  - Pros: already there.
  - Cons: overwriting loses experiments; old traces point to a config that no longer exists.
- **Prompts stored only in the database.**
  - Pros: editable at runtime.
  - Cons: not reviewable in PRs; lost on a reset.
- **Repo presets + append-only versions in the DB + prompts as files with hashes (chosen).**

## Decision
Three layers:

| Layer | Where | Holds | Changed by |
|---|---|---|---|
| Bootstrap | git: process packs, `agents/presets/{quality,cheap,fast}.json`, `agents/prompts/*.md` | defaults | pull requests |
| Runtime | PostgreSQL | agent config versions, rules, decisions, traces | the app, while it runs |
| Secrets | `.env` (never committed) | API keys, ERP credentials | each deployment |

- **Agent configuration** (`agent_config` table): per role (`compiler_a`, `compiler_b`,
  `extractor_1`, `extractor_2`, `assistant`, later `corrector`), append-only versions with
  model chain, settings, retries, request limit, prompt file, optional prompt override,
  author and note. At most one active version per role (partial unique index). Editing
  creates a version; rolling back activates an older one; each activation is a trace event.
- Presets are applied as new versions (`make setup` applies `quality` if missing); any
  version can be exported back as preset JSON and committed.
- **Prompts** are versioned files; the effective prompt (file or override) is hashed
  (`sha256[:12]`) and the hash goes into every trace event. Case data always goes in the
  user message, never in the prompt, so the hash means something.
- Secrets are referenced by variable name (e.g. in `sources.json`), never stored inline.

## Consequences
- Every result points to `agent_config.id` + prompt hash: experiments are comparable with
  one SQL query over `events`.
- The only update on an existing version row is moving `is_active`.
- The frontend moves from `/llm/config` to `/agents/.../config`.
- A role without an active version refuses to run ("run make setup").

## Evidence
- Current state: `features/llm/model.py` (`ConfigLLM`), `features/llm/cliente.py`.
- Design and endpoints: `docs/agents-plan.md` §4; layers table: `docs/process-packs.md`.
- Planned tests (task 1): versions and activation against Postgres, partial unique index,
  idempotent preset, export → apply gives the same config, invalid config → 422.

## Related
ADR 0006, 0007, 0012. Plan P22, P23.
