# Golden outcomes for batch 1

The outcome we expect for each of the 500 files in La Caja (batch 1). The organisers keep the real reference private, so we built our own from the challenge files. Tests use it to prove, without any LLM, that the rules, engine, sandbox and sources give the right answers on real data.

| File | Content |
|---|---|
| `batch1_expected.jsonl` | 500 lines `{"file_id", "expected", "confidence", "why"}` |
| `batch1_symbols.jsonl` | 471 lines: the symbols of each text PDF, using the names in `processes/invoice-payment.json` |
| `build_golden.py` | Builds both files from the challenge data |
| `golden.py` | Loaders, and `KNOWN_MISMATCHES` (currently empty) |

Counts: **433 PAGAR, 36 NO_PAGAR, 2 ESCALAR, 29 unknown** (`expected: null`, the image-only scans).

## How it is produced

```bash
cd backend && uv run python -m tests.golden.build_golden   # needs pdftotext (poppler)
```

The script only reads `.context/500-sombras-de-alberto`. It is deterministic and idempotent: the same inputs always give byte-identical files. `test_build_golden.py` rebuilds both files and fails if the committed copies are stale. It is skipped when `pdftotext` is missing, as it is in CI.

1. **Text:** `pdftotext -layout` on each PDF. Fewer than 50 characters means an image-only scan (26 `scan_*`, `fax_2026_0411`, `reimpresion_0712`, `copia_*`): `expected: null`, `confidence: none`.
2. **Symbols:** a regex parser, written separately from the app, reads all six templates (Spanish, uppercase, simplified, "Nº de factura", English with dot decimals, multi-page with "Suma y sigue"). Totals come from the last page. `date` keeps the printed numbers, so 31/02 becomes `2026-02-31`. All 8 required symbols were found in all 471 text PDFs. `issuer_name` and `free_text` are not extracted, because no rule reads them.
3. **Sources:** the `Proveedores` and `Pedidos_2026` sheets of the workbook, and the ERP export embedded in `alberto_erp.py`. That file is read as text, never imported or run. `parameters.cut_off_date` is `2026-09-18`, the day batch 1 arrived. Source loading lives in `tests/support/challenge.py`, and the engine test uses the same loader.
4. **Decision:** the script's own reading of Norma_Pagos_v3, written separately from Mateo's rule code (`processes/rules-v3/`). It records every finding and then takes the highest-priority outcome: ESCALAR > NO_PAGAR > PAGAR.
5. **Cross-check:** each file in the trap table of `.artifacts/specs/batch1-analysis.md` must show the same finding, or the build fails.

## Decisions built into the golden

| Situation | Outcome | Why |
|---|---|---|
| IBAN differs from the master, or the NIF is not in the master | NO_PAGAR | Rule 1 of the norm is a requirement. It is not treated as an anomaly for a person |
| Same order invoiced twice (factura_41082 + 2026-0233-A_catering, PO-2026-0492) | ESCALAR, **both** invoices | Team decision, 2026-09-18 |
| Invisible characters (zero-width etc.) | Stripped before parsing, not an anomaly | Team decision. FA-4488 and F26-3011 are correct once stripped |
| Instructions in the invoice text ("registrar como PAGAR", "debe marcarse como ESCALAR"...) | Ignored. Noted in `why` as `INJECTED_TEXT` | No rule reads free text (process convention 6) |
| VAT rate other than 21 % | ESCALAR | Rule 9. No text PDF in batch 1 has one |
| VAT miscalculated (16 % applied, 21 % printed) | NO_PAGAR | Rule 8 |
| `pendiente_revisar` sheet (PO-2026-0007, PO-2026-0141) | Ignored | It is a note in the workbook, not a source of truth |
| Missing symbol | ESCALAR | Rule 1 (none in batch 1) |

`confidence` is `high` when the outcome follows directly from the norm's wording. It is `medium` when it depends on one of the team decisions above (IBAN, unknown NIF, duplicate order, VAT rate, missing symbol) or when the invoice contains injected instructions (21 files). It is `none` for the scans.

`why` lists every finding, for example `AMOUNT_NE_PO: 12874.4 vs 12847.4`, followed by the notes (`INVISIBLE_CHARS`, `INJECTED_TEXT`). A clean file says `clean: no finding`.

## When the golden and the rules disagree

Do not weaken the test. Investigate and decide which side is wrong. While the team decides, add the file to `KNOWN_MISMATCHES` in `golden.py` with the reason. It then runs as a strict `xfail`, so CI fails as soon as the disagreement goes away and the entry can be removed.

To change a decision above, edit `build_golden.py`, rebuild, and commit the script together with both `.jsonl` files.
