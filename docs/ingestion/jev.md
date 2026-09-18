# Historical Jev textual selection experiment

Current integration is described in [committee](committee.md).
This experiment used `jev-1.13.0`, `TYPESAFE_API_KEY` and the direct
`POST https://api.typesafe.ai/v1/systemone` endpoint.

Jev consumes text/JSON, not document images. It selects an existing candidate or `none`;
it cannot independently verify OCR digits. The same mistaken transcription can receive
high textual support.

Six real requests used two scan_023 Gemini transcripts and four synthetic development cases.
Each asked a Choice selection and a Noul textual-support question. Expected answers were
not sent, and prompts were not tuned after the responses.

| Case | Selection | Choice score | Proposed-value textual support |
|---|---|---:|---:|
| Full scan_023 transcript | B98233411 | 0.98 | 0.97 |
| Partial B9623341[ILLEGIBLE] | none | 1.00 | 0.09 |
| Supplier versus customer identifier | B96233419 | 0.91 | 0.09 for customer |
| Tax-inclusive total versus base | 2,480.50 | 0.99 | 0.02 for base |
| Currency absent, supplier in Madrid | none | 1.00 | 0.02 for EUR |
| Embedded instruction to complete NIF | none | 0.94 | 0.17 |

All six match their textual references. They are not six visually verified invoices.
The first NIF was disputed by the provisional image reference; the current full audit
excludes that field because it is not reliably legible.

Usage: 3,309 input/413 output tokens; 5.784 seconds total, median 0.449, range 0.424–2.204.
Historical input-token price estimate: $0.000138978, not a verified bill or current quote.
There is no representative p95 from six calls.

The current API can use configured Jev selections as best available readings. Such a
selection is not an extra visual vote. Jev calls do not train account-specific weights;
continuous learning would require verified labels and a separately evaluated training step.

## Reproduce

```powershell
uv run python -m app.features.ingestion.tools.probe_jev --output ../reports/jev/probe-v1 --offline
```

Run from `backend/`. Without `--offline`, uncached requests are sent. Request identity
includes model, text, instructions and options; journals are written before sending.
Incomplete delivery is not automatically retried. Keys/headers are not logged.
Summary: [jev-summary.json](jev-summary.json).
