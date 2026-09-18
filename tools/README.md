# tools — a stand-in, on purpose

These scripts do what `features/ingestion` and `features/extraction` will
do for real. They exist so the whole process can be run end to end today, over the real
corpus, and so there is a baseline to hold the real ones against. They are not imported by
the application and they go away when those features land.

| File | Stands in for |
|---|---|
| `workbook.py` | reading the spreadsheet: header mapping to the names the rules use, and JSON-safe values. The ERP needs nothing here: `features/sources` has a real connector for it |
| `extractor.py` | reading an invoice's symbols, from the PDF text layer and with no model |
| `demo_run.py` | the driver: load the spreadsheet and the invoices, then call the application's own API to sync the ERP, decide and export |

## Running it

```bash
make erp            # in another terminal: the bridge must be up
make demo
```

`make demo` loads the pack, activates its rules, ingests the corpus and writes
`output/outcomes.jsonl` plus `output/detail.json` (per invoice: the symbols read and which
rules fired). It needs `pdftotext` (`poppler-utils`).

## What it is worth knowing

- The extractor reads **all 471** invoices that have a text layer, and **none of the 29
  scans** — those have no text at all and need OCR or vision. An invoice without symbols is
  escalated by the rules, which is the honest answer, not a failure of the run.
- Two things here will matter just as much in the real loaders: sources must map their
  columns to the names the rules use (`ProveedorID` -> `supplier_id`), and every value
  must be JSON-safe, because sources are JSONB and the sandbox serialises each case.
- This corpus hides zero-width characters inside an IBAN. Anything that does not strip them
  reads that IBAN as something else and escalates the invoice.
