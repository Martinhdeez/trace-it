# trace-it: guide for assistants and newcomers

Configurable decision processes: a process pack (JSON) declares decision types, symbols and
rules in plain language; agents compile the rules to Python; a deterministic engine runs them
in a sandbox and every instance ends with a decision and its evidence. The invoice-payment
process of the "500 Sombras de Alberto" challenge is the first pack. No LLM ever decides.

## Where things are

| Path | What |
|---|---|
| `backend/app/features/{users,processes,rules,decisions,ingestion,sources,agents}` | One folder per feature: `model.py`, `schemas.py`, `service.py`, `router.py`, `tests/` |
| `backend/app/core/` | settings (`TRACE_*`), database, `events.py` (the trace table) |
| `backend/app/cli.py` | `load <pack> [--compile] [--activate]`, `sources sync <pack>` |
| `processes/` | Process packs; `invoice-payment.json` + `invoice-payment/sources.json` + `rules-v3/*.py` |
| `tools/` | Demo stand-ins for extraction over the challenge corpus (`make demo`) |
| `frontend/` | The manager's console (Vite + React). Its API, screen by screen: `docs/api.md` |
| `docs/adr/` | Decisions. ADR 0001 wins over any other document |
| `.artifacts/` | Archived plans and analyses. History, not guidance |

## Rules of the house

- English everywhere: code, docs, commits, API. Domain names from `docs/CONVENTIONS.md`.
- Don't overcomplicate: this is an MVP built in a weekend. One implementation, no
  abstraction for a second case that does not exist yet.
- The engine is pure: no clock, network or database inside `decisions/engine.py`. A cut-off
  date is a row in a source, never `today()`.
- Rule code contract: `evaluate(instance, sources, others) -> {"fires": bool, "reason": str}`,
  run only through `agents/sandbox.py`.
- History is append-only: decisions, sources and files are never edited. A rule change is
  checked against past decisions before it is adopted.
- Tests beside their feature; `make check` must be green (unit + golden e2e) before merging.
  No test may need an LLM key: script models with `tests/support/models.py`.
- Branch from `dev`, PR into `dev`, squash merge. `main` is what we show.

## Running

```bash
make setup      # Postgres + API in Docker, pack loaded        make test       # unit tests
make erp        # the challenge ERP bridge (other terminal)    make test-e2e   # golden + API flow
make demo       # decide the 500 invoices -> output/outcomes.jsonl
make reset-db   # only for a database older than migration 0001
```

Details: `docs/team-guide.md`. Why things are the way they are: `docs/adr/README.md`.
