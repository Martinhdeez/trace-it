# tools: demo stand-ins, on purpose

The application now ingests PDF/XLSX through its production API, including OCR
and visual verification. These scripts retain the original text-layer baseline
for comparison; they are not imported by the application. To reproduce the
complete OCR run, follow the [ingestion setup guide](../docs/ingestion/setup.md).

| File | Stands in for |
|---|---|
| `workbook.py` | reading the spreadsheet: header mapping to the names the rules use, JSON-safe values. The ERP needs nothing here: `features/sources` has a real connector for it, driven by `processes/invoice-payment/sources.json` |
| `extractor.py` | reading an invoice's symbols from the PDF text layer, with no model |
| `demo_run.py` | the driver: stores the spreadsheet sources and the invoices (one `File` and one `Instance` per PDF, symbols with `origin: "pdf-text"`), then calls the application's own API: sync the ERP, run, export |

## Running it

```bash
make erp            # in another terminal: the ERP must be up
make demo
```

`make demo` loads the pack, activates its hand-written rules (`load --activate`), ingests the 500 PDFs and writes `output/outcomes.jsonl` plus `output/detail.json` (per invoice: the decision, the reasons of the rules that fired, the symbols). It needs `pdftotext` (`poppler-utils`). Result: PAGAR 433 / NO_PAGAR 36 / ESCALAR 31, identical to the golden (`backend/tests/golden/`) on all 471 text PDFs; the engine runs in about a second. `--limit N`, `--cutoff`, `--output` are options of `demo_run.py`.

## Worth knowing

- The extractor reads all 471 invoices that have a text layer and none of the 29 scans, which have no text at all and need OCR or vision. A scan is stored with no symbols, so rule R01 escalates it: the honest answer, not a failure of the run.
- Two things here will matter just as much in the real loaders: sources must map their columns to the names the rules use (`ProveedorID` -> `supplier_id`), and every value must be JSON-safe, because sources are JSONB and the sandbox serialises each case.
- This corpus hides zero-width characters inside an IBAN. Anything that does not strip them reads that IBAN as something else and rejects the invoice.
