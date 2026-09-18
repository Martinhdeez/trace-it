# Full PDF corpus audit

2026-09-19: **500 PDFs, 522 pages, 471 native documents and 29 scans**.
Originals were preserved and identified by SHA-256.

## Reference

All pages were rendered and visually inspected. Native documents were compared with separate
Poppler extraction. Scans were inspected as original renders and crops. Their ten-field
references are provisional assistant readings, not independent human ground truth or
character-exact CER/WER labels.

The user corrected two assistant readings where the models were right:
`scan_023.pdf` invoice **2026/22608**, and `scan_011.pdf` IBAN
**ES83 6888 4400 1235 8890 0142**.

Eight fields lack reliable references: NIF/IBAN in `copia_2026_0518.pdf`,
`fax_2026_0411.pdf` and `scan_023.pdf`; invoice number/NIF in `scan_021.pdf`.
Their model proposals are excluded from accuracy counts. Workbook values were not used.

## Current v2 results

All 500 PDFs were submitted and retrieved through the real API without processing failures.
Local OCR ran again; completed visual/textual responses were reused from provider journals.

| Scan field result | Count |
|---|---:|
| Selected reading matches provisional reference | 279 |
| Selected reading differs | 2 |
| No normalized reading | 1 |
| No reliable reference, excluded from denominator | 8 |

The 282 known-reference fields include two selected-value disagreements:

- `scan_004.pdf`, order: secondary OCR `PO-2028-0480`, reference `PO-2026-0480`.
  Visual text `PC-2026-0480` was not parsed as a valid PO.
- `scan_010.pdf`, IBAN: visual reading contains `1236`, reference `1235`.
  The correct primary OCR candidate remains available.

The unnormalized field is `scan_017.pdf` NIF; raw text is preserved.

| Requested document | Fields with a normalized reading |
|---|---:|
| `scan_016.pdf` | 10/10 |
| `scan_017.pdf` | 9/10 |
| `scan_023.pdf` | 10/10 |
| `fax_2026_0411.pdf` | 9/10 |
| `copia_2026_0518.pdf` | 10/10 |

Coverage is not accuracy: counts include proposals for fields without reliable references.
Results retain alternatives and provenance and do not select document review states.

Native documents produced 4,532 matching normalized fields, 175 absent currencies and three
invalid printed dates: `2026-03-19_P008.pdf`, `FA-1123_construcciones.pdf` and
`FA-2967_seguridad.pdf`. Raw text is retained.

## Historical comparison

v1.8 accepted 113 scan values, withheld 169 known-reference fields and had no accepted
disagreement. v1.9 accepted 224, withheld 58 and had no accepted disagreement.
Both excluded eight fields lacking references.

The v1.9 real committee run made 58 local OCR, 28 Gemini and 18 Jev adapter calls, with
no provider errors. On Gemini's 272 known-reference fields, 269 matched, one differed
and two were not parsed. Jev selected 162 matching candidates and abstained on ten
known-reference fields across 18 documents.

These acceptance statistics do not describe v2: the current contract exposes more readings
and has the two selected-value discrepancies above. The old COMPLETE/NEEDS_REVIEW document
counts are retired.

## Artifacts

Ignored local evidence lives in `backend/reports/corpus-audit-20260919/`: SHA manifest,
renders, reader text, references, API responses and comparison tables.
Current results: `readings-v2-records/`, `readings-v2-fields.csv`,
`readings-v2-summary.json`. Historical runs remain separately labelled.

No filename-specific production rules were added. A human-labelled holdout is still needed
before claiming general accuracy or training a student model.
