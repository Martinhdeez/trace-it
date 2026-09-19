# Process packs: configuring trace-it for any use case

**Status:** accepted design. Parts marked *(planned)* are not implemented yet.

## Why this matters
trace-it is not programmed for each problem. It is configured for each problem. The application code knows nothing about invoices, travel expenses or any other domain. Everything specific to a use case lives in a **process pack**: a folder of declarative files. A generic loader installs the pack into the database.

The invoice challenge ("500 Sombras de Alberto") is our first pack and the one we demo. A second pack (`travel-expenses`) shows that the same code serves a different problem without changes.

## Two layers of configuration
Best practice: **configuration as code to start, database for runtime changes.**

| Layer | Where | Holds | Changed by |
|---|---|---|---|
| Bootstrap configuration | Git (`processes/`, `backend/app/features/agents/presets/`) | Decision types, symbols, rules, description, policies, sources, agent presets | Pull requests |
| Runtime state | PostgreSQL | Active rules and their versions, agent config versions, decisions, findings, traces | The app (UI/API), while it runs |
| Secrets | `.env` (never committed) | API keys, ERP credentials | Each developer / deployment |

The bootstrap layer makes a setup reproducible on any machine. The runtime layer lets the manager change behaviour without touching code or restarting. Every runtime change is kept as a new version and never overwritten.

## Anatomy of a process pack
```
processes/
  invoice-payment/
    process.json   # decision types, symbols, rules, description (domain conventions), policies
    sources.json   # sources the rules read and where each comes from
    demo.json      # optional: where the sample data lives, for one-command demos (planned)
  travel-expenses/
    process.json
```

### `process.json`
- `name`, `description`: the description states the domain conventions every rule inherits (normalisation, units, tolerances, missing values). The compiler agents and the assistant receive it as shared context.
- `decision_types`: `[{name, priority, is_default, requires_human}]`. Exactly one default. Names are data (the invoice pack uses `PAGAR`, `NO_PAGAR`, `ESCALAR` because the challenge requires them).
- `symbols`: `[{name, type, description}]`: the data the rules use and extraction must fill.
- `rules`: `[{text, type: requirement|prohibition, decision}]`: natural language. Two blind agents compile each rule to code.
- `policies` *(planned)*: behaviour that differs between businesses and must not be hardcoded:

| Policy | Options | Invoice pack |
|---|---|---|
| `exported_decision` | `engine` (the process output) / `final` (latest decision, including a person's) | `engine` |
| `unresolved_review` (our own doubt, state `REVIEW`, not corrected by a person) | `block` (cannot export until corrected) / a decision type name | `block` |
| `unresolved_escalation` (a case sent to a person that nobody resolves) | `keep` (stays as it is, indefinitely) | `keep` |

- `users` (optional): initial users and roles (`manager`, `operator`).

### `sources.json`
Implemented for HTTP sources (the challenge ERP): format, guarantees and commands in `docs/sources-http.md`. The file sits in a folder named after the pack file (`processes/invoice-payment/sources.json`).

Declares each source of truth the rules read (`sources` in `evaluate(instance, sources, others)`) and its connector: spreadsheet sheets and column mapping, an HTTP API such as the challenge ERP (base URL; credentials referenced by `.env` variable name, never inline), or a CSV. This is what makes connectors reusable across processes.

### `demo.json` *(planned)*
Optional pointers to sample data (e.g. the challenge PDFs folder and Excel file) so a full demo runs with one command.

## Agent presets (shared by all processes)
`backend/app/features/agents/presets/{quality,cheap,fast}.json` define, per agent role, the model fallback chain, settings, retries, request limit, timeout and prompt file. See `docs/agents-plan.md`.

## Commands
| Command | Does |
|---|---|
| `make setup` | Starts infrastructure, runs migrations, loads the default agent preset and the invoice pack (current behaviour) |
| `make load PROCESS=<pack>` *(planned)* | Installs or updates one pack (idempotent) |
| `make demo PROCESS=<pack>` *(planned)* | `load` + ingest sample files + load sources + sync ERP + compile rules + run → export |
| `POST /processes/definition` | Same as `load`, from the API or the UI |
| Export endpoint *(planned)* | Returns the current process (and agent config) as pack JSON, so changes made in the app can be committed |

For the challenge: `make demo PROCESS=invoice-payment`. When batch 2 and policy v4 arrive, the manager adds the new rules in the app, exports the pack and commits it.

## Loader rules (the contract)
1. **Idempotent.** Loading the same pack twice changes nothing.
2. **Loading never overrides runtime decisions.** Missing items are added. A rule whose text changed in the file enters as a new **draft**; active rules are never modified or removed by a load. What the manager decided in the app always wins.
3. **Round trip.** What is tuned in the app can be exported back to pack JSON and committed, so a good configuration is never lost and can be reproduced elsewhere.
4. **Validation first.** A pack is validated before anything is written (e.g. exactly one default decision type, a default type cannot require a human, every rule names an existing decision type). Invalid packs are rejected whole.

## Adding a new use case
1. Create `processes/<name>/process.json` with its decision types, symbols, description and rules.
2. Declare its sources in `sources.json`.
3. `make load PROCESS=<name>`, compile the rules from the app, review the validation report and activate them.
4. Ingest its documents and run.

No code changes are needed. If a new kind of source appears, a new connector is the only code to write, and it becomes available to every process.
