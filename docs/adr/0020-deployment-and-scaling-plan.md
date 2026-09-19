---
status: proposed
---

# Deploy as one small server with a remote LLM, and scale by measured triggers

## Context
The jury weighs scale and cost at 25 of 100 points and asks where the system breaks, what it
costs and how it grows. What is already true:
- Deciding runs no LLM and costs 0 tokens (ADR 0002); tokens are spent only when a norm
  changes (~150k per norm, ~12.4k per rule) or a person asks the assistant (~3.7k).
- Measured on 2026-09-19 (`docs/scale-and-cost.md`, `demo-logs/scale/`): 500 invoices decide in
  0.8 s, but the sandbox runner builds `others` for every instance of every rule, so the engine
  is quadratic in the process's population: the duplicate-order rule takes 9.4 s of its 10 s
  limit at 8,000 invoices, and at 50,000 all 16 rules time out and every invoice escalates.
- OCR is the ingestion bottleneck (1.2 s median per scan, 25 ms per text PDF) and peaks at
  2.6 GB of RAM with the default workers.
- Background compilation lives in the API process (ADR 0004): one API process only.
- A norm check whose compile fails (for example every model rate-limited, ADR 0019) ends
  `draft`, which the engine does not run: the older rule set decides without it.

## Alternatives considered
- **Build for scale now: Kubernetes, a queue, a sandbox pool and partitioned tables.**
  - Pros: ready for millions of invoices.
  - Cons: a weekend MVP with no second tenant; each piece is operational cost before any
    metric asks for it; contradicts "one implementation, no abstraction for a second case".
- **Stay as is and document the limits.**
  - Pros: no work.
  - Cons: the 8k-population ceiling arrives after 16 batches of 500; the failed-compile gap
    can pay an invoice a new norm forbids.
- **One small server with a remote LLM, and a list of scaling steps each gated by a metric of
  our own spans (chosen).**
  - Pros: €6-10 a month of infrastructure; every step is justified by a number the system
    already records (`GET /processes/{id}/metrics`); the same containers move to Kubernetes or
    a cloud without a rewrite.
  - Cons: someone has to watch the triggers; the first steps (H1-H3) are code, not config.
- **Air-gapped with a local LLM as the default.**
  - Pros: no data leaves the company.
  - Cons: needs a 20-48 GB GPU for a 30B-class model; an 8B model failed our real compile
    (measured); only worth it when the client requires it.

## Decision
- **Baseline deployment:** API, Postgres, OCR and sandbox on one server (2-4 vCPU, 4-8 GB; with
  4 GB set `TRACEPAY_WORKERS=1`, `TRACEPAY_OCR_THREADS=2`), the LLM remote (Helmcode or any
  PydanticAI provider), spans in Postgres and optionally Logfire's free tier. Scenarios (ii)
  own infrastructure, (iii) managed cloud and (iv) air-gapped are in `docs/scale-and-cost.md`
  section 7; (iv) requires a model that passes `make eval-compiler` and `make eval-norm`.
- **Scaling order, each step on its trigger** (`docs/scale-and-cost.md` section 8):
  H1 `others` only for rules that read it plus an index for population rules (population
  ≥ 3,000 or `evaluate_rule` p95 ≥ 3 s); H2 chunks and a sandbox worker pool (slowest rule
  ≥ 5 s or any timeout); H3 compile moved to a queue and one worker (before a second API
  replica); H4 API replicas; H5 OCR workers; H6 engine in a worker; H7 monthly partitions of
  `events`; H8 read replica; H9 PDFs to object storage; H10 a second LLM key or provider.
- **Fail closed on a failed compile:** a norm check that ends `draft` with a compile error is
  enforced like a `blocked` rule (every instance escalates with the error) until it compiles,
  as ADR 0016 requires of a rule that cannot be evaluated. Not built yet.
- **Cost is tracked in three parts** (`C_tokens + C_infra + C_people`) with the formulas of
  section 6; tokens and span counts come from our own metrics.

## Consequences
- Until H1 ships, a process holds about 8,000 invoices before its duplicate rule times out; a
  timeout escalates, never pays, but floods the manager's queue. Archiving old batches into a
  separate process is the stop-gap.
- Until H3 ships, the API cannot run as several replicas.
- With the fail-closed change, a provider outage during a norm change escalates invoices the
  new check covers instead of deciding them under the old norm: louder, but correct.
- The deployment prices are references read on one date; they change (Hetzner raised prices
  twice in 2026).
- The people who resolve escalations dominate the monthly cost at 10,000 invoices; the
  escalation rate, not the infrastructure, is the lever.

## Evidence
- `demo-logs/scale/02-capacity-500-5k-8k.txt`, `03-capacity-50k.txt` (`tools/bench_scale.py
  capacity`): 500 / 5k / 8k / 50k at 0.79 / 13.1 / 29.5 / 163.9 s; R16 9.38 s at 8k; 16
  timeouts and 47,100 `RULE_ERROR` at 50k; simulated fix 31.2 s at 50k.
- `04-api-run.txt`: real `POST /processes/1/run` of 4,500 over 5,000 in 13.5 s, API RSS 348 MB.
- `05-storage-*.txt`: ≈ 25 kB per invoice through the upload API, 4.5 kB per further decision.
- `06-ingest.txt`: 500 PDFs in 74.4 s, scan median 1,216 ms, 2.64 GB peak RSS.
- `08-ollama-compile.txt`: `llama3.1:8b` 384 / 38.5 tokens/s, R02 and R16 compiles failed.
- Code: `agents/sandbox.py` (`_RUNNER` builds `others`), `rules/service.py`
  (`compile_in_background` leaves `draft`), `rules/model.py` (`ENFORCED`).
- Helmcode limits: helmcode.com/docs/rate-limits (100 rpm, 5-10 concurrent per model, 429 with
  `Retry-After`), read 2026-09-19.

## Related
ADR 0002, 0004, 0005, 0016, 0017, 0018, 0019, 0021; `docs/scale-and-cost.md`.
