# Extraction validation

Current reading accuracy and limitations are recorded in the [full audit](corpus-audit.md).
The integrated dev application passed **263 tests**, with one skipped and one LLM test
deselected, using an isolated PostgreSQL 16 database on Windows. Ruff lint and formatting
passed. Async tests used the Selector event loop and UTF-8 mode. Two Starlette test-client
deprecation warnings remain.

Coverage includes mixed PDFs, corrupt inputs, limits, concurrent cache reuse, job recovery,
provider failures, ambiguous amounts, identifiers without digit repair, missing currency,
uncached formulas, conflicting headers and incorrect workbook dimensions. Process API tests
cover PostgreSQL originals/evidence, retrieval without SQLite, idempotence, preserved
decisions and no review transition for missing fields.

## Historical performance

These measurements belong to `invoice-v1.7.1+xlsx-v1.3`, not the current contract:

| Check | Result |
|---|---|
| Inputs | 500 PDFs and one XLSX |
| Native PDFs | 471 without OCR |
| Scans | 29 primary and 15 verification readings |
| Cold run | 142.028 seconds; 3.53 files/second |
| Cached run | 7.341 seconds; 68.25 files/second; 501 cache hits |
| Former states | 299 COMPLETE, 202 NEEDS_REVIEW; no failed jobs |
| Independent native check | No detected reviewed-field differences |
| Workbook | 14 sheets; 3,193 XML cells and 3,124 canonical fields checked |
| Provisional scan comparison | 254/283 matching readings; four incorrect OBSERVED values |

The four historical accepted errors were in `scan_013.pdf` (NIF, order, VAT amount)
and `scan_017.pdf` (date). These references were provisional. Later abstention and
committee policies changed coverage. See [historical abstention](abstention.md).

Measurements were individual CPU runs on Windows 11/Python 3.12.13, four ONNX threads
per session and one OpenCV thread. Peak memory and sustained load were not measured.
[benchmark-summary.json](benchmark-summary.json) retains the historical summary.

## Reproduce

From `backend/`, with the challenge submodule, OCR weights and Poppler:

```powershell
uv run python -m app.features.ingestion.tools.benchmark ../.context/500-sombras-de-alberto --output reports/cold
uv run python -m app.features.ingestion.tools.review_corpus ../.context/500-sombras-de-alberto reports/cold/files.jsonl --output reports/review
uv run python -m app.features.ingestion.tools.evaluate_scans --extractions reports/cold/files.jsonl --output reports/scans
```

Use a new `TRACEPAY_DATA_DIR` for a cold run. Detailed results remain outside Git.
These tests do not replace independent human references or the private payment validator.
