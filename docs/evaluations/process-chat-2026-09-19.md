# Process chat: live challenge evaluation, 19 September 2026

The evaluation used a disposable PostgreSQL copy of the recorded hackathon invoice
process, the production ASGI endpoints, and real Helmcode model calls. The original
database and frontend were not modified. The branch included dev through #68.

## Data and model

- 500 recorded invoices: 437 PAGAR, 36 NO_PAGAR, 27 ESCALAR.
- 16 published deterministic rules; 12 supplier rows, 516 orders and 516 ERP entries.
- Existing OCR/extraction outputs and recorded decisions were retained. This did not
  repeat OCR or reinterpret the original invoice images.
- Discovery used the pack's `helmcode:deepseek-v4-flash` configuration. Responses reported
  `deepseek/deepseek-v4.1-flash`. The same model was configured for optional review in
  the disposable database and pinned through normal manager publication.
- Discussion sampled 30 recent cases: 24 ESCALAR and 6 PAGAR, all engine-authored.
  There were no rejected or human-resolved cases in that bounded sample.

## Findings and fixes

The first discussion returned the correct cited findings for cases 499, 500 and 491,
but misstated sample counts as 26 ESCALAR and 4 PAGAR and blurred the distinction between
OCR-extracted amounts and confirmed printed values. A later response incorrectly claimed
IBAN and duplicate-order checks were absent, influenced by setup guidance about possible
policy changes.

The fixes supply computed outcome/author counts, permit citations to those summaries,
require the assistant to distinguish extracted values from verified document evidence,
and present authoring guidance as background rather than instructions defining published
policy. A retry exposed the initially missing count-citation references; that rejection
left the saved conversation unchanged. Regression tests cover count references and
separation of authoring guidance from instructions.

After the fixes, discussion correctly reported 24 ESCALAR and 6 PAGAR and accurately
explained the three cited cases. A separate coverage question correctly identified rule 3
for IBAN mismatch, rule 4 for conflicting supplier rows, and rule 16 for duplicate purchase
orders. Both successful discussion requests preserved the plan, acceptance, preview and
diff. The calls took 13.17 and 7.42 seconds respectively.

## Guidance proposal and publication

The revision request explicitly preserved all rules, sources, symbols, outcomes and
process conventions. It enabled optional review and proposed one `ownership_uncertainty`
guidance item recommending ESCALAR for uncertain purchase-order ownership, without changing
deterministic findings. It also supplied three real cases as fixed acceptance examples.

The real revision response changed exactly `guidance`, `decision_review` and `examples`.
It retained every supplied acceptance example unchanged and raised no unrelated questions.
This call took 61.39 seconds. Preparation and publication before proposal acceptance both
returned 409.

After explicit acceptance, preparation took 144.02 seconds and returned:

| Check | Result |
|---|---|
| Compiled rules | All 16 original artifacts reused |
| Historical deterministic impact | 500 unchanged, zero changes/conflicts/errors |
| Case 1, ordinary invoice | PAGAR, passed |
| Case 64, ERP already paid | NO_PAGAR, passed |
| Case 500, missing IBAN | ESCALAR, passed |
| Reviewer previews | Ten completed; four PAGAR and six ESCALAR recommendations |
| Recorded decisions and active version during preparation | Unchanged |

The baseline reviewer was disabled, so the paired previews show a disabled baseline and
new recommendations. All ten recommendations agreed with their recorded outcomes. No live
review records or decisions were written by preparation.

Publication occurred only in the disposable copy, producing version 3 with the approved
guidance and saved preview. The original 500 decision records were compared by digest
before and after; their outcomes, reasons, rule results, authors and version/execution
references were unchanged. Rule IDs and hashes were also unchanged.

A new test instance copied the evidence of `scan_029.pdf`, while preserving the original.
The resulting duplicate purchase order and missing IBAN produced ESCALAR. The live reviewer
completed, received the published `ownership_uncertainty` guidance and recommended ESCALAR,
citing the missing-data and duplicate-order findings. Its decision pinned version 3 and
captured execution inputs. Deterministic replay matched exactly. This run took 18.23 seconds.

## Scope and automated validation

This was a live smoke evaluation of discussion, a narrow subjective-guidance change,
review/approval gates, publication and subsequent execution. It did not exercise live
compilation of a new deterministic rule. The ten reviewer cases are a bounded recent
sample, not broad proof of recommendation quality. Model output can still vary.

Full `make check` passed after the fixes with PostgreSQL integration enabled:
472 unit/integration tests and 8 end-to-end/golden tests, with three expected skips.
No model keys are required by that automated suite.

To repeat against another recorded batch, clone its database, upgrade the clone to the
branch's migration head, load the discovery agent configuration, and use the manager
endpoints in [process chat](../process-chat.md). Configure and publish the reviewer model
only in the clone. Compare stored decision digests before preparation and after approval,
then run a copied invoice and replay its new decision. Do not use a live process for these
publication and duplicate-invoice checks.
