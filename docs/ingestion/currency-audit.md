# Currency audit of 175 native invoices

The batch context suggests EUR, but these 175 invoices do not print an explicit currency
field. The extractor does not silently fill EUR. Contextual resolution belongs downstream
and must retain its source and batch scope.

## Evidence

- All 471 native PDFs were read with PyMuPDF; the 175 missing-currency cases were checked
  with independent Poppler extraction.
- 174 contain no currency code/symbol. `factura_2018.pdf` mentions a tolerance of 1 EUR
  inside an instruction, not a monetary field or authorized rule.
- All 175 have one native-text page and no embedded images. Initial visual spot checks
  covered standard invoices (73), uppercase supplier headers (57) and simplified invoices (45).
  The later full audit inspected every page.
- The other 296 native invoices have explicit EUR.
- Workbook `Norma_Pagos_v3!A3:A4` specifies 0.01 EUR reconciliation/tax tolerances.
- Supplier/order sheets have no currency column. All 3,192 non-empty workbook values use
  General number formatting; the ERP entry contract also lacks currency.
- 174 documents match workbook order identifiers: 166 totals agree within 0.01 and eight
  do not. Numerical agreement alone does not prove currency or authorize payment.
- 174 have other invoices from the same supplier with explicit EUR. The exception,
  `FA-2508_consultoría.pdf`, NIF `B87654321`, order `PO-2026-9999`, has neither.

`2026-01-08_P001.pdf` prints total 3,012.89 without currency; context may propose EUR
with explicit provenance. `factura_2018.pdf` prints 4,295.50 versus order 4,295.10:
its instruction about 1 EUR cannot override the official 0.01 EUR tolerance.

Keep observed currency separate from any contextually resolved currency. An explicit
document currency takes precedence; the batch inference must not become a global default.

## Reproduce

From `backend/`, with Poppler installed:

```powershell
uv run python -m app.features.ingestion.tools.audit_currency ../.context/500-sombras-de-alberto
```

Ignored `reports/currency-audit/` contains per-file hashes, independent currency searches,
order/amount comparisons and related-document evidence. Original material commit:
`18d43b3`; the report records the workbook hash.
