# ERP integration: analysis of Mateo's work and the live-source contract

Date: 2026-09-19. Author: Claude, for Martín. Scope: read-only analysis of Mateo's
(mateo19182) ERP/source work on `origin/dev`, `feat/process-chat` (PR #69, open) and
`feat/resilience-sources`, against the product owner's decisions of 2026-09-19 (ADR 0028).
Nothing in Mateo's code was changed; changes his code would need are proposals (last section).

## 1. What exists

**There is no natural-language "integrate any ERP" connector agent on `dev` yet.** Mateo's
commits on `dev` (#51, #56, #58, #66) and PR #69 build *process discovery*: an agent
(`backend/app/features/agents/discovery.py`, prompt `prompts/discovery.md`) that proposes a
whole process draft (decision types, symbols, sources, rules, examples) from uploaded
workbooks, loaded snapshots and a chat. PR #69's own docs say "conversational connector
generation ... outside this extension" (`docs/process-chat.md`). `feat/resilience-sources` is
Martín's (connectors found through the use case, LLM fallback chain), already merged as #45.

What the discovery agent does with sources:
- `SourceProposal` (`processes/draft_schemas.py`), three kinds:
  - `workbook`: a table mapping `{canonical_name: "Excel column letter"}` over a row range
    of an uploaded XLSX. The LLM **chooses the output field names**; ordinary code
    (`sources/discovery.py::materialize`) extracts the rows.
  - `snapshot`: rows of a source already downloaded into the draft
    (`POST /process-drafts/{id}/sources/{name}/sync`, `processes/drafts.py::sync`), which uses
    the **existing** `HttpConnector` with a configuration from the use case's
    `sources.json`. The agent can search those rows (`search_snapshot`) but cannot write or
    change a connector.
  - `constant`: literal rows approved with the proposal.
- On publication (`drafts.py::publish`) the materialised tables are appended as `Source` rows
  with origin `draft:<id>:revision:<n>`, and names omitted from the proposal get an empty
  load ("retired").

## 2. How the connector config is produced

By hand. `processes/invoice-payment/sources.json` (Martín, ADR 0013) holds one `http` source,
`erp`: base URL and credentials by environment variable, XML format, form-token auth,
page-number pagination, retries, rate limit, and `fields`, the mapping from the ERP's
element names to the names rules read (`"purchase_order": {"source": "pedido"}`, with
`decimal_comma` / `date_dmy` converters). `HttpSourceConfig` (`sources/http_connector.py`)
validates it strictly (`extra="forbid"`). No agent writes it. A process finds it through its
use case's pack (`sources/service.py::find_pack`).

## 3. Where the source schema is defined

Before this PR: nowhere as one contract. It was implicit in four places that had to agree:
- the connector's `fields` keys (`sources.json`) for `erp`;
- `sources/workbook.py::TABLES` for `suppliers` / `orders` (+ its own required columns);
- `tests/support/challenge.py::sources()` for the golden tests;
- the column names the compiler shows the agents (`compiler.context` lists the *current*
  snapshot's columns and three sample rows), so compiled rules read whatever names the last
  snapshot happened to have.

ADR 0028 adds `processes/<pack>/schema.json`: per source, `required` and `optional`
canonical fields and `sync_before_run`. For invoices: `erp` entry_id, date, supplier_id,
purchase_order, amount, status (+ nif optional); `suppliers` id, nif, iban; `orders`
purchase_order, total_amount, status; `parameters` cut_off_date. Documented in
`docs/sources-http.md`.

## 4. How rules read sources today

Contract `evaluate(instance, sources, others)`; `sources` is `{name: [row, ...]}`, the latest
load per name. The 16 hand-written rules (`processes/rules-v3/`) and the 12 frozen ones
(`processes/invoice-payment/frozen/2026-09-19/rules/`) read through a helper,
`rows(sources, "erp")`, then `row.get(...)`:

| Source | Keys read | Rules |
|---|---|---|
| `erp` | `purchase_order`, `status`, `amount`, `supplier_id`, `nif` | r13, r14, r15; frozen n5-1, n5-2 |
| `orders` | `purchase_order`, `supplier_id`, `nif`, `total_amount` | r05, r06, r07, r13, r14; n2-1..n2-3 |
| `suppliers` | `id`, `nif`, `iban` | r02, r03, r04, r06; n1-1, n1-2, n2-2 |
| `parameters` | `cut_off_date` | r12; n4-2 |

`compiler.read_keys` (the coder's output validator) only sees `x["k"]` / `x.get("k")` on the
second parameter, so it did not see the helper form. `compiler.source_reads` (this PR)
covers both and falls back to "every source" for anything it cannot resolve. It does **not**
check the row keys (`row.get("status")`): those are only constrained by the column list the
compiler prompt shows.

## 5. How a sync is stored and traced

- `sources/service.py::sync`: `HttpConnector.download()` returns every row or raises
  (`SyncError`); all-or-nothing, rows sorted by key, duplicate keys and short pages rejected.
- Append-only: each success is a new `Source` row (`origin =
  "erp:<ISO time>|<base url>"`); nothing is updated or deleted. The current load is the
  latest row per name (`current_loads`).
- `rows_hash` = sha256 of the canonical JSON of the rows, returned and put on the span (not
  stored on the row). `diff_latest` compares the last two loads by key.
- Trace: one `sync_source` span (ingestion plane) with connector stats (requests, pages,
  retries, logins, 429s, transient errors, timeouts, invalid values), origin, row count,
  `rows_hash`, diff summary, ERP status fields; on failure the span is `error` with the
  reason. A sync with changed rows triggers `alerts.after_source_load` (ADR 0026).
- Execution inputs (`versions/execution.py::capture`, Mateo's #66) record the `source_ids`
  used, so a decision replays against the exact snapshot.
- The draft sync (`drafts.py::sync`) writes no `Source` row: rows go into the draft revision
  as `snapshots[name]` with origin `discovery:<name>:<rows_hash>`, span `discover_source`.

## 6. Gaps against the contract (ADR 0028) and what this PR closed

| Contract | Before | Now |
|---|---|---|
| Sync before every run | Manual (`POST .../sync`, `make erp-sync`, `demo_run.py`) | `run` and `reprocess` sync live sources first; span under `run_process` / `reprocess` |
| ERP down: no stale snapshot | Failed sync left the previous snapshot "current"; runs used it | Down source's loads excluded from the execution inputs; `inputs.down` recorded; replay matches |
| Escalate only what depends on it | n/a | Rules reading a down source do not run; `SOURCE_UNAVAILABLE: erp` unless a rule that ran already rejects |
| Which rules read which source | Not known (`read_keys` blind to helpers) | `source_reads`, from code, for compiled, hand-written and frozen rules; `report.sources` on compile |
| Source down visible | Only an error span | `status: down` in `GET /sources`, ingestion plane `degraded`, `down_sources` in run/reprocess |
| Canonical schema | Implicit | `schema.json`; sync fails on an unmapped or missing required field |
| Draft/discovery sources validated | No | **Still no** (Mateo's code, proposal P1/P2) |

## 7. Risks

1. **Field-name drift between mappings and compiled rules (highest).** The discovery agent
   names workbook columns freely (`columns: {"order_ref": "A"}`); the compiler then shows
   those names to the coder, so a rule compiled in that draft reads `order_ref`. Later the
   live ERP (or another workbook) delivers `purchase_order`; the rule's `row.get("order_ref")`
   is always None and the rule passes silently: PAGAR where it should reject. The same
   happens when a published draft replaces `orders` with differently named columns under
   rules compiled earlier. Nothing fails; the golden would catch it only for the invoice pack.
2. **Discovery publication writes empty loads for omitted names.** With `erp` omitted from a
   proposal, publication appends an empty `erp` load; for a live source the next run syncs
   over it, but with `sync_before_run` off, every ERP rule reads `[]` and passes.
3. **A draft snapshot named like a live source.** A `snapshot` proposal named `erp`
   publishes a frozen copy (`draft:...`) that the next run immediately replaces by a sync;
   the backtest in the preview used the draft copy, not what will run.
4. **Row keys are unchecked.** `source_reads` knows the *source* a rule reads, not the
   *fields*. A rule reading a field outside the canonical schema is not rejected at compile
   time.
5. **Status from spans.** A source's `down`/`ok` status is read from the latest
   `sync_source` span; pruning `events` would lose it.
6. **Latency.** Every run waits for the ERP (5 s up; about 15 s to give up when unreachable,
   `retry.max_attempts` x backoff). Acceptable for batches; tune `retry` in `sources.json`.

## 8. Proposals for Mateo (not implemented; his code)

- **P1. Validate proposals against the canonical schema.** In `discovery.validate`
  (the agent's output validator) and in `draft_compilation`/`drafts.prepare`: a
  `SourceProposal` whose `name` is in the pack's `schema.json` must map every `required`
  field, and only canonical or declared-optional names (`sources.load_schema(pack)[name]`,
  `sources.nonconforming(rows, schema, key)` on the materialised rows). Raise `ModelRetry`
  in the agent, `ConflictError` at prepare. Give the agent the schema in its prompt
  (`prompts/discovery.md`) so it maps to it instead of inventing names.
- **P2. Validate the draft sync.** `drafts.py::sync` should call `sources.sync`'s checks:
  simplest, `sources.nonconforming(rows, schema, config.key)` after `connector.download()`,
  and fail like a live sync. Today a draft can load a non-conforming ERP snapshot and
  backtest against it.
- **P3. Never publish a live source as a static load.** In `drafts.py::publish`, skip names
  whose schema entry has `sync_before_run` (the next run syncs them), and do not append an
  empty "retired" load for them.
- **P4. Show the compiler the schema, not the snapshot.** `compiler.context` lists the
  current snapshot's columns; list the canonical fields from `schema.json` (with the sample
  rows) so compiled code reads canonical names even when the snapshot is incomplete.
  Optionally extend the coder's `_allowed` check to row keys read from canonical sources.
- **P5. If a connector-generation agent is built**, its output is a `HttpSourceConfig` whose
  `fields` keys are exactly the canonical names: validate with
  `HttpSourceConfig.model_validate` plus `set(schema.required) <= fields.keys()` (what
  `sources.sync` now checks), and a dry download through `nonconforming` before saving it to
  `sources.json`. No change to the engine or rules is needed for a new ERP.
