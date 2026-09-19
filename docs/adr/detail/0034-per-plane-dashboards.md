---
status: accepted
---

# Show one dashboard per monitoring plane, never a mixed total

## Context
ADR 0018 groups every span into three planes: ingestion, agents and execution. They cost
and fail in different ways. One live run of 500 invoices spent 214,734 LLM tokens. As one
number that reads as "every invoice costs AI". By plane: ingestion 52,395 (the 29 scans,
first read only), agents 162,339 (the norm, once per version), execution 0
(`docs/observability-dashboards.md`). The jury asks which signals show errors, retries,
pending work and cost.

## Alternatives considered
- **One overview dashboard with global totals.**
  - Pros: one screen.
  - Cons: hides that deciding costs 0 and that the cost is per norm and per scan.
- **A hosted tool's dashboards (Logfire, Phoenix).**
  - Pros: no frontend work.
  - Cons: they see spans, not decisions, rules and versions; the manager would leave the
    console. We still mirror spans there for engineers (ADR 0018).
- **Three dashboards over typed per-plane endpoints, each number drilling down to its
  spans (chosen).**
  - Pros: the cost structure is visible at a glance; every number is auditable.
  - Cons: three typed response schemas to keep in sync with the console.

## Decision
- `GET /metrics/{plane}` and `GET /processes/{id}/metrics/{plane}` for `ingestion`,
  `agents` and `execution`, each with its own typed schema in the OpenAPI contract.
- Cost is USD only where the model's price is known (`known_cost_usd`); requests without a
  price are counted in `unpriced_requests` and never shown as 0.
- Every row carries its drill-down into `GET /traces`. `GET /health/planes` gives each
  plane `ok`, `degraded` or `down`; `GET /events/stream?plane=` streams it live.
- Never add tokens or cost across planes into one number.
- Each plane answers the jury's signals in its own terms (#150): ingestion gives
  `rate_limited` (HTTP 429) per provider and `sources[]` (syncs, errors, retries,
  `rate_limited`, p95 per source of truth, drill-down `GET /traces?source=`); agents holds
  every LLM call, the escalation assistant's `suggest_escalation` and `propose_decision`
  included; execution counts each instance's latest decision and gives
  `escalation_reasons`, the queue by first reason code.

## Consequences
- The console shows the three dashboards under Panel → *Detalles técnicos*.
- A price that is unknown (Helmcode's billing plan) stays visible as unpriced work, not as
  free work.
- Health is an error ratio per plane; a small provider outage inside a busy plane can read
  `ok` (known gap, `docs/resilience.md`).

## Evidence
- `backend/app/features/traces/router.py` (`_plane_routes`), `traces/schemas.py`
  (`IngestionMetrics`, `AgentsMetrics`, `ExecutionMetrics`); 8 tests in
  `traces/tests/test_planes.py`.
- `frontend/src/components/process/PlaneDashboards.tsx` (#126).

## Related
ADR 0018, 0020, 0022; `docs/observability-dashboards.md`.
