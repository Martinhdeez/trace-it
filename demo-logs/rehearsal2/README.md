# Rehearsal 2: tools after #92 (B8) and batch 2 with manager auth (B7)

2026-09-19, `integration` at 8972c2b. API on the host (`uvicorn`), Postgres in `trace-pay-db-1`,
the challenge ERP on its own port. `docs/backend-plan.md` B7 and B8.

## b8/: the driver scripts on a fresh database (`trace_b8_test`)

| Tool | Result |
|---|---|
| `make demo` (`make-demo.log`, `outcomes.jsonl`) | 500 exported in 118 s, `check-outcomes` OK, golden 471/471. 436 PAGAR / 36 NO_PAGAR / 28 ESCALAR, not 443/36/21: Gemini answered 429 `RESOURCE_EXHAUSTED` (free-tier daily quota) on every call, so 7 scans it corroborated on Friday ended `MISSING_DATA` instead of PAGAR. Text PDFs are identical |
| `make demo-llm-down` | As documented: `deepseek-v4-flash` "Connection error", `glm5.3` answered, one ESCALAR check |
| `bench_scale.py capacity --sizes 500 5000` | 447/s and 190/s sequential, 0 RULE_ERROR. `engine --runs 2`: 429 instances/s |
| `audit_page/build.py` | 500 instances, 12.1 MB page |
| `make trace-decision FILE=scan_002.pdf` | Full trace; shows the Gemini `ProviderUnavailable` errors |
| `no-workbook.txt` | Frozen pack with no workbook: two golden PAGAR/ESCALAR invoices end NO_PAGAR (reported, not fixed) |

No tool got a 401, 403 or 422.

## b7/: `docs/runbook-batch2.md` step by step

Friday's dump restored into `trace_rehearsal2_test`. One file per step (`NN-name.txt`: the
command, its output, exit code, seconds and clock time). `inputs/` holds the simulated
delivery and the helper that ran each step; `outputs/` the exports. Timings and findings:
the runbook's "Rehearsal 2" section.
