# Conventions

Everything in this repository is in English: identifiers, database names and the values the system writes, API paths and fields, error codes and messages, prompts, comments, tests, docs, commits. Exceptions: (1) domain data an external contract fixes: the invoice process keeps `PAGAR`, `NO_PAGAR`, `ESCALAR` and the export fields `file_id` / `result` because `outcomes.jsonl` requires them verbatim; (2) values that arrive as data (file names, workbook cells such as `ABIERTO`, ERP statuses `PENDIENTE` / `PAGADA`, text printed on an invoice); (3) third-party material under `.context/`.

## Naming

| Where | Style | Example |
|---|---|---|
| Python modules, functions, variables | `snake_case` | `load_definition`, `rules_hash` |
| Python classes | `PascalCase` | `DecisionType`, `Outcomes` |
| Python constants | `UPPER_SNAKE_CASE` | `RULE_STATUSES`, `MAX_REPAIRS` |
| Tables | `snake_case`, plural nouns | `decision_types`, `findings` |
| Columns | `snake_case`; booleans read as a statement; timestamps end in `_at` | `is_default`, `requires_human`, `activated_at` |
| Constraints and indexes | `pk_`, `fk_`, `uq_`, `ck_`, `ix_` + table + columns (`backend/app/core/database.py`) | `fk_rules_process_id_decision` |
| URL paths | lowercase plural nouns; an action on one resource is a verb sub-path | `/processes/{process_id}/rules`, `/rules/{rule_id}/compile` |
| Path and query parameters, JSON fields | `snake_case` | `process_id`, `?status=` |
| Operation ids | `camelCase` verb + resource | `listRules`, `resolveInstance` |
| Headers | `X-` + `Title-Case` | `X-User-Id`, `X-Duplicate-Names` |
| Error codes | `snake_case` | `not_found`, `compilation_failed` |
| Event steps (`events.step`) | `snake_case` | `compile_rule`, `decision`, `resolution` |
| Rule `reason` codes | `UPPER_SNAKE_CASE` | `IBAN_MISMATCH`, `RULE_ERROR` |
| Feature folders; process files | `snake_case` plural; `kebab-case` | `features/rules/`, `processes/invoice-payment.json` |
| Branches; commits | `type/short-kebab`; Conventional Commits, imperative, scope = feature folder | `feat/rule-audit`; `fix(decisions): export the engine decision` |

## Domain terms

- **Process**, **decision type** (`priority`, `is_default`, `requires_human`), **symbol**, **source** (of truth), **instance** (one case; its `name` is the export's `file_id`), **rule**. An instance's `symbols` are what the rules read; `sources` are shared by every instance of the process.
- **Process version**: design term (ADR 0015), not a table. Every decision records `rules_hash`, the rule set it was taken with.
- **Rule finding**: one rule's answer on one instance, `{rule_id, hash, fires, reason}`, stored in `decisions.results` (`RuleResult` in the engine). **Audit finding** (`Finding`, table `findings`): a past decision that a newer rule says was wrong; a notice, never a correction (ADR 0008). Never write "finding" alone in code.
- **Engine decision**: a `decisions` row with `author = "engine"`. **Final decision**: an instance's latest row, whoever wrote it. **Exported decision**: the engine's latest decision; a person's decision is exported only when the engine never decided that instance (ADR 0016). Export answers 409 while any instance is `PENDING`.
- **Escalation type**: the process's highest-priority `requires_human` type. The engine sends there any instance whose rule code failed (`RULE_ERROR ...`), whose rule is `blocked` for missing data (`RULE_NEEDS_DATA ...`) or whose fired types tie on priority (`RULE_CONFLICT ...`). There is no REVIEW state.
- **Manager** and **operator**: the two user roles. A person who resolves an instance writes a new decision row; the engine's row is never edited.

## Statuses

| Entity | Values |
|---|---|
| Instance | `PENDING`, `DECIDED` |
| Rule | `compiling`, `draft`, `active`, `blocked` (enforced: escalates every instance), `retired` |

## The rule contract

Every rule's `code` defines exactly this function; the sandbox, the compiler and the engine rely on it:

```python
def evaluate(instance: dict, sources: dict[str, list[dict]], others: list[dict]) -> dict:
    return {"fires": bool, "reason": str}
```

`instance` maps symbol name to value. `sources` maps source name to its rows. `others` holds the other instances of the process, each with its symbols plus the key `_instance` (its name). Pure function: allowed imports are `decimal`, `datetime`, `re`, `math`, `unicodedata` only.

## Symbols

Symbols have two shapes; `backend/app/features/instances/symbols.py` is the only place that converts between them. Stored (`instances.symbols`, the instance API): `{name: {"value": <json>, "origin": <str>}}`; the model refuses anything else with a `ValueError`. Rule code (`instance` and each entry of `others`): `{name: value}`, produced by `flatten_symbols`. `origin` is provenance for the trace (ADR 0008); rule code never sees it.

## Errors

Domain errors are `TraceError` subclasses in `backend/app/common/exceptions.py`, each with a `status_code` and a `code` (`NotFoundError` 404, `ConflictError` 409, `PermissionDeniedError` 403, `CompilationError` and `AgentError` 502). `app/main.py` turns every one into `{"code", "message"}` with that status. Request validation failures are FastAPI's 422.
