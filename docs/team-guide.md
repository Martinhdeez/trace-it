# trace-it: team guide

How we work in this repo: branches, backend layout, running it. What the system is and why: the root `README.md` and `docs/adr/`.

## Git

`main` is the stable branch, the one we show; it only receives merges from `dev`. `dev` is where features come together, only through pull requests. Work happens on `feat/<topic>`, `fix/<problem>` or `docs/<topic>` branches (short, lowercase, hyphenated).

1. Branch from an up-to-date `dev`: `git switch dev && git pull && git switch -c feat/erp-client`.
2. Small commits in Conventional Commits form, English, imperative, scope = feature folder: `feat(rules): add impact check`, `fix(sources): retry on ORA-00600`, `docs: update team guide`. Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.
3. Before the PR: `git fetch && git rebase origin/dev`, then `make check`.
4. `git push -u origin feat/erp-client && gh pr create --base dev --fill`. Someone else reviews. **Squash merge**: each feature lands in `dev` as one commit. Delete the branch.

Never push directly to `dev` or `main`; never `--force` on shared branches (`--force-with-lease` on your own). No secrets in the repo: keys live in `.env`, which is ignored. One PR = one feature. If you change a shared contract (a model, a schema, a signature another feature calls), say so in the group first.

## Backend layout

Organised by feature, not by file type (ADR 0012).

```
backend/
  pyproject.toml              # dependencies (uv)
  alembic/versions/           # 0001_initial_schema.py, 0002_use_cases.py
  app/
    main.py                   # FastAPI app, routers, TraceError -> {"code", "message"}
    models.py                 # imports every model (Alembic needs it)
    cli.py                    # `load <pack.json> [--compile] [--activate]`, `sources sync <pack.json>`
    core/                     # config.py (Settings, TRACE_*), database.py, events.py (trace table + record())
    common/exceptions.py      # TraceError and its subclasses
    features/
      users/                  # users, roles manager/operator, X-User-Id
      use_cases/              # use cases and the versioned configuration of their agents
      processes/              # process, decision types, symbols; definition.py loads a pack
      rules/                  # rule life cycle draft -> active -> retired; compile, impact
      decisions/              # engine.py (pure), service.py (run, queue, resolve, export), audit.py
      instances/              # files, instances, symbols.py (stored shape <-> rule shape)
      sources/                # sources of truth, snapshots; http_connector.py (the ERP)
      agents/                 # llm.py (PydanticAI seam), compiler.py, assistant.py, sandbox.py, prompts/*.md
  tests/
    support/                  # challenge.py, pack.py, fakes.py, models.py, prepare_db.py
    golden/                   # expected outcomes of batch 1 (README there)
    e2e/                      # golden engine run, API flow
  evals/                      # opt-in compiler evaluation against the hand-written rules
```

Inside a feature: `model.py` (SQLAlchemy tables), `schemas.py` (Pydantic in/out), `service.py` (logic, takes the session), `router.py` (thin: validate, call the service, return), `tests/`. A router runs no SQL. A feature imports another's `model.py` or `service.py`, never its `router.py`. Errors are `TraceError` subclasses (`app/common/exceptions.py`); the API maps them to status codes. Naming and vocabulary: `docs/CONVENTIONS.md`.

Agents (tester, compiler, assistant) run on PydanticAI: ADR 0006 and `features/agents/llm.py`.

## Use cases and agent configuration

A **use case** is what the app is used for (e.g. "Invoice payment"): its `description` (domain conventions) and how its agents work. A **process** is one set of rules inside a use case (`processes.use_case_id`); `ProcessOut.description` is its use case's. What an agent does is not in the code (ADR 0011): the platform prompt is a file in `features/agents/prompts/`, the same for every use case, and each use case adds a versioned configuration per role (`compiler`, `tester`, `assistant`): model, domain guidance, model settings, limits, examples. A role without one runs with `TRACE_<ROLE>_MODEL` and the defaults in `compiler.py`. Every agent event records `config_id` and `prompt_hash` (sha256[:12] of the effective instructions). The pack file `processes/<pack>/use-case.json` seeds it (`processes/README.md`).

| Endpoint | Who | What |
|---|---|---|
| `GET /use-cases`, `GET /use-cases/{id}` | anyone | Use cases; one with the active configuration of each role |
| `GET /use-cases/{id}/agents/{role}/versions` | anyone | Every version of a role's configuration, oldest first |
| `PUT /use-cases/{id}/agents/{role}` | manager | Body `{config, note}`: a new version, active from now on |
| `POST /agent-configs/{id}/activate` | manager | Activate an existing version: rollback, or adopt one loaded from the pack |

Versions are append-only: only `active` moves. Tests script the model with `FunctionModel` (`tests/support/models.py`): no network, no keys. Before writing PydanticAI code, read `.context/pydantic-ai/START-HERE.md`: the v2 API differs from what a model remembers.

## Running locally

Requirements: Docker, [uv](https://docs.astral.sh/uv/), `pdftotext` (poppler) for the demo and the golden tests.

| Command | What it does |
|---|---|
| `make setup` | `.env` from the example, Postgres + backend (`docker compose`), migrations, loads `processes/invoice-payment.json`. Repeatable. API at http://localhost:8000/docs (`BACKEND_PORT=8001 make setup` if 8000 is taken) |
| `make erp` | Starts the challenge ERP from the submodule (port 8009). Keep it running in another terminal |
| `make erp-sync` | Downloads the ERP into a new snapshot (`docs/sources-http.md`) |
| `make activate` | Activates every draft rule whose code is validated: the hand-written `rules-v3/` need no model |
| `make compile` | Compiles the draft rules with the two agents (needs LLM keys) |
| `make demo` | The whole invoice process over the 500 challenge PDFs, through the API: `output/outcomes.jsonl` (`tools/README.md`) |
| `make test` | Unit tests (`-m "not e2e and not llm"`) |
| `make test-e2e` | Golden outcomes of batch 1 and the API flow (needs the challenge submodule) |
| `make check` | `ruff check`, `ruff format --check`, then `test` and `test-e2e`. Run before every PR |
| `make eval-compiler` | Opt-in, calls real LLMs: compiles the 16 rules and compares with `rules-v3/`; report in `backend/evals/reports/` |
| `make down` | Stops the containers; data stays |
| `make reset-db` | Deletes the database volume. Then `make setup` |

Without Docker for the backend (faster loop): `docker compose up db -d`, then in `backend/`: `uv sync`, `uv run alembic upgrade head`, `uv run uvicorn app.main:app --reload`.

## Environment

`.env.example` lists everything; `make setup` copies it to `.env`.

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` | LLM providers. Only `make compile`, `make eval-compiler` and the assistant need them |
| `TRACE_ERP_USER`, `TRACE_ERP_PASSWORD`, `TRACE_ERP_URL` | The ERP connector, named in `processes/invoice-payment/sources.json`. Docker sets the URL to `host.docker.internal:8009` |
| `TRACE_COMPILER_MODEL`, `TRACE_TESTER_MODEL`, `TRACE_ASSISTANT_MODEL` | One model per agent role, `provider:model` (any PydanticAI provider, or `helmcode:<model>` with `HELMCODE_API_KEY`). Defaults in `app/core/config.py`; tester and compiler should differ (ADR 0004) |
| `TRACE_AUTO_ACTIVATE_MAX_CHANGE` | Share of past decisions a compiled rule may change and still activate by itself (default 0.05) |
| `TRACE_DATABASE_URL` | Set by Docker; the Makefile overrides it for tests |

## Database and migrations

The migration history starts at `alembic/versions/0001_initial_schema.py` (squashed); a database older than it needs `make reset-db && make setup`. `0002_use_cases.py` moves each process's description into a use case of its own, so `alembic upgrade head` is enough from 0001.

To change a table: edit the feature's `model.py` (a new table must be imported in `app/models.py`), then in `backend/`: `uv run alembic revision --autogenerate -m "add x to rules"`. Read the generated file before committing. Two branches generating migrations at once leave two heads: `uv run alembic merge heads` and tell the group.

Tests use their own database, `TEST_DB_URL` in the `Makefile` (default `trace_test` on the same Postgres). `make test` recreates it empty on every run (`tests/support/prepare_db.py`) and applies the migrations, so tests never touch the database `make setup` filled for the demo.
