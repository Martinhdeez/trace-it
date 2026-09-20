# Scale and cost

How much data trace-it processes, on what hardware, where it breaks, what it costs and how it
grows. Every figure says whether it was **measured** (with the command or log behind it) or
**estimated** (with its arithmetic). Measurements are from 2026-09-19. Raw outputs:
`demo-logs/scale/`. The decision behind the deployment and scaling plan: ADR 0020.

For a separate Windows run with the full Gemini/Jev OCR committee, see the
[500-document benchmark](ingestion/benchmark-2026-09-19.md): 19 min 11.7 s end to end,
73 real provider requests and USD 0.02768012 of attributable token cost, plus one
failed request with unknown usage. Its CPU, reader configuration and commit differ
from the measurements below; do not combine their throughput or memory figures.
Current [OCR modes and billing configuration](ingestion/providers-and-modes.md)
explain local/API/hybrid operation and Helmcode's account-dependent costs.

**Headline.**
- Deciding costs **0 tokens** and no LLM runs per invoice (ADR 0002). Tokens are spent when a
  norm changes (**~150k tokens per 6-sentence norm, ~12.4k per rule**) and, optionally, when a
  person asks the assistant about an escalated case (~3.7k).
- The engine decides **500 invoices in 0.8 s** with 16 rules (measured). It is linear up to a
  few thousand invoices and then **quadratic**: at **8,000 invoices** in a process the
  duplicate-order rule takes 9.4 s of its 10 s limit, and at **50,000 every rule times out**,
  so all 47,100 invoices with data escalate (`RULE_ERROR`). Nothing is paid by mistake, but
  every invoice goes to a person. The cause and a measured fix (50,000 in 31 s, linear) are in section 3.
- Ingestion is bound by **OCR**: scans are 6 % of batch 1 and 76 % of its ingestion time
  (1.2 s median per scan against 25 ms per text PDF), and OCR peaks at **2.6 GB of RAM**.
- A month of 10,000 invoices costs about **2.6M tokens**; the people who resolve escalations
  cost more than the machines and the tokens together (section 6).

## 1. Hardware and conditions

| | |
|---|---|
| Machine | MacBook Pro `Mac16,7`, Apple M4 Pro, 14 cores (10 performance + 4 efficiency), 24 GB RAM, macOS 26.5 (`sysctl hw`, `demo-logs/scale/00-hardware.txt`) |
| Python | CPython 3.12.13 (uv), backend on the host; benchmarks in process (`httpx.ASGITransport`) or through a temporary Uvicorn on :8050 |
| Database | PostgreSQL 16.15 in Docker (VM: 14 CPUs, 7.75 GB), databases `trace_bench` (section 2) and `trace_scale` (sections 3-5) |
| Sandbox | One `python -I -S -B` subprocess per rule per run, over all instances at once (ADR 0005), 10 s limit per rule |
| ERP | The challenge's `alberto_erp.py` on :8009, with its built-in latency and faults |
| LLMs | Vercel AI Gateway `zai/glm-5.3` for every role, with Helmcode `deepseek-v4-flash` / `qwen3.6` fallbacks (ADR 0019), `TRACE_COMPILE_CONCURRENCY=5`; one local probe with Ollama `llama3.1:8b-instruct-q4_K_M` |
| OCR | Local ONNX readers, 98 MB of weights (`.models/`), CPU only, `TRACEPAY_WORKERS=2`, `TRACEPAY_OCR_THREADS=4` (defaults) |
| Data | Batch 1: 500 PDFs (471 with a text layer, 29 scans), the challenge workbook, 516 ERP rows; synthetic copies for 5k-50k |

Reproduce (see the docstring of `tools/bench_scale.py`): `make setup` on a scratch database,
`make erp`, `make demo`, then `bench_scale.py engine | extract | upload | workbook | capacity |
grow`. `CHALLENGE_DIR` points at the corpus if the submodule lives elsewhere. The 500-invoice
fill of `trace_scale` (`01-demo-run-500.txt`) used the earlier text-layer `demo_run.py`; the
current `make demo` goes through the production upload API with OCR (ADR 0022,
`docs/ingestion/setup.md`), whose per-file cost is the ingestion table below.

## 2. Measured throughput at batch size (500)

### Engine (deciding)

| Rules | Instances | Run | Median | Per second | `evaluate_rule` p50 / p95 |
|---|---:|---|---:|---:|---|
| 16 hand-written | 500 | `run_process`, 1 run, writes 500 decisions | 1019 ms | 491 | - |
| 16 hand-written | 500 | `reprocess?dry_run=true`, 3 runs: 822 / 876 / 851 ms | 851 ms | **588** | 38 / 91 ms |
| 11 generated from the norm | 500 | same, 3 runs: 554 / 570 / 556 ms | 556 ms | **899** | 39 / 67 ms |

A dry-run reprocess is the engine alone (same `decide_all` as a run, nothing written);
`run_process` adds the 500 decision rows and their spans. Rules run one after another, about
35-40 ms each at this size (18 ms to start an empty subprocess), so fewer, generated rules
beat the 16 hand-written ones. A new `make demo` into `trace_scale` (ingest, ERP sync, run,
export) took 16 s inside the script, `PAGAR 433 / NO_PAGAR 36 / ESCALAR 31`, 306 MB peak RSS
(`01-demo-run-500.txt`).

### Ingestion, per file type (measured, `06-ingest.txt`, `07-workbook.txt`)

Through `POST /processes/{id}/files`, one sequential client, cold cache, local OCR only (no
Gemini, VLM or JEV key):

| File type | Files | Median | Max | Total | Notes |
|---|---:|---:|---:|---:|---|
| Text PDF (native text layer) | 471 | **25 ms** | 78 ms | 12.0 s | `native_text` p50 2 ms |
| Scanned PDF (OCR, two readers) | 29 | **1,216 ms** | 8,872 ms | 56.4 s | 58 `ocr` spans, p50 823 ms, max 6.9 s; all 29 got symbols |
| Workbook (31 kB XLSX) | 3 loads | **66 ms** warm | 172 ms cold | - | `POST /processes/{id}/sources/workbook` |
| Whole batch | 500 | - | - | **74.4 s, 6.7 files/s** | 176 CPU-s (OCR is multi-threaded), **2.64 GB peak RSS** |

The demo path (`tools/extractor.py`, pdftotext + regex, no OCR) reads the 500 in 4.9 s
(101/s) and leaves the scans without symbols. So a scan costs seconds and about 5.6 CPU-s
(estimated: (176 − 12) / 29), a text PDF milliseconds. The earlier benchmark with OCR on
Windows (`docs/ingestion/benchmark-summary.json`, 32 threads) gave 3.53 files/s cold and a
Gemini page call a median of 2.6 s (`docs/ingestion/gemini-ocr.md`).

### ERP sync

`POST /processes/{id}/sources/erp/sync`, 3 runs: **516 rows, 26 pages, median 5.4 s
(96 rows/s)**, 2-3 `ORA-00600` retried per run, 0 rate-limited answers. The floor is our own
client limit (6 requests/s in `processes/invoice-payment/sources.json`) plus the ERP latency.

### Rule compilation (norm → rules)

`POST /processes/1/norm` with the six sentences of `Norma_Pagos_v3` on an empty rule set:

| Step | This run | Previous integrated run |
|---|---|---|
| Normalizer (6 sentences → 11 checks) | 6.9 s | 19.4 s |
| One rule: tester + coder + tests + impact check | p50 10.8 s, max 18.4 s | p50 18.6 s, max 33.8 s |
| Norm → rules active | 102.9 s, 10 of 11 active | 84.7 s, 11 of 11 |

The eleventh rule failed after 85 s: the coder hit the provider's default output limit and
returned nothing. **Fixed** (ADR 0019): every role has a `max_tokens`, and an answer cut by it
moves to the next model of the chain.

## 3. Capacity: where the engine breaks (measured, `02-capacity-*.txt`, `03-capacity-50k.txt`)

`bench_scale.py capacity`: the real engine (`engine.decide`) and sandbox, 16 hand-written
rules, batch 1's 500 instances copied up to *n* (each copy with its own name and purchase
order), the whole population as `others`, nothing written.

| Instances | Sequential (today) | Per second | Slowest rule | Child RSS | `stdin` per rule | 4 workers | 14 workers | Fix path, sequential |
|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 500 | 0.79 s | 629 | R14 0.09 s | 22 MB | 0.4 MB | 0.30 s | 0.36 s | 0.67 s |
| 5,000 | 13.1 s | 381 | R16 3.84 s | 48 MB | 2.6 MB | 6.45 s | 6.03 s | 3.47 s (1,443/s) |
| 8,000 | 29.5 s | 271 | **R16 9.38 s (limit 10 s)** | 63 MB | 4.1 MB | 14.5 s | 13.9 s | 5.28 s (1,515/s) |
| 50,000 | 163.9 s | - | **all 16 time out** | 269 MB | 24.8 MB | 41.5 s, 16 time out | 20.6 s, 16 time out | **31.2 s (1,605/s)**, slowest 6.4 s |

- **Per worker (measured):** one sandbox subprocess uses one core (child CPU ≈ wall: 12.5 CPU-s
  for 13.1 s at 5k) and 22 MB at 500 → 269 MB at 50k (about 5 kB per instance plus ~20 MB).
  On Linux the sandbox caps it at 512 MB of address space: about 100k instances (estimated).
- **Parallel (measured):** running the 16 subprocesses at once helps 2.6× at 500 and ~2.2× at
  5k-8k, not 14×: the parent serialises 16 copies of the population to JSON under one GIL,
  and the slowest rule is the critical path.
- **Why it is quadratic (from the code):** the sandbox runner builds, for **every instance of
  every rule**, a fresh `others` list of the other n − 1 instances
  (`sandbox.py`, `_RUNNER`), even for the 15 rules that never read it. R1 goes 0.04 s → 0.52 s
  → 1.10 s from 500 to 8k (≈ n²). R16 (duplicate purchase order) then scans that list again.
  R16 breaks first at ~8k; as n², R14 (2.05 s at 8k) would reach 10 s near 8k × √(10 / 2.05) ≈
  **18k** and the other rules by ≈ 24k (estimated).
- **What a timeout does (measured):** the rule fails for every instance, the engine escalates
  them with `RULE_ERROR <id>: Timed out (10.0s)` (ADR 0016): 47,100 `ESCALAR` at 50k (the
  2,900 scans were already `MISSING_DATA`). It fails closed: nothing is paid by mistake.
- **The population is every instance of the process**, not the batch being decided, so the
  limit is reached by history (16 batches of 500), not by batch size.
- **Real API run at 5k (measured, `04-api-run.txt`, Uvicorn on :8050):** `POST
  /processes/1/run` decided 4,500 pending over a population of 5,000 in **13.5 s**
  (333/s, 4,500 decision rows and their spans written); a dry-run reprocess of 5,000 took 13.5 s; API
  RSS 220 MB idle → 348 MB peak. (The copies' purchase orders are not in the ERP, so most are
  `NO_PAGAR`: the mix is synthetic, the work per rule is the same.)

**Fix path** (measured as a simulation in `bench_scale.py`, not in the product yet):
1. Build `others` only for a rule whose code reads it (an AST check at compile time). The 15
   single-invoice rules become linear.
2. Give population rules an index built once per run instead of a scan: the platform adds a
   derived source (instances grouped by the symbol the rule compares, e.g. `purchase_order`),
   or the rule contract gets an optional `prepare(population)` run once per subprocess.
   Simulated with R16 on a purchase-order index: 50,000 in **31.2 s, 1,605/s**, slowest rule
   6.4 s.
3. Chunk instances (e.g. 10,000 per subprocess) so no subprocess approaches the time limit,
   and run chunks and rules in a pool of `cpu − 1` workers: at 50k, about 31 s / 8 ≈ **4-6 s**
   (estimated). With 1-3 the engine is linear; raising the timeout alone only moves the wall.

## 4. Storage: Postgres growth (measured, `05-storage-*.txt`)

| What | Bytes | How measured |
|---|---:|---|
| One invoice, whole row set via the upload API | **≈ 25 kB** | PDF + text 13.6 kB (`files`), instance 2.4-2.7 kB, decision 1.7-1.8 kB, spans ≈ 7.5 kB (below) |
| One invoice, demo path (no upload spans) | ≈ 19.9 kB | same without the upload spans |
| One more decided invoice (no new file) | **4.5 kB** | database 19.3 MB → 39.7 MB for 4,500 decisions (`trace_scale`) |
| Span, average including indexes | 571-954 B | `pg_total_relation_size('events') / count` (5,572 and 1,038 spans) |
| Upload spans per invoice | ≈ 6.4 kB + 0.7 kB indexes | `trace_demo`: `ingest_document` 5.0 kB (the evidence), `extraction` 0.64 kB, `upload_document` + `store_file` + `native_text` 0.54 kB |
| `decision` span | 353 B | one per invoice per run |
| `llm_run` span | tester 4.9 kB, compiler 7.7 kB, normalizer 8.6 kB, assistant 4.6 kB | average row, compressed (TOAST); the prompt and the answer are kept whole (ADR 0018) |
| One compiled rule | ≈ 14 kB | tester + compiler `llm_run` + 5 small spans (estimated from the rows) |
| One norm (11 rules) | ≈ 165 kB | normalizer + 11 rules (estimated) |

```
DB_bytes ≈ invoices × 25 kB + reruns × invoices × 2.1 kB + norms × 165 kB + assistant_asks × 5 kB
```

Example (estimated): 10,000 invoices a month, one re-decision each, 2 norms: 271 MB a month,
**3.3 GB a year**. 1M invoices a year: ≈ 27 GB. The PDFs are half of it; moving `files.content`
to object storage leaves ≈ 11 kB per invoice in Postgres.

## 5. Rate limits and resilience

### Provider limits

| Limit (Helmcode, per API key) | Value | Source |
|---|---|---|
| Requests | **100 per minute** | helmcode.com/docs/rate-limits, read 2026-09-19 |
| Concurrency | **5 per model**; 10 on DeepSeek V4 Flash, GLM 5.3, GLM 5.3 Flash | same |
| Tokens | 2M per minute (docs); the pricing page says 3M | same, helmcode.com/pricing |
| Monthly volume | DeepSeek V4 Flash and GLM 5.3 Flash count against a cap: 5B tokens on Starter; Qwen and Gemma unlimited | helmcode.com/pricing |
| Over the limit | `429 Too Many Requests` with `Retry-After` | helmcode.com/docs/rate-limits |
| Per day | none published | - |

Other providers (Anthropic, OpenAI, Gemini) publish tiered limits per organisation; for a key we
do not hold we write "unknown, assumed at least Helmcode's".

**Our demand (measured → estimated).** A whole norm is 24 requests and ~150k tokens in ~100 s:
~14 requests and ~90k tokens a minute, **14 % of the request limit and 4.5 % of the token
limit**. With `TRACE_COMPILE_CONCURRENCY = c` and ~11 s and 2 requests per rule, a norm
sends about `c × 2 × 60 / 11 ≈ 11 c` requests a minute: `c = 5` → 55/min, safe; `c ≈ 9` reaches
100/min. A norm of 50 rules at `c = 5` takes ~2 minutes and never trips the limit.

### What happens when we hit one (from the code)

1. The OpenAI SDK retries a 429 or 5xx twice, honouring `Retry-After`.
2. Then `FallbackModel` moves to the next model of the role's chain (ADR 0019). A 429 on
   concurrency is per model, so the fallback helps; a 429 on **requests per minute is per key**,
   so every model of the same key shares it and the chain only helps if it spans keys or
   providers.
3. All models fail: `AgentError` 502; the rule leaves `compiling` as `blocked` with
   "every model failed: ..." in its report (every instance escalates with
   `RULE_COMPILE_FAILED` until it compiles, ADR 0020) and an `llm_run` span in `error` (ADR 0018).
4. While any rule is `compiling`, `run` and `reprocess` refuse (409): no invoice is decided
   half-way through a norm (ADR 0017).
5. The rules already `active` keep deciding at 0 tokens; the assistant answers 502 and the
   case stays in the manager's queue.

**Known gap: a norm check whose compile failed is not enforced.** It ends `draft`, and the
engine runs only `active` and `blocked` rules, so the older rule set decides and an invoice
the new check would have stopped can be paid. ADR 0020 fixes it by treating such a check like
a `blocked` rule (every instance escalates with the error) until it compiles, which is what
ADR 0016 promises for a rule that cannot be evaluated.

**Superseded by ADR 0031 (atomic publication):** step 3 and this gap no longer apply. A rule
whose compile fails stays a `draft` that cannot be published, so the published version keeps
deciding with its complete rule set; there is no `blocked` / `RULE_COMPILE_FAILED` for it.

### Budget per day, and running out

```
tokens(day) = norm_changes(day) × 150k + assistant_asks(day) × 3.7k [+ reviews(day) × T_review]
```

`T_review` applies only when the optional decision reviewer (ADR 0021) is on: then there is one
LLM call **per decided invoice**; it is off by default and not measured (assume the
assistant's 3.7k). On Helmcode Starter the 5B tokens/month cap is ~166M a day, about 1,100
norms: the budget is not a practical limit. On a per-token provider, set a daily cap at the
provider and alert at 80 % (`llm` tokens by model and role in `GET /processes/{id}/metrics`).
When tokens run out (cap, prepaid credit, 402/429), steps 1-5 above apply: new rules do not
activate, deciding continues at 0 tokens with the rules in force, nothing is paid on a rule
that did not compile once the gap above is closed.

**When to escalate to a person:** a rule ends `draft` with "every model failed" (the manager
retries or rolls back the norm); `llm_run` errors above 5 % in an hour; tokens above 80 % of the
day's budget; a norm not active after 10 minutes.

## 6. Cost formula

Three parts, per month: `C = C_tokens + C_infra + C_people`.

### (a) Tokens

| Variable | Meaning | Measured value |
|---|---|---|
| `T_t` | tester, per rule | 2.6k in / 2.4k out = 5.0k |
| `T_c` | coder, per attempt | 6.5k in / 0.9k out = 7.4k |
| `a` | coder attempts per rule | 1 (every rule of the last three runs) |
| `T_n` | normalizer, per norm | 3.4k in / 2.8k out = 6.2k |
| `R` | rules (checks) per norm | 11-12 for `Norma_Pagos_v3` |
| `N` | norm changes in the month | - |
| `E`, `T_a` | escalations a person asks the assistant about; 3.7k each | 2.4k / 1.3k |
| `L`, `T_l` | on-demand norm proposals from past cases (`docs/learning.md`) | not measured |
| `I` | invoices | **0 tokens each** |

```
T_rule   = T_t + a × T_c                ≈ 12.4k tokens        (per rule)
T_norm   = T_n + R × T_rule             ≈ 142k-150k tokens    (per norm; measured 149k and 150.6k)
T_change = T_norm today (a new norm is a new set of norm rules, ADR 0017);
           T_n + R_changed × T_rule once re-normalising one sentence is built
tokens(month) = N × T_norm + E × T_a + L × T_l  (+ I × T_review if the decision reviewer is on)
```

Measured totals: whole norm 106.1k in / 42.4k out = 149k (24 calls); integrated run 103.1k /
47.7k = 150.8k (23 calls); coverage run 109.5k / 40.9k = 150.4k including one assistant call.

### (b) Deployment and infrastructure

```
C_infra = C_api + C_db + C_storage × GB + C_ocr + C_vlm + C_obs + C_llm
GB      = section 4 (≈ 25 kB per invoice, ≈ 11 kB with PDFs in object storage)
C_llm   = flat subscription, or tokens(month) × price per token
```

Reference prices (EUR or USD as published, excluding VAT, read 2026-09-19):

| Item | Price | Source |
|---|---|---|
| Hetzner CX23, 2 vCPU / 4 GB | €5.49/month | costgoat.com/pricing/hetzner (Sep 2026) |
| Hetzner CX33, 4 vCPU / 8 GB | €8.49/month | same |
| Hetzner CX43, 8 vCPU / 16 GB | €15.99/month | same |
| Hetzner GEX44, RTX 4000 Ada 20 GB | €184/month + setup (reports of €234 after 2026 changes) | hetzner.com press room; bex.co, 2026-07-13 |
| AWS RDS PostgreSQL db.t4g.medium (2 vCPU / 4 GB) | $0.065/hour ≈ $47/month single-AZ | instances.vantage.sh/aws/rds/db.t4g.medium |
| Helmcode Starter (5 keys, flat) | €399/month | helmcode.com/pricing |
| DeepSeek V4.1 Flash, per 1M in / out / cached in | $0.30 / $1.20 / $0.006 | benchlm.ai/deepseek/api-pricing, read 2026-09-19 |
| DeepSeek V4 Flash, per 1M in / out / cached in | $0.14 / $0.28 / $0.0028 | same |
| Claude Opus 5 / Sonnet 5 (per 1M tokens in / out) | $5 / $25; $2 / $10 | Anthropic public list prices, cached 2026-06-24 |
| Logfire Personal | free, 10M records/month, 30 days | pydantic.dev/pricing |
| Logfire Team | $49/month, then $2 per 1M records | same |
| Arize Phoenix, self-hosted | $0 (runs in our compose profile) | `docker compose --profile observability` |

Helmcode publishes no per-token rate, so PydanticAI cannot price a run on it and an
`llm_run` span would carry no cost at all. The span is priced at the answering model's public
list price above (`_RATES` in `agents/llm.py`), which answers what the tokens would cost per
token elsewhere; it is not our invoice, which is the flat subscription. A model with neither a
provider price nor a listed rate records no cost, and the demo driver counts those calls
separately rather than reporting them as free.

OCR runs on CPU with 98 MB of local weights: no per-page price. A vision model or Gemini is
optional and per page. A span is one record for Logfire: at ≈ 7 spans per invoice, 10,000
invoices are ≈ 70k records a month, 0.7 % of the free tier.

### (c) People and operations

```
C_people = I × e × t_case × rate_manager + H_ops × rate_engineer
```

`e` is the escalation rate. In the delivered run (`delivery/outcomes.jsonl`) it is
28 / 500 = **5.6 %**, and 26 of those 28 are scans whose fields the reader did not extract;
only 2 are a genuine business doubt, so `e` falls toward 0.4 % when every scan is read.
An earlier run without OCR gave 31 / 500 = 6.2 %. `t_case` is minutes per case and `H_ops`
engineer hours a month (backups, upgrades, norm changes). The worked example below keeps
6.2 % as a conservative upper bound.

### Worked example (10,000 invoices a month, 2 norm changes; assumptions marked)

| Part | Arithmetic | Month |
|---|---|---|
| Tokens | 2 × 150k + 620 escalations × 3.7k (assistant on every one) | **2.6M tokens** |
| … on Helmcode Starter | flat | €399 (0.05 % of its cap) |
| … or per token, Sonnet 5 / Opus 5 (illustrative) | ≈ 1.7M in + 0.9M out at the list prices | ≈ $12 / $31 |
| Infrastructure, scenario (i) | CX33 €8.49 + backups (assumed €2) + Logfire free | **≈ €10** |
| Storage | 10,000 × 25 kB = 250 MB/month | included |
| People | 620 × 3 min (assumed) × €35/h (assumed) + 4 h × €60/h (assumed) | **≈ €1,325** |

At this volume the people who resolve escalations are most of the cost (76 % with the flat
subscription, 98 % with a per-token API); the levers are the
escalation rate (OCR, cleaner sources) and the time per case (the evidence on screen). A flat
LLM subscription pays off only above ~80M tokens a month at Sonnet-class prices (estimated:
€399 / ≈ $4.8 per 1M blended in this mix, € ≈ $).

## 7. Deployment scenarios

| | (i) Small company | (ii) Own infrastructure | (iii) Cloud, managed | (iv) Air-gapped, local LLM |
|---|---|---|---|---|
| Compute | 1 VM, 2-4 vCPU / 4-8 GB, no GPU | Kubernetes: API ×2-3, compile worker ×1, OCR workers ×n | Containers (ECS Fargate / Cloud Run / Container Apps) | On-prem servers + 1 GPU server |
| Postgres | Same VM, daily `pg_dump` | Managed or operator (CloudNativePG), read replica | RDS / Cloud SQL / Azure Flexible Server | Local, replicated |
| OCR | CPU, 1 worker, 2 threads | CPU pool, GPU optional (`TRACEPAY_OCR_CUDA=1`) | CPU tasks, scaled on queue length | CPU or the GPU |
| LLM | Remote (Helmcode or a per-token API) | Remote, or vLLM on own GPUs | Provider API (Bedrock / Vertex / Azure OpenAI) or Helmcode | vLLM or Ollama, 30B-class model |
| Observability | Logfire free tier | Phoenix self-hosted or Logfire Team | Logfire, or the cloud's OTLP collector | Phoenix self-hosted |
| Throughput (estimated) | ~15-20 text PDFs/s, ~1 scan per 3-6 s, 500 decided in ~2 s (estimated) | engine 1.5k-10k/s after the fix path (estimated) | same as (ii) | same as (i)-(ii); compile ~2 min per rule |
| Monthly cost, infra only (estimated) | €6-10 | depends on the cluster; ≈ €200-400 extra | ≈ $150-250 | GPU server €184-234 + hardware |

**(i) Pessimistic: one small server.** API, Postgres, OCR and the sandbox on one 2 vCPU / 4 GB
VM, the LLM remote. The limit is memory: OCR peaked at 2.6 GB with the defaults (measured), so
set `TRACEPAY_WORKERS=1` and `TRACEPAY_OCR_THREADS=2` or take the 8 GB CX33 (€8.49). The
engine runs one rule at a time on one core: 500 invoices in about 2 s and 5,000 in about 30 s
(estimated at half the M4's per-core speed). Enough for thousands of invoices a month; the
8k-population ceiling of section 3 applies until the fix path ships. The LLM stays remote: it
is used only when a norm changes, so a remote API costs a few euros and needs no GPU.

**(ii) A tech company with its own infrastructure.** Stateless API replicas behind a load
balancer, but the background compile must move out first: today it runs in the API process,
and several API workers would each re-queue the same `compiling` rules on startup (ADR 0004).
One compile worker consumes a queue; OCR runs as its own deployment scaled by queue length;
the sandbox runs as a worker pool (section 3, step 3). Managed Postgres with a read replica for
the console, traces and metrics. GPUs only if they want a local LLM or GPU OCR.

**(iii) A move to the cloud.** The same shape on managed services: containers for API, compile
worker and OCR; RDS / Cloud SQL / Azure Flexible Server for Postgres (db.t4g.medium ≈ $47/month
is plenty for 1M invoices a year, section 4); object storage for the PDFs; a managed queue
(SQS / Pub/Sub / Service Bus); the provider's model API through PydanticAI (`bedrock:`,
`google-vertex:`, `azure:` strings, ADR 0006). Data residency: Helmcode or a regional endpoint
keeps inference in the EU.

**(iv) Fully local or air-gapped.** Everything on-prem, the LLM on vLLM or Ollama. Inference is
needed **only at compile time**, never per invoice: a GPU can be shared or started on demand.
Hardware (estimated, 4-bit weights plus a 16k context): 8B ≈ 6-8 GB VRAM; 14B ≈ 10-12 GB;
30-32B (qwen-class) ≈ 20-24 GB (one 24-48 GB card, e.g. the GEX44's 20 GB is tight, an L40S or
RTX 6000 fits); 70B ≈ 40-48 GB; DeepSeek V4-class MoE needs a multi-GPU node. **Measured
probe** (`08-ollama-compile.txt`): `llama3.1:8b` on the M4 Pro reads 384 tokens/s and writes
38.5 tokens/s, and the real compile of R02 and R16 **failed**: the tester's structured output
was rejected three times (49 s and 93 s). So an 8B model is not good enough. Estimated
compile time with a 30B-class model at similar speed: 9k tokens in / 3.3k out per rule ≈ 24 s
+ 86 s ≈ **2 minutes per rule, 5-20 minutes per norm** depending on batching. Quality risk:
a weaker model misreads more rules; the tests, the blind tester, the impact check and the
fail-closed engine stop wrong code from deciding, but more rules end `draft`. Gate: run
`make eval-compiler` and `make eval-norm` on the chosen model before adopting it.

## 8. Scaling plan

Each step has a trigger read from the three monitoring planes: **ingestion** (`upload_document`,
`extraction`, `ocr` spans), **agents** (`llm_run`, `compile_rule`, tokens by role) and
**execution** (`run_process`, `evaluate_rule`, decisions by cause). All come from our spans
(`GET /processes/{id}/metrics`, `GET /traces`, ADR 0018). `GET /health/planes` already marks a
plane `degraded` at 5 % errors or a p95 over its limit (ingestion 10 s, agents 60 s, execution
5 s over 15 minutes; `TRACE_HEALTH_*`): a plane that stays `degraded` for a day is the signal to
read the table below.

### Horizontal (more volume)

| # | Step | Trigger (metric ≥ threshold) | Plane | Effect |
|---|---|---|---|---|
| H1 | `others` only for rules that read it; index for population rules | population ≥ 3,000, or any `evaluate_rule` p95 ≥ 3 s | execution | linear engine; 50k in 31 s (measured, simulated) |
| H2 | Chunk instances per subprocess + sandbox worker pool (`cpu − 1`) | slowest `evaluate_rule` ≥ 5 s (half the limit) or any `Timed out` | execution | no timeouts; ≈ cores × faster (estimated) |
| H3 | Move background compile to a queue and one worker | a second API replica is needed, or a restart leaves rules `compiling` | agents | API stateless; compiles survive restarts |
| H4 | Stateless API replicas | API p95 ≥ 300 ms or CPU ≥ 70 % sustained | all | linear with replicas (after H3) |
| H5 | OCR as its own worker deployment, then GPU OCR | `upload_document` p95 ≥ 5 s, OCR queue ≥ 100 files, or scans ≥ 20 % of a batch | ingestion | API memory off OCR's 2.6 GB |
| H6 | Engine runs in a worker, decisions written in batches | `run_process` ≥ 60 s or API RSS ≥ 70 % of memory | execution | API stays responsive during runs |
| H7 | Partition `events` by month on `started_at`; index `data->>'role'` for the use case feed | `events` ≥ 10M rows or ≥ 20 GB, or `/traces` p95 ≥ 500 ms | all | cheap retention, fast feeds |
| H8 | Read replica for console, traces and metrics | read queries ≥ 30 % of database CPU | all | writes unaffected |
| H9 | `files.content` to object storage | database ≥ 50 GB | ingestion | ≈ 55 % smaller database |
| H10 | Second LLM key or provider in the chain; shared compile semaphore | `llm_run` 429 or failed attempts ≥ 5 % in an hour, or a norm not active in 10 min | agents | the chain escapes a per-key limit |

### Vertical (more input types)

A new input reaches the rules as symbols through an ingestion reader; the engine and the rules
do not change. A new process or use case is a pack (ADR 0007).

| New input | Reader | LLM? | Config | Code |
|---|---|---|---|---|
| **XML e-invoice (Facturae 3.2, UBL 2.1)** | Parse the XML: every field is typed, no OCR | No | Map XML paths to symbols | A small reader; the best input there is: deterministic, milliseconds |
| **CSV** of invoices or reference data | Rows → instances or a source snapshot | No | Column mapping | Small reader (the workbook reader already maps sheets) |
| **Images** (JPG, PNG, phone photos) | The OCR path already used for scans | Optional VLM | `TRACEPAY_VLM_*` for low-quality photos | Accept image types at upload |
| **Emails** (`.eml`) | Attachments to the PDF / XML readers, body as text | Optional, for fields in the body | Extraction guidance | A small reader |
| **Spreadsheets** (another workbook) | Existing workbook upload | No | Column mapping | None if it maps to known sources |
| **A new ERP or API** | HTTP connector (`<pack>/sources.json`) | No | URL, auth, paging, retries, rate limit | None for XML with form-token auth (ADR 0013) |
| **Scanned PDFs** | Local OCR (weights downloaded) | Optional VLM / Gemini | `TRACEPAY_*` | None |
| **A new use case** (e.g. travel expenses) | Its pack and `use-case.json` | Compile only | Decision types, symbols, rules, agent settings | None (ADR 0007, 0011) |
| **A new norm version** | `POST /processes/{id}/norm` | Compile only | - | None: ~12.4k tokens and ~11 s per new rule, checked against past decisions (ADR 0004, 0017) |

Trigger for a new reader: a use case asks for it, or ≥ 5 % of a month's files arrive in a type
we escalate as unreadable (ingestion plane: `extraction` warnings by `reader`).

## Related

ADR 0002, 0004, 0005, 0007, 0011, 0013, 0016, 0017, 0018, 0019, 0020, 0021;
`docs/runbook-batch2.md` (timings of the batch-2 rehearsal); `docs/ingestion/` (OCR
benchmarks); `demo-logs/scale/` (this document's raw outputs).
