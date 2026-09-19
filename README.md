# trace-it

Configurable decision processes with compiled rules, document evidence and an audit trail.
Built for the MAISA track of the "500 Sombras de Alberto" hackathon (ETSIT UPM, 18-20
September 2026): 500 supplier invoices, a chaotic workbook and a 2009 ERP, decided as
`PAGAR`, `NO_PAGAR` or `ESCALAR`.

## How it works

1. A **process pack** (`processes/invoice-payment.json`) declares the decision types with
   their priorities, the symbols to extract from each document and the rules in plain
   language. It is configuration, not code; a second pack (`travel-expenses.json`) runs on
   the same application.
2. **Ingestion** reads each PDF (native text, OCR, vision) and the workbook; the ERP is
   read through a fault-tolerant HTTP connector into versioned snapshots.
3. **Rules become Python** through two blind agents that write code and tests for the same
   rule text; a rule is only valid when both agree on every test and on the whole history.
   The invoice rules also ship hand-written, so the process runs without any model.
4. The **engine** runs every active rule in a sandbox; the highest-priority decision type
   that fired wins, the default applies when none does, and a rule that cannot be evaluated
   escalates the case to a person with the reason. Every instance ends with a decision.
5. **People** resolve escalated cases and approve rule changes. Before a rule is activated
   or retired, it is replayed over every past decision and the impact is shown; history is
   never rewritten.

Result on batch 1: `PAGAR 433 / NO_PAGAR 36 / ESCALAR 31`, identical to an independently
built reference on all 471 text invoices, in one second of engine time.

## Run it

```bash
make setup                      # Postgres + API in Docker, invoice pack loaded
make erp                        # the challenge ERP bridge, in another terminal
make demo                       # 500 invoices -> output/outcomes.jsonl (+ detail.json)
```

API docs at <http://localhost:8000/docs>; identify with `POST /login` and the `X-User-Id`
header. For local development without Docker, from `backend/`:

```bash
uv sync --locked
uv run alembic upgrade head
uv run python -m app.features.ingestion.tools.download_models   # OCR weights, once
uv run uvicorn app.main:app --env-file ../.env --host 127.0.0.1 --port 8000 --workers 1
```

Native PDF and Excel reading need no OCR weights. LLM keys (`ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `GEMINI_API_KEY`) are only needed to compile rules from text and for the
escalation assistant; see `.env.example`.

## Read more

- [Team guide](docs/team-guide.md): git flow, layout, running and testing
- [Conventions](docs/CONVENTIONS.md): language, naming, contracts
- [Architecture decisions](docs/adr/README.md): what we chose and what we gave up
- [Process packs](processes/README.md), [invoice rules](docs/invoice-payment-rules.md),
  [ERP connector](docs/sources-http.md), [ingestion](docs/ingestion/README.md),
  [frontend](frontend/README.md)
- [Contributing](CONTRIBUTING.md)

The challenge data lives in the `.context/500-sombras-de-alberto` submodule and is never
modified. Credentials, model weights and local results stay out of Git.
