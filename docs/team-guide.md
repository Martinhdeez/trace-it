# trace-it: team guide

How we work in the trace-it repo: branches, commits, backend structure and how to run it.
What we are building and why: `docs/application-blueprint.md`. Who does what: `docs/mvp-plan.md`.

## Quick start

Requirements: Docker and [uv](https://docs.astral.sh/uv/).

```bash
make setup      # .env, Postgres + backend, migrations and the "Invoice payment" process with its users
```
API at http://localhost:8000/docs (if port 8000 is taken: `BACKEND_PORT=8001 make setup`). Sign in as `martin@trace-it.local` (`manager`).

| Command | What it does |
|---|---|
| `make compile` | Compiles the draft rules (needs LLM keys in `.env`) |
| `make erp` | Starts the challenge ERP |
| `make test` | Backend tests against the local Postgres |
| `make down` | Stops the containers (the data stays) |
| `make reset-db` | **Deletes the database** |

Processes are JSON files in `processes/` (format in `processes/README.md`). `make setup` can be repeated: it duplicates nothing and does not touch active rules.

## 1. Git

### Branches
| Branch | What for | Who writes to it |
|---|---|---|
| `main` | Stable version, the one we show | Only merged from `dev` when everything works |
| `dev` | Integration: every feature comes together here | Only through pull requests |
| `feat/<feature>` | A new feature | One person (or a pair) |
| `fix/<problem>` | A fix | Whoever fixes it |
| `docs/<topic>` | Documentation only | Anyone |

Short, lowercase, hyphenated names: `feat/erp-client`, `feat/rule-compiler`, `fix/vat-rounding`.

### Flow
1. Always start from an up-to-date `dev`:
   ```bash
   git switch dev && git pull
   git switch -c feat/erp-client
   ```
2. Small, frequent commits (see the format below).
3. Before opening the PR, bring in the latest `dev` and check that everything passes:
   ```bash
   git fetch && git rebase origin/dev
   cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest
   ```
4. Push the branch and open a pull request against `dev`:
   ```bash
   git push -u origin feat/erp-client
   gh pr create --base dev --fill
   ```
5. Someone else reviews and approves. It is merged with **squash merge**, so each feature lands in `dev` as a single commit.
6. Delete the branch after merging.

### Rules
- Never push directly to `dev` or `main`.
- Never `git push --force` on shared branches. On your own branch, only `--force-with-lease`.
- No secrets in the repo: keys go in `.env`, which is not committed. See `.env.example`.
- One PR = one feature. If it grows too much, split it.
- If you touch a shared contract (a model, schema or signature of another module), tell the group first.

### Commit format
Conventional Commits, in English, in the imperative:
```
feat(rules): add cross-test runner for compiled rules
fix(sources): retry on ORA-00600 before renewing token
docs: add team guide
test(decisions): cover priority when several rules fire
chore: bump pydantic-ai
```
Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. The scope in parentheses is the feature folder.

## 2. Backend structure

Organized **by feature**, not by file type. Everything for a feature lives in its folder.

```
backend/
  pyproject.toml          # dependencies (uv)
  alembic/                # database migrations
  app/
    main.py               # creates the FastAPI app and mounts the routers
    models.py             # imports every model (Alembic needs it)
    core/                 # infrastructure: configuration, database
    common/               # shared utilities: errors
    features/
      users/              # users and current user (X-User-Id header)
      processes/          # processes, symbols, decision types
      ingestion/          # files and instances, text extraction
      sources/            # sources of truth: spreadsheets and external systems (ERP)
      extraction/         # symbols with double LLM extraction
      rules/              # rules: creation, statuses, activation
      agents/             # agents (compiler A/B, assistant), sandbox, versioned config, presets and prompts
      decisions/          # engine, history, audit, queues, export
      traces/             # trace events
      llm/                # PydanticAI runtime: model from config, run and trace
```

### Inside each feature
| File | What it holds |
|---|---|
| `model.py` | Tables (SQLAlchemy) |
| `schemas.py` | API input and output (Pydantic) |
| `service.py` | Business logic. Receives the database session |
| `router.py` | Endpoints. Thin: validate, call the service and return |
| `tests/` | That feature's tests (`test_*.py`) |
| others | Feature-specific pieces with clear names: `engine.py`, `sandbox.py`, `erp.py`… |

Rules:
- A router does **not** run SQL queries: it calls the service.
- A feature may import another feature's `model.py` or `service.py`, but never its `router.py`.
- Errors are raised with the classes in `app/common/exceptions.py` (`NotFoundError`, `ConflictError`…). The API turns them into JSON responses.
- Whatever is not done yet raises `NotImplementedYetError` (the API answers 501). That way the contract exists and the frontend can work against it.
- All code is in English (identifiers, database, API, messages, prompts): see `docs/CONVENTIONS.md` and its glossary.

### Agents (LLM)
Every agent uses PydanticAI v2. Architecture, versioned configuration and tasks: `docs/agents-plan.md`.
- Every LLM call goes through `features/llm/run.py`, with an `agent_config` role: that way it lands in the trace with its configuration version, cost and latency.
- Prompts are files in `features/agents/prompts/`. Case data goes in the message, never in the prompt.
- In extraction, a failing validator sends the instance to `REVIEW`; it is never fed back to the model with `ModelRetry`.
- Tests without network: `FunctionModel`/`TestModel` with `agent.override(...)`.
- **Before writing PydanticAI code, check `.context/pydantic-ai/`** (start with `START-HERE.md` and `SECTIONS.md`, and open only the section you need). This applies to people and to coding assistants: the API changed a lot in v2 and what a model remembers is usually v1. `llms-full.txt` (5.5 MB, the whole documentation) is not in the repo: download it from https://ai.pydantic.dev/llms-full.txt if you need it for searching.

## 3. Running locally

Requirements: Docker and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env              # add your LLM keys
docker compose up --build         # Postgres + backend at http://localhost:8000
```
- API docs: http://localhost:8000/docs
- Migrations are applied automatically when the backend starts.
- If port 8000 is taken: `BACKEND_PORT=8001 docker compose up --build`.

Working on the backend without Docker (faster for tests):
```bash
docker compose up db -d
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check . && uv run ruff format .
```

Challenge ERP (in another terminal):
```bash
cd .context/500-sombras-de-alberto && make erp
```

### Changing the database
1. Edit or create your feature's `model.py`. If the table is new, import it in `app/models.py`.
2. Generate the migration and **review it** before pushing:
   ```bash
   uv run alembic revision --autogenerate -m "add column x to rules"
   ```
3. If two people generate migrations at the same time, there will be two "heads". Resolve it with `uv run alembic merge heads` and tell the group.

## 4. Who touches what
| Person | Folders |
|---|---|
| Martín | `features/agents/` (compiler, sandbox, assistant, agent config), `features/llm/` |
| Mateo | `features/rules/`, `features/decisions/` (engine, audit, API), `features/processes/`, `features/users/` |
| Álvaro | `features/ingestion/`, `features/sources/` (workbook, ERP), `features/extraction/` |
| Carlos | `frontend/` |
| Varsovia | `docs/`, ADRs, demo |

If you need to change something in someone else's folder, talk to them first.
