# Processes

Each JSON file in this folder defines a complete decision process. trace-it knows nothing about invoices: the invoice payment process is just one more file (`invoice-payment.json`).

## Loading a process

```bash
make setup                                                          # loads invoice-payment.json
cd backend && uv run python -m app.cli load ../processes/travel-expenses.json
cd backend && uv run python -m app.cli load ../processes/invoice-payment.json --compile  # needs LLM keys
```

Also from the API: `POST /processes/definition` with the same JSON as the body.

Loading can be repeated safely:
- the process is looked up by `name`; if it does not exist, it is created;
- decision types and symbols are created or updated by `name`;
- a rule enters as `draft` only if the process does not already have one with the same text; existing rules (active ones too) are not touched. To change a rule, change its text: it enters as a new draft;
- users are created by `email` if they do not exist.

`--compile` compiles every draft not yet validated with the two agents and prints one line per rule. If one fails, it carries on with the others. `--activate` activates every draft whose code is validated; with the hand-written rules in `rules-v3/`, `load ... --activate` runs the invoice process without any model.

## Format

| Field | Required | What it is |
|---|---|---|
| `name` | yes | Unique name of the process |
| `description` | no | Free text. The agents (compiler and assistant) receive it as the context of every rule: put the shared conventions here (normalisation, units, what to do when a value is missing) |
| `decision_types` | yes | `[{name, priority, is_default, requires_human}]`. The highest `priority` wins when several rules fire. Exactly one `is_default` (applies when none fires), and that one cannot be `requires_human` |
| `symbols` | no | `[{name, type, description}]`: the data extraction fills in for each instance and the rules read |
| `rules` | no | `[{text, type, decision, code}]`. `type`: `requirement` (fires if it does not hold) or `prohibition` (fires if it holds). `decision`: one of the `decision_types`. `code` (optional): path, relative to the definition, of a file with hand-written code that defines `evaluate(instance, sources, others)`; the rule then arrives validated and needs no compiler. Only the CLI resolves it, never `POST /processes/definition` |
| `users` | no | `[{name, email, role}]`, `role`: `manager` or `operator` |

A definition with repeated types, symbols or rule texts, without exactly one default type, or with a rule whose decision does not exist is rejected without touching the database.

Names inside a definition (process, decision types, symbols, sources) are the process's own data. Write them in English, except where an external contract fixes them: the invoice process keeps `PAGAR`, `NO_PAGAR` and `ESCALAR` because the challenge's `outcomes.jsonl` requires them verbatim.

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

An 800 € report without a receipt fires both rules and ends up in `ESCALATE` (priority 3 > 2).
