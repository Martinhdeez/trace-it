---
status: accepted
---

# Exchange rates are a source of truth, not something a rule looks up

## Context
Batch 2 brought eight invoices in USD, CHF, GBP, BRL, JPY and MXN against orders that are
always in EUR. Comparing them at all needs a rate, and the engine is pure: no clock, no
network, no database inside `backend/app/features/decisions/engine.py` (ADR 0002), because
a decision must replay to the same verdict years later (`/decisions/{id}/replay`). A rate
is reference data of exactly the kind the process already has: the supplier master, the
order book, the ERP and the cut-off date are all rows in a source, never a live lookup.

## Alternatives considered
- **Call a rates API from inside the rule.** Pros: always current. Cons: breaks the pure
  engine, makes a replay depend on a third party that may answer differently or not at
  all, and puts an outage between us and every foreign invoice. Rejected.
- **Hardcode the rates in the rule code.** Pros: no new source. Cons: a rate change
  becomes a code change and a new rule version, and the rate a past decision used is
  buried in a diff instead of being a row we can show. Rejected.
- **Convert the order into the invoice's currency instead.** Pros: one fewer table.
  Cons: it moves the arithmetic away from the figure the supplier actually asks for, and
  a rounding difference would land on the order, which is the master data. Rejected.
- **A `rates` source, like every other reference table (chosen).**
  - Pros: immutable snapshots, one row per rate with its own validity window, the rate
    that was actually used is stored with the decision, and the engine stays pure.
  - Cons: the table has to be kept up to date by someone; for the delivery, by hand.

## Decision
- `rates` is a source of the invoice pack, with the canonical schema in
  `processes/invoice-payment/schema.json`: `currency`, `eur_per_unit`, `as_of`,
  `valid_until`, `tolerance_pct`, `reference`.
- For the delivery it is filled by hand from `processes/invoice-payment/rates.json` and
  loaded with the workbook (`backend/app/features/sources/workbook.py`), so a manager who
  loads the reference data gets the rates with it.
- A connector that syncs the same rows from a published feed — the ECB reference rates,
  say — is a `sources.json` entry and a schema flag, exactly like the ERP
  (`docs/sources-http.md`, ADR 0028). It writes the same rows into the same source, so
  moving from the hand-filled table to a live feed is configuration, not code.
- R18 picks the row whose `as_of`..`valid_until` covers the invoice's own `date`. No
  covering row means ESCALAR; there is no nearest-row fallback and no clock. A rate change
  is a new row with its own window; a row is never edited, like every other source here.

## Consequences
- If `rates` is ever synced and the sync fails, it is down for that run: no rule that
  reads it runs on an older snapshot, and the affected cases escalate as
  `SOURCE_UNAVAILABLE` rather than being decided with a stale rate. The same holds if the
  source was never loaded at all ("never loaded"), which is how the engine treats missing
  reference data in general (`decisions/service.py::_inputs`, ADR 0028). A wrong payment
  is never the quiet outcome of an unavailable rate.
- The table's freshness is a human responsibility until a connector exists. The delivery
  carries one window per currency, the 2026 financial year, which is the granularity we
  can cite; a monthly table is a change to `rates.json`, not to the rule.
- Honest note: the challenge's invoices are dated 2026, so no public feed publishes those
  fixings. The values in `rates.json` are declared rates carrying a named reference. They
  were checked afterwards against the orders they have to reproduce, and never derived
  from them: the integrity rule is that a rate enters the table as a published figure, so
  a rate that did not reproduce its order would be evidence about the invoice, not a
  reason to change the rate.

## Evidence
- `backend/app/features/decisions/tests/test_rules_v3.py`: the eight foreign invoices of
  batch 2 through the real sandbox; the rate in force per window; an invoice outside every
  window escalating; an unknown currency code escalating.
- Rehearsal of the 540 PDFs through the real routes on an isolated database: batch 1
  unchanged (0 of 500 verdicts differ from the same symbols under the previous rules) and
  every conversion reproducing its order to the cent, so `tolerance_pct` is 0.

## Related
ADR 0002 (the pure engine), ADR 0028 (a source that is down stops the rules that read it),
ADR 0035 (learning from resolved escalations: the six reviews fire only R18).
