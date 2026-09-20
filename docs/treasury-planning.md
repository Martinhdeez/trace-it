# Treasury planning

Open a process's Treasury tab to distribute approved invoices across a weekly budget.
Enter a start date and budget, select a horizon, and generate a preview. Select a week
to inspect its invoices; each invoice links back to its decision evidence. The supplier
summary and exclusions explain what was scheduled and what still needs attention.

The date defines the beginning of consecutive seven-day buckets. It does not refresh
the ERP, reinterpret the decision at a new cut-off date, or establish a bank balance.
Invoices are considered in due-date order and placed in the first eligible bucket with
enough budget. Whole invoices stay together. Unused budget does not carry forward.
An invoice exceeding the weekly budget remains unscheduled.

If recorded evidence has neither a due date nor payment terms, the optional fallback
terms field supplies an explicit scenario assumption, measured from the invoice date.
Leaving it empty excludes invoices whose due date cannot be established. Historical
source snapshots are not rewritten to add terms that were ingested later.

Changing any scenario input requires generating a new preview before export. The CSV
contains scheduled invoices, scenario inputs and evidence references. It is a planning
draft; generating or downloading it does not execute payments or mark invoices paid.

## API

`POST /processes/{process_id}/treasury/preview` is read-only and follows the existing
console policy for reading process evidence. It requires no model key or external call.

```json
{
  "as_of": "2026-09-21",
  "weekly_budget": "150000.00",
  "horizon_weeks": 8,
  "default_payment_terms_days": 30
}
```

`as_of` and a positive budget with at most two decimal places are required. The horizon
is between 1 and 52 weeks. Fallback terms are optional. Decimal amounts in responses are
JSON strings; consumers must not use binary floating-point arithmetic to schedule them.

The response contains `rows`, `weeks`, `suppliers`, `exclusions` and `totals`. Week
`row_ids` refer to scheduled rows. Each row retains its instance, decision, version,
execution and source references, together with the basis for the amount and due date.
Exclusions carry a machine-readable `reason_code` and explanation; an unknown amount
is null, not zero. Consult the committed OpenAPI contract for exact field types.

`backlog` counts eligible invoices that could not be scheduled. It is a subset of the
exclusions, so these figures must not be added together. Each week's backlog includes
invoices already due but assigned to a later week. `excluded_amount` includes only known
amounts in EUR; foreign-currency invoices remain visible individually without conversion.

The preview uses the latest final decision and its captured evidence. Pending review,
missing snapshots, changed evidence and unresolved alerts prevent scheduling. It never
changes a decision, a process version, a source load or the deterministic rules engine.

The implementation boundary and deferred payment-execution lifecycle are documented
in [ADR 0038](adr/detail/0038-read-only-treasury-planning.md).
