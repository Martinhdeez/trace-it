# OCR reuse, refresh and difficult scans

The extraction cache, reader caches and process evidence have different lifetimes.
Restart the service after deploying code changes. Keep the original files, historical
extractions and decisions; no cache refresh requires deleting the database.

## Dependency boundaries

| Change | Work on the next extraction or pending-instance refresh |
|---|---|
| Same bytes and effective options | Reuse the final extraction. No reader calls. |
| Filename only | Reuse extraction content with the new upload identity. Process instances still distinguish names. |
| Parser, normalization, committee or field policy | Recompute field interpretation; reuse matching image-reader transcripts. |
| Confidence threshold or requested verification fields | Reinterpret evidence and run only missing reader inputs. |
| Image bytes, render DPI/pixel limit, preprocessing, local model artifacts or OCR runtime | Recompute affected local readings. The other model's unchanged readings remain reusable. |
| Visual/judge prompt, generation parameters, model or endpoint | Invalidate the corresponding interpretation/request identity. Existing unrelated readers remain reusable. |
| Excel limits or Excel reader | Refresh workbook extraction, independently of OCR configuration. |
| Source rows or symbol schema/payment adapter | Refresh pending process symbols and source-triggered verification; document OCR stays reusable. |
| New source snapshot with identical rows | Reuse evidence and retain the original snapshot IDs in its provenance. |
| Rules only | Evaluate rules against evidence through the decision workflow; do not rerun OCR just for a rule change. |

Final extraction keys include source-code fingerprints, effective options, relevant limits,
reader configurations and model file hashes. File contents are hashed once per observed
file revision. Changing an ONNX model, dictionary or detector configuration in place no
longer depends on remembering to edit its manifest. An existing local session reloads
when its reader identity changes.

Local transcripts live in `TRACEPAY_DATA_DIR/reader-cache/local/`. Their identity includes
the input image, page/coordinate frame, preprocessing implementation, model artifacts
and runtime. They contain original text, confidence, geometry and preprocessing evidence,
not parsed fields. Writes are atomic and protected by file locks; exceptions are not
cached, and malformed local cache entries are recomputed. Final extractions also serialize
identical concurrent requests. This does not turn the job queue into a distributed queue.

Remote request journals remain separate. They key complete requests by image/text,
model, endpoint, prompt and generation settings. A recorded uncertain delivery is not
automatically resent. Inspect its journal before deliberately recovering it. Keep one
provider account per data directory and use pinned model versions: switching credentials
does not imply a new OCR experiment, and redeploying an alias under the same model ID
cannot be detected remotely from these inputs.

## Process evidence and history

Uploading an existing pending file or calling `POST /instances/{id}/extract` first checks
the recorded request key, source contents and symbol/adapter schema. An unchanged request
returns its existing extraction and symbols without appending another extraction event.
The response retains the extraction ID and evidence, but marks `cache_hit=true` and
zeroes current-request reader counters on a copy; the stored historical result is unchanged.
Missing legacy provenance and transient reader failures cause another extraction attempt.
Source-triggered focused verification records both the initial request and the expanded
verification request, so subsequent identical uploads do not continually refresh it.

A stale pending instance refreshes its symbols under the same row lock used by the
decision run. The original file and previous events stay immutable. A duplicate upload
of a decided instance returns its stored evidence and symbols before invoking readers;
it cannot replace the document shown beside an existing decision. Explicit re-extraction
of a decided instance still returns 409. Comparing a new OCR policy against decided cases
requires a separate evaluation/process, not rewriting their history.

Refresh is checked on upload/re-extraction, not by a background watcher. After changing
sources, refresh affected pending documents before `/run`; the demo already visits its
selected pending documents through the extraction endpoint.

## Metrics and a repeatable local benchmark

`ocr_calls`, `vlm_calls` and `jev_calls` count logical reader attempts in the extraction.
`*_calls_this_request` excludes reused local transcripts and remote journal responses.
`*_cache_hits_this_request` reports reader reuse. On a final extraction cache hit all
these current-request counters are zero; historical extraction counters remain available.
An uncertain remote journal contributes zero new provider requests.

From `backend/`, with the pinned models already downloaded:

```text
uv run --locked python -m app.features.ingestion.tools.benchmark_cache
```

This tests the five difficult scans with local readers only, writes an isolated run under
`reports/ocr-cache/`, and compares cold extraction, final-cache reuse and re-interpretation
with a stricter confidence threshold (0.90 to 0.95). It checks source hashes against the
development references. Threshold changes can legitimately change accepted fields;
cache speed must not be reported as accuracy improvement. Cold timings include loading
both models and depend on other work running on the machine.

The local five-scan run `reports/ocr-cache/81c96f1b4480/summary.json` recorded 10 OCR
executions when cold, zero when repeated, and zero for the stricter-threshold reparse
(10 cached reader transcripts). All five repeated results preserved every returned field.
The cold and repeated runs matched 40/46 labeled returned values, with zero wrong non-null
values. The stricter threshold lost one correct IBAN on scan_026 (39/46), so the default
stays at 0.90. These are local-only results; they do not measure Gemini/Jev accuracy or cost.
The first measurement encountered an unavailable audit table; the benchmark now writes
its spans to the isolated run's `traces.jsonl` instead of the application database.

## Quality findings and current model research

`scan_024.pdf` is absent. The source raster resolutions for 021, 022, 023, 025 and 026
are approximately 105, 110, 60, 200 and 200 dpi. The first three already lack fine detail;
rendering them at 600 dpi does not recreate lost glyphs. Existing illumination/stripe
correction is useful for 025/026; 022 benefits from geometrical correction and independent
visual corroboration. Unreadable identifiers in 021/023 must remain unresolved.

The focused route now shares its identical 600 dpi image between local and final visual
readers. It retains the independent reading and conflict checks: skipping them merely
because early readers agree can hide contradictory evidence. The text-only judge runs
after focused image verification and receives only still-unresolved fields with actual
candidates. It does not override confirmed image evidence.

The model review used primary sources (September 2026):

- [PaddleOCR releases](https://github.com/PaddlePaddle/PaddleOCR/releases) include PP-OCRv6.
  Its [recognition documentation](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/module_usage/text_recognition.en.md)
  uses different evaluation sets for v5 and v6; published scores do not establish a gain
  on these invoices. Keep the pinned readers until a paired benchmark supports replacing them.
- PaddleOCR's [document preprocessor](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/doc_preprocessor.html)
  supports orientation and geometric correction. Evaluate these selectively on measured
  defects, preserving the original observation and an unchanged-document control set.
- Gemini's [document guidance](https://ai.google.dev/gemini-api/docs/document-processing)
  emphasizes orientation and readable inputs. [Structured output](https://ai.google.dev/gemini-api/docs/structured-output)
  constrains syntax, not semantic correctness. A visual response still needs corroboration.

The scan references are development visual transcriptions, not independent organizer
ground truth. No new model, synthetic sharpening or source-table substitution was promoted
as a measured accuracy improvement. Future model comparisons need human-reviewed held-out
documents, field error/abstention rates and actual inference counts alongside latency.
