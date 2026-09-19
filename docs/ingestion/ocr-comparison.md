# Historical difficult-OCR comparison

Development documents: scan_021, 022, 023, 025 and 026; scan_024 is absent.
The original provisional reference had 47 fields. See the [full audit](corpus-audit.md)
for revised references and current behavior.

| Reader and input | Matching fields |
|---|---:|
| Local before targeted preprocessing | 35/47 |
| Local v1.7.1 with illumination/band correction and verification | 42/47 |
| GOT-OCR v2 original pages, current parser | 12/47 |
| GOT-OCR v2 corrected/cropped inputs, current parser | 29/47 |
| Gemini 3.1 Flash-Lite original pages | 46/47 |

These measure OCR plus field parsing on development cases, not universal model accuracy.
Local per-document counts were 7/8, 7/10, 8/9, 10/10 and 10/10.

Eleven authenticated GOT requests completed: five pages, five crops and one formatted-output
variant. The last scan_025 request recovered 2/10 fields and degenerated into repetitions.
The scan_023 crop excluded part of its header because cropping used locally detected evidence;
it cannot test recovery of fields outside that crop.

At the historical quoted $0.05/image, eleven attempts had a theoretical $0.55 cost,
not a verified bill or current pricing claim. GOT remains an explicit experiment and
does not replace the local initial route.

From `backend/`:

```powershell
uv run python -m app.features.ingestion.tools.compare_fal_ocr --output ../reports/fal-got --offline
```

Without `--offline`, the tool may send images and incur charges using `FAL_KEY`.
Request identifiers are stored before waiting so existing jobs can be recovered after timeout.
Crops require `--local-extractions`.

Separate GPU workers, region-level model routing and correction training remain future work.
Any training or model replacement needs human-verified references and held-out documents.
