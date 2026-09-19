# Defense script (6-8 minutes)

One laptop, one terminal, the API on <http://localhost:8000/docs>. The order follows the
rubric, heaviest first. Every claim has a command or a document behind it.

**Before the jury arrives** (10 minutes, from a clean clone with the keys in `.env`; README "Run it"):

```bash
make setup && make activate MANAGER_ID=1   # API + pack, rules published as version 1
make erp                                   # other terminal, keep it open
make demo                                  # 500 invoices decided, output/outcomes.jsonl
API=http://localhost:8000
```

Ports taken: `DB_PORT=5442 BACKEND_PORT=8030 ERP_PORT=8031` on `make setup`, the same
`ERP_PORT` on `make erp` and `BACKEND_PORT` on the rest, and `API=http://localhost:8030`.

| # | Min | Rubric (pts) | Say | Show |
|---|---|---|---|---|
| 1 | 0:00-1:30 | Product and ADRs (35) | A process pack declares decision types, symbols and rules in plain language; agents compile the rules to Python; a deterministic engine decides. No LLM ever decides. Every invoice ends as `PAGAR`, `NO_PAGAR` or `ESCALAR`, and a rule that cannot run escalates instead of guessing | `processes/invoice-payment.json` (the rules as text); [ADR index](adr/README.md): 0001 (configurable process), 0002 (LLM never decides), [0016](adr/0016-every-instance-gets-a-decision.md) (every instance gets a decision), [0025](adr/0025-scan-decision-policy.md) (scans decided only on confirmed data) |
| 2 | 1:30-2:15 | Product (35) | The result, and that it matches the reference on every text invoice | `curl -s $API/processes/1/summary \| python3 -m json.tool \| head -15`; `make check` runs the golden test: 471/471 |
| 3 | 2:15-4:00 | Traceability (20) | Follow one real decision: state, evidence with its origin, the process version and rules hash, latency per step, errors and retries, pending work | `make trace-decision FILE=scan_002.pdf` (a scan that escalated), then `make trace-decision FILE=2026-03-28_P002.pdf` (a `NO_PAGAR`). Saved outputs: [`demo-logs/defense/`](../demo-logs/defense/). The same data as JSON: `$API/instances/{id}/trace`, `$API/rules/{id}/trace`. [ADR 0018](adr/0018-observability-own-audit-spans-plus-opentelemetry.md) |
| 4 | 4:00-5:15 | Scale and cost (25) | Deciding costs 0 tokens; 500 invoices in 0.8 s; OCR is the bottleneck (1.2 s per scan, 2.6 GB peak); the engine breaks at about 8,000 invoices per process and we measured the fix (50,000 in 31 s); 10,000 invoices a month is about 2.6M tokens, and people cost more than machines | `curl -s $API/processes/1/metrics/execution \| python3 -m json.tool \| head -20`; [docs/scale-and-cost.md](scale-and-cost.md) headline and section 3; [ADR 0020](adr/0020-deployment-and-scaling-plan.md) (one small server, scale by measured triggers) |
| 5 | 5:15-6:15 | Resilience (10) | The ERP fails on purpose (`ORA-00600`, 429, timeouts): the client retries and never replaces a good snapshot with a bad one. An LLM provider down: the next model of the chain answers. A rule that fails to compile escalates its cases, never pays them | The `erp sync` line of step 3 (requests, retries, timeouts); `curl -s $API/health/planes`; `make demo-llm-down` (needs keys; prints `failed_attempts` and the model that answered). [ADR 0013](adr/0013-fault-tolerant-erp-client.md), [ADR 0019](adr/0019-llm-fallback-chain.md), [ADR 0016](adr/0016-every-instance-gets-a-decision.md) |
| 6 | 6:15-7:00 | Quality of execution (10) | Small and proportionate: one engine, one feature per folder, a README that runs from a fresh clone, tests beside each feature and no test that needs an LLM key | README first screen; `make check` (ruff on backend and `tools/`, unit tests, golden 471/471, API flow), green in CI on every PR |
| 7 | 7:00-8:00 | Bonus (10) | Stale decision alerts: when the ERP or the rules change, the past is re-decided in a dry run and every decision that would change becomes an alert for the manager. Nothing is rewritten | Below. [ADR 0026](adr/0026-stale-decision-alerts.md); captured run in `demo-logs/alerts/` |

**Step 7, live** (about 30 s; it changes one ERP row, so do it last):

```bash
# Ctrl+C on `make erp`, then restart it with one entry no longer paid:
printf 'asiento_id,fecha_registro,proveedor_id,nif,pedido,importe_esperado,estado\nAS-00476,2026-03-28,P002,A41220987,PO-2026-0476,2551.64,PENDIENTE\n' > /tmp/erp_change.csv
python3 .context/500-sombras-de-alberto/alberto_erp.py --lote2 /tmp/erp_change.csv
curl -s -X POST $API/processes/1/sources/erp/sync | python3 -m json.tool   # diff: AS-00476 PAGADA -> PENDIENTE
curl -s "$API/processes/1/alerts?status=open" | python3 -m json.tool       # 2026-03-28_P002.pdf NO_PAGAR -> PAGAR
make trace-decision FILE=2026-03-28_P002.pdf                                # the alert under "Pending work"
```

`demo-logs/defense/trace-no-pagar-alert.txt` is this step's output.

**If something fails live**: every step has its saved output (`demo-logs/defense/`,
`demo-logs/alerts/`, `demo-logs/scale/`); show the file and say what failed. The trace of
that failure is itself the traceability demo.
