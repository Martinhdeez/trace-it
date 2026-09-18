# Extraction committee

Pipeline `invoice-v2.0.0+xlsx-v1.3` returns available readings without document review
states. A single model can supply a value when others cannot read it.

## Routing

1. Read sufficient native PDF text directly.
2. Run both local OCR recognizers on pages needing OCR, including incomplete first readings.
3. Consult the configured visual server or Gemini for unresolved readings. Missing currency
   alone in native documents does not trigger visual inference.
4. Ask configured Jev to select existing candidates or `none` from labelled transcriptions.

Omitted `vlm`/`jev` options permit configured providers; `false` disables them.

## Selection

Use a valid Jev selection, otherwise a corroborated internal reading, otherwise the first
reader with one usable candidate: native, visual, primary OCR, secondary OCR, then unlabelled
OCR. Preserve every alternative and source text. A field can have `value=null` while
retaining raw `text`. Disagreement does not erase available readings or demand human review.

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
