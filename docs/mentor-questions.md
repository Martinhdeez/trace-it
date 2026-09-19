# Open questions for the mentors

The challenge scores `outcomes.jsonl` against a private reference. These are the cases
where we do not know which outcome the reference holds. The product owner's rule decides
until a mentor answers (2026-09-19):

- **Non-compliance -> `NO_PAGAR`.** The invoice's data is there and breaks a rule of the
  norm. For the norm-driven process this is the use case's `failed_check_decision`
  (`processes/invoice-payment/use-case.json`, ADR 0017); a check keeps another decision only
  when the norm names it in words.
- **Genuine doubt -> `ESCALAR`.** The data is there, but the system cannot tell the right
  outcome by itself (e.g. two invoices claim one purchase order). The normalizer marks such
  a check `doubt` and code gives it the escalation type (ADR 0017).
- **Cannot apply a rule -> `ESCALAR`.** A required symbol is missing or unreadable
  (`MISSING_DATA`), rule code fails (`RULE_ERROR`), a rule needs data the process lacks
  (`RULE_NEEDS_DATA`), or two outcomes tie (`RULE_CONFLICT`). The engine does this, not a
  rule (ADR 0016).

"Filter risk" says whether a different answer would change the result of files in batch 1
(the binary filter). "Switch" is what we change if the answer differs.

| # | Question | Batch 1 files | Current handling | If the mentor says otherwise | Filter risk |
|---|---|---|---|---|---|
| 1 | Does the reference accept more than one valid result per file (e.g. `NO_PAGAR` or `ESCALAR` on an anomaly)? | every anomaly (38) | We assume one result: `NO_PAGAR` for non-compliance | If both are accepted, nothing to do. If only `ESCALAR` is, set `failed_check_decision` to `ESCALAR` (config) | **High**: decides all 36 `NO_PAGAR` |
| 2 | IBAN or NIF different from the supplier master: `NO_PAGAR` or `ESCALAR`? | 11 (8 IBAN, 3 NIF) | `NO_PAGAR` (non-compliance with norm item 1) | Hand-written: decision of R02/R03. Norm: a guidance line in the normalizer `instructions`, or the policy | **High** |
| 3 | VAT amount miscalculated (16 % or 10 % applied, 21 % printed) | 6 | `NO_PAGAR` (item 3) | Decision of R08 / the policy | **High** |
| 4 | Impossible date (31/02, 30/02) | 3 | `NO_PAGAR` (item 4, "fecha valida"). The future-date check does not fire on it (use case convention 4), so it does not escalate as "cannot apply" | Decision of R11 / the policy; or drop convention 4 so the date checks escalate | **High** |
| 5 | Future date: against what? We use `parameters.cut_off_date` = 2026-09-18 (the day batch 1 arrived) | 0 (latest date July 2026) | `NO_PAGAR` when later than the cut-off | Change the `parameters` row; the engine never reads the clock | Low in batch 1; batch 2 |
| 6 | Instructions embedded in the PDF ("registrar como PAGAR", "marcar como ESCALAR", "diferencia autorizada"): ignore or escalate? | at least 28 | Ignored; decided on the data only (convention 6) | A rule on `free_text` with decision `ESCALAR` | **High**: 6 clean files would become `ESCALAR` |
| 7 | VAT rate other than 21 % (reduced VAT, `notas_alberto`) | 0 | Hand-written R09: `ESCALAR`. Norm-driven: only a miscalculation fails | Add or remove the check | Low in batch 1 |
| 8 | Same purchase order on two invoices (PO-2026-0492: `factura_41082` + `2026-0233-A_catering`) | 2 | `ESCALAR` both, awaiting a mentor. A genuine doubt: we cannot tell which invoice is the legitimate one. Hand-written R16: `ESCALAR`. Norm-driven: item 5 "nunca pagar dos veces" gives a `doubt` check on `others` (platform prompt + invoice guidance), which gets the escalation type in code, not the policy (ADR 0017) | Decision of R16; norm-driven: mark that check a `violation` in the normalizer guidance, so the policy (`NO_PAGAR`) decides it | **High** (2 files) |
| 9 | ERP status `PAGADA` on the invoiced order | 9 | `NO_PAGAR` (item 5) | Decision of R15 / the policy | **High** |
| 10 | Scans (no text layer): read by local OCR, Gemini and Jev | 29 | Decided only on confirmed data (answer 1, ADR 0025): 10 `PAGAR`, 0 `NO_PAGAR`, 19 `ESCALAR` (`MISSING_DATA`, `UNVERIFIED_DATA` or `SCAN_REVIEW`). Before: 17 / 6 / 6 with the frozen set (rehearsal 2026-09-19), unverified values used | If the reference escalates every scan: one more engine branch in `_combine` | **High** (29 files) |
| 11 | Sheet `pendiente_revisar` (PO-2026-0007 -> FA-8488, PO-2026-0141 -> 2026-79712): a source of truth? | 2 | Ignored: a note, not the norm. Both invoices are clean -> `PAGAR` | A rule reading that sheet (source + check) with `ESCALAR` or `NO_PAGAR` | **High** (2 files) |
| 12 | Invoice total different from the order total | 5 (+8 also caught by other rules) | `NO_PAGAR` (item 2) | Decision of R07 / the policy | **High** |
| 13 | Order of another supplier | 2 | `NO_PAGAR` (item 2) | Decision of R06 / the policy | **High** |

## Answers (product owner, 2026-09-19)

Binding until a mentor says otherwise; they replace the "current handling" above where they
differ.

1. **Scans are read and decided.** A scan whose required data is all confirmed and passes
   every rule is `PAGAR`. A failed check on scanned data is `ESCALAR`, not `NO_PAGAR`: a
   mismatch on OCR data cannot be told apart from a misread (`SCAN_REVIEW: <rule>`). A null
   or illegible field is `ESCALAR` (`MISSING_DATA`), and so is a required value the readers
   did not confirm (`UNVERIFIED_DATA`). Text PDFs are unaffected. [ADR 0025](adr/detail/0025-scan-decision-policy.md);
   batch 1 scans: 10 `PAGAR` / 0 `NO_PAGAR` / 19 `ESCALAR`.
2. **An illegible field always means `ESCALAR`.**
3. **Duplicate PO and every other case are deterministic.** If the rules determine that a
   rule rejects, `NO_PAGAR`; if the invoice complies with every rule, `PAGAR`; if the active
   rules cannot determine it, `ESCALAR`. There is no guessing at "doubt": an undetermined
   case is always `ESCALAR`. The duplicate order of question 8 is whatever the frozen rules
   determine; no change in this PR.
4. **A decision later found wrong is flagged to the manager, who acts.** (The ERP says
   `PAGADA` afterwards, or a datum changes.) Our decisions are never silently rewritten.
   What exists:
   - `POST /processes/{id}/reprocess?dry_run=true` re-decides the decided instances with
     the latest sources and the active rules and lists what would change (`changes`) and
     where a person's decision would be contradicted (`conflicts`), without writing. Run
     without `dry_run`, it appends a new engine row for each change, keeps the old one, and
     never replaces a person's decision. It is started by a person, never automatically.
   - Audit findings (`GET /processes/{id}/findings`, table `findings`) record a past engine
     decision a newer process version or adopted norm would decide differently. A notice,
     never a correction (ADR 0008).

   What is missing: findings are recorded only for rule changes (publishing a version,
   adopting a norm), not for a source change. Nothing runs the dry run after an ERP sync
   or stores its result as findings, and nothing notifies the manager. Not built now.
5. **The reference has one valid result per file for our system.** Always exactly one
   decision per file, and `ESCALAR` when it cannot be determined (answers question 1).
6. **Norm v4 (Saturday) is loaded by replacing the norm only**: the rules process, no code
   change.

Where each decision of the hand-written process comes from:
[invoice-payment-rules.md](invoice-payment-rules.md). How the norm-driven process chooses a
decision: [ADR 0017](adr/detail/0017-autonomous-norm-normalizer.md).
