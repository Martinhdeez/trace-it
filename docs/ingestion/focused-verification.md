# Focused OCR verification

This document describes the historical `invoice-v2.1.4` evaluation. The refreshed
export and its actual extraction version are in
[`backend/reports/ocr-current/`](../../backend/reports/ocr-current/); use that
directory for the current shared outcomes.

Pipeline `invoice-v2.1.4+xlsx-v1.3`, evaluated on the 500 PDFs and workbook on
19 September 2026. The implementation improves accepted readings and decisions,
with an explicit coverage tradeoff: two previously correct fields become proposals
without confirmation. Their documents were already escalated.

## Reader policy

Unresolved NIF, IBAN and purchase-order fields trigger bounded crops at 150 and
600 dpi, measured deskew and local/visual corroboration. Changing the scale of the
same recognizer does not create an independent reader. A text-only judge can propose
an existing candidate; it cannot confirm pixels. `value` holds confirmed identifiers;
`proposed_value`, alternatives and original-page coordinates preserve the evidence.

When local detection fails and periodic scanner bands are measurable, a bounded
geometric transformation removes the column displacement before another local read.
It resamples existing pixels; no generative restoration or master-data replacement
supplies missing characters. Provider errors remain visible and prevent a complete
extraction cache entry. The provider journal still prevents automatic resends after
uncertain delivery.

The production process API calls `extract_for_payment`: supplier, order and ERP
mismatches select fields for at most one additional extraction. Only field names
reach the readers, never expected values. Both results and the source snapshot IDs
are retained. See [the integrated API](api.md) for workbook/PDF upload, pending
re-extraction, deterministic execution and export.

## Corpus comparison

The original and candidate runs use identical document hashes, workbook data,
frozen ERP rows, 16 rules and the cut-off date 2026-09-19. Repeated deterministic
execution is identical; all 500 decisions also match the independent golden evaluator.

| Outcome | Before | After |
|---|---:|---:|
| PAGAR | 450 | 451 |
| NO_PAGAR | 45 | 41 |
| ESCALAR | 5 | 8 |

| Case | Change | Assessment |
|---|---|---|
| scan_010 | NO_PAGAR -> PAGAR | The IBAN digit 5 is recovered by stable local readings and a corroborating visual crop. |
| scan_004 | NO_PAGAR -> ESCALAR | The user confirmed 2026. Automatic readers still disagree, so 2028 is withheld; the year is not yet reliably recovered. |
| copia_2026_0518 | NO_PAGAR -> ESCALAR | Obscured identifiers cannot justify the previous definitive rejection. |
| scan_023 | NO_PAGAR -> ESCALAR | Blurred identifiers remain unconfirmed. |

The other 496 decisions are unchanged. All 4,239 compared fields of the 471 native
PDFs are unchanged. Workbook sheets, cells, formulas and records are unchanged apart
from execution metadata. The geometric correction preserves scan_022's complete
NIF, IBAN and order; six source-triggered rechecks preserve their decisions.

The two known accepted field errors become zero: one is corrected, the other withheld.
This is not the same as reading both correctly. The fax's order and scan_017's IBAN
lose confirmation but remain available as proposals. `field_coverage_losses` lists
both cases and `no_regression_on_all_metrics` is explicitly false.

## Evidence and reproduction

The local ignored `backend/reports/ocr-improved-20260919/` directory contains
`extractions.jsonl` (501 documents), `symbols.jsonl`, `decisions.jsonl`, `outcomes.jsonl`
(500 cases), `comparison.jsonl` (individual comparisons), `comparison-summary.json`,
`source-rechecks.json` and test logs. Documentary data and provider journals are not
committed to Git. The comparison can be repeated offline from `backend/`:

```powershell
.venv/Scripts/python.exe -X utf8 -m evals.ocr_regression --baseline reports/ocr-advanced-20260919 --candidate reports/ocr-improved-20260919
```

This evaluation helper is not an application dependency. The actual ingestion,
source loading, symbol mapping and decisions run through backend feature services
and their HTTP endpoints. The evaluation uses the current dev engine's single-code
rule contract, and compares its results with the separate golden evaluator.

The visual reference is the assistant's prior multimodal review, including explicit
uncertainty and the user's correction for scan_004; it is not the private official
ground truth. This is the development corpus, not an unseen validation set. Existing
provider responses are replayed from the journal to control variability. Elapsed
time does not establish a speed improvement.

Final extraction counters increase from 58 to 147 OCR calls and 28 to 59 visual calls;
Jev stays at 18. These include journal replays and do not separately count the payment
adapter's initial extraction. They are not billed-request or monetary-cost measurements.
Difficult documents require more processing. No payments or ERP updates were performed.

## Verification

Tests cover disputed years without hardcoding 2026, IBAN recovery, correlated readers,
text-only proposals, image limits, page separation, geometric correction, HTTP options,
cache failure handling and source-triggered rechecks without answer leakage. API tests
exercise workbook/PDF upload, stored symbols, real sandbox rules, JSONL export, invalid
printed dates, immutable history, pending re-extraction and atomic workbook validation.
The API follows the current dev migrations and use-case model without adding a migration.

Full checks run against a disposable PostgreSQL database. On Windows, Psycopg uses
`WindowsSelectorEventLoopPolicy`; Python runs with `-X utf8` for Poppler. OCR API corpus
and test evidence is stored in `backend/reports/ocr-api-integration-20260919/`.

The integration run uploaded the workbook and all 500 PDFs through the production
endpoints, activated the existing 16 rules, ran the process and exported JSONL.
All 500 exported decisions match the comparison above; a second run decided zero
additional instances. External ERP evidence was the frozen real HTTP snapshot;
existing provider responses and extraction caches were reused.

After integrating the latest norm-normalizer and console endpoints, the full suite
passed 321 tests (one skipped known-mismatch placeholder, two LLM tests excluded),
including the concurrent-run regression. The API corpus was rerun with identical
500-case outcomes. Ruff, format checks and OpenAPI operation-ID validation pass.
No additional database migration was needed; the tests used the current dev
migrations 0001 through 0005. Workbook loads and document re-extractions appear
in the process-level event feed alongside the existing console events.
