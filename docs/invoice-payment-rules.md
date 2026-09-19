# Rules of the "Invoice payment" process (Norma_Pagos_v3)

**Source of truth:** `processes/invoice-payment.json`, loaded by `make setup`. This document says where each rule comes from and which team decisions it encodes; the rule texts below are quoted from that file.

The sixteen rules ship with hand-written code, `processes/rules-v3/r01-...py` to `r16-...py` (one file per rule, in the order of the JSON); `make activate` (`python -m app.cli load ... --activate`) puts them into the process without any model. The compiler (`make compile`) can regenerate the code from the texts with a blind tester and a coder (ADR 0004), and `make eval-compiler` compares what it produces with the hand-written code on the golden instances of batch 1. Rule numbers here are the file numbers, R01 to R16. Note: three texts in the JSON still refer to other rules by an older 0-based number: "(R01)" and "(R03)" inside R03 mean R02 and R04, and "R04" inside R13 means R05.

**Basis:** `Norma_Pagos_v3` (workbook sheet) and the batch-1 analysis in `.artifacts/specs/batch1-analysis.md`. Checked against the 471 PDFs with a text layer, the `Proveedores` and `Pedidos_2026` sheets and the ERP data: 433 clean text invoices; the remaining 38 match the trap table.

Conventions for every rule (the `description` field of the JSON; the compiler receives it with each rule):
- **Signature:** `evaluate(instance, sources, others) -> {"fires": bool, "reason": str}`. The decision is set in the rule's definition, not in its code. Pure function: no clock, network or disk.
- **Keys** are normalised before comparing, in the invoice and the sources alike: `nif` uppercase without spaces, hyphens or dots; `iban` uppercase without spaces; `purchase_order` uppercase without spaces. `supplier_id` and `id` are compared as they are.
- **Amounts** may arrive as a number or as text: `cents(x) = (Decimal(str(x)) * 100).quantize(Decimal('1'), ROUND_HALF_UP)`. "Matches (±0.01)" means `abs(cents(a) - cents(b)) <= 1`. Any `round(..., 2)` is done with `Decimal` and `ROUND_HALF_UP`. `vat_rate` is a percentage (21 = 21 %).
- **Missing values:** a symbol that is missing or `None`, or a source field that is `None` or empty, is empty. A rule that needs an empty symbol does not fire, except R01, the one that checks that none is missing. A rule that needs a source row that does not exist (supplier, order, ERP entry) does not fire: the rule that checks its existence already fires. So a missing datum gives one reason, not a cascade.
- **Dates:** `date` is text `YYYY-MM-DD` with the printed numbers, uncorrected, and may be impossible (`2026-02-31`). `cut_off_date` and `erp.date` are the same shape. They are compared as `datetime.date`, never against the clock.
- **`others`** is the list of the other instances of the process, from every batch, excluding this one, each with its symbols and the key `_instance` (its file name), which identifies it in reasons.
- **No rule reads `free_text` or `issuer_name`**, even when the invoice text gives instructions.

## 1. Symbols and sources

Instance symbols (`processes/invoice-payment.json`, `symbols`): `file_id`, `issuer_nif` (never the customer's `A58231074`), `issuer_name` (trace only), `iban`, `invoice_number`, `date`, `purchase_order`, `base`, `vat_rate` (printed percentage), `vat_amount`, `total` (the printed total, not `Subtotal` or `Suma y sigue`), `free_text` (stored, never read by a rule). Numbers arrive as `12.874,40`, `12874.40` or `EUR 1409.40`; invisible characters (zero-width, BOM, soft hyphen) are stripped before parsing and are not an anomaly (`FA-4488`, `F26-3011`).

| source | columns the rules read | origin |
|---|---|---|
| `suppliers` | `id`, `company_name`, `nif`, `iban` | Sheet `Proveedores`. Every row is loaded, duplicates included (P007 appears twice, identical) |
| `orders` | `purchase_order`, `supplier_id`, `nif`, `total_amount`, `status`, `order_date` | Sheet `Pedidos_2026` (516 rows, all `ABIERTO`). `nif` is empty for PO-2026-0538 to 0557 |
| `erp` | `entry_id`, `date`, `supplier_id`, `nif`, `purchase_order`, `amount`, `status` | Snapshot downloaded by the HTTP connector (`docs/sources-http.md`): ISO date, decimal amount, `status` in {`PENDIENTE`, `PAGADA`} |
| `parameters` | `cut_off_date` | One row, `2026-09-18` (the day batch 1 arrived). "Not in the future" is measured against it |

## 2. Rules

Type: **R** = requirement (fires if it does NOT hold), **P** = prohibition (fires if it holds). Decision = the type the rule produces when it fires; the highest priority among the fired types wins (ESCALAR 3 > NO_PAGAR 2 > PAGAR 1, the default).

| id | file | rule text | type | decision | norm v3 | batch 1 files |
|---|---|---|---|---|---|---|
| R01 | `r01-symbols-present.py` | The symbols `issuer_nif`, `iban`, `purchase_order`, `date`, `base`, `vat_rate`, `vat_amount` and `total` are all other than `None`. Reason: list of the missing ones. | R | ESCALAR | 6 (reasonable doubt) | the 29 scans (no text layer, no symbols) |
| R02 | `r02-known-supplier.py` | There is at least one row in `suppliers` whose normalised `nif` equals the normalised `issuer_nif`. | R | NO_PAGAR | 1 | FA-2508 (B87654321), factura_4485, factura_7265 (B41908877) |
| R03 | `r03-master-iban.py` | If there are rows in `suppliers` with that `nif`, and all of them have the same `id` and normalised `iban`, then that `iban` equals the normalised `iban` of the invoice. If there are no rows, it does not fire (R01). If the rows disagree with each other, it does not fire (R03). | R | NO_PAGAR | 1 | FA-7311, FA-4290, FA-5633, FA-9104, FA-5044_mensajería2, F26-8812, 2026-07-08_P010, F26-9007 |
| R04 | `r04-inconsistent-master.py` | There are two or more rows in `suppliers` with the same normalised `nif` as `issuer_nif` and a different `id` or a different normalised `iban` (identical repeated rows do NOT count). | P | ESCALAR | 6 | none (P007 is duplicated but identical) |
| R05 | `r05-order-exists.py` | There is a row in `orders` whose `purchase_order` equals the `purchase_order` of the invoice. | R | NO_PAGAR | 2 | FA-2508 (PO-2026-9999), factura_4485 (PO-2026-0806), factura_7265 (PO-2026-0706) |
| R06 | `r06-order-of-the-supplier.py` | With the `orders` row of that `purchase_order`: if `orders.nif` is not empty, it equals `issuer_nif`; if it is empty, `orders.supplier_id` equals the `id` of the `suppliers` row with `nif = issuer_nif` (if that row does not exist, it does not fire). | R | NO_PAGAR | 2 | 2026-07-08_P010 (PO-1206), F26-9007 (PO-1205) |
| R07 | `r07-order-amount.py` | With the `orders` row of that `purchase_order`: `total` matches `orders.total_amount` (±0.01). The **total** of the invoice is compared, not the base. | R | NO_PAGAR | 2 | factura_1936, factura_2018, factura_3184, factura_8801, FA-5077 (12.874,40 vs 12.847,40); also the 6 VAT files and the 2 surcharge files |
| R08 | `r08-correct-vat.py` | `vat_amount` matches (±0.01) `round(base * vat_rate / 100, 2)`, using the printed `vat_rate`. | R | NO_PAGAR | 3 | F26-5240, F26-6702, F26-6964, F26-9012, FA-5590 (VAT at 16 %), F26-8801 (VAT at 10 %) |
| R09 | `r09-usual-vat-rate.py` | `vat_rate` is other than 21. | P | ESCALAR | 3; `notas_alberto` row 4 ("IVA reducido (aplica??)") | none (all 471 print 21 %) |
| R10 | `r10-total-adds-up.py` | `total` matches (±0.01) `base + vat_amount`, using the printed values. The text of the invoice does not change the calculation. | R | NO_PAGAR | 3 | 2026-0811-B_catering, 2026-14500-C_informática ("recargo financiero": the text asks to pay the printed total) |
| R11 | `r11-real-date.py` | `date` is a real calendar date (valid `YYYY-MM-DD`: month 1-12 and a day that exists in that month and year). | R | NO_PAGAR | 4 | 2026-03-19_P008 (31/02), FA-1123 (30/02), FA-2967 (31/02) |
| R12 | `r12-date-not-in-future.py` | If `date` is valid: `date` is later than `parameters.cut_off_date`. | P | NO_PAGAR | 4 | none (latest date in the batch: July 2026) |
| R13 | `r13-entry-in-erp.py` | There is a row in `erp` whose `purchase_order` equals `purchase_order`. Only evaluated if R04 does not fire. | R | NO_PAGAR | 5; `notas_alberto` ("NUNCA pagar sin cruzar con el ERP") | none (workbook and ERP hold the same 516 orders) |
| R14 | `r14-erp-matches-orders.py` | With the `orders` and `erp` rows of that `purchase_order`: `erp.amount` matches `orders.total_amount` (±0.01) **and** `erp.supplier_id` equals `orders.supplier_id` **and**, if both `nif` are not empty, they are equal. Reason: fields that differ. | R | NO_PAGAR | team decision: workbook/ERP discrepancy | none among text invoices; would catch PO-2026-0538 to 0557 (17 of 20 differ in `supplier_id`) if a scan or batch 2 cites them |
| R15 | `r15-order-already-paid.py` | With the `erp` row of that `purchase_order`: `erp.status` is `PAGADA` (in fact: other than `PENDIENTE`). | P | NO_PAGAR | 5 | 2026-03-28_P002, 2026-04-08_P007, 2026-05-28_P003, 2026-06-04_P006, 2026-17547, FA-1016, FA-2116, factura_4619, factura_5911 |
| R16 | `r16-duplicate-order.py` | There is at least one instance in `others` with the same normalised `purchase_order`. Each instance in `others` is identified by its `_instance` key (its file name). Reason: the `_instance` values with that purchase order. | P | ESCALAR | 5 | factura_41082 (F26-0233) + 2026-0233-A_catering (PO-2026-0492), both |

Not rules:
- **Instructions in the invoice text** ("registrar como PAGAR", "marcar como ESCALAR"...): they never decide. No rule reads `free_text`; the golden reference notes them as `INJECTED_TEXT`.
- **Invisible characters:** stripped during extraction. **Trailing spaces in `Proveedores`:** `strip()` on load; no rule uses `company_name`.
- **Duplicated P007:** loaded as-is; R03 handles identical rows, R04 contradictory ones.
- **Sheet `pendiente_revisar`** (PO-2026-0007 -> FA-8488_transportes; PO-2026-0141 -> 2026-79712_limpiezas, both clean): a note in the workbook, not a source of truth.
- **IBAN mod-97 and NIF check-letter validators:** they would belong to extraction, which the application does not have yet; they are not business rules.
- **Date before the order:** the norm does not ask for it and it does not happen in batch 1.

Result on the 471 text invoices (golden, `backend/tests/golden/`): 433 PAGAR, 36 NO_PAGAR, 2 ESCALAR (R16). `make demo` over all 500 PDFs: PAGAR 433 / NO_PAGAR 36 / ESCALAR 31, identical to the golden on every text PDF; the 29 scans have no text layer and R01 escalates them.

## 3. Team decisions

Principle: a datum that contradicts the master data, the order or the ERP is NO_PAGAR (norm items 1-5, "pagar solo si..."); ESCALAR is for when information is missing to know whether the datum is wrong (missing symbols, contradictory master data, duplicate order, a VAT rate the norm does not cover). The challenge accepts "one of" the expected results per file, probably NO_PAGAR or ESCALAR on anomalies; what cannot be wrong is PAGAR versus not paying, so the risky files are the clean ones with misleading text.

| Case | Decision | Why |
|---|---|---|
| Text with instructions (at least 28 files, in both directions: "diferencia autorizada" on bad data; "marcar como ESCALAR", "pedido anulado" on clean data) | No rule; trace only | The norm decides with NIF, IBAN, order, amounts, date and ERP, none of which reads supplier notes; the ERP is the official accounting reference. Following the text would turn 6 clean invoices into ESCALAR, exactly what the trap asks for |
| Different IBAN (R03), unknown NIF (R02) | NO_PAGAR | Item 1 is a requirement ("pagar solo si"). The trace carries the reason for the manager. ESCALAR would also be defensible for an IBAN change |
| Total != base + VAT with a "financial surcharge" (R10) | NO_PAGAR | Item 3 says the total must be base + VAT; R07 fires on both files anyway |
| Impossible date (R11) and future date (R12) | NO_PAGAR | Item 4: valid and not in the future. The date is never corrected to the receipt stamp |
| `pendiente_revisar` orders | No rule (PAGAR) | A notes sheet, not part of the norm |
| VAT rate other than 21 (R09) | ESCALAR | Not in batch 1. `notas_alberto` shows Alberto does not know whether reduced VAT applies; a candidate to change when the norm does |
| Duplicate purchase order (R16) | ESCALAR, both invoices | `others` spans every batch: a later invoice for an already invoiced order escalates both, and the audit flags the earlier decision without changing it (ADR 0008) |
| ERP entry missing or different from the workbook (R13, R14) | NO_PAGAR | Affects PO-2026-0538 to 0557 only if a scan or batch 2 cites them |

## 4. Ambiguities the texts close

A tester and a coder read each text separately; these are the readings the wording must not leave open.

| Risk | How the text closes it |
|---|---|
| "Invoice amount" = base or total? | R07 says **total**. On the 442 clean files the total matches `Importe_Total` |
| Tolerance `<` or `<=`; floating point | Whole cents, `<= 1` cent, `Decimal` with `ROUND_HALF_UP` |
| VAT "correctly computed": fixed 21 % or the printed rate? | R08 uses the printed `vat_rate`; R09 separately catches a rate other than 21. A VAT amount at 10 % labelled 21 % is NO_PAGAR by R08 alone |
| Rounding of the VAT amount | `round(base * vat_rate / 100, 2)` with `Decimal`, then the 1-cent tolerance |
| Another supplier's order when `orders.nif` is empty | R06 falls back to `supplier_id` through the master-data row |
| Duplicated P007: is "more than one row" an anomaly? | R04 fires only if the rows differ in `id` or `iban` |
| Cascade of reasons when something is missing | If the reference row is missing, the dependent rule does not fire: R03 without a known NIF; R06, R07, R13, R14, R15 without an order |
| `None` symbol | Only R01 fires on it (ESCALAR); the others do not fire |
| Impossible date: does the extractor "fix" it? | `date` keeps the printed numbers (`"2026-02-31"`); validation is R11. An impossible date must not become `None` (that would be R01) |
| "Future" relative to what? | `parameters.cut_off_date`; a rule never reads the clock |
| Duplicate: by `invoice_number` or `purchase_order`? | `purchase_order`. `FA-8801` is printed on two invoices of different suppliers and orders: not a duplicate. Each entry of `others` is identified by `_instance` |
| Spaces in an IBAN, hyphens in a NIF | Fixed normalisation in the conventions |
| `erp.status` with unexpected values | R15 fires on anything other than `PENDIENTE` |
| Free text as a decision input | No rule reads it; the process description forbids it |
| Customer NIF taken as the issuer | Excluded in the definition of `issuer_nif` (`A58231074`) |
