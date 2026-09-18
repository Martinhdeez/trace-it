# Ingestion API

Use `app.main:app`. Its `/health` remains `{"status":"ok"}`.
The combined contract is in `/docs`, `/redoc` and `/openapi.json`.
Ingestion uses the existing `X-User-Id` header obtained through `POST /login`.

## Extraction

`POST /v1/extractions`: multipart `file`, optional `ocr=true`, `vlm` and `jev`.
No business fields are required as input.

```powershell
curl.exe http://127.0.0.1:8000/v1/extractions -H "X-User-Id: 1" -F "file=@invoice.pdf"
```

The response contains `id`, `file_id`, `sha256`, `kind`, `fields`, `text`,
`data`, `warnings`, `pages`, `metrics`, `pipeline_version` and `cache_hit`.
There is no document `status`, `review` or required-field completeness gate.

Invoice fields expose `value`, `text`, `selected_by`, `agreeing_readers`,
`confidence` and `candidates`. The value is the best available normalized reading,
not a verified business fact, and may come from a single reader.
Raw text remains available when normalization fails. No reading means `null`, not an error.
Confidence is an available OCR score, not a calibrated probability. Supporting readers
are actual readers, not extra votes inferred from Jev's textual selection.

Candidates retain original text, method, page, region and normalized proposals.
Document-level `text` retains reader-labelled full transcriptions.
`data` contains processing evidence, committee metadata or workbook sheets/cells.
Workbook cell diagnostics do not impose workflow states.

`GET /v1/extractions/{id}` retrieves a persisted result. Identical content with another
filename reuses processing while retaining document identity. Re-upload historical
documents for the v2 contract; versioned cache keys prevent reuse of the old policy.

## Process upload

`POST /processes/{process_id}/files` accepts a PDF and the same options.
The 201 response includes `instance_id`, `process_id`, `name`, `file_hash`,
`created`, the existing instance `status`, and `extraction`.

Original bytes/text are stored in PostgreSQL. New instances are `PENDING` with no approved
symbols. Missing readings never change this to `REVIEW`. Re-uploading the same process,
filename and content preserves the instance and any existing downstream decisions.

`GET /instances/{instance_id}/document` retrieves the latest extraction from PostgreSQL
events independently of the local cache. Use `/v1/extractions` to inspect XLSX.
Mapping readings to configurable symbols or workbook data to source snapshots is separate.

## Batches and errors

`POST /v1/batches` accepts multipart `files` and returns 202.
`GET /v1/batches/{id}` reports jobs: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`.
These are execution states, not document completeness states. Missing fields do not fail jobs.

Unknown identifiers return 404; unsupported/corrupt/oversized files 422; internal failures 500.
Application errors follow `{"code":"invalid_document","message":"..."}`; FastAPI parameter
validation may return `detail`. The standalone local API has no authentication.
