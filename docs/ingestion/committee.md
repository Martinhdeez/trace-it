# Extraction committee

Pipeline `invoice-v2.1.4+xlsx-v1.3` returns available readings without document review
states. NIF, IBAN and purchase order separate proposals from verified transcriptions;
other fields retain the v2.0 best-reading policy. See [verification results](focused-verification.md).

## Routing

1. Read sufficient native PDF text directly.
2. Run both local OCR recognizers on pages needing OCR, including incomplete first readings.
3. Consult the configured visual server or Gemini for unresolved readings. Missing currency
   alone in native documents does not trigger visual inference.
4. Ask configured Jev to select existing candidates or `none` from labelled transcriptions.
5. Reread unresolved critical identifiers in bounded crops at 150 and 600 dpi, with
   measured deskew. Require local/visual corroboration; changes of scale do not create
   independent readers. Stable local readings can trigger one final visual crop.
6. If local detection failed and coherent periodic scanner bands are measurable,
   recover the column displacement and rerun local OCR once per page. Preserve original
   evidence; geometric resampling supplies no invented digits or reference values.

Omitted `vlm`/`jev` options permit configured providers; `false` disables them.

## Selection

Use a valid Jev selection, otherwise a corroborated internal reading, otherwise the first
reader with one usable candidate: native, visual, primary OCR, secondary OCR, then unlabelled
OCR. This produces `proposed_value`. Critical identifiers additionally require native
evidence or corroboration; unresolved focused checks withhold `value`. Preserve every
alternative and source text. A field can have `value=null` while retaining raw `text`
and proposals. Business rules decide the consequence of missing verified identifiers.

Jev receives text, not images. Its selection is not independent pixel evidence.
`agreeing_readers` identifies actual supporting readers. OCR confidence is not calibrated.
Partial arithmetic checks route additional readers and record disagreements; they do not
change printed amounts. Identifiers are not reconstructed from source tables or checksums.

## Evidence and recovery

`data.committee` records readers and selections. Candidate locators distinguish primary
and secondary OCR, page and region. Transformations remain traceable.

Provider journals preserve request identities and completed responses without credentials.
Completed responses can be reused. Interrupted/failed delivery is not resent automatically.
Available readings survive provider errors. Journals contain document text and stay outside Git.

Adapter-call metrics can include journal reuse; they do not necessarily mean new remote calls.
Extraction cache hits have zero calls for the current request.
Shared OCR errors and wrong visual proposals remain possible; see [audit](corpus-audit.md).
