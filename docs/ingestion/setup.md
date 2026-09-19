# Reproduce the OCR and ingestion setup

This guide runs the production PDF/XLSX ingestion API from a fresh checkout of
`dev`. Run commands from the repository root unless a block says otherwise.
Use the Docker backend for the complete process, including on Windows. The
standalone option below runs extraction without PostgreSQL or the ERP.

## 1. Install tools and get the data

Install Git, [Docker with Compose v2](https://docs.docker.com/compose/install/)
and [uv](https://docs.astral.sh/uv/getting-started/installation/). Docker Desktop
must be running and use Linux containers. A recent Compose version is needed for
the optional `env_file` configuration. No GPU is required.

Install uv if it is missing:

```powershell
# Windows PowerShell; reopen the terminal after installation.
winget install --id=astral-sh.uv -e
```

```bash
# Linux/macOS; reopen the terminal after installation.
curl -LsSf https://astral.sh/uv/install.sh | sh
```

For a new checkout (use your GitHub account's repository access):

```text
git clone --branch dev https://github.com/Martinhdeez/trace-it.git
cd trace-it
git submodule update --init .context/500-sombras-de-alberto
uv python install 3.12
uv sync --project backend --locked
docker compose version
```

For an existing checkout, update `dev` with `git pull --ff-only` before following
this guide. Python **3.12** is required by `backend/pyproject.toml`; the lockfile
installs RapidOCR, ONNX Runtime (CPU), PyMuPDF, OpenCV, Pillow, openpyxl and the
provider clients. Do not install a separate PaddlePaddle training environment or
Tesseract. The production reader renders PDFs with PyMuPDF; host Poppler is only
needed for historical text-layer benchmarks and golden-reference tools. The
Docker image includes Poppler and OpenCV's Linux system libraries.

The corpus should contain 500 PDFs under
`.context/500-sombras-de-alberto/facturas/` and
`FINAL_v7_DEFINITIVO_ahorasi.xlsx` beside that directory.

## 2. Download both local OCR readers

Run this from the repository root, before starting the API:

```text
uv run --project backend --locked python -m app.features.ingestion.tools.download_models --profile v5-latin --output .models
```

The command downloads the primary reader **and its verifier**. It obtains
`inference.onnx` and `inference.yml` for each detector/recognizer, generates the
matching `rec/keys.txt` character dictionaries and writes SHA-256 manifests.
The public Hugging Face model repositories do not require a paid API key.

| Reader component | Repository | Pinned revision |
|---|---|---|
| Primary detector | `PaddlePaddle/PP-OCRv5_mobile_det_onnx` | `df0bd9dee2bc627e80a2a1798ccab35a332e22d6` |
| Primary recognizer | `PaddlePaddle/latin_PP-OCRv5_mobile_rec_onnx` | `89d3a50e2c27e2e7cceeab0e944c25c807d5db4f` |
| Verifier detector | Same mobile detector | Same pinned revision |
| Verifier recognizer | `PaddlePaddle/PP-OCRv5_server_rec_onnx` | `b70df217f4fd99d14f970bad092cebe7d74cc4d1` |

```text
.models/
  manifest.json
  det/inference.onnx
  det/inference.yml
  rec/inference.onnx
  rec/inference.yml
  rec/keys.txt
  verify/
    manifest.json
    det/inference.onnx
    det/inference.yml
    rec/inference.onnx
    rec/inference.yml
    rec/keys.txt
```

The four ONNX files occupy approximately 102 MB together; allow additional space
for download caches, Python dependencies and Docker images. `.models/` is ignored
by Git and mounted read-only at `/srv/.models` in the running backend. Model
loading is lazy. By default, both API applications verify the pinned weights,
detector configuration and dictionaries at startup, and require the evaluated
Gemini/Jev model IDs and credentials. Missing or different components stop startup
with a configuration error. This checks configuration, not provider availability.

Do not use `--no-verifier`, `v6-small`, or a different primary profile when
reproducing this setup. Those switches are for experiments. The API never
downloads missing models at request time. An offline machine needs the complete
directory above, including dictionaries and metadata, copied from a downloaded
installation.

## 3. Configure credentials

Create `.env` without overwriting an existing file:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

```bash
test -f .env || cp .env.example .env
```

Edit the root `.env` and supply your own credentials. These model identifiers are
the configuration used for the documented OCR evaluation, not a guarantee that
every provider account has access to them:

```dotenv
GEMINI_API_KEY=your_gemini_key
TYPESAFE_API_KEY=your_typesafe_key
TRACEPAY_GEMINI_MODEL=gemini-3.1-flash-lite
TRACEPAY_OCR_PROFILE=verified
TRACEPAY_JEV_MODEL=jev-1.13.0
TRACEPAY_WORKERS=2
TRACEPAY_OCR_THREADS=4
TRACEPAY_OCR_CUDA=0
```

| Credential | Used for | Needed to reproduce the OCR committee? |
|---|---|---|
| `GEMINI_API_KEY` | Image transcription and focused visual rechecks. Create a key through [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key). | Yes, for the Gemini path |
| `TYPESAFE_API_KEY` | Jev's text-only selection among reader candidates, via `https://api.typesafe.ai/v1/systemone`. Obtain API access from [TypeSafe](https://typesafe.ai/). | Yes, for the Jev stage |
| `HELMCODE_API_KEY` | Norm normalization, rule compilation and escalation assistant with the current invoice use-case configuration | No; needed when invoking those agents |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` | Alternative rule-agent providers, if selected in the agent configuration | No |
| `FAL_KEY` | Historical `compare_fal_ocr` experiments | No; not used by the production committee |
| `LOGFIRE_TOKEN` | Optional external observability | No |

The OCR adapter specifically reads `GEMINI_API_KEY`; setting only
`GOOGLE_API_KEY` does not enable it. Jev never sees pixels and is not another
visual verifier. `load --activate --manager-id 1` uses the supplied hand-written rules without
calling rule agents. Agent settings in `processes/invoice-payment/use-case.json`
are separate from `TRACEPAY_*`; changing the compiler model does not change OCR.

For local-only operation or a different model, explicitly set
`TRACEPAY_OCR_PROFILE=experimental` before starting the API. Native PDF/XLSX
extraction and available local readers still work in that mode, but it has
different coverage. The default `verified` profile never silently drops those
providers. `make setup` installs both pinned local readers and runs `make ocr-check`
before starting Docker. You can run `make ocr-check` separately after editing `.env`.
Focused local/visual corroboration requires an enabled visual provider. Requests
omit `vlm` and `jev` to permit configured providers automatically; `vlm=false`
and `jev=false` explicitly disable them, even when keys exist.

An alternative image service can be configured with `TRACEPAY_VLM_URL`,
`TRACEPAY_VLM_MODEL` and optionally `TRACEPAY_VLM_API_KEY`. The URL is the API
base, typically ending in `/v1`; the adapter appends `/chat/completions` and sends
an image. A complete URL/model pair takes precedence over Gemini; leave all three
unset to reproduce the Gemini run. Partial generic settings permit configured
Gemini. A failure of a fully configured generic server does not retry through Gemini.

Keys stay in the ignored `.env`. Changing `.env` requires recreating the Docker
backend (`docker compose up -d --force-recreate backend`) or restarting a local
server. Avoid printing `docker compose config` or sharing full environments:
they can contain resolved credentials.

## 4. Start the complete application

From the root, in PowerShell or a POSIX shell:

```text
docker compose up -d --build --wait
docker compose exec -T backend python -m app.cli load /processes/invoice-payment.json --activate --manager-id 1
```

The container runs database migrations at startup. `--activate` publishes the pack's
hand-written rules as a process version and needs a manager's user id: on a fresh
database the seeded manager is 1 (`curl -s localhost:8000/users`). `make setup` then
`make activate MANAGER_ID=1` does the same. Record the process ID printed by `load`; do
not assume it is 1 in an existing database. The API is at
`http://127.0.0.1:8000/docs`. `BACKEND_PORT` in `.env` changes its host port.

Check configuration inside the container without revealing keys:

```text
docker compose exec -T backend python -c "from app.features.ingestion.config import Settings; from app.features.ingestion.ocr.local import LocalOCR; from app.features.ingestion.ocr.vision import VisionFallback; from app.features.ingestion.ocr.judge import TextJudge; s=Settings(); print('models:', LocalOCR(s).signature()); print('visual:', VisionFallback(s).configured, 'jev:', TextJudge(s).configured); print('model_dir:', s.model_dir)"
```

Expect both manifests, `visual: True`, `jev: True`, and `/srv/.models` for the
full committee. This checks configuration, not provider credentials or quota.
Make an actual scan request in the next section and inspect its warnings.

For the payment flow, start the ERP in another terminal from the repository root:

```text
uv run --project backend --locked python .context/500-sombras-de-alberto/alberto_erp.py
```

Leave it running on port 8009. Compose points the backend at
`http://host.docker.internal:8009` (`ERP_PORT=<port>` for both `make erp` and `make setup`
if 8009 is taken). Docker Desktop supplies that hostname. On
Linux Docker Engine, add `extra_hosts: ["host.docker.internal:host-gateway"]` to
the backend in a local Compose override if the name does not resolve. Allow the
container to reach the host ERP. The challenge credentials in `.env.example`
are `TRACE_ERP_USER=alberto` and `TRACE_ERP_PASSWORD=FACTURAS2009`.

## 5. Check a real scan

Use the pack's seeded manager account. A different team account can also be
used for extraction. Examples use `scan_010.pdf`, which exercises local OCR.

### Windows PowerShell

```powershell
$ErrorActionPreference = 'Stop'
$api = 'http://127.0.0.1:8000'
$user = Invoke-RestMethod -Method Post -Uri "$api/login" -ContentType 'application/json' -Body '{"email":"martin@trace-it.local"}'
$userId = $user.id
New-Item -ItemType Directory -Force output/ocr-setup-run | Out-Null
curl.exe --fail-with-body --silent --show-error "$api/v1/extractions" -H "X-User-Id: $userId" -F 'file=@.context/500-sombras-de-alberto/facturas/scan_010.pdf' --output output/ocr-setup-run/scan-check.json
if ($LASTEXITCODE -ne 0) { throw 'Scan extraction failed; inspect the response file' }
Get-Content output/ocr-setup-run/scan-check.json
```

### Linux/macOS (bash)

```bash
set -euo pipefail
api=http://127.0.0.1:8000
user_id=$(curl --fail --silent --show-error "$api/login" -H 'Content-Type: application/json' -d '{"email":"martin@trace-it.local"}' | uv run --project backend --locked python -c 'import json,sys; print(json.load(sys.stdin)["id"])')
mkdir -p output/ocr-setup-run
curl --fail-with-body --silent --show-error "$api/v1/extractions" -H "X-User-Id: $user_id" -F 'file=@.context/500-sombras-de-alberto/facturas/scan_010.pdf' --output output/ocr-setup-run/scan-check.json
cat output/ocr-setup-run/scan-check.json
```

Inspect `warnings`, `metrics`, `data.committee`, `data.focused_verification` and
the candidates of `fields.payment_iban`. A 200 response can retain provider
failures alongside partial readings. On a new scan extraction expect local OCR
activity; configured remote readers run only when the pipeline needs them.
`cache_hit=true` means this request reused an extraction. The current-request
call counters can then be zero. A critical `value=null` with a `proposed_value`
is intentional when the reading cannot be corroborated.

For an explicitly local-only smoke check, add `-F 'vlm=false' -F 'jev=false'`
to the extraction command. This makes no Gemini/Jev requests and does not
reproduce the full committee's results.

## 6. Run all 500 PDFs through the production process API

Use a fresh process/database for a comparable run. Uploading a previously
decided instance does not replace its symbols or decision. The demo compares
filename and SHA-256 against existing instances: matching `DECIDED` files skip
OCR and retain stored symbols; matching `PENDING` files check extraction, source and schema
freshness and refresh only when necessary. Its
`output/extractions.jsonl` records each selected PDF, with `reused: true`
and stored symbols for a skipped decided file. First load and
activate the pack as above, then load sources, upload **all** PDFs, and only
then run the engine so duplicate-order checks see the whole batch.

The demo command automates that same sequence using the running Docker backend
and ERP. From the repository root, after steps 1-4:

```text
make demo
```

It needs the published rules of step 4 (`make activate MANAGER_ID=1`); without them the
run answers 409. It logs in as the seeded manager, uploads the
workbook, syncs the ERP, uploads PDFs with `ocr=true`, runs pending decisions and
writes `output/outcomes.jsonl` and `output/detail.json`. For a small local-only
check, run `make demo DEMO_ARGS="--limit 5 --local-only"`. This disables
Gemini/Jev calls, but still uses the downloaded OCR weights. `DEMO_ARGS` can
also pass `--invoices <directory>`, `--book <workbook.xlsx>`,
`--cutoff YYYY-MM-DD`, `--output <directory>` and `--api-url <url>`.
The demo defaults to cut-off `2026-09-18`; pass `--cutoff 2026-09-19`
to match the manual evaluation below. `--limit` restricts uploads; the engine
and export still cover all instances already in the process.
On Windows PowerShell, run these through a Make installation or invoke
`uv run --project backend --locked --env-file .env python tools/demo_run.py`
after activating the pack in Docker. The commands below show each API call
directly, which is useful for inspecting extraction evidence.

These examples continue in the same shell as section 5. Replace the example
process ID with the one printed by `load`. The cut-off `2026-09-19` matches the
documented focused-OCR evaluation; it is policy data, not today's date.

### Windows PowerShell

```powershell
$processId = 1 # Replace with the ID printed by the loader.
$headers = @{ 'X-User-Id' = "$userId" }
curl.exe --fail-with-body --silent --show-error "$api/processes/$processId/sources/workbook" -H "X-User-Id: $userId" -F 'file=@.context/500-sombras-de-alberto/FINAL_v7_DEFINITIVO_ahorasi.xlsx' -F 'cut_off_date=2026-09-19' --output output/ocr-setup-run/workbook.json
if ($LASTEXITCODE -ne 0) { throw 'Workbook upload failed' }
Invoke-RestMethod -Method Post -Uri "$api/processes/$processId/sources/erp/sync" -Headers $headers
$files = Get-ChildItem -LiteralPath .context/500-sombras-de-alberto/facturas -Filter *.pdf | Sort-Object Name
foreach ($file in $files) {
    Write-Host "Uploading $($file.Name)"
    curl.exe --fail-with-body --silent --show-error "$api/processes/$processId/files" -H "X-User-Id: $userId" -F "file=@$($file.FullName)" --output "output/ocr-setup-run/$($file.Name).json"
    if ($LASTEXITCODE -ne 0) { throw "Upload failed: $($file.Name)" }
}
Invoke-RestMethod -Method Post -Uri "$api/processes/$processId/run" -Headers $headers
curl.exe --fail-with-body --silent --show-error "$api/processes/$processId/export" -H "X-User-Id: $userId" --output output/ocr-setup-run/outcomes.jsonl
if ($LASTEXITCODE -ne 0) { throw 'Export failed' }
```

### Linux/macOS (bash)

```bash
set -euo pipefail
process_id=1 # Replace with the ID printed by the loader.
curl --fail-with-body --silent --show-error "$api/processes/$process_id/sources/workbook" -H "X-User-Id: $user_id" -F 'file=@.context/500-sombras-de-alberto/FINAL_v7_DEFINITIVO_ahorasi.xlsx' -F 'cut_off_date=2026-09-19' --output output/ocr-setup-run/workbook.json
curl --fail-with-body --silent --show-error -X POST "$api/processes/$process_id/sources/erp/sync" -H "X-User-Id: $user_id"
for file in .context/500-sombras-de-alberto/facturas/*.pdf; do
    printf 'Uploading %s\n' "$file"
    curl --fail-with-body --silent --show-error "$api/processes/$process_id/files" -H "X-User-Id: $user_id" -F "file=@$file" --output "output/ocr-setup-run/$(basename "$file").json"
done
curl --fail-with-body --silent --show-error -X POST "$api/processes/$process_id/run" -H "X-User-Id: $user_id"
curl --fail-with-body --silent --show-error "$api/processes/$process_id/export" -H "X-User-Id: $user_id" --output output/ocr-setup-run/outcomes.jsonl
```

Validate the exported filenames, result types and one-line-per-file contract:

```text
uv run --project backend --locked python -m app.cli check-outcomes output/ocr-setup-run/outcomes.jsonl --files .context/500-sombras-de-alberto/facturas
```

This validation does not prove the decisions match the private organizer
reference. Keep the per-file API responses: they include extraction evidence and
the stored symbols. `/v1/batches` is an extraction-only endpoint; it does not
create process instances, and accepts at most 100 files per request.

`make demo` uses these production endpoints. With `--limit`, it uploads only the
selected PDFs, while run/export still cover the whole process. Use a fresh
process and omit that option for a comparable 500-invoice run.

## 7. Optional: extraction only, without Docker

After steps 1-3, start this from the repository root:

```text
uv run --project backend --locked --env-file .env uvicorn app.features.ingestion.application:create_app --factory --host 127.0.0.1 --port 8001 --workers 1
```

This standalone API has `/health`, `/v1/extractions` and `/v1/batches`, without
authentication. Use the scan commands with port 8001 and omit the user header;
there is no login, process API, PostgreSQL or ERP synchronization in this mode.
Its `/health` includes model manifests and provider-configuration booleans.
The main app's `/health` only reports `status`.

The ingestion settings read environment variables, not `.env` automatically.
Keep `--env-file .env` when running locally. Default paths resolve to the
repository's `.models/` and `.data/`. Use one server per data directory;
`TRACEPAY_WORKERS` controls internal jobs, not Uvicorn processes.

On Debian/Ubuntu hosts, OpenCV may need
`sudo apt-get install libgl1 libglib2.0-0`. If using the historical text-layer
benchmark or golden tools, also install `poppler-utils` (macOS:
`brew install poppler`). Windows
users can use the Docker image for those tools instead of installing Poppler.

## Reproducibility and troubleshooting

Record `git rev-parse HEAD`, both model manifests, `backend/uv.lock`, model IDs,
request options, corpus hashes, source snapshots, cut-off date and active rules.
The [focused-verification report](focused-verification.md) describes the
historical run, including its remaining uncertainty and coverage losses.

That run reused recorded provider responses. A fresh teammate installation has
no such journal and makes live requests when needed; identical provider names
do not guarantee identical text or final counts. Current `dev` also has changes
after that evaluation. Exact offline replay requires the original ignored
reports, provider journal, source snapshots and matching code/rules, not just a
Git clone. `backend/evals/ocr_regression.py` compares those saved artifacts;
its example paths are local evaluation outputs, not downloadable datasets.

| Symptom | Check / action |
|---|---|
| `OCR models missing` or verifier unavailable | Rerun the downloader with the command above; confirm `.models/verify` exists and both manifests are visible inside Docker. |
| Download fails | Check access to Hugging Face and the pinned repositories. Preserve the complete profile; do not mix a recognizer with another dictionary. |
| API is healthy but scans have missing values | Inspect the scan response's warnings and reader candidates; `/health` is not a model-inference test. |
| Gemini/Jev 401, 403, 404 or 429 | Check your key, account/model access and quota. Confirm the model ID. Provider failures can yield partial results, not necessarily an HTTP 500. |
| Changed `.env` has no effect | Recreate the backend container or restart the standalone server with `--env-file`. A plain container restart does not reload Compose environment configuration. |
| An old failed provider request is not resent | Journals intentionally block automatic resends after uncertain delivery. Inspect the recorded failure. Use a separate data directory/volume for a deliberate fresh experiment; keep the original evidence. |
| `CUDAExecutionProvider` unavailable | Keep `TRACEPAY_OCR_CUDA=0`; the locked setup uses CPU ONNX Runtime. GPU deployment is a separate configuration. |
| Data-directory lock error | Stop the other ingestion server using that directory; use one Uvicorn worker. |
| ERP connection refused | Keep the ERP terminal open; check port 8009 and Docker-to-host connectivity. `localhost` inside the backend is the container. |
| `/login` returns 404 | Load the process pack to seed users, or inspect `GET /users` for an existing account. |
| `/export` returns 409 | Inspect pending instances/rules; ensure every upload succeeded and `/run` completed. |

Docker stores extraction objects, SQLite jobs/results and provider journals in
the `ingestion_data` volume; PostgreSQL uses the `db` volume. The standalone
service uses `.data/`. `docker compose down` preserves volumes;
`docker compose down -v` / `make reset-db` deletes both databases and journals.
Neither should be used as a routine setup or cache-refresh step. Downloaded
weights remain in the host `.models/` directory.
