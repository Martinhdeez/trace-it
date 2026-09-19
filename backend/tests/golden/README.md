# Golden outcomes for batch 1

The outcome we expect for each of the 500 files of batch 1. The organisers keep the real reference private, so this one is built from the challenge files by code that shares nothing with the application: its own regex parser and its own reading of Norma_Pagos_v3. Tests use it to prove, without any LLM, that the hand-written rules, the engine, the sandbox and the source shapes agree with an independent reading of the norm on real data.

| File | Content |
|---|---|
| `batch1_expected.jsonl` | 500 lines `{"file_id", "expected", "confidence", "why"}` |
| `batch1_symbols.jsonl` | 471 lines: the symbols of each text PDF, named as in `processes/invoice-payment.json` |
| `build_golden.py` | Builds both files from the challenge data |
| `golden.py` | Loaders, and `KNOWN_MISMATCHES` (empty) |

Counts: **433 PAGAR, 36 NO_PAGAR, 2 ESCALAR, 29 unknown** (`expected: null`, the image-only scans).

## How it is produced

```bash
cd backend && uv run python -m tests.golden.build_golden   # needs pdftotext (poppler)
```

Deterministic and idempotent: the same inputs give byte-identical files. `test_build_golden.py` rebuilds both and fails if the committed copies are stale; it is skipped without the challenge submodule or `pdftotext`.

1. **Text:** `pdftotext -layout`. Fewer than 50 characters means an image-only scan: `expected: null`, `confidence: none`.
2. **Symbols:** a regex parser reads all six invoice templates; totals come from the last page; `date` keeps the printed numbers (31/02 becomes `2026-02-31`). All 8 symbols the rules need were found in all 471 text PDFs. `issuer_name` and `free_text` are not extracted: no rule reads them.
3. **Sources:** `tests/support/challenge.py` reads the `Proveedores` and `Pedidos_2026` sheets and the ERP export embedded in `alberto_erp.py` (as text, never imported), shaped as `processes/invoice-payment.json` describes them. `parameters.cut_off_date` is `2026-09-18`, the day batch 1 arrived. The e2e engine test uses the same loader.
4. **Decision:** every finding is recorded, then the highest-priority outcome wins: ESCALAR > NO_PAGAR > PAGAR.
5. **Cross-check:** every file in the trap table of `.artifacts/specs/batch1-analysis.md` must show the same finding here, or the build fails.

## Decisions built into the golden

| Situation | Outcome | Why |
|---|---|---|
| IBAN differs from the master, or the NIF is not in the master | NO_PAGAR | Item 1 of the norm is a requirement; not treated as an anomaly for a person |
| Same order invoiced twice (factura_41082 + 2026-0233-A_catering, PO-2026-0492) | ESCALAR, **both** | Team decision, 2026-09-18 |
| Invisible characters (zero-width etc.) | Stripped before parsing, not an anomaly | FA-4488 and F26-3011 are correct once stripped |
| Instructions in the invoice text ("registrar como PAGAR", "marcar como ESCALAR"...) | Ignored; noted in `why` as `INJECTED_TEXT` | No rule reads free text (process convention 6) |
| VAT rate other than 21 % | ESCALAR | Rule R09. No text PDF in batch 1 has one |
| VAT miscalculated (16 % applied, 21 % printed) | NO_PAGAR | Rule R08 |
| `pendiente_revisar` sheet (PO-2026-0007, PO-2026-0141) | Ignored | A note in the workbook, not a source of truth |
| Missing symbol | ESCALAR | Rule R01 (none among the text PDFs) |

`confidence` is `high` when the outcome follows from the norm's wording, `medium` (21 files) when it rests on a team decision above or the invoice carries injected instructions, `none` for the scans. `why` lists every finding (`AMOUNT_NE_PO: 12874.4 vs 12847.4`) and the notes (`INVISIBLE_CHARS`, `INJECTED_TEXT`); a clean file says `clean: no finding`.

## The norm-driven process

The golden checks the hand-written rules, whose decisions are explicit. The rules the
normalizer writes from the norm (ADR 0017) take the decision of a failed check from the use
case policy `failed_check_decision` whenever the norm does not name one. The invoice use
case sets `NO_PAGAR` (product owner, 2026-09-19: a rule not complied with rejects; a rule
that cannot be applied escalates), which matches the decisions above except the duplicate
order, which the golden escalates as a team decision. The golden is not changed to follow
the policy: `make eval-norm` reports the difference, and `docs/mentor-questions.md` lists the
doubts that would move either side.

## When the golden and the rules disagree

Do not weaken the test. Investigate and decide which side is wrong. Meanwhile add the file to `KNOWN_MISMATCHES` in `golden.py` with the reason; it runs as a strict `xfail`, so CI fails as soon as the disagreement goes away. To change a decision above, edit `build_golden.py`, rebuild, and commit the script with both `.jsonl` files.
