# Scale and cost

How many files we process per second, on what hardware and under which conditions; how we
count cost; and what changes when Alberto brings new kinds of input. Every figure below was
measured on 2026-09-19 unless it says otherwise, and each one says how.

**Headline.** The engine decides the 500 invoices of batch 1 in **0.56 s with 11 generated
rules (899/s)** and **0.85 s with 16 hand-written rules (588/s)**, and deciding costs **0 tokens**:
no LLM runs per invoice (ADR 0002). Tokens are spent only when the norm changes (**~149k
tokens for the whole 6-sentence norm → 11 rules**) and when a person asks the assistant about
an escalated case (**~3.7k tokens each**). The real ingestion bottleneck is OCR of scans, not
the engine.

## 1. Hardware and conditions

| | |
|---|---|
| Machine | MacBook, Apple M4 Pro, 14 cores (10 performance + 4 efficiency), 24 GB RAM, macOS 26.5 |
| Python | CPython 3.12.13 (uv), backend run on the host, in process (`httpx.ASGITransport`, no HTTP hop) |
| Database | PostgreSQL 16.15 in Docker 29.5 (VM: 14 CPUs, 7.75 GB), private database `trace_bench` |
| Sandbox | One `python -I -S -B` subprocess per rule per run, over all instances at once (ADR 0005) |
| ERP | The challenge's `alberto_erp.py` on its own port, with its built-in latency and faults |
| LLMs | Helmcode `deepseek-v4-flash` for every role (the provider reports `deepseek-v4.1-flash`), fallbacks `glm5.3` / `qwen3.6` (ADR 0019), concurrency 5 |
| Data | Batch 1: 500 PDFs (471 with a text layer, 29 scans), the challenge workbook, 516 ERP entries |

Reproduce: `make setup` on a scratch database, `make erp`, `make demo`, then
`tools/bench_scale.py` (`engine`, `extract`, `upload`; see its docstring). Durations come from
our own spans (ADR 0018) through `GET /traces` and `GET /processes/{id}/metrics`.

## 2. Measured throughput

### Engine (deciding)

| Rules | Instances | Run | Median | Per second | `evaluate_rule` p50 / p95 |
|---|---:|---|---:|---:|---|
| 16 hand-written | 500 | `run_process`, 1 run, writes 500 decisions | 1019 ms | 491 | - |
| 16 hand-written | 500 | `reprocess?dry_run=true`, 3 runs: 822 / 876 / 851 ms | 851 ms | **588** | 38 / 91 ms |
| 11 generated from the norm | 500 | same, 3 runs: 554 / 570 / 556 ms | 556 ms | **899** | 39 / 67 ms |

A dry-run reprocess is the engine alone (same `decide_all` as a run, nothing written);
`run_process` adds the 500 decision rows and their spans. An earlier measurement (ADR 0018,
471 invoices, 16 rules) gave 449/s; a previous integrated run with 11 generated rules, 789/s.

**How it scales.**
- *With rules:* linear. Each rule is one subprocess (18 ms to start an empty one) that
  receives the sources and the population once, then evaluates every instance. Rules run one
  after another, so a run costs about 35-40 ms per rule plus what the rule itself does. Fewer,
  generated rules are why 11 rules beat 16.
- *With instances:* linear for rules that read one instance, quadratic for rules that read
  `others` (the duplicate check R16 compares every invoice with every other one). Measured
  with the sandbox directly, 16 rules, batch 1 copied k times:

  | Instances | Total | Per second | Slowest rule |
  |---:|---:|---:|---|
  | 471 | 0.76 s | 616 | R14 0.12 s |
  | 1,884 | 2.91 s | 648 | R16 0.57 s |
  | 4,710 | 11.8 s | 400 | R16 3.25 s |

  The population is every instance of the process (all batches), even when only a new batch
  is decided, so R16's cost grows with history.

### Ingestion (reading PDFs)

| Path | What was measured | Result |
|---|---|---|
| Demo path, `tools/extractor.py` (pdftotext + regex, no model) | all 500 PDFs, one thread | 4.9 s, **101 PDFs/s** (29 scans detected and left without symbols) |
| Upload API `POST /processes/{id}/files`, cold cache, one sequential client | all 500 PDFs | 18.0 s, **27.8 files/s**; text PDF median 18 ms (max 65 ms), scan median 134 ms |
| Spans of the same uploads | `upload_document` / `native_text` p50 | 16 ms / 2 ms |
| Whole batch 1, `demo_run.py` (ingest, ERP sync, run, export) | one run | 15 s inside the script (30 s wall with `uv` start-up) |

**OCR is not measured on this machine**: the local ONNX weights are not downloaded
(`.models/` is absent; `python -m app.features.ingestion.tools.download_models`), so each
scan's two OCR readers fail fast with `ProviderUnavailable` and the scan escalates with
`MISSING_DATA`. That is the 134 ms above: not OCR. The teammate's benchmark with OCR
(`docs/ingestion/benchmark-summary.json`, Windows 11, 32 threads, 501 files including the
workbook, 44 OCR calls) is **3.53 files/s cold** and 68 files/s with the extraction cache;
a Gemini page call took a median of 2.6 s (`docs/ingestion/gemini-ocr.md`). So a scan costs
seconds where a text PDF costs milliseconds.

### ERP sync

`make erp-sync` / `POST /processes/{id}/sources/erp/sync`, 3 runs, from the `sync_source` span:
**516 rows, 26 pages of 20, 5.2 / 5.4 / 5.6 s (median 5.4 s, 96 rows/s)**, 1 login, 2-3
`ORA-00600` retried per run, 0 rate-limited answers, 0 invalid values. The floor is our own
client limit: 26 pages at 6 requests/s is 4.3 s, plus the ERP's built-in latency. The limit
is in `processes/invoice-payment/sources.json` (`rate_limit.requests_per_second`).

### Rule compilation (norm → rules)

`POST /processes/1/norm` with the six sentences of `Norma_Pagos_v3` on an empty rule set, one
real run (spans `norm`, `compile_rule`, `llm_run`):

| Step | This run | Previous integrated run |
|---|---|---|
| Normalizer (6 sentences → 11 checks) | 6.9 s | 19.4 s |
| One rule, tester + coder + tests + impact check (10 rules right first time) | p50 10.8 s, max 18.4 s | p50 18.6 s, max 33.8 s |
| Coder attempts | 1 for every rule | - |
| Norm → rules active | 102.9 s wall, 10 of 11 active | 84.7 s, 11 of 11 |

The eleventh rule failed after 85 s: the coder's model generated until it hit the provider's
default output limit and returned nothing (`UnexpectedModelBehavior`). That is not a provider
error, so the fallback chain did not switch (ADR 0019); the rule stayed `draft` with the
error, as designed, and `POST /rules/23/compile` made it active in 103 s (the tester call alone
took 98 s). One slow call dominates a norm's wall time; the median rule takes about 11 s.

## 3. Cost model, in tokens

Deciding an invoice costs **0 tokens**: rules are code, the engine and the export are
deterministic (ADR 0002, 0003). Tokens are spent only when:

| Event | Agent calls | Tokens measured (input / output) |
|---|---|---|
| A rule compiles | tester 1 + coder × attempts | tester 2.6k / 2.4k; coder 6.5k / 0.9k per attempt → **~12.4k per rule** at 1 attempt |
| A norm is normalized | normalizer 1 | 3.4k / 2.8k for the 6-sentence norm |
| Whole norm (normalizer + 11 rules, recompile included) | 24 calls | **106.1k / 42.4k = ~149k** |
| A person asks for a suggestion on an escalated case | assistant 1 | 2.4k / 1.3k = **~3.7k** (3 cases) |

Averages from `GET /processes/1/metrics` (`llm`, by model and role) over this run. The
previous integrated run: normalizer 3.4k / 3.8k, tester ~2.6k / 2.8k, coder ~6.4k / 1.2k.
The assistant has no model in the invoice use case (platform default `anthropic:claude-opus-5`);
for this measurement it ran on `helmcode:deepseek-v4-flash` (`TRACE_ASSISTANT_MODEL`).
The failed coder call recorded 0 tokens; a provider may still bill what it generated.

```
tokens(month) = norms_changed × (normalizer + rules × (tester + coder × attempts))
              + escalations_asked × assistant
              ≈ norms_changed × (6.2k + rules × (5.0k + 7.4k × attempts)) + escalations_asked × 3.7k
```

Invoice volume is not in the formula: 500 or 500,000 invoices cost the same tokens. Example
(assumed volumes, not measured): 10,000 invoices a month, two norm changes of 11 rules each,
and the assistant opened on every escalation at batch 1's rate (31/500 = 6.2 %, so 620):
2 × 149k + 620 × 3.7k ≈ **2.6M tokens a month**, 88 % of it the optional assistant.

**In currency (optional).**
- *Helmcode, what we run:* flat rate for its open models, so the cost does not depend on
  tokens up to the key's limits: 100 requests/min, 5 concurrent per model, 2M tokens/min. A
  whole norm is 24 requests and ~149k tokens, far below them.
- *Illustrative only, with public list prices of frontier models (Anthropic, cached
  2026-06-24):* Claude Opus 5 at $5 / $25 per million input / output tokens puts a whole norm
  at ~$1.59 and an assistant suggestion at ~$0.04, so the example month is ~$30; Claude Sonnet
  5 at $2 / $10, ~$0.64 and ~$0.02, ~$12.5. The engine is $0 either way.

## 4. Limits and bottlenecks

- **OCR.** Scans are 6 % of batch 1 and seconds each; text PDFs are milliseconds. Workers
  (`TRACEPAY_WORKERS`, 1-8) and OCR threads (1-16) are the knobs; one Uvicorn per data
  directory (a lock).
- **The quadratic rule.** Every rule has a 10 s sandbox timeout. R16 took 3.25 s over 4,710
  instances; growing as n², it would reach the timeout near 8,000 instances in the process
  (extrapolated), and a timed-out rule escalates every instance with `RULE_ERROR` (fails
  closed, never pays). Fix when needed: index `others` by purchase order before the loop, or
  raise the timeout.
- **Rules run one after another** on one core; the machine has 14. Running the per-rule
  subprocesses in a thread pool would divide engine time by about the core count.
- **Rate limits** on norm changes: 5 concurrent requests per model (`compile_concurrency: 5`)
  and 100 requests/min. A norm of 50 rules is ~100 requests: about a minute of quota.
- **Slow or runaway LLM calls** set a norm's wall time (above: 85 s and 98 s calls against an
  11 s median). A `max_tokens` in the roles' `model_settings` would cut the runaway case
  sooner; it is configuration, not code.
- **One API process.** Background compilations run in the API's own event loop
  (`BackgroundTasks`), so a norm's compilation shares it with requests; a killed process loses
  in-flight compilations (the rules stay `compiling` and are recompiled by hand).
- **Synchronous span inserts:** one insert per trace on the event loop, milliseconds; a
  writer thread if it shows in latency (ADR 0018).
- **Memory:** 352 MB peak RSS for the whole batch-1 run (`/usr/bin/time -l`); each sandbox
  subprocess holds the sources and the population as JSON. On Linux the sandbox caps a rule at
  512 MB of address space; macOS cannot.

## 5. Evolution: what changes for a new input

| New input | Config | Connector | Prompt | Schema | Code |
|---|---|---|---|---|---|
| **Scanned PDFs** | Download the OCR weights; optionally a VLM or Gemini key (`TRACEPAY_*`) | - | - | - | None: the OCR path exists (`docs/ingestion/`) |
| **Spreadsheets** (another workbook) | Column mapping to the rules' names | Existing workbook upload (`POST /processes/{id}/sources/workbook`) | - | - | None if it maps to known sources; a new sheet layout may need a reader |
| **Emails** | - | New: read `.eml`, pass attachments to the PDF path, body as text | Extraction guidance if the body carries fields | New symbols if the email adds data | Yes, a small reader; the engine and rules do not change |
| **A new ERP or API** | Its entry in `<pack>/sources.json` (URL, auth, pagination, fields, retries, rate limit) | The HTTP connector | - | Source columns mapped to the rules' names | None for XML with form-token auth; a JSON or OAuth API adds a branch in `http_connector.py` (ADR 0013) |
| **A new use case** (e.g. travel expenses) | A process pack (`processes/travel-expenses.json`: decision types, symbols, rules) and its `use-case.json` (description, agent settings) | Its sources, as above | Guidance and examples live in `use-case.json` (ADR 0011) | Its symbols and decision types, declared in the pack | None (ADR 0007) |
| **A new norm version** | - | - | - | - | None: `POST /processes/{id}/norm`; ~12.4k tokens and ~11 s per new rule; checked against past decisions before it changes anything (ADR 0004, 0017) |

## Related

ADR 0002, 0004, 0005, 0007, 0011, 0013, 0017, 0018, 0019; `docs/runbook-batch2.md` (timings
of the batch-2 rehearsal); `docs/ingestion/` (OCR benchmarks).
