# trace-it: team guide

How we work in this repo: branches, backend layout, running it. What the system is and why: the root `README.md` and `docs/adr/`.

## Git

`main` is the stable branch, the one we show; it only receives merges from `dev`. `dev` is where features come together, only through pull requests. Work happens on `feat/<topic>`, `fix/<problem>` or `docs/<topic>` branches (short, lowercase, hyphenated).

1. Branch from an up-to-date `dev`: `git switch dev && git pull && git switch -c feat/erp-client`.
2. Small commits in Conventional Commits form, English, imperative, scope = feature folder: `feat(rules): add impact check`, `fix(sources): retry on ORA-00600`, `docs: update team guide`. Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.
3. Before the PR: `git fetch && git rebase origin/dev`, then `make check`.
4. `git push -u origin feat/erp-client && gh pr create --base dev --fill`. Someone else reviews. **Squash merge**: each feature lands in `dev` as one commit. Delete the branch. Every merged branch and how to restore it: [`docs/branches.md`](branches.md).

Never push directly to `dev` or `main`; never `--force` on shared branches (`--force-with-lease` on your own). No secrets in the repo: keys live in `.env`, which is ignored. One PR = one feature. If you change a shared contract (a model, a schema, a signature another feature calls), say so in the group first.

## Backend layout

Organised by feature, not by file type (ADR 0012).

```
backend/
  pyproject.toml              # dependencies (uv)
  alembic/versions/           # 0001_initial_schema.py (squashed), then one file per change
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
      rules/                  # rule life cycle (below); compile, impact
      decisions/              # engine.py (pure), service.py (run, queue, resolve, export), audit.py
      instances/              # files, instances, symbols.py (stored shape <-> rule shape)
      sources/                # sources of truth, snapshots; http_connector.py (the ERP)
      agents/                 # llm.py (PydanticAI seam), compiler.py, assistant.py, sandbox.py, prompts/*.md
  tests/
    support/                  # challenge.py, pack.py, fakes.py, models.py, prepare_db.py
    golden/                   # expected outcomes of batch 1 (README there)
    e2e/                      # golden engine run, API flow
  evals/                      # opt-in evaluations: compiler vs hand-written rules, norm vs golden
```

Inside a feature: `model.py` (SQLAlchemy tables), `schemas.py` (Pydantic in/out), `service.py` (logic, takes the session), `router.py` (thin: validate, call the service, return), `tests/`. A router runs no SQL. A feature imports another's `model.py` or `service.py`, never its `router.py`. Errors are `TraceError` subclasses (`app/common/exceptions.py`); the API maps them to status codes. Naming and vocabulary: `docs/CONVENTIONS.md`.

Agents (tester, compiler, assistant, normalizer, decision reviewer, learner) run on PydanticAI: ADR 0006 and `features/agents/llm.py`.

## Rule life cycle

A manager saves a rule in plain language (`POST /processes/{id}/rules`); nobody has to press anything else.

| Status | Meaning | Enforced by the engine |
|---|---|---|
| `compiling` | Saved; tester and coder are writing its tests and code in the background (1-4 min). A restart re-queues it | no |
| `active` | Its code passed the tests and changes few past decisions (ADR 0004), or a manager activated it | yes |
| `blocked` | The agents answered NeedsData: the process lacks a symbol or source it needs, and every instance escalates with `RULE_NEEDS_DATA` (ADR 0016) until the data exists and it is recompiled. (A failed compile on save used to block the rule with `RULE_COMPILE_FAILED`; superseded by ADR 0031: it now stays a `draft` that cannot be published) | yes, as an escalation |
| `draft` | Compiled but waiting for a person: failing tests or too much impact | no |
| `retired` | Taken out of the process by a manager | no |

`POST /rules/{id}/compile` recompiles a `draft` or `blocked` rule and waits for the result; `make compile` does the same for every draft. A `blocked` rule that compiles goes through the impact check, where undoing its own escalations does not count: it becomes `active` by itself unless it would contradict a person.

## Use cases and agent configuration

A **use case** is what the app is used for (e.g. "Invoice payment"): its `description` (domain conventions) and how its agents work. A **process** is one set of rules inside a use case (`processes.use_case_id`); `ProcessOut.description` is its use case's. What an agent does is not in the code (ADR 0011): the platform prompt is a file in `features/agents/prompts/`, the same for every use case, and each use case adds a versioned configuration per role (`compiler`, `tester`, `assistant`, `normalizer`, `decision_reviewer`, `learner`): model, fallback models, per-request timeout, domain guidance, model settings, limits, examples. A role without one runs with `TRACE_<ROLE>_MODEL` and the defaults in `compiler.py`. Every agent event records `config_id` and `prompt_hash` (sha256[:12] of the effective instructions). The pack file `processes/<pack>/use-case.json` seeds it (`processes/README.md`).

| Endpoint | Who | What |
|---|---|---|
| `GET /use-cases`, `GET /use-cases/{id}` | anyone | Use cases; one with the active configuration of each role |
| `GET /use-cases/{id}/agents/{role}/versions` | anyone | Every version of a role's configuration, oldest first |
| `PUT /use-cases/{id}/agents/{role}` | manager | Body `{config, note}`: a new version, active from now on |
| `POST /agent-configs/{id}/activate` | manager | Activate an existing version: rollback, or adopt one loaded from the pack |

**When a provider fails** (ADR 0019): a role's `fallback_models` are tried in order when the model before answers 5xx, 429 (after the SDK's two retries), times out (`timeout_seconds`) or refuses the connection. An answer a validator rejects never switches models. The `llm_run` span holds `chain`, `failed_attempts` (`[{model, error}]`) and `model`, the one that answered. When every model fails the run is a 502 and the rule stays a `draft` with the error; it cannot be published, so the published version keeps deciding (ADR 0031, atomic publication, supersedes the `blocked` behaviour of ADR 0020). The invoice use case starts every role on `deepseek-v4-flash` and falls back to `glm5.3` / `qwen3.6`. To see it: `make demo-llm-down` sends the normalizer's primary model to an unreachable address (`OPENAI_BASE_URL=http://127.0.0.1:9/v1`) and prints the span:

```
chain: ["deepseek-v4-flash", "glm5.3", "qwen3.6"]
failed_attempts: [{"model": "deepseek-v4-flash", "error": "ModelAPIError: Connection error."}]
model: "glm5.3"
```

The [learning flow](learning.md) analyzes past cases on demand and prepares deterministic norms or subjective review guidance. A manager approves each validated norm before adoption. Preparation never enters the live rule-creation path.

**The client's norm** (ADR 0017): `POST /processes/{id}/norm` (manager), body `{"text": ...}`, the norm as the client wrote it, in any language. The normalizer agent keeps each sentence as one **norm rule** (`norm_rules`, the unit the client owns) and splits it into atomic checks: ordinary rules (one code, one decision), compiled in one background job, at most `TRACE_COMPILE_CONCURRENCY` (default 5) at once, linked by `rules.norm_rule_id`, with the normalizer's reading in `report.norm`. Statements that are not checkable conditions become the norm rule's `policies`. `GET /processes/{id}/norm-rules` lists each norm rule with its checks. `make eval-norm` runs norm -> normalizer -> compiler -> engine on batch 1 against the golden outcomes (opt-in, real LLMs).

Versions are append-only: only `active` moves. Tests script the model with `FunctionModel` (`tests/support/models.py`): no network, no keys. Before writing PydanticAI code, read `.context/pydantic-ai/START-HERE.md`: the v2 API differs from what a model remembers.

## Running locally

For scanned documents, first follow [OCR and ingestion setup](ingestion/setup.md).
It covers both downloaded readers, Gemini/Jev credentials, Windows commands and
the production process API. `make setup` does not download OCR weights. Download
them before `make demo`, which uploads the PDFs through the API and uses OCR on scans.

Requirements: Docker and [uv](https://docs.astral.sh/uv/). The old text-layer
benchmark and golden-reference tools also need `pdftotext` (poppler).

| Command | What it does |
|---|---|
| `make setup` | `.env` from the example, Postgres + backend (`docker compose`), migrations, loads `processes/invoice-payment.json`. Repeatable. API at http://localhost:8000/docs. Ports taken: `DB_PORT=5442 BACKEND_PORT=8001 ERP_PORT=8011 make setup` (pass the same variables to the commands below) |
| `make activate MANAGER_ID=1` | Publishes the pack's validated draft as a process version ([process versions](process-versions.md)): the hand-written `rules-v3/` need no model. Nothing runs before it (409). `1` is the seeded manager on a fresh database (`curl -s localhost:8000/users`) |
| `make erp` | Starts the challenge ERP from the submodule (port 8009, or `ERP_PORT`). Keep it running in another terminal |
| `make erp-sync` | Downloads the ERP into a new snapshot (`docs/sources-http.md`) |
| `make backup` | `pg_dump` of the live database into `backups/` (`DB_CONTAINER`, `DB_NAME`) |
| `make export-batch FILES=<dir> OUT=<file>` | Outcomes of the instances named like the PDFs of `<dir>` only, then checked: one line per file, valid results (`docs/runbook-batch2.md`) |
| `make check-outcomes OUT=<file> FILES=<dir>` | Only the check, for a file already written |
| `make compile` | Compiles the draft rules with the two agents (needs LLM keys); compiling never publishes, `make activate` does |
| `make demo` | Uploads workbook and 500 PDFs through the production API, syncs the ERP, runs decisions and exports `output/outcomes.jsonl` (`tools/README.md`). Requires the backend and ERP running, plus downloaded OCR weights for scans |
| `make demo DEMO_ARGS="--limit 5 --local-only"` | Small API run with local OCR and no Gemini/Jev requests; use a fresh database for comparable results |
| `make trace-decision FILE=<file_id>` | One invoice through the API, as text: state, decisions (author, reason, process version, rules hash), symbols with origin, latency per step, errors and retries, pending work and alerts. `PROCESS=<id>` picks a process |
| `make openapi` | Dumps the API contract to `frontend/openapi.json` (no server needed) and regenerates `frontend/src/api/schema.d.ts`. Run it after changing a route or schema; a unit test fails while they are stale |
| `make test` | Unit tests (`-m "not e2e and not llm"`) |
| `make test-e2e` | Golden outcomes of batch 1 and the API flow (needs the challenge submodule) |
| `make check` | `ruff check`, `ruff format --check` (backend and `tools/`), then `test` and `test-e2e`. Run before every PR |
| `make eval-compiler` | Opt-in, calls real LLMs: compiles the 16 rules and compares with `rules-v3/`; report in `backend/evals/reports/` |
| `make eval-norm` | Opt-in, calls real LLMs: the client's `Norma_Pagos_v3` -> normalizer -> compiler -> batch 1 vs golden; report in `backend/evals/reports/` |
| `make demo-llm-down` | Opt-in, calls real LLMs (Helmcode): the normalizer's primary provider is unreachable and a fallback model answers; prints the `llm_run` span (ADR 0019) |
| `make down` | Stops the containers; data stays |
| `make reset-db` | Deletes the database volume. Then `make setup` |

Without Docker for the backend (faster loop): `docker compose up db -d`, then in `backend/`: `uv sync`, `uv run alembic upgrade head`, `uv run uvicorn app.main:app --env-file ../.env --reload` (the settings read `.env` from the working directory, so without `--env-file` the keys in the root `.env` are missed).

The console: `cd frontend && npm install && npm run dev`, then http://127.0.0.1:5173. It proxies `/api` to the API of `make setup` (:8000); for another port set `VITE_API_TARGET=http://127.0.0.1:<port>`. It always talks to the real API; `VITE_API_MODE=mock` is the only way to see the simulator, and it says so on screen (`frontend/README.md`).

## Environment

`.env.example` lists everything; `make setup` copies it to `.env`.

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` | LLM providers. Only `make compile`, `make eval-compiler` and the assistant need them |
| `TRACE_ERP_USER`, `TRACE_ERP_PASSWORD`, `TRACE_ERP_URL` | The ERP connector, named in `processes/invoice-payment/sources.json`. Docker sets the URL to `host.docker.internal:${ERP_PORT:-8009}` |
| `TRACE_HEALTH_*` | `GET /health/planes` thresholds: window, error rates, p95 per plane, and `TRACE_HEALTH_MIN_SPANS` (default 5): below it a plane is `ok`, "not enough data" |
| `TRACE_COMPILER_MODEL`, `TRACE_TESTER_MODEL`, `TRACE_ASSISTANT_MODEL` | One model per agent role, `provider:model` (any PydanticAI provider, or `helmcode:<model>` with `HELMCODE_API_KEY`). Default `helmcode:deepseek-v4-flash` for every role, with `TRACE_FALLBACK_MODELS` (`helmcode:glm5.3`, `helmcode:qwen3.6`) for roles the use case does not set (`app/core/config.py`) |
| `TRACE_AUTO_ACTIVATE_MAX_CHANGE` | Share of past decisions a compiled rule may change and still activate by itself (default 0.05) |
| `TRACE_DECISION_WORKERS` | Rule sandbox subprocesses evaluated concurrently (default 4) |
| `TRACE_DATABASE_URL` | Set by Docker; the Makefile overrides it for tests |
| `LOGFIRE_TOKEN`, `OTEL_EXPORTER_OTLP_ENDPOINT` | Live monitoring (see Traces and observability). Unset: spans stay in `events` only |

## Traces and observability

Every step is a span in the `events` table (ADR 0018): the audit, joinable with decisions and
rules. In code: `with events.span("my_step", rule_id=rule.id, count=3) as s: ...; s.set(x=1)`;
children nest by themselves across `await`, `gather` and threads.

| Endpoint | What it gives |
|---|---|
| `GET /traces?process_id=&name=&status=&limit=` | Recent spans, newest first (`name` is the step, `status` `ok`/`error`) |
| `GET /traces/{trace_id}` | One trace as a tree (`children`) |
| `GET /instances/{id}/trace` | An invoice's journey: file, reading spans, symbols with origin, decisions with each rule's answer (rule text, norm rule), resolutions, exports, `exported_decision` |
| `GET /rules/{id}/trace` | How a rule was produced (norm sentence, normalizer run, each compilation: tester, coder attempts, test runs, reviews, impact check, activation), its `lifecycle` (saved, compiled, activated, retired, impact previews, with author) and its runtime in process runs (fired, errors, p50/p95) |
| `GET /processes/{id}/metrics?since=` | Completed runs (refused ones are `run_process` errors), instances/s, p50/p95 per step type, LLM calls/retries/errors/tokens by model and role, decisions by outcome, escalations by cause (`MISSING_DATA`, `RULE_ERROR`, `RULE_NEEDS_DATA`, `RULE_COMPILE_FAILED`, `RULE_CONFLICT`), escalated and pending |
| `GET /processes/{id}/metrics/{plane}`, `GET /health/planes` | The ingestion, agents and execution planes; each plane `ok`, `degraded` or `down` now (`TRACE_HEALTH_*`) |
| `GET /processes/{id}/alerts?status=open` | Past decisions newer data or rules would decide otherwise (ADR 0026) |

`make trace-decision FILE=<file_id>` reads these endpoints for one invoice and prints them as
text; sample outputs in `demo-logs/defense/`.

Who changed what is in the feed: rule saves, compilations, activations and retirements carry
`author` (a person, `cli` or `auto`) and the status before and after; agent configuration
changes (`configure_agent`, `activate_agent_config`) carry the author and the version before
and after, and appear in the feed of every process of the use case. A refused change is an
`error` span. Pass `X-User-Id` when saving a rule so it has an author.

Each `llm_run` span holds the exact instructions, user message, output and retry prompts.
Cost is tokens (`input_tokens`, `output_tokens`).

The same spans go to OpenTelemetry through the Logfire SDK, but only when configured:
- **Logfire cloud** (free tier): create a project, put its write token in `.env` as
  `LOGFIRE_TOKEN`, restart the API.
- **Local Phoenix**: `docker compose --profile observability up -d`, then
  `OTEL_EXPORTER_OTLP_ENDPOINT=http://phoenix:6006` in `.env` (backend in Docker) or
  `http://localhost:6006` (backend on the host). UI at http://localhost:6006, project
  `default`. Only traces are exported to it.

## Database and migrations

The migration history starts at `alembic/versions/0001_initial_schema.py` (squashed); a database older than it needs `make reset-db && make setup`. `0004_norm_rules.py` adds `norm_rules` and `rules.norm_rule_id`; `0005_events_process_id.py` adds `events.process_id`, backfilled from each event's instance; `0007_symbols_required.py` marks required symbols; `0008_event_spans.py` turns events into spans (ADR 0018). `0002_use_cases.py` moves each process's description into a use case of its own, so `alembic upgrade head` is enough from 0001.

To change a table: edit the feature's `model.py` (a new table must be imported in `app/models.py`), then in `backend/`: `uv run alembic revision --autogenerate -m "add x to rules"`. Read the generated file before committing. Two branches generating migrations at once leave two heads: `uv run alembic merge heads` and tell the group.

Tests use their own database, `TEST_DB_URL` in the `Makefile` (default `trace_test` on the same Postgres). `make test` recreates it empty on every run (`tests/support/prepare_db.py`) and applies the migrations, so tests never touch the database `make setup` filled for the demo.
