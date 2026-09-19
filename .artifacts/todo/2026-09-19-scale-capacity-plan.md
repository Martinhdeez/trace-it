# Scale, capacity and deployment plan (branch `docs/scale-capacity-plan`)

Goal: answer the rubric's "scale & cost" (25 of 100) with measured limits, a cost formula, four
deployment scenarios and a scaling plan with triggers. Written after the first engine runs had
started (the coordinator asked for the plan mid-task); items 1-3 were already under way.

## What `docs/scale-and-cost.md` covers today vs what is missing

| Topic | Covered | Missing |
|---|---|---|
| Hardware | M4 Pro, 14 cores, 24 GB, Docker VM | `sysctl hw` reference, the new DB `trace_scale` |
| Engine | 500 invoices (16 and 11 rules); sandbox up to 4,710 | 5k and 50k; where it breaks; the real cause of the quadratic cost; parallel workers; fix path measured |
| Sandbox | 18 ms start, 512 MB cap on Linux | CPU and RSS per worker at each size |
| Postgres | nothing | bytes per invoice, per span, per `llm_run`, per decision; growth formula |
| Ingestion | text PDF (API), extractor, OCR not measured (no weights) | OCR measured on this machine (weights now in `.models`), workbook |
| Rate limits | Helmcode 100 req/min, 5 concurrent, 2M tok/min; `compile_concurrency` | what happens on 429 (SDK retries, chain), daily budget, tokens run out, when to escalate |
| Cost | tokens formula, Helmcode flat rate, Anthropic list prices | per-rule/norm/norm-change split; infrastructure and people formulas with € reference prices |
| Deployment | nothing | 4 scenarios (small server, own infra, cloud, air-gapped local LLM) |
| Scaling plan | limits listed | horizontal and vertical steps with metric triggers tied to the monitoring planes |

## Benchmarks (all on `trace_scale`, Docker Postgres `trace-pay-db-1`)

| # | What | Inputs and sizes | Output |
|---|---|---|---|
| B0 | Hardware | `sysctl hw.model hw.ncpu hw.memsize ...` | `demo-logs/scale/00-hardware.txt` |
| B1 | Fill `trace_scale`: migrate, load pack (16 hand-written rules), `demo_run.py` (500 PDFs, workbook, ERP sync on :8009, run, export) | batch 1 | `01-demo-run-500.txt` |
| B2 | Engine + sandbox directly (`bench_scale.py capacity`): sequential, 4 and 14 workers, simulated fix (no population for rules that do not read `others`, indexed R16) | 500, 5k, 8k, then 50k | `02-capacity-500-5k-8k.txt`, `03-capacity-50k.txt` |
| B3 | Real run through a temporary API on :8050 (`bench_scale.py grow`, then `POST /processes/1/run`), API RSS | 5k (and 50k if time allows) | `04-api-run.txt` |
| B4 | Postgres growth: table sizes and average row size per table and per span name | after B1 and B3 | `05-storage.txt` |
| B5 | Ingestion per file type: text PDF and OCR scan through `POST /processes/{id}/files` with the ONNX weights, workbook through `POST /sources/workbook`; peak RSS with `/usr/bin/time -l` | 500 PDFs (29 scans), workbook ×3 | `06-ingest.txt`, `07-workbook.txt` |
| B6 | Local LLM probe: `ollama` is installed with `llama3.1:8b`; one structured call timed (tokens/s) to estimate a compile | 1 call | `08-ollama-probe.txt` |

Every number in the docs is marked measured (with its file) or estimated (with its arithmetic).

## Rate-limit research
- Helmcode public docs (web search); if not public, keep the key limits we already recorded and
  mark "from the provider's dashboard, not public" / "unknown, assumed".
- Behaviour from code: OpenAI SDK retries twice (429/5xx), then `FallbackModel` moves to the
  next model (ADR 0019); `TRACE_COMPILE_CONCURRENCY` bounds parallel compiles; all models fail ->
  rule stays `draft`, instances keep being decided by the rules already active; nothing is paid
  on a missing rule (ADR 0016).
- Daily budget: tokens per norm change × changes per day; what happens when it runs out.

## Cost formula variables
- Tokens: `R` rules per norm, `a` coder attempts, `T_t` tester, `T_c` coder, `T_n` normalizer,
  `N` norm changes, `E` escalations the assistant is asked about, `A` assistant tokens; per invoice 0.
- Infrastructure: `C_api`, `C_db`, `C_storage × GB`, `C_ocr` (CPU share), `C_vlm` (optional),
  `C_obs`; GB from B4 bytes per invoice × invoices × retention.
- People: manager minutes per escalation × escalation rate × invoices; engineer hours per month.
- One worked example with public list prices (date and source per price).

## Deployment scenarios
(i) small server 2 vCPU / 4 GB, LLM remote; (ii) own Kubernetes + managed Postgres; (iii) cloud
managed services; (iv) air-gapped with Ollama/vLLM (VRAM, compile time from B6, quality risk,
inference only at compile time). One table plus one paragraph each.

## Scaling steps and triggers
- Horizontal: stateless API replicas, compile to a queue worker (ADR 0004 consequence), sandbox
  worker pool, fix `others` (population only for rules that read it + indexed lookups), engine
  batching, `events` partitioning by month, read replicas. A trigger per step from the three
  monitoring planes (ingestion: upload p95, OCR queue; agents: `llm_run` errors, 429s, tokens/day;
  execution: `run_process` duration, `evaluate_rule` p95 vs the 10 s limit, `RULE_ERROR` count).
- Vertical: emails, Facturae/UBL XML, images, CSV through the ingestion readers; new processes are packs.

## ADR 0020
`docs/adr/0020-deployment-and-scaling-plan.md` (context, alternatives, decision, consequences,
evidence) and a row in `docs/adr/README.md`. ADR 0018, `docs/api.md` and the traces code are not touched.

## Done checks
- [x] docs updated (`docs/scale-and-cost.md`, ADR 0020, ADR index, `docs/README.md`)
- [x] `demo-logs/scale/` added with `git add -f`
- [x] `make check`: ruff and unit tests locally on `trace_test_scale` (2 tests need the challenge
      submodule, which is not checked out in this worktree, and `.context/` is off limits); the
      full `make check`, golden e2e included, runs in CI with the submodule
- [x] PR into `dev` open, not merged (CI status in the PR)
- [x] temporary API on :8050 stopped; `trace_scale` left in place; `ollama serve` stopped

## Deviations from the plan
- B3 ran at 5k only: 50k through the API would only repeat B2's timeouts (16 rules × 10 s)
  and write 47k escalations; B2 measured it directly.
- B6 went further than a probe: a real compile of R02 and R16 on `llama3.1:8b` (both failed the
  tester's structured output), plus a token-rate probe.
- Found while writing section 5: a norm check whose compile fails ends `draft` and is not
  enforced. Recorded as a gap and a decision in ADR 0020 (not implemented here).
