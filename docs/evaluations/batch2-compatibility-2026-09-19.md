# Batch 2 compatibility evaluation — 2026-09-19

All 540 PDFs were processed before and after the change. With the original references
and population, all 500 original decisions and their reasons are unchanged. The
471 native PDFs match every official golden outcome. The 15 international PDFs now
have 135/135 correct verified reference fields, up from 72/135.

## Inputs and method

- Challenge: `f831e34`, pulled from `500-sombras-de-alberto`; 500 original PDFs plus
  40 `facturas_primin` PDFs. Capture manifests pin each file's SHA-256.
- Reader baseline: dev `df739dd`, the checkout used for the preceding audit. The work
  branch starts from the subsequently updated dev `f1e8b7e`; its additional mail,
  reviewer-learning and CI changes are included in the application tests.
- Extraction: hybrid local OCR plus configured Helmcode Qwen 3.6/Gemma 4 visual readers
  and Jev/Helmcode judge. The controlled comparison reuses baseline raw reader journals
  and reruns interpretation, source-triggered verification and the real sandbox.
- References: original workbook/516 ERP entries, then the cumulative workbook/556 ERP
  entries. Cut-off is explicitly 2026-09-19 in these captured scenarios. The existing
  independent golden tests also retain their original 2026-09-18 cut-off.
- New policy: the adapted 18-rule development pack, including review for explicit
  non-EUR currency. No invented v4, inferred exchange rates or corrected master values.

The API rehearsal used an isolated PostgreSQL database, a published process version
pinning `helmcode:qwen3.6`, the real workbook upload and PDF upload routes, the live
challenge ERP and real sandbox execution. Its 540 labels exactly match the controlled
comparison. One unreadable fax IBAN is classified as `unverified` versus `ambiguous`
between the provider configurations; both withhold the value and escalate the case.

## Results

| Check | Before | After |
|---|---:|---:|
| Original decisions, original references | 444 PAGAR / 36 NO_PAGAR / 20 ESCALAR | Identical |
| Official native golden agreement | 471/471 | 471/471 |
| Reviewed scan fields, correct returned transcription | 275/282 | 275/282 |
| Reviewed scan fields, correct and verified | 236/282 | 236/282 |
| International fields, correct and verified | 72/135 | 135/135 |
| Incorrect international fields marked verified | 2 | 0 |
| Visual-reader invocations on the 40 new PDFs, including source checks | 18 | 3 |
| Local OCR invocations on the 40 new PDFs | 6 | 6 |

The scan fixture covers 29 documents. Five reviewed fields remain without a returned
value. Two returned scan proposals are wrong (`scan_010.pdf` VAT and the fax date), but
neither is verified or authorizes payment. These are existing unresolved readings,
not newly solved cases or official scan outcome labels. The independent native-reader
digest also remains unchanged, including candidates, invalid dates and absent currency.

Notable new corrections:

- e01/e03/e04/e07/e08 now have enough literal evidence to reach PAGAR under v3.
- e05/e06 now expose supplier/account mismatches and reach NO_PAGAR.
- e13 preserves the issuer's full CNPJ and terminal `C1` in the Brazilian account.
  The customer NIF is no longer accepted as the issuer.
- e16 changes from PAGAR to ESCALAR because its date is unverified.
- e18 changes from PAGAR to ESCALAR because the base and total are visibly amended.
- All eight explicit non-EUR cases require a conversion policy; e10's previous numeric
  comparison with an EUR order no longer produces an unjustified rejection.
- e17 remains unresolved and requires review; no date or master values are invented.

With the cumulative references and all 540 documents in the duplicate population:

| Batch | PAGAR | NO_PAGAR | ESCALAR |
|---|---:|---:|---:|
| Original 500 | 443 | 36 | 21 |
| New 40 | 23 | 5 | 12 |
| Combined | 466 | 41 | 33 |

The "Original 500" row is the state of the database this evaluation ran on, not the
delivered file. The shipped `delivery/outcomes.jsonl` is **436 / 36 / 28**: its run hit the
scan reader's daily quota, so seven scans corroborated here ended `MISSING_DATA` instead of
`PAGAR`. The batch-2 conclusions below are unaffected — they are about the 40 new documents.

The intended historical change is `factura_4635.pdf`: updating sources alone changes
PAGAR to NO_PAGAR because the ERP now includes a paid entry. Adding the new PDF
`2026-08-22_P010.pdf` introduces a duplicate purchase order, so both escalate. This is a
source/population change, not a regression against the unchanged original scenario.

## Integration and regression checks

- API: 540 uploads, 540 decisions and 540 correctly named JSONL export rows. Running
  again produces zero new decisions. Four representative stored decisions replay
  exactly, including e16/e18 and the original invoice affected by the new ERP entry.
- ERP HTTP: 556 entries, 28 pages, 33 requests, three recovered ORA-00600 errors;
  no missing or malformed values. Pending and paid entries coexist without row-order
  dependence. The adapter's startup and compose overlay are also tested.
- Import: 4 new supplier rows and 39 new order rows; original rows preserved, repeat
  import adds zero, conflicts fail without a partial workbook.
- Backend: the full run passed 865 tests and found one recipient-section boundary
  regression in a synthetic repeated-NIF test. That boundary was corrected; the
  affected ingestion, golden-engine and batch-two rule suite then passed 353 tests,
  with three documented skips. The failed-test recheck passes. Thus all 866 executed
  backend tests have passing evidence after the relevant corrections; four full-suite
  skips and two opt-in LLM exclusions remain.
- Deployment/import tooling: 14 tests pass. Ruff lint/format and `git diff --check`
  pass. The independent golden builder uses explicit UTF-8 for Windows; its reference
  JSONL files were not changed.

Raw runs are under `output/comparison/`: `before-complete`, `after-replay`, `report`
and `api-final`. Logs are under `output/batch2-audit/`. The checked-in JSON summary
records the aggregate gates and individual changed labels. Reproduction and rollout
instructions are in [Batch 2 compatibility](../batch2-compatibility.md).

This establishes no observed regression on the supplied corpus, not perfect OCR on
arbitrary documents. New foreign-currency business outcomes remain provisional until
an actual conversion/v4 policy is supplied. The frozen production pack and existing
production histories were not rewritten or deployed by this evaluation.
