---
status: accepted
---

# Build a configurable decision process with reviewed learning

We will build a reusable decision system rather than an invoice-specific application. A process version defines its sources of truth, normalized facts, deterministic rules, allowed outcomes, and conflict policy. The invoice workflow is the first process configured on this system.

Users may provide policies and source descriptions as unstructured material. An LLM helps turn that material into a draft process version, but a manager must approve it before use. Published rules execute deterministically.

For each case, the system collects evidence through source adapters, normalizes it, evaluates the approved rules, and records the findings. A separate decision step then considers those findings together with approved process context. Context can influence the recommendation or expose uncertainty, but it cannot alter a deterministic rule finding.

The system returns an automatic decision when the findings and context support one of the process's existing outcomes with enough certainty. Missing evidence, conflicting sources, uncertain judgment, or a detected anomaly produces a recommendation with evidence and sends the case to a manager. The manager owns the final decision for every escalated case and must choose one of the process's existing outcomes.

Manager decisions and justifications become learning evidence. The system looks for repeated patterns across resolved escalations and may propose a new rule, better context, or a change to extraction. A proposal never changes a published process automatically. A manager must review and approve a new process version.

Before a new process version is published, the system runs a shadow backfill over previous cases. It preserves each original decision and evaluates the same historical evidence under the proposed version. The impact report shows which rule findings, automatic decisions, or recommendations would change. Backfill results do not overwrite history.

The main interfaces are intentionally small:

```text
evaluate(process_version, case_evidence) -> decision_record
simulate(draft_process_version, historical_cases) -> impact_report
```

A decision record keeps three results distinct: deterministic rule findings, the system recommendation when present, and the final decision. It also includes the process version, source evidence, normalized facts, manager justification when present, and timestamps.

The system stops at the decision. Executing payments or other downstream actions is outside its scope.

## Consequences

- Invoice terms such as NIF, IBAN, and ERP status belong to the invoice process definition, not the reusable decision module.
- Published process versions and past decisions are immutable.
- LLM output may draft rules, extract evidence, explain uncertainty, and propose learning. It cannot silently change rules or finalize an escalated case.
- Process context informs the decision step but does not rewrite deterministic findings.
- Historical impact analysis becomes part of rule approval, giving managers evidence before they publish a change.

**Update (2026-09-19).** Approval and impact analysis apply to whole process versions: the draft is
validated (`POST /processes/{id}/draft/validate`) and then published (ADR 0031). The interfaces
above are conceptual: the engine is `engine.decide` and the replay is `versions.service.inspect`.
