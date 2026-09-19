---
status: accepted
---

# Read the ERP only through a fault-tolerant client into a versioned local snapshot

## Context
The invoice process needs the legacy ERP (order status PENDIENTE / PAGADA) as a source of
truth: never pay an invoice without checking it. The challenge ERP fails on purpose, and
the Saturday and Sunday versions may be worse (more failures, truncated responses, invalid
XML, data changes). The jury wants to see retries, errors and a provider failure handled.

Findings from the challenge ERP (manual and `alberto_erp.py`):
- Token expires after 15 minutes or 300 uses (`SES-401`); every authenticated call spends a
  use, **including calls that fail**.
- `ORA-00600` (HTTP 500) on every 10th authenticated call; the counter is global across all
  clients, so the failing call cannot be predicted.
- 10 requests/s limit (`ERP-429`, `Retry-After: 1`); **rejected requests count** towards the
  limit, and login counts too. Hammering during a 429 extends the block.
- Lookups are by entry id, not by order: matching by order means downloading every page
  (516 entries, 26 pages in batch 1), using `meta.pages` and `meta.total`.
- XML in ISO-8859-1 (latin-1), dates `DD/MM/YYYY`, amounts `12.874,40`; values that fail
  conversion are returned **raw**, unrepresentable characters as `?`.
- ~0.12 s latency per call; the server is multithreaded. The batch 2 update modifies
  existing entries and appends new ones, so pages can shift.

## Alternatives considered
- **Read the data embedded in `alberto_erp.py` (zlib + base64 CSV).**
  - Pros: instant and reliable.
  - Cons: against the spirit of the challenge; breaks when the live ERP changes on
    Saturday or Sunday. Allowed only as an offline cross-check, never as a source.
- **Query the ERP per invoice at decision time.**
  - Pros: always fresh.
  - Cons: 500+ calls under a 10 req/s limit and 10 % failures inside the decision path;
    decisions not reproducible.
- **Fault-tolerant client + full download into a versioned snapshot (chosen).**

## Decision
The ERP connector (a source adapter reusable by any process) must:
1. Log in at start; renew the token pre-emptively before 300 uses or ~14 minutes, and
   always on `SES-401`.
2. Retry `ORA-00600`, other 5xx and timeouts with exponential backoff and jitter, bounded.
3. Honour `Retry-After` on 429, and run a client-side rate limiter below 10 req/s that
   counts every request, including login and retries.
4. Set connection and read timeouts on every call.
5. Validate every response: well-formed XML, decoded as latin-1, expected fields present,
   dates and amounts convertible. An invalid response is retried, never accepted.
6. Download all pages; check the count equals `meta.total` and ids are unique.
7. Store the result as a new load of the `erp` source (versioned local snapshot with date and
   hash). Rules read the snapshot, never the live ERP; decisions cite the load they used.
8. Open a circuit breaker after N consecutive failures; the rest of the pipeline continues,
   but no instance is decided without ERP data.
9. On an ERP update: download again, diff against the previous snapshot and re-run only the
   affected instances.

All parameters (retries, backoff, rate, timeouts, breaker threshold) are configurable at
runtime; values are fixed after load testing against the challenge ERP.

The connector configuration belongs to the **use case** (ADR 0011), not to one process: a
sync finds the pack whose `use_case` is the process's use case and reads its
`sources.json`, so every process of the use case (one created from a norm included) reads
the same ERP. We found this in a live demo: the lookup went by process name, and "Invoice
payment - live norm" got 404. Alternatives were copying `sources.json` into the database
(a migration, and a change would no longer apply on the next sync without a reload) or a
`sources` section inside `use-case.json` (the same file split in two places); the lookup
through the use case needs neither.

## Consequences
- ERP data can be minutes old; accepted, because decisions must be reproducible (ADR 0008).
- One more connector to maintain, but it is the template for any HTTP source.
- Combined with model fallback chains (ADR 0019), this is the resilience story for the demo.

## Evidence
- Implemented in `features/sources/http_connector.py`, configured by
  `processes/invoice-payment/sources.json`; see `docs/sources-http.md`. Points 1-7 and 9
  are done; the circuit breaker (8) is bounded retries plus "the previous snapshot stays
  current" rather than a breaker with a cool-down.
  **Update (2026-09-19).** The failed sync still keeps the previous load stored, but a run
  does not use it: a live source (`sync_before_run` in `schema.json`) whose pre-run sync
  fails, or that was never loaded, is down for that run, and the rules that read it
  escalate with `SOURCE_UNAVAILABLE` (ADR 0028; `sources/service.py`, `sync_before_run`).
- `sources/tests/test_erp_sync.py`: a second process of the use case syncs through the
  pack's connector; a use case without a pack answers 404.
- `sources/tests/test_erp_sync.py` against the real challenge ERP as a subprocess: 516
  entries in 26 pages, `ORA-00600` retried, 429 honoured, token renewed by uses, a failed
  sync keeps the previous snapshot, a batch-2 update diffed. `make demo`: 516 rows, 26
  pages, 2-3 retries, 1 login, about 5 s.
- Behaviour table: `.artifacts/archive/2026-09-18-reglas-sistema.md` §4; counts:
  `.artifacts/specs/batch1-analysis.md` (516 entries: 507 PENDIENTE, 9 PAGADA).

## Related
ADR 0007 (`sources.json`), 0008, 0011 (use cases). `docs/sources-http.md`.
