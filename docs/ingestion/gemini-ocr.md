# Historical Gemini OCR experiment

This five-document experiment predates the integrated committee. Current behavior and
the revised references are in [committee](committee.md) and [full audit](corpus-audit.md).

Real `gemini-3.1-flash-lite` calls used original page PNGs with the same hashes as the
GOT experiment. Expected labels, workbook values and other models' answers were not sent.

| Document | Local v1.7.1 | Gemini | Provisional reference fields |
|---|---:|---:|---:|
| scan_021.pdf | 7 | 8 | 8 |
| scan_022.pdf | 7 | 10 | 10 |
| scan_023.pdf | 8 | 8 | 9 |
| scan_025.pdf | 10 | 10 | 10 |
| scan_026.pdf | 10 | 10 | 10 |
| Total | 42 | 46 | 47 |

The denominator was provisional and later revised: scan_023 NIF/IBAN now lack reliable
references. Historical Gemini NIF `B98233411` differed from provisional `B96233419`.
A sixth cropped request returned `B9623341[ILLEGIBLE]`. Its IBAN proposal was excluded
from scoring. Scan_021's covered identifiers were also excluded.

Five page calls took 17.618 seconds total, median 2.632 seconds, using 5,945 input and
1,012 output tokens. Historical token-price estimate: $0.00300425, not a billed amount
or current price quote. The crop used 1,182 input/204 output tokens in 1.784 seconds;
six completed calls had an estimated combined cost of $0.003606.
Other attempted models returned 503, 404 or 429 and were not retried or ranked.

Response identities and hashes remain in [gemini-summary.json](gemini-summary.json).
Current configured Gemini participates automatically when unresolved readings remain;
the earlier experiment itself was explicit.

## Reproduce

From `backend/`, with `GEMINI_API_KEY` in the root `.env`:

```powershell
uv run python -m app.features.ingestion.tools.compare_gemini_ocr --model gemini-3.1-flash-lite --output ../reports/gemini-ocr/flash-lite --offline
```

Omitting `--offline` sends uncached requests and may incur charges. Cache identity includes
model, prompt, configuration and image hashes. An incomplete request blocks automatic
resending. `--input-images` accepts crops named `file.pdf.png`; no original PDF coordinates
are invented for them.
