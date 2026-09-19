# trace-it

Configurable decision processes with compiled rules, document evidence and an audit trail.
Built for the MAISA track of the "500 Sombras de Alberto" hackathon (ETSIT UPM, 18-20
September 2026): 500 supplier invoices, a chaotic workbook and a 2009 ERP, decided as
`PAGAR`, `NO_PAGAR` or `ESCALAR`. No LLM ever decides: agents write the rules' code, a
deterministic engine runs it, and every decision keeps its evidence, rule versions and
latency.

**Run the demo** (Docker, [uv](https://docs.astral.sh/uv/), OCR keys in `.env`; see
[Run it](#run-it)):

```bash
make setup                             # Postgres + API in Docker, invoice pack loaded
make activate MANAGER_ID=1             # publish the hand-written rules (1: seeded manager)
make erp                               # the challenge ERP, in another terminal
make demo                              # 500 invoices -> output/outcomes.jsonl
make trace-decision FILE=scan_002.pdf  # follow one decision: evidence, versions, latency
```

**Why it is built this way**: [architecture decisions](docs/adr/README.md). **Demo script
for the jury**: [docs/defense.md](docs/defense.md).

## How it works

1. A **process pack** (`processes/invoice-payment.json`) declares the decision types with
   their priorities, the symbols to extract from each document and the rules in plain
   language. It is configuration, not code; a second pack (`travel-expenses.json`) runs on
   the same application.
2. **Ingestion** reads each PDF (native text, OCR, vision) and the workbook; the ERP is
   read through a fault-tolerant HTTP connector into versioned snapshots.
3. **Rules become Python** through two agents: a tester writes tests from the rule text
   alone, and a coder iterates until its code passes them (disputes are settled by the
   tester from the text). A manager publishes rule changes as a new process version,
   after they are replayed over past decisions. The invoice rules also ship hand-written,
   so the process runs without any model.
4. The **engine** runs every active rule in a sandbox; the highest-priority decision type
   that fired wins, the default applies when none does, and a rule that cannot be evaluated
   escalates the case to a person with the reason. Every instance ends with a decision.
5. **People** resolve escalated cases and approve rule changes. Before a rule is activated
   or retired, it is replayed over every past decision and the impact is shown; history is
   never rewritten.

The historical text-layer baseline for batch 1 gave `PAGAR 433 / NO_PAGAR 36 /
ESCALAR 31`, identical to an independently built reference on all 471 text
invoices, in one second of engine time. OCR can change the scan outcomes.

## Run it

For the complete OCR setup (both local model downloads, Gemini/Jev keys, Docker,
Windows/Linux/macOS commands and the production API corpus run), start with the
[OCR and ingestion setup guide](docs/ingestion/setup.md). `make demo` uploads
the workbook and all PDFs through that production API, so scans run through OCR.

```bash
make setup                      # OCR weights + check, Postgres + API in Docker, pack loaded
make activate MANAGER_ID=1      # publish the rules; before it, runs answer 409
make erp                        # the challenge ERP bridge, in another terminal
make demo                       # 500 invoices -> output/outcomes.jsonl (+ detail.json)
```

`make setup` downloads the pinned OCR weights and checks the `verified` OCR profile
(`make ocr-check`: it needs the Gemini/Jev keys in `.env`). Ports taken?
`DB_PORT=5442 BACKEND_PORT=8030 ERP_PORT=8031 make setup`, then `ERP_PORT=8031 make erp`
and `BACKEND_PORT=8030 make demo`. API docs at <http://localhost:8000/docs>; identify with `POST /login`
and the `X-User-Id` header. A local smoke run with no Gemini or Jev calls is
`make demo DEMO_ARGS="--limit 5 --local-only"`, with `TRACEPAY_OCR_PROFILE=experimental`
in `.env`; it still needs the local OCR weights for scanned files. For local development without Docker, from `backend/`:

```bash
uv sync --locked
uv run alembic upgrade head
uv run python -m app.features.ingestion.tools.download_models   # OCR weights, once
uv run uvicorn app.main:app --env-file ../.env --host 127.0.0.1 --port 8000 --workers 1
```

Native PDF and Excel reading need no OCR weights. The full OCR committee uses
`GEMINI_API_KEY` for images and `TYPESAFE_API_KEY` for text-candidate selection;
both are optional for local-only extraction. Rule agents have separate provider
configuration (the invoice use case currently uses `HELMCODE_API_KEY`). The
hand-written rules run without agent keys. See `.env.example` and the setup guide.

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
