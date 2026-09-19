# Current invoice outcomes

Use [`ocr-current/outcomes.jsonl`](ocr-current/outcomes.jsonl) for the current
500-invoice corpus. [`ocr-current/summary.json`](ocr-current/summary.json) records
the extraction version, pinned OCR models, source hashes and outcome counts.

The export is generated through the production workbook/PDF upload, process
publication, run and export endpoints, with a fresh process and extraction store.
It uses the evaluated Latin OCR reader plus the server verifier, Gemini visual
corroboration and Jev candidate selection. Python rules determine the outcomes.
The ERP snapshot and cut-off date are frozen for comparison with previous runs.

The current result is **443 PAGAR, 36 NO_PAGAR and 21 ESCALAR**, using
`invoice-v2.2.0+xlsx-v1.3` and the default 16-rule invoice pack. All 500 API decisions
match the independent evaluator plus the current [scan policy](../../docs/adr/0025-scan-decision-policy.md).
That policy explains all 13 changes from the previous improved export. All 4,239
compared fields in the 471 text PDFs are unchanged. The prior visual reference
detects no accepted field errors; two previously documented missing-field coverage
losses remain on already escalated documents. See
[`validation.json`](ocr-current/validation.json) for the comparison.

All 500 documents were first reread with empty local and provider caches. After
the scan policy landed on `dev`, a second fresh process/store reused only that
content-addressed reader evidence, rebuilding symbols and decisions with the new
policy. No old decisions were copied. Reader failures remain in the summary and
uncertain scan data is escalated.

The six older OCR outputs previously committed here have been superseded. They
remain in Git history at `f940e3c`; the reviewed variant was a separate visual
audit, not an automatic OCR result. `demo-logs/` contains historical demonstrations.

## Regeneration

Follow [the OCR setup guide](../../docs/ingestion/setup.md), then use a migrated,
isolated PostgreSQL database via `TRACE_DATABASE_URL`. From `backend/`:

```text
uv run --env-file ../.env python -m evals.refresh_outcomes --invoices ../.context/500-sombras-de-alberto/facturas --book ../.context/500-sombras-de-alberto/FINAL_v7_DEFINITIVO_ahorasi.xlsx --erp-snapshot <erp-snapshot.json> --output reports/new-run --cutoff 2026-09-19
```

Use the same ERP snapshot SHA-256 recorded in the summary for a like-for-like
comparison. The helper requires the verified model profile and refuses to reuse
an output directory containing previous extraction data. It records detailed
evidence locally. When only decision policy changes, `--reader-cache-from <data>`
can reuse reader journals/caches whose image, model and implementation identities
match; it never copies the extraction database or decisions.
Review changed decisions and reader failures before replacing
the shared export. Provider output can vary between fresh runs; matching the
configuration does not establish accuracy against the challenge's private answers.
