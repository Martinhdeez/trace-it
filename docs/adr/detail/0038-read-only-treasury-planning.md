---
status: accepted
---

# Plan payments from recorded decisions without executing them

An approved invoice tells the operator whether it may be paid. It does not tell the operator how to fit the approved invoices into a limited weekly budget. The console needs a planning view that preserves the distinction between a recorded decision and a proposed payment date.

## Decision

Add a read-only treasury preview beside the process's existing operational screens. The invoice adapter selects eligible recorded decisions and their captured evidence. A deterministic scheduler places complete invoices into bounded weekly buckets using an explicit planning date and weekly budget. It uses exact decimal arithmetic and a stable ordering by due date and instance identity.

The preview does not execute transfers, write a payment ledger, change a decision, publish a rule, or synchronize a source. It extends the operator's view of decisions while preserving ADR 0001's boundary around downstream execution. Invoice field mappings stay outside the reusable decision engine.

Recorded due dates and supplier terms are preferred. Historical sources may lack payment terms. The operator can supply an explicit fallback term for that scenario; each resulting date is labelled as a planning assumption. The preview never quietly substitutes the system date or invents missing evidence. Changing the planning date does not revalidate the original decision against an ERP at that later date.

Invoices with insufficient evidence, unresolved review or stale decision context remain visible with exclusion reasons. An invoice larger than the entire weekly budget is left unscheduled with an explicit reason. The scheduler never silently exceeds the budget or splits an invoice. Items beyond the bounded horizon remain visible as backlog.

Every planned row retains its instance and decision references so the operator can open the original evidence. CSV export is a planning draft, not a bank instruction, and protects spreadsheet readers from formula injection in external text.

## Alternatives

- Extend the deterministic decision engine with payment scheduling. Rejected because a cash budget changes an operational plan, not whether an invoice satisfies its decision rules.
- Read the newest supplier values regardless of when the decision was made. Rejected because the plan would combine a historical approval with evidence it never used.
- Assume a default payment term or use the computer's current date. Rejected because the resulting dates would look observed without having a recorded basis.
- Persist schedules and mark invoices as paid. Deferred until there is a separate authorization, idempotency and reconciliation lifecycle. The present feature is a preview.
- Optimize a global payment portfolio. Deferred. A stable due-date-first schedule is explainable and sufficient for this product slice.

## Consequences and validation

The preview is reproducible for the same eligible evidence and explicit scenario inputs. A refreshed decision or changed source can make a previous preview unsuitable; the interface must keep the submitted inputs and the generated result together and require a fresh preview after editing them.

Validation covers cent-exact limits, deterministic ordering, seven-day buckets anchored to the explicit start date, missing evidence, oversized invoices, horizon overflow, review/currentness exclusions, and unchanged decision history. Browser checks cover navigation, input validation, weekly selection, exclusions, export and narrow viewports. This feature does not establish available bank balances or certify that a payment file is bank-ready.
