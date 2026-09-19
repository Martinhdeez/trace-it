# Production OCR benchmark: 500 PDFs, 2026-09-19

This is a completed baseline measurement of commit
`f56bf0388d3e58932dcd1b5500e01aa811b19251`, before the later `dev` cache merge and
Helmcode integration. It is not a measurement of the final provider-mode changes.
Raw evidence and the runner remain in the ignored local directory
`reports/ocr500-20260919-0929/`: `run.py`, `run-metadata.json`, `uploads.jsonl`,
`extractions.jsonl`, `events.jsonl`, `decisions.jsonl`, `outcomes.jsonl`, provider
journals, `analysis.json`, `REPORT.md`, and per-file/provider CSVs. No keys are
included in the report. Raw documents and transcripts remain outside Git.

## Conditions and completion

- Windows 11, Python 3.12.13, AMD Ryzen 9 9955HX (16 cores / 32 threads), about
  31.2 GiB physical RAM. This was a shared workstation, not an isolated capacity test.
- Production FastAPI over localhost HTTP, fresh isolated PostgreSQL database and
  extraction/provider caches, sequential client requests. Two configured extraction
  workers, four OCR threads, CPU recognition, 240 DPI. Pinned weights already present.
- 471 native-text PDFs and 29 scanned PDFs from the challenge corpus; workbook and
  the actual simulated ERP service, including its built-in delays and faults.
- The supplied 16 invoice rules were loaded and activated without LLM compilation.
  Cut-off date: 2026-09-18, matching the reference challenge. No rule-agent API calls.
- **500 successful uploads, 500 decisions, 500 exported outcomes, zero upload errors.**

## Elapsed time

| Phase | Seconds |
|---|---:|
| API startup and login | 3.112 |
| Workbook upload | 0.551 |
| ERP synchronization | 5.190 |
| 500 PDF uploads and extraction | 1125.675 |
| Decision run | 16.692 |
| Export | 0.451 |
| Whole pipeline | **1151.745 (19 min 11.745 s)** |

The pipeline timing ends at export; diagnostics collection is outside it. The
ingestion throughput was 26.65 PDFs/minute for this mixture at client concurrency 1.

| Population | Mean | Median | p95 | Maximum | Sum of HTTP requests |
|---|---:|---:|---:|---:|---:|
| 471 native PDFs | 0.194 s | 0.188 s | 0.233 s | 0.501 s | 91.524 s |
| 29 scans | 35.639 s | 31.218 s | 87.661 s | 96.185 s | 1033.530 s |
| All 500 | 2.250 s | 0.188 s | 8.783 s | 96.185 s | 1125.053 s |

Scans were 5.8% of files and about 91.9% of measured upload time. The slowest was
`scan_029.pdf` (96.185 s), followed by `fax_2026_0411.pdf` (91.452 s). These are
observed latencies for this run, not guaranteed service levels or an estimate of
parallel throughput.

There were 507 extraction spans: seven documents received an additional
source-triggered verification. All passes together produced 70 whole-page OCR
spans, 132 focused-reading spans, 34 vision spans and 22 text-judge spans. Final
per-file extraction counters alone omit work done by earlier passes.

Provider network spans summed to 389.744 s inside 1073.437 s of server upload
spans: about 36.3% network-provider time and 63.7% local/application time. Calls
were serial within these requests. OCR, rendering, parsing and uninstrumented
gaps are included in the latter; it is not a direct measurement of CPU utilization.
Whole-page OCR spans alone summed to 429.230 s. Focused spans contain provider
calls, so adding focused and provider time would double-count work.

All uploads shared one trace ID; per-document accounting follows each
`upload_document` span's parent/child tree, not just `trace_id`.

## Providers, usage and cost

| Provider / model | Actual requests | Completed | Failed | Journal replays | Reported input | Reported output | Mean / p95 call latency | Calculable USD |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| Gemini / `gemini-3.1-flash-lite` | 54 | 52 | 2 | 12 | 62,271 | 6,798 | 6.944 / 21.707 s | 0.02576475 |
| TypeSafe / `jev-1.13.0` | 19 | 19 | 0 | 3 | 45,604 | 8,351 | 0.777 / 1.062 s | 0.00191537 |
| Total | **73** | **71** | **2** | **15** | **107,875** | **15,149** | — | **0.02768012** |

Gemini had one HTTP 200 response rejected by local validation: 1,177 input and
198 output tokens, USD 0.00059125, included above. A separate HTTP 503 had no
reported usage, so possible billing for that request is unknown. Two blocked
replays of uncertain Gemini requests did not attempt the network. No HTTP 429
was observed. Do not describe these failures as demonstrated rate limiting.

No cached prompt or thinking tokens were reported in the completed Gemini
responses. Costs use standard published tariffs: Gemini USD 0.25/M input and
USD 1.50/M output; Jev USD 0.042/M input and free output. These are list-price
estimates for reported usage, excluding local hardware, tax, subscriptions and
account credits. They are not a reconciled invoice or a guaranteed total bill.
[Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing),
[Jev pricing](https://typesafe.ai/blog/introducing-system-one-models-and-jev).

The ERP connector made 30 local HTTP requests: 26 result pages containing 516
rows, one login, two transient `ORA-00600` retries, no rate limits or timeouts.
Its reported synchronization duration was 5.110 s (outer HTTP duration 5.190 s).
There were no model download or rule-compilation calls during this run.

## Quality

| Reference | Scored fields | Correct accepted | Wrong accepted | Abstained |
|---|---:|---:|---:|---:|
| 471 native golden files, nine fields each | 4239 | **4239 (100%)** | 0 | 0 |
| 29 scans, provisional visual reference | 282 | **278 (98.58%)** | 0 | 4 |

The 29 scanned reference rows contain ten fields each; eight explicitly
unverifiable fields are excluded. Their labels are provisional visual
transcriptions checked against document SHA-256, not official decision truth.
Two withheld proposals were correct and two were wrong; proposal accuracy was
280/282. The four withheld accepted values were:

- `fax_2026_0411.pdf`: purchase order, insufficient independent support.
- `scan_004.pdf`: purchase order, conflicting readings.
- `scan_017.pdf`: supplier NIF and IBAN, insufficient independent support.

All **471 native decisions** matched their golden outcomes: 433 `PAGAR`,
36 `NO_PAGAR`, two `ESCALAR`. Scanned decisions were 18 `PAGAR`, five `NO_PAGAR`,
six `ESCALAR`, without official expected decisions to score. The full output
was **451 `PAGAR`, 41 `NO_PAGAR`, eight `ESCALAR`**.

Arithmetic warnings are not automatically OCR errors: some invoices genuinely
contain inconsistent figures. Verification here measures transcription, not
business eligibility for payment.

## Helmcode probe

After the baseline ended, six separate image requests tested Qwen 3.6 and Gemma 4
on `scan_001.pdf`, `scan_004.pdf` and `fax_2026_0411.pdf`. Each used a 240-DPI image,
literal-transcription instructions, `reasoning_effort=none`, a 2,500-token cap,
and no automatic retry. All returned HTTP 200 with `finish_reason=stop`.

| Model | Three request latencies | Input tokens | Output tokens |
|---|---|---:|---:|
| `qwen3.6` | 2.970, 2.798, 5.031 s | 16,569 | 521 |
| `gemma4` | 8.768, 9.766, 4.390 s | 1005 | 532 |

Total reported use: **18,627 tokens**. These calls are separate from the 73
baseline requests and its USD estimate. Helmcode's actual account tariff was
not verified. Providers tokenize images differently, so token counts alone
are not a comparable measure of image processing or accuracy.

Qwen correctly proposed `PO-2026-0480` on scan 004, where the baseline withheld
an incorrect proposal. Gemma introduced several wrong digits on scans 001/004;
both models struggled with the poor fax image. This small qualitative probe
supports Qwen as the first fallback, not a general accuracy claim or permission
to bypass corroboration. Raw probe requests' safe metadata/transcripts are in
`helmcode-probes.jsonl` beside the baseline artifacts.
