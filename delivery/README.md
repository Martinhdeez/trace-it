# delivery/

The three files the hackathon (hackathon.maisa.ai) expects in this folder, and nothing else.

| File | What |
|---|---|
| `outcomes.jsonl` | The first batch: one line per invoice PDF of `.context/500-sombras-de-alberto/facturas` |
| `outcomes_lote2.jsonl` | Saturday's batch: one line per invoice PDF of the batch-2 folder |
| `albertitos_plan.pdf` | The plan document, written by hand |

## The contract

One JSON object per line. `file_id` is the exact PDF name, `result` is `PAGAR`, `NO_PAGAR` or
`ESCALAR`. Any other top-level key is optional and ignored by the organisers' verifier.

```json
{"file_id": "2026-01-08_P001.pdf", "result": "PAGAR"}
```

## Regenerate

Needs the API of `make setup`, `make erp` and the batch PDFs (`docs/runbook-batch2.md`):

```bash
make delivery
```

It exports both batches through `python -m app.cli export` and checks both files. Overridable:
`DELIVERY_PACK=<pack.json>` (relative to `backend/`, the frozen pack by default),
`B1=<batch 1 PDFs>`, `L2=<batch 2 PDFs>`, `OUT1=<file>`, `OUT2=<file>`.

History is append-only: these files are only rewritten by a new export, never edited by hand.

## Validate

```bash
python3 tools/check_delivery.py delivery/outcomes.jsonl --files .context/500-sombras-de-alberto/facturas
```

Standard library only, no backend and no database. It fails on a line that is not a JSON
object, a missing or empty `file_id`, a `result` outside the three values, a duplicated
`file_id` and, when `--files` is given, on a name that is not a PDF of that folder or a PDF
with no line. It prints the count per result, and warns without failing about extra fields.

## The optional trace fields

`make delivery` exports with `--trace`, so every line also carries why the result is what it
is: the decision's reason, the rules that fired and the process version that decided it, so a
line can be followed back to its evidence through `make trace-decision FILE=<file_id>`. The
verifier ignores them.

Each `trace_url` identifies a document by its exact `file_id` within the process. The console
resolves the latest instance with that name, matching export's duplicate-name policy, so
recreating demo instances no longer invalidates these links. The link opens the current stored
case, not an archived execution: a document that has been removed shows "Documento no
encontrado", and it never selects another case silently. Existing numeric `?i=` links still
work while their original instance exists.

## The two batches are two process versions

Each line's `rules_hash` identifies the version that decided it. `outcomes.jsonl` is the rule
set frozen on 2026-09-19 for batch 1, untouched because a decision already taken is never
rewritten; `outcomes_lote2.jsonl` is the version published for batch 2, which adds the currency
policy the foreign invoices of that batch made necessary. Each of its lines carries the whole
trace (`export --full`), so the rule that decided, the rate applied and the arithmetic behind
it can be read without opening the console.

Each batch is decided in its own process, as it was for the original delivery, so the
duplicate-order check compares a batch with itself and an invoice is never escalated for
repeating the order of an invoice from the other batch.
