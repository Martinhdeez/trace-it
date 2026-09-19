# PDF field traceability

The document popup renders the original PDF. Selecting an extracted field navigates
to its source page and highlights its quote. Zoom and rotation apply to the image
and rectangles together. The field list comes from the saved extraction, so new
schema/rule fields require no viewer code. Re-extract a pending document to apply a
new extraction plan; historical decisions retain their original readings.

Document-origin symbols in the decision trace open the viewer at their reading.
The response includes `symbol_fields`, mapping process symbols to extraction
fields using the persisted ingestion adapter (for example `total` to
`gross_amount` for invoice-payment). Generic and newly added schema fields keep
their names. The current process definition cannot redirect historical evidence.
The popup's Info button exposes processing metadata on desktop and mobile;
the panel starts collapsed to leave room for the PDF and extracted fields.
Evidence-loading errors show an explicit retry instead of a generated facsimile.

`GET /instances/{id}/document/locations` returns the extraction ID, file SHA-256,
page dimensions and a `fields` map. Each field contains its candidate readings:
`candidate` (zero-based index), `page` (one-based), `raw`, normalized `value`, reader
`method`, original `locator`, `precision` and `boxes`. Candidates remain separate,
including disagreements and unverified proposals. Metadata fields without a
document quote have no candidate location.

Each box is `[left, top, right, bottom]`, normalized to `[0, 1]` on the displayed
page after the PDF's intrinsic rotation. Multiline values have separate rectangles.
OCR rectangles include a small height-relative margin so the border does not clip
characters. The viewer draws the outline outside the measured rectangle, keeping
short native words readable too. Matching tolerates spaces omitted between labels,
amounts and currencies.
The quote, rather than the normalized value, determines the geometry: for example,
`2027-04-21` highlights `21/04/2027`.

| Precision | Meaning |
|---|---|
| `text` | Unique quote matched to native PDF glyphs within its evidence region |
| `ocr` | Unique quote matched to OCR character/word boxes within its evidence region |
| `region` | Only a bounded source region is available; shown with a dashed border |
| `page` | Source page known, precise location unavailable; no rectangle |
| `unavailable` | No valid source page recorded |

Local OCR retains character geometry before combining boxes into lines. For historical
scans or visual readings without geometry, the locator may run local OCR once per
required page, using the existing image/model cache. This only grounds the saved
quote; it does not propose values, call remote models, or change saved evidence,
symbols or decisions. Missing local weights or ambiguous matches fall back to the
recorded region/page. A whole-page transcript never becomes a precise rectangle.
Focused/dewarped word coordinates without an inverse transform are not reused.

`GET /instances/{id}/document/pages/{page}` returns a bounded-resolution PNG rendered
from the stored PDF. Both endpoints use the same user requirement as document
evidence. The viewer downloads the original PDF via the existing file endpoint.
