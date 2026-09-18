---
status: accepted
---

# Use FastAPI, PostgreSQL and a feature-based layout

## Context
Five people build the backend, agents, ingestion and frontend in parallel over one weekend,
and each needs to work without waiting for the others. The system is I/O bound (LLM calls,
the ERP) and keeps JSON-shaped data (symbols, per-rule results, source rows, traces) next
to relational data (processes, rules, decisions). Everything must start with one command.

## Alternatives considered
- **SQLite (earlier idea).**
  - Pros: zero setup, a single file.
  - Cons: no concurrent writers; no `jsonb`, partial unique indexes or `DISTINCT ON`, which
    we use; differs from production.
- **Django.**
  - Pros: admin, ORM and migrations out of the box.
  - Cons: sync-first; its app layout and ORM fight async LLM and ERP calls; heavier than
    the API we need.
- **Layered-by-type layout (`models/`, `services/`, `routers/`).**
  - Pros: familiar.
  - Cons: every change touches several shared folders; owners collide in the same files.
- **FastAPI + PostgreSQL + feature folders (chosen).**

## Decision
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic migrations, Pydantic
  schemas; `uv` for dependencies and lockfile; `ruff` and `pytest`.
- **Database:** PostgreSQL 16 (`jsonb` for symbols, rule results, source rows and traces;
  partial unique indexes for "one active per role").
- **Runtime:** Docker Compose (`db`, `backend`); `make setup` starts it, migrates and loads
  the invoice pack; `make test` runs the suite against Postgres.
- **Layout:** `backend/app/features/<feature>/` with its own `model.py`, `schemas.py`,
  `service.py`, `router.py` and `tests/`, one owner per feature. Features talk through
  services and models, not each other's routers.
- **Conventions:** English for code, docs and domain names (process, rule, instance,
  symbol, decision type, source, finding, `requires_human`, PENDING / DECIDED, `manager`);
  see `docs/CONVENTIONS.md`.

## Consequences
- Contributors need Docker for Postgres; there is no in-memory database for tests.
- Sandbox work must stay off the event loop (`asyncio.to_thread`).
- The migration history was squashed into one `0001` once the schema settled; a local
  database from before needs `make reset-db && make setup`.

## Evidence
- `docker-compose.yml`, `Makefile`, `backend/pyproject.toml`, `backend/alembic/`.
- `uv run pytest -q` on `dev` at `d3745e9` against local Postgres, e2e included:
  **258 passed in 53 s**.
- Feature folders: `agents`, `decisions`, `ingestion`, `processes`, `rules`, `sources`,
  `users`; shared code in `app/core` (settings, database, events) and `app/common`.

## Related
ADR 0006, 0011. `docs/team-guide.md`.
