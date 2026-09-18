# Conventions

**Everything in this repository is written in English.** New code must follow this file. When something is missing here, pick the plain English term, use it, and add it to the glossary in the same pull request.

`docs/adr/0001-configurable-decision-process.md` is the accepted design. Where its vocabulary and this file overlap, they mean the same thing; the glossary says how each design term maps to code.

## What must be in English

- Code identifiers: packages, modules, classes, functions, variables, constants, test names.
- Database: tables, columns, constraints, indexes, sequences, and every enum-like value the system writes (statuses, roles, kinds, trace steps, JSON keys).
- API: paths, path and query parameters, request and response fields, headers, operation ids, tags.
- Error codes and messages, log lines, CLI commands and output.
- LLM prompts and the context objects sent to a model.
- Comments, docstrings, tests, documentation, commit messages and pull requests.

## Exceptions

1. **Domain data of a specific process** that an external contract fixes. The invoice process keeps its decision names `PAGAR`, `NO_PAGAR` and `ESCALAR`, and the export keeps the field names `file_id` and `result`, because the challenge requires them verbatim in `outcomes.jsonl`.
2. **Values that come from outside the system as data**: supplied file names (`FA-1016_papelería.pdf`), cell values of the challenge workbook (`ABIERTO`), ERP statuses (`PENDIENTE`, `PAGADA`), names of people, text printed on an invoice.
3. **Third-party material**: `.context/` (the challenge submodule and vendored library docs) and anything we did not write.

Everything else a process defines (its name, description, symbol names, source and column names, rule texts, other decision names) is written in English.

## Naming

| Where | Style | Example |
|---|---|---|
| Python modules, functions, variables | `snake_case` | `load_definition`, `rules_hash` |
| Python classes | `PascalCase` | `DecisionType`, `LLMConfig` |
| Python constants | `UPPER_SNAKE_CASE` | `HUMAN_KINDS`, `MAX_REPAIRS` |
| Tables | `snake_case`, plural nouns | `decision_types`, `files` |
| Columns | `snake_case`; booleans read as a statement (`is_default`, `requires_human`); timestamps end in `_at` | `created_at`, `activated_at` |
| Constraints and indexes | the naming convention in `backend/app/core/database.py` (`pk_`, `fk_`, `uq_`, `ck_`, `ix_` + table + columns) | `fk_rules_process_id_decision` |
| Status values | `UPPER_CASE` for instance statuses, `lowercase` for everything else, as the table below lists | `PENDING`, `draft` |
| URL paths | lowercase plural resource nouns; a multi-word segment is `kebab-case`; an action on one resource is a verb sub-path | `/processes/{process_id}/rules`, `/rules/{rule_id}/compile` |
| Path and query parameters, JSON fields | `snake_case` | `process_id`, `?status=`, `human_kind` |
| Operation ids | `camelCase` verb + resource | `listRules`, `resolveInstance` |
| Headers | `X-` + `Title-Case` | `X-User-Id`, `X-Duplicate-Names` |
| Error codes | `snake_case` | `not_found`, `compilation_failed` |
| Trace steps (`events.step`) | `snake_case` verb or noun | `compile_rule`, `suggest_escalation` |
| Rule `reason` codes | `UPPER_SNAKE_CASE` | `IBAN_MISMATCH`, `RULE_ERROR` |
| Files and folders | feature folders `snake_case` plural where a collection (`rules/`), process files `kebab-case` | `processes/invoice-payment.json` |
| Branches | `type/short-kebab-description` | `feat/rule-audit` |
| Commits | [Conventional Commits](https://www.conventionalcommits.org/), imperative, scope = feature folder | `fix(decisions): export the engine decision` |

## Glossary

Spanish term used in earlier code and documents, and the English term to use now.

### Domain

| Spanish | English | In code |
|---|---|---|
| proceso | process | `Process`, table `processes`, `features/processes/` |
| versión de proceso | process version | design term (ADR); not a table yet |
| regla | rule | `Rule`, table `rules`, `features/rules/` |
| instancia | instance (the ADR's "case") | `Instance`, table `instances` |
| caso | case | prose only; the entity is `Instance` |
| símbolo | symbol (the ADR's "normalized fact") | `Symbol`, table `symbols` |
| tipo de decisión | decision type (the ADR's "outcome") | `DecisionType`, table `decision_types` |
| fuente (de verdad) | source (of truth) | `Source`, table `sources`, `features/sources/` |
| fichero | file | `File`, table `files` |
| decisión | decision | `Decision`, table `decisions` |
| resultado de una regla | rule finding (ADR), rule result (code) | one entry of `decisions.results`: `{rule_id, hash, fires, reason}` |
| hallazgo | finding (audit finding) | `Finding`, table `findings`: a past decision a later rule says was wrong. Not the same as an ADR "rule finding" |
| recomendación | recommendation | design term (ADR); today the assistant's `Suggestion` |
| decisión final | final decision | the latest row of an instance in `decisions` |
| evento / traza | event / trace | `Event`, table `events`, `features/traces/` |
| extracción | extraction | `Extraction`, table `extractions`, `features/extraction/` |
| ingesta | ingestion | `features/ingestion/` |
| usuario | user | `User`, table `users`, `features/users/` |
| responsable (rol) | manager | role value `manager` |
| operador | operator | role value `operator` |
| requisito | requirement | rule type `requirement` |
| prohibición | prohibition | rule type `prohibition` |
| salta (una regla) | fires | `fires` |
| motivo | reason | `reason` |
| prioridad | priority | `priority` |
| por defecto | default | `is_default` |
| requiere persona | requires a human | `requires_human` |
| tipo de decisión humana | human kind | `human_kind` |
| resolución | resolution | human kind `resolution` |
| corrección de revisión | review correction | human kind `review_correction` |
| origen | origin | `sources.origin`, symbol `{value, origin}` |
| valor | value | symbol `{value, origin}` |
| motor | engine | `features/decisions/engine.py`, decision author `engine` |
| veredicto | verdict | `Verdict` |
| impacto | impact | `Impact`, `GET /rules/{rule_id}/impact` |
| auditoría | audit | `features/decisions/audit.py` |
| cambio | change | `Change` |
| conflicto | conflict | `conflicts` |
| sin cambio | unchanged | `unchanged` |
| compilador | compiler | `features/agents/compiler.py` |
| asistente | assistant | `features/agents/assistant.py` |
| sugerencia | suggestion | `Suggestion`, `GET /instances/{instance_id}/suggestion` |
| informe | report | `rules.report` |
| válida | valid | report key `valid` |
| discrepancias | discrepancies | report key `discrepancies` |
| histórico | history | report key `history` |
| coinciden | agree | report key `history.agree` |
| código A/B | code A/B | `code_a`, `code_b` (`tests_a`, `tests_b` unchanged) |
| papel | role | `role`; LLM roles `compiler_a`, `compiler_b`, `extractor_1`, `extractor_2`, `assistant` |
| configuración LLM | LLM config | `LLMConfig`, table `llm_config` |
| reparación | repair | `repairs` |
| agentes | agents | `features/agents/` |

### Statuses

| Spanish | English |
|---|---|
| instancia `PENDIENTE` / `REVISION` / `DECIDIDA` | `PENDING` / `REVIEW` / `DECIDED` |
| regla `borrador` / `rechazada` / `activa` / `retirada` | `draft` / `rejected` / `active` / `retired` |
| símbolo `texto` / `numero` / `fecha` / `booleano` | `text` / `number` / `date` / `boolean` |

### Actions

| Spanish | English | In code |
|---|---|---|
| cargar (definición) | load (definition) | `load_definition`, `python -m app.cli load`, `POST /processes/definition` |
| compilar | compile | `compile_rule`, `POST /rules/{rule_id}/compile`, `make compile` |
| activar / retirar | activate / retire | `POST /rules/{rule_id}/activate`, `/retire`, `python -m app.cli load --activate` |
| ejecutar (proceso) | run | `POST /processes/{process_id}/run` |
| ejecutar (sandbox) | run | `sandbox.run`, `sandbox.run_batch` |
| comprobar | check | `sandbox.check`, `audit.check` |
| decidir | decide | `engine.decide` |
| resolver | resolve | `POST /instances/{instance_id}/resolve` |
| exportar | export | `GET /processes/{process_id}/export` |
| cola | queue | `GET /processes/{process_id}/queue` |
| registrar (traza) | record | `traces.service.record` |
| evaluar | evaluate | the rule contract below |

### The rule contract

Every compiled rule defines exactly this function, and the sandbox, the compiler and the engine all rely on it:

```python
def evaluate(instance: dict, sources: dict[str, list[dict]], others: list[dict]) -> dict:
    return {"fires": bool, "reason": str}
```

`instance` maps symbol name to value. `sources` maps source name to its rows. `others` holds the other instances of the process, each with its symbols plus the key `_instance` (its name).

### Symbols

An instance's symbols have two shapes, and `backend/app/features/ingestion/symbols.py` is the only place that converts between them.

| Where | Shape | Example |
|---|---|---|
| Stored: `instances.symbols`, the instance API | `{name: {"value": <json>, "origin": <str>}}` | `{"total": {"value": 3012.89, "origin": "text"}}` |
| Rule code: `instance` and each entry of `others` | `{name: value}` | `{"total": 3012.89}` |

- Whatever writes `Instance.symbols` (ingestion, tests, a future endpoint) writes the stored shape. The model refuses anything else with a `ValueError`; an endpoint must turn that into a 422.
- `origin` keeps each value's provenance for the trace (ADR 0008, 0010). Rule code never sees it.
- The engine run, the impact check and the compiler's history check pass `flatten_symbols(instance.symbols)` to rule code.

### API

| Before | Now |
|---|---|
| header `X-Usuario-Id` | `X-User-Id` |
| header `X-Nombres-Repetidos` | `X-Duplicate-Names` |
| `/salud` | `/health` |
| `/yo` | `/me` |
| `/usuarios`, `/procesos`, `/reglas`, `/instancias` | `/users`, `/processes`, `/rules`, `/instances` |

### Invoice process data

The invoice process is data, but it is ours, so its names are English too. Only the decision names keep the challenge's spelling.

| Spanish | English |
|---|---|
| Pago de facturas | Invoice payment (`processes/invoice-payment.json`) |
| Gastos de viaje | Travel expenses (`processes/travel-expenses.json`) |
| REVISAR, RECHAZAR, APROBAR (travel expenses) | `REVIEW`, `REJECT`, `APPROVE` |
| nif_emisor, razon_social_emisor | `issuer_nif`, `issuer_name` |
| numero_factura, fecha, pedido | `invoice_number`, `date`, `purchase_order` |
| base, tipo_iva, cuota_iva, total | `base`, `vat_rate`, `vat_amount`, `total` |
| texto_libre | `free_text` |
| fuentes proveedores, pedidos, erp, parametros | `suppliers`, `orders`, `erp`, `parameters` |
| columnas razon_social, proveedor_id, importe_total, estado, fecha_pedido | `company_name`, `supplier_id`, `total_amount`, `status`, `order_date` |
| columnas asiento_id, importe, fecha_corte | `entry_id`, `amount`, `cut_off_date` |
| céntimos | cents |
| _instancia | `_instance` |
| procesos/reglas-v3/ (hand-written rule code), key `codigo` | `processes/rules-v3/`, key `code` |
