# Ingestion API

Use `app.main:app`. Its `/health` remains `{"status":"ok"}`.
The combined contract is in `/docs`, `/redoc` and `/openapi.json`.
Ingestion uses the existing `X-User-Id` header obtained through `POST /login`.

## Extraction

`POST /v1/extractions`: multipart `file`, optional `ocr=true`, `vlm`, `jev` and
repeated `verify_fields` (`supplier_tax_id`, `payment_iban`, `purchase_order_ref`).
The last option requests a bounded blind rereading; it never accepts expected values.
No business fields are required as input.

```powershell
curl.exe http://127.0.0.1:8000/v1/extractions -H "X-User-Id: 1" -F "file=@invoice.pdf"
```

The response contains `id`, `file_id`, `sha256`, `kind`, `fields`, `text`,
`data`, `warnings`, `pages`, `metrics`, `pipeline_version` and `cache_hit`.
There is no document `status`, `review` or required-field completeness gate.

Invoice fields expose `value`, `proposed_value`, `proposed_by`, `verification`,
`verification_reason`, `text`, `selected_by`, `agreeing_readers`, `confidence` and
`candidates`. In `invoice-v2.1.4+xlsx-v1.3`, NIF, IBAN and purchase order require
clear native evidence or reader corroboration for `value`; an unresolved conflict
returns `value=null` and preserves `proposed_value` and candidates. Jev can propose
an existing reading but cannot verify these identifiers. `selected_by=null` when
no value is accepted. The other fields retain the best-reading v2.0 policy.
Verification concerns transcription, not business validity: a clearly printed IBAN
that differs from the master remains a document observation for the rules to reject.
Raw text remains available when normalization fails. No reading means `null`, not an error.
Confidence is an available OCR score, not a calibrated probability. Supporting readers
are actual readers, not extra votes inferred from Jev's textual selection.

Candidates retain original text, method, page, region and normalized proposals.
Document-level `text` retains reader-labelled full transcriptions.
`data` contains processing evidence, committee metadata or workbook sheets/cells.
`data.focused_verification` records crop bounds, reader candidates, transformations,
reader failures and the verification reason. Historical committee warnings describe
the earlier whole-page stage; use the field's final `verification` for its final state.
Workbook cell diagnostics do not impose workflow states.

`GET /v1/extractions/{id}` retrieves a persisted result. Identical content with another
filename reuses processing while retaining document identity. Re-upload historical
documents for the v2 contract; versioned cache keys prevent reuse of the old policy.

## Process upload

`POST /processes/{process_id}/files` accepts a PDF and the same options.
The 201 response includes `instance_id`, `process_id`, `name`, `file_hash`,
`created`, the existing instance `status`, `extraction` and stored `symbols`.

Original bytes/text are stored in PostgreSQL. New instances are `PENDING`. Processes
declaring the invoice-payment symbols (`issuer_nif`, `iban`, `purchase_order`, `date`,
`base`, `vat_rate`, `vat_amount`, `total`) automatically receive document-derived symbols
in the current dev format: `{name: {value, origin}}`. Other processes keep `symbols=null`;
their business vocabulary is not guessed. Missing readings never create a REVIEW state.
Re-uploading the same process,
filename and content preserves the instance and any existing downstream decisions.

`GET /instances/{instance_id}/document` retrieves the latest extraction from PostgreSQL
events independently of the local cache. The process upload calls the
`extract_for_payment(service, item, options, sources)` adapter, which checks the
invoice-payment `suppliers`, `orders` and `erp` snapshots and requests at most one
additional extraction for discrepancies not already reread. It returns both result
IDs and trigger field names. PostgreSQL events retain both readings when a source
discrepancy triggers another extraction, along with the exact source snapshot IDs.
Source values never enter OCR prompts. The adapter maps `fields[*].value` to rule
symbols and leaves unresolved identifiers null; it never promotes `proposed_value`.
Impossible printed dates retain their components (31/02/2026 -> 2026-02-31) so the
existing invalid-date rule can reject them. Amounts remain exact decimal strings.

`POST /instances/{instance_id}/extract` accepts a JSON `ExtractOptions` body (`{}`
uses defaults). It reads the original PDF again with the latest snapshots and fills
symbols for a supported pending instance, including uploads predating this integration.
It appends an `extract_document` event. It returns 409 once the instance is decided.
Extraction and `/run` lock pending instances so re-extraction cannot overwrite the
evidence of a concurrently completed engine decision.

## Workbook sources and decision flow

`POST /processes/{process_id}/sources/workbook` accepts multipart XLSX `file` and
optional ISO `cut_off_date`. The invoice adapter maps recognized supplier and order
tables into new `suppliers` and `orders` snapshots. A supplied date adds a `parameters`
snapshot; an omitted date leaves the existing parameters untouched. No clock-based
date is invented. Missing required rows/fields reject the upload atomically with 422.
Conflicting supplier rows remain separate for the existing master-conflict rule.
Unsupported process schemas return 409. Workbook ledger sheets never overwrite ERP.

The 201 response contains `process_id`, `file_hash`, `extraction_id`, `sources`
(`id`, `name`, `rows`) and extraction `warnings`. Original bytes and complete workbook
evidence are retained in PostgreSQL. `/v1/extractions` remains available for inspection.

The standard application flow is:

1. Load the process pack and activate its approved rules using the existing CLI/API.
2. Upload the workbook and set the policy cut-off date through the new source endpoint.
3. Call the existing `POST /processes/{id}/sources/erp/sync`.
4. Upload PDFs to `POST /processes/{id}/files`; verified symbols are stored immediately.
5. Call `POST /processes/{id}/run`, then `GET /processes/{id}/export` for JSONL.

Upload the complete batch before `/run` so duplicate-order rules see all its instances.
After source changes, explicitly re-extract affected pending documents before running
them. The decision engine always uses the current active rules and current snapshots.
Previously decided instances and their exports are never changed by re-uploading.
No `tools/` module or evaluation script participates in this application flow.

## Batches and errors

`POST /v1/batches` accepts multipart `files` and returns 202.
`GET /v1/batches/{id}` reports jobs: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`.
These are execution states, not document completeness states. Missing fields do not fail jobs.

Unknown identifiers return 404; unsupported/corrupt/oversized files 422; internal failures 500.
Application errors follow `{"code":"invalid_document","message":"..."}`; FastAPI parameter
validation may return `detail`. The standalone local API has no authentication.
