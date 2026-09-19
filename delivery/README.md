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

`make delivery` asks the export for the trace fields when the CLI supports them (`--trace`);
without that flag it writes the minimal `file_id`/`result` export and says so. They carry, per
invoice, why the result is what it is: the decision's reason, the rules that fired and the
process version that decided it, so a line can be followed back to its evidence through
`make trace-decision FILE=<file_id>`. The verifier ignores them.
