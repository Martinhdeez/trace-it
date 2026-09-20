# Document ingestion

**New machine:** follow [Reproduce the OCR and ingestion setup](setup.md) for
prerequisites, the two pinned OCR readers, API keys, Docker/standalone startup,
scan checks and the full production API flow on Windows or Linux/macOS.

Choose [local, API or hybrid execution](providers-and-modes.md), configure Helmcode
fallbacks, and inspect usage/cost/latency through the same operator guide. The
[500-document benchmark](benchmark-2026-09-19.md) records measured baseline quality
and timings separately from the later Helmcode probe.

The API returns as many field readings as it can from PDF, JPG/JPEG, PNG, HTML and XLSX. Missing or conflicting
fields retain available text and alternatives, without document review states.
NIF, IBAN and purchase order separate verified transcriptions from proposals;
see [focused verification and measured tradeoffs](focused-verification.md).
For cache dependencies, pending-document refresh and the difficult scans, see
[OCR reuse and quality](cache-and-quality.md).
For native columns, table cells, spacing diagnostics and the comparison gate, see
[Native PDF layout and quality](native-layout.md).

Use the main API, `uv run uvicorn app.main:app --env-file ../.env --workers 1`, from
`backend/`. Follow the [team setup](../team-guide.md) for PostgreSQL and users.
Ingestion routes use dev's `X-User-Id` header.

For isolated local extraction without PostgreSQL, use
`uv run uvicorn app.features.ingestion.application:create_app --factory --workers 1`.
The standalone application has no authentication.

Download pinned weights once with
`uv run python -m app.features.ingestion.tools.download_models`.
The included ONNX runtime uses CPU. Native PDFs and Excel need no OCR weights.

Docker Compose mounts the downloaded root `.models` directory read-only and keeps jobs,
results and provider journals in the `ingestion_data` volume. `make reset-db` removes
Compose volumes, including this local extraction data; PostgreSQL stores attached originals
and evidence separately. Download weights on the host before using local OCR in Docker.

## Images and HTML

Images use the same configured local/API/hybrid OCR readers, verification policy and
process field mapping as scanned PDFs. EXIF orientation is applied and transparent pixels
are flattened onto white for reading. The original bytes and SHA-256 remain unchanged.

HTML uses native text, tables and text-input values without OCR. A sanitized, paginated
view provides stable coordinates for the existing field evidence viewer. Scripts, styles,
hidden content and external resources are excluded; no browser or JavaScript is executed.
Pages whose contents require JavaScript or embedded images must be supplied as PDF/JPG/PNG.
HTML originals download as attachments with sandbox and nosniff headers. Configured semantic
field mapping may still read the extracted text for custom process schemas.

This support applies to process uploads, the console and standalone extraction/batches.
Mail reception retains its existing PDF attachment filter. Synthetic tests cover format
validation, OCR routing, table fields, byte-exact downloads, duplicate uploads and evidence;
real-world image accuracy still depends on document quality and the configured readers.

## Pipeline

Preserve originals by SHA-256; validate; read native text; run both local recognizers on
pages needing OCR; consult configured visual and textual providers; return readings and
evidence. The second recognizer runs even when the first extraction is incomplete.
Process uploads also populate declared invoice-payment symbols from these readings;
the existing `/run` and `/export` endpoints then execute the active rules and return
JSONL. Workbook reference tables can be loaded through the source-upload API.
See the [complete application flow](api.md#workbook-sources-and-decision-flow).

The invoice adapter extracts invoice number, supplier NIF, IBAN, purchase order, date,
base, VAT rate/amount, total and currency. Amounts are decimal strings.
By project convention `$` means USD; absent currency is not assumed to be EUR.
Excel preserves sheets, cells, formats, formulas and stored results. It never executes
formulas or converts an unavailable formula result into zero.

## Configuration

| Variable | Default or purpose |
|---|---|
| `TRACEPAY_OCR_MODE` | `hybrid`; choose `local` or `api` explicitly |
| `TRACEPAY_VISION_PROVIDERS` | `compatible,gemini,helmcode`; configured entries only |
| `TRACEPAY_TEXT_PROVIDERS` | `jev,helmcode`; candidate recommendations only |
| `HELMCODE_API_KEY` | Optional OCR fallback and separately configured rule agents |
| `TRACEPAY_HELMCODE_VISION_MODELS` | `qwen3.6,gemma4`; distinct visual readers |
| `TRACEPAY_HELMCODE_TEXT_MODEL` | `qwen3.6` |
| `TRACEPAY_PROVIDER_TIMEOUT_S` | 60 seconds per attempted provider request |
| `TRACEPAY_HELMCODE_BILLING_MODE` | `unknown`; select `included` or `metered` with verified account terms |
| `TRACEPAY_DATA_DIR` | `.data`: objects, SQLite results/jobs and journals |
| `TRACEPAY_MODEL_DIR` | `.models`: pinned ONNX weights |
| `TRACEPAY_WORKERS` | 2, bounded to 1–8 |
| `TRACEPAY_OCR_THREADS` | 4, bounded to 1–16 |
| `TRACEPAY_OCR_CUDA` | 0; GPU needs a compatible ONNX runtime |
| `TRACEPAY_OCR_FORCE_RECOMPUTE` | 0; 1 ignores extraction/OCR caches and the provider journal (spans say `outcome=forced`) |
| `TRACEPAY_VLM_URL`, `TRACEPAY_VLM_MODEL`, `TRACEPAY_VLM_API_KEY` | Compatible visual server |
| `GEMINI_API_KEY` | Gemini in the configured visual chain |
| `TRACEPAY_GEMINI_MODEL` | `gemini-3.1-flash-lite` |
| `TYPESAFE_API_KEY` | Jev textual selection |
| `TRACEPAY_JEV_MODEL` | `jev-1.13.0` |

Omit `vlm`/`jev` upload options to permit configured providers when needed; `false`
disables them. Without keys, extraction stays local. The library reads environment
variables; Uvicorn's `--env-file` loads the root `.env`.

## Limits

25 MiB per file, 40 PDF/HTML pages, 100 files per batch. XLSX: 200 MiB uncompressed, 2,000 ZIP
members, 500,000 cells, 25,000 rows and 100 columns per sheet. Encrypted/corrupt documents
are rejected. Process documents accept PDF, JPG/JPEG, PNG and HTML/HTM. XLSX remains a reference-source
format; XLS, CSV and other image formats are not supported. Images are limited to 18 million
pixels before decoding. HTML is limited to 100,000 elements and 256 nesting levels.

One Uvicorn process per data directory, enforced by a lock. Workers and OCR threads are
bounded; MuPDF calls are serialized. SQLite jobs recover after restart. Cache identity
includes content, options, configuration and pipeline/model versions.

Provider failures preserve available evidence. Journals prevent resending requests whose
delivery is uncertain; inspect them before a deliberate retry. Journals contain document
data and stay outside Git.

The implemented evidence and provider-tracing contract is recorded in
[ADR 0022](../adr/detail/0022-ocr-evidence-and-provider-tracing.md). Follow the
[trace API guide](api.md#tracing-readers-and-provider-usage) to inspect a document's
model calls and distinguish network usage from saved responses. The
[fal.ai review](fal-fallback.md) evaluates possible additional visual readers;
[ADR 0023](../adr/detail/0023-fal-visual-fallback-evaluation.md) records that proposed extension.

See [API](api.md), [committee](committee.md), [integration](architecture.md),
[audit](corpus-audit.md) and [validation](extraction-validation.md).
