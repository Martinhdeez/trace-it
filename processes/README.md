# Processes

Each JSON file in this folder defines a complete decision process (a process pack, ADR 0007). trace-it knows nothing about invoices: the invoice payment process is just one more file, `invoice-payment.json`.

## Loading a process

```bash
make setup                                                          # loads invoice-payment.json
make activate MANAGER_ID=1                                          # publishes its hand-written rules
cd backend && uv run python -m app.cli load ../processes/travel-expenses.json
cd backend && uv run python -m app.cli load ../processes/invoice-payment.json --compile  # needs LLM keys
```

`POST /processes/definition` with the same JSON as the body is the only way to create a process over the API; there is no other creation endpoint. A definition that fails validation is rejected without touching the database: 422 over HTTP, an error message from the CLI.

Loading is idempotent (`backend/app/features/processes/definition.py`):
- the CLI first loads the pack's use case, `<pack>/use-case.json`, if it exists (see below);
- the process is looked up by `name` and created if missing, inside the use case named by `use_case` (which must exist: 409 otherwise). Without `use_case`, the process gets a use case of its own, with the process's name and `description`;
- decision types and symbols are created or updated by `name`;
- a rule enters as `draft` only if the process has no rule with the same text; existing rules, active ones included, are never touched. To change a rule, change its text: it enters as a new draft;
- users are created by `email` if they do not exist.

`--compile` compiles every draft without validated code with the two agents and prints one line per rule; one failure does not stop the others. A rule that needs data the process lacks becomes `blocked`: enforced, every instance escalates (`docs/team-guide.md`, rule life cycle). `--activate` activates every draft whose code is validated.

## Format

| Field | Required | What it is |
|---|---|---|
| `name` | yes | Unique name of the process |
| `use_case` | no | Name of the use case the process belongs to. Its description and agent configuration apply to the process. Give `use_case` or `description`, not both (422) |
| `description` | no | Only without `use_case`: the description of the process's own use case. Free text the compiler and the assistant receive with every rule: the conventions shared by all rules (normalisation, units, what to do when a value is missing) |
| `decision_types` | yes | `[{name, priority, is_default, requires_human}]`. The highest `priority` wins when several rules fire. Exactly one `is_default` (applies when none fires) and it cannot be `requires_human`. Priorities must be distinct. At least one type must be `requires_human` |
| `symbols` | no | `[{name, type, description, required, extraction?}]`: what extraction fills in for each instance and the rules read. `required` (default `false`): an instance where the symbol is missing, `None` or blank is always escalated with `MISSING_DATA: <symbols>`, whatever the rules say (ADR 0016). Optional `extraction` declares labels and a source; see [process-driven extraction](../docs/dynamic-extraction.md) |
| `rules` | no | `[{text, type, decision, code}]`. `type`: `requirement` (fires if it does not hold) or `prohibition` (fires if it holds). `decision`: one of the `decision_types`. `code` (optional): path, relative to the definition, of a file defining `evaluate(instance, sources, others)`; see `rules-v3/` below |
| `users` | no | `[{name, email, role}]`, `role`: `manager` or `operator` |

Rejected: repeated types, symbols or rule texts; no default type or more than one; a default that requires a human; two types sharing a priority; no `requires_human` type; a rule whose decision does not exist.

The document extraction contract comes from declared symbols and their optional
`extraction` hints. The backend also inspects literal symbol and source references in
enforced rule code with Python's AST and reports undeclared symbols; it does not infer
new extraction fields or call an LLM for this analysis. The plan is available at
`GET /processes/{id}/extraction-plan`. Once a process has an active published version,
that version supplies the contract. Unpublished draft edits have no effect until
publication. Each request reads the current version; unchanged rule analysis is cached
in memory, and publication changes its cache identity without a server restart.

When a required symbol is missing, a rule's code fails at runtime, or two fired types tie on priority, the engine decides the highest-priority `requires_human` type with the reason (`MISSING_DATA ...` / `RULE_ERROR ...` / `RULE_CONFLICT ...`), so a person sees the case and the default is never produced with a rule unevaluated (ADR 0016). That is why every process needs such a type.

Names inside a definition (process, decision types, symbols, sources) are the process's own data. Write them in English, except where an external contract fixes them: the invoice process keeps `PAGAR`, `NO_PAGAR` and `ESCALAR` because the challenge's `outcomes.jsonl` requires them verbatim.

## `invoice-payment/frozen/<date>/`: a compiled rule set, frozen

The checks the normalizer and the compiler wrote from `Norma_Pagos_v3`, kept exactly as they
were adopted for delivery: `invoice-payment.json` (a pack of its own process, `Invoice payment -
frozen <date>`, whose rules point at `rules/n<norm rule>-<check>.py`) and `manifest.json` (the
norm's sentences, each check's hash, reading, test rows and test report, the models, the golden
result and how many norm runs it took). `make load-frozen MANAGER_ID=<id>` loads, validates and publishes it with no LLM,
exactly like the hand-written rules below; `backend/tests/e2e/test_frozen_rules.py` reloads it
and checks the hashes and 471/471 on the golden.

## `rules-v3/`: hand-written code

The invoice rules point at `rules-v3/r01-...py` to `r16-...py`, one file per rule in the order of the JSON. A rule that arrives with its code passes the sandbox's static check and is stored validated (`report.origin = "hand-written"`), so `--activate` runs the whole process without any model. Only the CLI resolves `code` paths, never `POST /processes/definition` (a client-supplied path would read any file the backend can); over HTTP such a rule is refused with 409. The compiler can regenerate the same rules from their texts, and `make eval-compiler` compares its output with these files. Where each rule comes from: `docs/invoice-payment-rules.md`.

## `invoice-payment/use-case.json`: the use case and its agents

A use case is what the app is used for (e.g. "Invoice payment"); a process is one set of rules inside it (ADR 0011). A pack may carry `<pack-name>/use-case.json`, loaded before the process:

| Field | What it is |
|---|---|
| `name` | Unique name of the use case; the process's `use_case` names it |
| `description` | The domain conventions every rule follows, shown to the compiler, tester and assistant |
| `agents` | `{role: settings}`, roles `compiler`, `tester`, `assistant`, `normalizer`. Settings: `model` (`provider:model` or `helmcode:<id>`; default `TRACE_<ROLE>_MODEL`), `fallback_models` (models tried in order when the one before fails at the provider: 5xx, 429, timeout, connection; ADR 0019), `timeout_seconds` (per request to the provider), `instructions` (domain guidance appended to the platform prompt in `backend/app/features/agents/prompts/`), `model_settings` (e.g. `{"temperature": 0}`), `limits` (compiler: `max_attempts`, `auto_activate_max_change`, `1.0` = a valid rule always activates; tester: `min_tests`, `max_reviews`), `failed_check_decision` (normalizer only: the decision of a check whose failure the norm does not name, e.g. "pay only if X"; a decision type of the process, never the default; without it the normalizer falls back to the norm's tie-breaker, then the most conservative type that requires a human), `examples` (`[{text, type, code}]`, `code` a path relative to this file; the compiler sees the examples of the other rules, never the one being compiled) |

Loading never overrides what was changed at runtime: a role with no stored version gets the file's settings as version 1, active; settings that differ from every stored version enter as a new, inactive version, for a manager to activate (`POST /agent-configs/{id}/activate`).

## `invoice-payment/sources.json`: source connectors

A pack may carry `<pack-name>/sources.json` with the connector configuration of its sources of truth. The invoice pack configures `erp` as an HTTP source: login, paged XML, field mapping, retries, rate limit. `make erp-sync` or `POST /processes/{id}/sources/erp/sync` download it into a new snapshot. The connectors belong to the pack's use case: any process of "Invoice payment", whatever its name, syncs with this file (ADR 0013). Format and behaviour: `docs/sources-http.md`.

## `hiring-screening/`: a second problem, born on stage

Not a pack: the raw inputs of a hiring screening (CVs, the client's policy as an email thread, the manager's notes, a workbook of sources) and an answer key. Discovery creates the process from them live; `make hiring-demo` drives it and writes the evaluation report. See [its README](hiring-screening/README.md).

## Minimal example: travel expenses

`travel-expenses.json`, another problem with other decisions:

```json
{
  "name": "Travel expenses",
  "description": "Approves or rejects each expense report of a business trip. Conventions for every rule: amount is in euros and is compared with Decimal(str(amount)); if a symbol the rule needs is missing (None), the rule does not fire.",
  "decision_types": [
    {"name": "ESCALATE", "priority": 3, "requires_human": true},
    {"name": "REJECT", "priority": 2},
    {"name": "APPROVE", "priority": 1, "is_default": true}
  ],
  "symbols": [
    {"name": "employee", "type": "text", "description": "Email of the travelling employee."},
    {"name": "amount", "type": "number", "description": "Total of the report in euros."},
    {"name": "has_receipt", "type": "boolean", "description": "The report attaches a receipt."}
  ],
  "rules": [
    {"text": "`has_receipt` is true.", "type": "requirement", "decision": "REJECT"},
    {"text": "`amount` is greater than 500.", "type": "prohibition", "decision": "ESCALATE"}
  ]
}
```

An 800 € report without a receipt fires both rules and ends up in `ESCALATE` (priority 3 > 2). Its rules have no `code`, so they wait for `--compile`.
