# Native PDF layout and quality

The native reader keeps PyMuPDF and the existing OCR committee. It annotates ruled
tables, reads clear prose columns in order, and reports suspect word spacing before
the invoice or generic-schema adapters consume the text. No new model or dependency
is required. The ideas come from Zenith's PDF ingestion, adapted to field evidence.

## Evidence and conservative fallbacks

- Native line IDs, raw quotes, page numbers and unrotated bounding boxes are retained.
  Layout changes are not independent reader votes. Original PDFs remain immutable.
- Columns require a visible gutter, overlapping vertical extent, and at least four
  prose lines / 24 words on each side. Sparse forms, totals, tables, and ambiguous
  crossing content keep the existing order. Full-width headings and footers remain
  before and after the column content. Page rotation does not change the text frame.
- Ruled tables add optional `table` metadata to each completely contained line:
  table ID, zero-based row/column, and grid dimensions. Text beside a table remains
  present. Empty cells remain empty. Merged cells and uncertain membership keep the
  original lines without a guessed grid. The optional detector is bounded and falls
  back to native text with a warning on failure.
- The schema mapper receives cell coordinates with the original line IDs. A local
  two-column form reader accepts explicit labels ending in `:`, `#` or `=` and a
  single value line. It does not treat an unmarked header row as a key/value fact.
  Complex tables still require grounded semantic mapping; quotations must come
  from one original line. No values are manufactured by joining cells.
- Full document text renders table rows once with explicit cell separators, without
  inventing a header. Display formatting never becomes a field candidate.
- Suspect long alphabetic runs produce `NATIVE_SUSPECT_SPACING`. Native text is not
  rewritten. Missing fields (or a requested generic transcript) can trigger the
  existing OCR/vision path. Complete readings do not cause new recognition calls
  just because a footnote has unusual spacing. URLs and digit-bearing identifiers
  are excluded from the signal.
- Layout implementation, shared line schema and mapping prompt changes invalidate
  extraction caches through the existing source signatures. Historical evidence
  and decisions remain unchanged; pending documents can be re-extracted normally.

The PDF viewer retains the original rendered page and quote highlights. Ctrl+wheel
and trackpad pinch zoom around the pointer; buttons zoom around the panel centre.
Zoom no longer scrolls back to the selected field on every step. Selecting a field,
rotating or resetting the view still focuses its evidence.

## Regression gate

`test_native_layout.py` exercises actual generated PDFs, including short columns,
tables with side text and empty cells, crop-box offsets, all four rotations,
ambiguous headers, merged cells, parser failure, field quotes and cache replay.
Existing native-invoice, scanned-reader, schema, location and hiring-CV tests remain
part of the normal suite.
`test_native_corpus_preserves_field_values_abstentions_and_candidates` pins the
pre-layout reader's values, statuses and candidates for all 500 challenge PDFs,
captured from `dev` commit `7fccfa8`. This runs in CI with the checked-out corpus.

Compare a clean base checkout against the candidate using the candidate environment:

```powershell
backend/.venv/Scripts/python.exe tools/compare_native_pdf.py `
  --baseline ../trace-pay-dev-sync `
  --corpus .context/500-sombras-de-alberto/facturas `
  --output reports/native-layout-comparison.json
```

This gate compares every native invoice field and candidate, parser warning and
original line. A changed field or dropped/changed line fails the gate. It reports
reading-order changes separately. It makes no provider calls and does not measure
recognition quality on the 29 image-only invoices; those retain the existing OCR path.
Run the ordinary `make check` and browser PDF-evidence test as well.
