---
status: accepted
---

# B. When in doubt, ESCALAR

**Claim.** Every file gets exactly one decision. What the rules reject is `NO_PAGAR`; what
the system cannot determine is `ESCALAR` with a reason code, never a guess.

**Rubric.** Quality of execution (10): "do its decisions and limits make sense for
Alberto?". It also keeps the binary validation safe: one valid `result` per file.

**Problem.** The export needs exactly one valid `result` per file. A wrong `PAGAR` costs
money, and a run that ends with files left undecided cannot be delivered. Scans, empty
fields, a broken rule and an ERP that fails on purpose all happen in La Caja.

**Decision.** The engine gives every file one of the process's decision types. When it cannot
decide, it escalates and names the reason: `MISSING_DATA` (a required field is empty),
`UNVERIFIED_DATA` (a scan value the readers did not confirm), `SCAN_REVIEW` (a scan the rules
would reject), `RULE_ERROR` (rule code failed), `RULE_CONFLICT` (a tie between decisions) and
`SOURCE_UNAVAILABLE: <source>` (a source a rule needs is down or was never loaded, and the
rules that did run do not already reject). Missing reference data is unknown, never an empty
table. A person resolves the escalation in the console, as a new row.

## Alternatives considered

| Option | Why we rejected it |
|---|---|
| An internal `REVIEW` state outside the export | A run can end with files that have no exportable result. It happened: a sandbox limit broke every rule (ADR 0009, superseded) |
| A rule that fails counts as "did not fire" | Always a result, but it pays exactly when the code that should stop the payment broke |
| Decide scans like text PDFs | An OCR misread becomes a wrong `NO_PAGAR`: 5 of 29 scans before ADR 0025 |
| Use the last ERP snapshot when the ERP is down | Pays against stale data, for example an invoice the ERP already marked paid |
| **Escalate with the reason (chosen)** | In the export our own failure looks like a business doubt; the reason code tells them apart |

## Evidence

| Claim | Number | Reproduce |
|---|---|---|
| One decision per file | Batch 1: 500 files, **443 `PAGAR` / 36 `NO_PAGAR` / 21 `ESCALAR`**, golden 471/471 | Re-decided for this ADR with `tools/bench_scale.py engine` on the delivery database: 500 unchanged; `make test-e2e` |
| Every escalation says why | The 21: 8 `MISSING_DATA`, 7 `UNVERIFIED_DATA`, 4 `SCAN_REVIEW` (19 scans), 2 duplicate purchase order (doubt) | The `reprocess` span's `failures` and `escalations`; `GET /processes/{id}/metrics/execution` |
| Scans never rejected on an OCR reading | 29 scans: 10 `PAGAR`, 0 `NO_PAGAR`, 19 `ESCALAR` | Same run; `decisions/tests/test_engine.py::test_a_scan_the_rules_would_reject_escalates_naming_the_rule` |
| A broken rule never pays | 50,000 invoices with every rule timing out: 47,100 `ESCALAR` `RULE_ERROR`, 0 paid | [scale-and-cost.md](../scale-and-cost.md) §3, reported; `test_engine.py::test_a_failing_rule_escalates_with_the_error` |
| A down source only affects what needs it | ERP down: the clean invoice and the already-paid one escalate `SOURCE_UNAVAILABLE: erp`; IBAN and date rejections stay `NO_PAGAR` | `decisions/tests/test_live_sources.py::test_erp_down_escalates_only_what_depends_on_it` |
| A never-loaded source is not an empty table | No workbook loaded: the invoice escalates instead of failing the supplier check | `test_live_sources.py::test_a_source_never_loaded_escalates_instead_of_reading_empty` |

With Helmcode as the OCR reader the batch gave 444 / 36 / 20: one scan confirmed that had
escalated (reported by the team, not reproduced here).

## Trade-offs accepted

- A person reviews 21 of 500 files (4.2 %). Some are our own limits (a scan we could not
  confirm), not business doubts.
- In `outcomes.jsonl` both look the same: `ESCALAR`. The reason code, in the trace and the
  queue, tells them apart.

## See it in the demo

- **Revisión**: the queue of escalated cases, each with its reason code, the evidence, and
  the assistant's explained options. The manager resolves; the engine's decision stays.
- **Panel** → *Detalles técnicos* → *Execution*: escalations by reason.

```mermaid
flowchart LR
  F["File"] --> M{"Required field<br/>missing or null?"}
  M -- yes --> E1["ESCALAR<br/>MISSING_DATA"]
  M -- no --> U{"Scan value<br/>not confirmed?"}
  U -- yes --> E2["ESCALAR<br/>UNVERIFIED_DATA"]
  U -- no --> R{"Every rule<br/>ran?"}
  R -- no --> E3["ESCALAR<br/>RULE_ERROR"]
  R -- yes --> SRC{"A rule needs a source<br/>down or never loaded?"}
  SRC -- "yes, and the rules that ran<br/>do not reject" --> E6["ESCALAR<br/>SOURCE_UNAVAILABLE"]
  SRC -- "no, or already rejected" --> V{"Which rules fire?"}
  V -- none --> P["PAGAR"]
  V -- "violation, text PDF" --> NP["NO_PAGAR"]
  V -- "violation, scan" --> E4["ESCALAR<br/>SCAN_REVIEW"]
  V -- "doubt or tie" --> E5["ESCALAR<br/>doubt, RULE_CONFLICT"]
  classDef kb fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#111
  class E1,E2,E3,E4,E5,E6 kb
```

Detail: [0016](detail/0016-every-instance-gets-a-decision.md),
[0025](detail/0025-scan-decision-policy.md),
[0009](detail/0009-review-state-and-export-semantics.md),
[0010](detail/0010-double-extraction-with-deterministic-validators.md),
[0021](detail/0021-optional-decision-review.md),
[0028](detail/0028-live-sources-sync-before-run.md),
[0029](detail/0029-bind-dynamic-extraction-to-published-execution.md),
[0030](detail/0030-report-partial-history-for-new-symbols.md). A rule that failed to
compile never decides: it cannot be published (key decision E).
