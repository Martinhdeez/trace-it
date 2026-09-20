# Batch 2 compatibility

The adapted development pack is `processes/invoice-payment.json`. It retains the v3
decision priorities and adds an explicit currency review rule. The frozen delivery
snapshot under `processes/invoice-payment/frozen/2026-09-19/` is unchanged. A database
that has already published that snapshot keeps its rules until a new version is
validated and published. Updating source code does not publish business policy.

## Reading evidence

The invoice adapter now reads the supplied Spanish, Catalan, Portuguese, English,
French, Italian and German labels and literal dates, foreign fiscal identifiers,
complete alphanumeric IBANs, and explicit currency formatting. Recipient fiscal
identifiers do not become issuer identifiers. Conflicting supplemental readings
remain ambiguous; missing fields are never filled from the supplier or order master.

Mixed documents retain their page text but route fragmented spans to OCR. Vector
strokes, strikeout/ink annotations and small raster overlays crossing financial text
block the affected native observations. The field retains its proposals and reasons;
OCR agreement cannot silently reinstate a crossed-out amount. This is a bounded risk
detector, not a general handwriting or forgery detector. Clean underlines, table borders
and unrelated logos have regression tests.

Required fields with unverified document evidence escalate in the engine, including
mixed documents. The same gate runs in live decisions, dry runs and replay. The existing
full-scan review policy remains in place. Explicit impossible native dates remain literal
business evidence and reach the invalid-date rule. Missing printed currency remains
optional for the 175 original documents that omit it.

## The currency policy

Money is only compared inside one currency. An invoice is refused only for what fails
in its own currency: its internal arithmetic (`total` against `base + vat_amount`), its
VAT against its own printed rate, its IBAN against the master, a duplicate purchase
order, an ERP entry already paid. Anything uncertain about the currency escalates; it
never refuses and never pays.

The order-total rule (R07) and the VAT rule (R08) therefore stand down on an invoice
with an explicitly printed currency other than EUR. The currency rule (R18) takes over
and escalates when the printed code is not a three-letter currency code, when no
published rate covers the invoice's date, when the conversion falls outside tolerance,
or when the VAT does not match the rate printed on the invoice. It deliberately stays
silent when the invoice is already refusable on its own data — a total that does not
add up, or an account the master never approved — because the engine takes the
highest-priority rule that fired and ESCALAR outranks NO_PAGAR, so an unconditional
currency rule would turn those refusals into reviews.

Rates come from `processes/invoice-payment/rates.json` and are loaded beside the
workbook, as the `rates` source: `currency`, `eur_per_unit`, `as_of`, `valid_until`,
`tolerance_pct` and a named published `reference`. The rule uses the row whose
`as_of`..`valid_until` covers the invoice's own date — the rate in force when the
invoice was issued, never the nearest row and never a clock. A currency may hold
several rows with non-overlapping windows: a rate change is a new row, never an edit,
like every other source here. The table as delivered carries one window per currency,
the 2026 financial year, because that is the granularity of the fixings we can cite; a
monthly or quarterly table is a change to `rates.json`, not to the rule, which already
picks by window. `tolerance_pct` is 0, so the comparison holds to the norm's own cent:
every published rate reproduces its order exactly (USD 0.92, CHF 1.05, GBP 1.17,
BRL 0.16129, JPY 0.00617, MXN 0.05). No rate is ever inferred from an order or an ERP
amount;
the reason string carries the whole multiplication, the window and the reference, so a
reader can redo the sum and see which rate applied.

This is a conservative development policy, not a claim about an as-yet-unsupplied norm
v4. It applies to the adapted development pack only; the frozen delivery snapshot is
unchanged.

## Cumulative references and ERP

Prepare a new workbook without editing the original:

```sh
python tools/prepare_batch2.py \
  --book .context/500-sombras-de-alberto/FINAL_v7_DEFINITIVO_ahorasi.xlsx \
  --suppliers .context/500-sombras-de-alberto/proveedores_nuevos.csv \
  --orders .context/500-sombras-de-alberto/pedidos_nuevos.csv \
  --output output/batch2/reference.xlsx
```

The expected cumulative row counts are 16 suppliers and 555 orders. An adjacent
manifest records input hashes and row counts. Reapplying the same CSVs to a new output
adds no rows. Conflicting keys, malformed columns and formula values fail before a
workbook is written. The existing inconsistent P007 master rows are preserved as
evidence; they are not silently reconciled.

The existing workbook API loads all three workbook sources together. Use an explicit
cut-off date for the scenario; the importer does not choose a new policy date.

Prepare the ERP bundle with the reviewed files:

```sh
python deploy/erp/prepare.py --output output/batch2/erp-release \
  --workbook output/batch2/reference.xlsx \
  --update .context/500-sombras-de-alberto/erp_export_lote2.csv
```

The optional `deploy/erp/compose.update.yml` mounts the CSV read-only. In the prepared
bundle, set `TRACE_ERP_UPDATE_FILE` to the absolute host path of that CSV and use
`docker compose -f compose.yml -f compose.update.yml up -d --build`. The file must
exist; startup fails if an explicitly requested update is missing. Without the overlay,
startup retains the original 516 entries. With it, startup loads 556 entries through
the challenge's original loader. Restarting rebuilds the same cumulative state.

Paid checks inspect every matching ERP entry, independent of row order. A pending row
cannot hide a paid one. ERP/order discrepancies also inspect every matching entry.
Source-sync alerts now include an earlier PAGAR decision that becomes NO_PAGAR;
the sync itself does not prove that the payment was ours. Alerts preserve historical
decisions and require a later recorded resolution or reprocessing decision.

## Reproduce the comparison

`tools/compare_invoice_readers.py` captures real extraction results, field origins,
reader configuration, metrics and all 540 input hashes. Supply `--sources` with the
reviewed cumulative source snapshot to exercise source-triggered verification too.
Run it once against the baseline checkout and once against the changed checkout.
`--reuse-readers <baseline-output>` copies raw OCR caches and provider journals while
rerunning interpretation, so model variation cannot masquerade as a parser improvement.

`tools/evaluate_batch2.py` compares both captures through the real rule sandbox using
original and updated reference snapshots. It reports field accuracy against the
reviewed fixtures, all changed labels/reasons and mismatches against the 471 official
native golden labels. The 29 scans have reviewed field transcriptions, not official
business outcome labels. The international fixtures likewise validate literal fields,
not invented v4 labels.

`tools/rehearse_batch2.py` requires a migrated database whose name ends in `_test`.
It uploads the cumulative workbook and all 540 PDFs through the real application
routes, publishes the adapted process, downloads the live challenge ERP, decides,
exports, checks idempotency and replays representative decisions. It can reuse reader
journals, but never replaces readers or rules with expected answers.

The extraction pipeline is `invoice-v2.3.0+xlsx-v1.3`; its cache fingerprint includes
the new normalizer and visual-risk modules. Existing production decisions and extraction
evidence remain immutable. Rehearse on a fresh isolated process before rollout; do not
reset decided instances or modify PDF bytes to force rereading.
