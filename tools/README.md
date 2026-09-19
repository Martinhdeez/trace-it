# Demo and corpus helpers

`demo_run.py` is an HTTP client for the running production backend. It uploads
the challenge workbook, syncs the ERP, uploads each invoice PDF with `ocr=true`,
runs the active invoice rules, and exports the outcomes. Scanned PDFs use the
same local OCR readers and optional visual/Jev providers as any API upload.
The older `extractor.py` and `workbook.py` remain as text-layer comparison tools;
the demo does not use them.

| File | Purpose |
|---|---|
| `demo_run.py` | Drive the invoice process through the production HTTP API |
| `hiring_mock.py` | `make hiring-data`: the hiring-screening mock data (CVs, workbook, answer key), deterministic |
| `hiring_demo.py` | `make hiring-demo`: a hiring process born from discovery, then the CV batch and a learning round; writes an evaluation report ([the experiment](../processes/hiring-screening/README.md)) |
| `trace_decision.py` | `make trace-decision FILE=<file_id>`: one invoice's state, decisions, evidence, latency, errors, retries and pending work, as text |
| `workbook.py` | Historical spreadsheet mapping helper for the text-layer baseline |
| `extractor.py` | Historical PDF text-layer extractor and regex symbols, without OCR |

## Run the demo

From the repository root, follow the [OCR setup guide](../docs/ingestion/setup.md)
to download both OCR model profiles into `.models/` and configure `.env`. Then:

```bash
make setup                  # Docker backend, database, migrations and process pack
make activate MANAGER_ID=1  # publish the hand-written rules (1: the seeded manager)
make erp                    # leave the challenge ERP running in another terminal
make demo              # 500 invoices -> output/outcomes.jsonl and detail.json
```

The API defaults to `TRACEPAY_OCR_PROFILE=verified`: startup verifies the evaluated
weight/dictionary hashes and requires the configured Gemini/Jev model IDs and keys.
`make setup` installs those weights and checks that profile. For explicit local-only
experiments, set `TRACEPAY_OCR_PROFILE=experimental` before starting the backend.
The current shared corpus export is linked from [the reports index](../backend/reports/README.md).

`make demo` runs the published rules; without `make activate` the run answers 409.
The API must be reachable
at the host port configured by `BACKEND_PORT` (8000 by default), and the backend
must reach the ERP on port 8009. The demo uses the pack's seeded manager account.
The workbook is uploaded before the PDFs; all PDFs are uploaded before the engine
runs, so duplicate checks see the full batch. A scan is sent to production OCR;
provider failures appear in the upload's extraction warnings and can leave
fields unresolved. For reproducible counts, use a fresh process/database:
uploading an already decided invoice does not rewrite its symbols or decision.
`detail.json` records the exported result's decision author and reason. Its
`engine_rules_that_fired` describes the engine decision, even when a later reviewed
human resolution is exported. `rules_that_fired` belongs to the exported decision.
The driver compares the filename and SHA-256 with existing instances. A matching
`DECIDED` instance is reused without another OCR call; a matching `PENDING`
instance is re-extracted through `POST /instances/{id}/extract`. Each selected
PDF gets a line in `output/extractions.jsonl`. Reused decided lines contain
`reused: true` and the stored symbols, without a new extraction response.
If a selected file matches an older version of a filename that has since been
replaced, the demo stops: the API exports the newest instance of that name.
Use a fresh process to evaluate that historical batch. Artifacts are staged
until the run succeeds, then each output file is replaced.
For a custom process with optional decision review enabled, pending human approval
blocks export with HTTP 409. Complete that review and rerun the driver; exported
results and detail then follow the approved human resolution. `--local-only`
controls OCR providers, not a separately configured decision reviewer.

For a bounded, local-only run without Gemini or Jev requests:

```bash
make demo DEMO_ARGS="--limit 5 --local-only"
```

`--local-only` still uses the two local OCR readers, so the weights must be
downloaded for scans. Without that flag, configured remote providers can be
called when the pipeline needs them; supply your own `GEMINI_API_KEY` and
`TYPESAFE_API_KEY` if you want both stages. The `DEMO_ARGS` variable also passes
through `--invoices <directory>`, `--book <workbook.xlsx>`, `--cutoff YYYY-MM-DD`,
`--output <directory>`, `--api-url <url>`, and `--limit <positive integer>`.
The default input is `.context/500-sombras-de-alberto`, and the output is
`output/`. The default cut-off is `2026-09-18`; use
`--cutoff 2026-09-19` to match the manual OCR evaluation in the setup guide.
`--limit` restricts uploads, while run/export still cover every instance
already stored in the process. `--process <id>` selects a process when more
than one is loaded; `--email <address>` chooses the seeded user; `--timeout`
sets the OCR request timeout in seconds.

Validate a full export with:

```bash
uv run --project backend --locked python -m app.cli check-outcomes output/outcomes.jsonl --files .context/500-sombras-de-alberto/facturas
```

The historical `433 / 36 / 31` result was measured with the text-layer
extractor, which left all 29 scans without symbols. It is not a target count
for the OCR run. The workbook mapping and JSON-safe source values still matter
because rules consume the uploaded source snapshot; this corpus also contains
zero-width characters inside an IBAN.
