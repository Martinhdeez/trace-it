# API OCR performance and verification

API extraction needs two independent visual models to verify fields without native
text. A text judge can recommend an existing candidate but cannot provide the
second visual vote. Re-reading the same model never adds another vote.

## Versioned configuration

`extraction.vision_model` remains the primary reader. The new
`extraction.vision_verification_models` list explicitly pins up to three additional
Gemini or Helmcode models. Readers are tried in configured order, two independent
models at a time; later entries replace unavailable readers. Duplicate model
identities, unsupported providers, and verifiers without a primary are rejected.
Deployment credentials determine which explicitly selected readers are available.

For example:

```json
{
  "mode": "api",
  "vision_model": "helmcode:qwen3.6",
  "vision_verification_models": ["helmcode:gemma4"],
  "text_judge_model": "jev:jev-1.13.0",
  "dpi": 240,
  "timeout_seconds": 120
}
```

These fields extend the existing extraction settings; the model directories and
other settings remain part of the full configuration. Newly created defaults pin
the deployment's available independent readers. Existing published versions retain
their explicit choices. For an existing process, edit its execution settings in a
new draft, add the verifier, validate and publish using the existing manager flow.
Re-extract pending documents; decided documents and historical evidence stay intact.

The editor warns when API mode has no verification reader. At runtime a legacy
single-reader configuration emits `INSUFFICIENT_VISUAL_READERS` and preserves
proposals without spending calls on impossible focused verification. A failed
configured verifier produces `VLM_ERROR`; that partial result is retained as
evidence but is not reused as a completed extraction cache entry. Successful
provider responses still replay from the journal when the missing reader recovers.

## Concurrency, resource bounds, and recovery

The deployment Compose default is three document workers and three simultaneous
requests per provider. `TRACEPAY_WORKERS` and `TRACEPAY_VISION_MAX_CONCURRENCY` can
override those limits. Existing installations must also update their installed
Compose file: replacing an image does not change a literal `TRACEPAY_WORKERS: "1"`
in `/opt/trace-it/compose.yml`. This repository change does not alter that live file.

Independent visual requests run concurrently, with copied trace and usage context.
Provider semaphores remain authoritative; the old lock around the entire visual
HTTP request is removed. Visual readers, judges, and schema readers reuse HTTP
connections across requests and process configurations. Pools close on service
shutdown. PyMuPDF access and duplicate request journals remain locked.
API readers release each full-page PNG after transcription rather than retaining
every rendered page until a multi-page document finishes.

`TRACEPAY_EXTRACTION_TIMEOUT_S` defaults to 120 seconds. A version can override it
with `extraction.timeout_seconds`. Nested payment verification inherits the earlier
deadline. Queue waits and provider retries consume this budget, and remaining time
caps HTTP transport timeouts. Queue expiration is an explicit retryable HTTP 503,
`extraction_deadline_exceeded`. This is not a hard cancellation mechanism for local
CPU work or a streaming peer that keeps resetting a transport read timeout.

A request that expires while waiting for a provider slot is journaled as
`not_started`, so it can be retried without pretending a network delivery occurred.
Actual uncertain delivery retains the existing no-automatic-retry safeguard.

Focused verification reuses one image and provider result when several identifiers
share a crop. It does not re-read immutable conflicts that another crop cannot
resolve. In API mode the text judge is reserved for competing candidate values.
No change relaxes evidence acceptance or arithmetic checks.

The trace now separates `render_page`, `render_region`, `worker_wait_ms`,
`journal_wait_ms`, `slot_wait_ms`, and `network_latency_ms`. Render spans belong to
the ingestion plane. Warm extraction metrics reset the worker wait to zero.

## Measured corpus run

All 540 PDFs from challenge commit `f831e3432d739cabcc3fb6d76d61eb58bec2ecd9`
were run with real providers and empty local caches on September 19, 2026. The
baseline and candidate used the same updated benchmark driver. The baseline loaded
the previously deployed extraction implementation and its single-reader process
configuration. Both ran on the same four-thread VPS, alongside other activity,
outside the production container's CPU/memory cgroup.

| Configuration | Wall time | Files/s | Network calls | Accepted scan fields |
|---|---:|---:|---:|---:|
| Previous code, Qwen + Jev, one worker, 240 dpi | 182.061 s | 2.97 | 93 | 0/290 |
| Updated code, Qwen + Gemma + Jev, three workers, 240 dpi | 89.033 s | 6.07 | 114 | 173/290 |
| Updated code, same readers/workers, 150 dpi experiment | 118.641 s | 4.55 | 117 | 196/290 |

The 240 dpi candidate took 51% less wall time in these runs while performing more
verification. The candidate rejected three HTTP-200 transcripts as invalid; the
150 dpi experiment rejected one. There were no document extraction exceptions.
Those reader failures remain visible and the affected partial extractions are not
cached as complete. Model latency and answers vary: these are individual runs,
not a statistical guarantee of production latency or payment accuracy. More
verification can increase provider usage and cost even when wall time falls.

150 dpi remains an experiment rather than a new default: smaller PNGs did not
reliably mean faster remote inference. The DPI setting remains explicit.

The current visual reference set covers `scan_001.pdf` and `scan_026.pdf`, 20 fields,
reviewed against the current rendered documents and bound to their SHA-256 values.
The 240 dpi candidate accepted 13 matching values and abstained on seven; the
150 dpi experiment accepted 17 matching values and abstained on three. Neither
accepted a wrong value in this small reference set. These are assistant-reviewed
development labels, not organizer ground truth or a claim about all 290 fields.

The old 29-document `scans-reviewed.json` remains historical: its file hashes do
not match the current corpus. `evaluate_scans` defaults to the newly reviewed
`scans-reviewed-current.json`, reports the chosen label file and coverage, and
checks all hashes before making a billable call. Expanding coverage requires
visual review; changing hashes alone is not a valid refresh.

## Reproduction

From `backend`, with configured provider credentials, use a new output directory
for a cold run. The benchmark stores its own objects, caches, and JSONL spans under
that directory and does not write audit events to the application database.

```sh
TRACEPAY_VISION_PROVIDERS=helmcode TRACEPAY_HELMCODE_VISION_MODELS=qwen3.6,gemma4 \
TRACEPAY_TEXT_PROVIDERS=jev uv run python -m app.features.ingestion.tools.benchmark \
  ../.context/500-sombras-de-alberto --pdf-only --mode api --workers 3 --dpi 240 \
  --output reports/ocr-performance

uv run python -m app.features.ingestion.tools.evaluate_scans \
  --input ../.context/500-sombras-de-alberto/facturas \
  --extractions reports/ocr-performance/files.jsonl --output reports/ocr-quality
```

Repeating the same benchmark output directory measures cache reuse. Unit tests use
mock transports, synchronization barriers, controlled deadlines, and scripted
reader responses; they never require an API key.
