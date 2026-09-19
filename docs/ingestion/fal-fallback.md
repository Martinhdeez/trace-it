# fal.ai as a possible visual fallback (research, 2026-09-19)

This is an API and implementation review, not a claim that a fal-hosted reader
improves invoice accuracy. No new paid requests were made for this review. The
current production committee uses local OCR, optional Gemini or an
OpenAI-compatible visual endpoint, and Jev's text-only selection. `FAL_KEY` is
used only by the existing explicit GOT-OCR experiment; fal is not a production
fallback today.

## Documented candidates

| Endpoint | Documented request and response | Published price | Fit for this corpus |
|---|---|---|---|
| [`fal-ai/moondream3-preview/query`](https://fal.ai/models/fal-ai/moondream3-preview/query/api) | Required `image_url` and `prompt`; optional `reasoning`, `temperature`, `top_p`. Response includes `output` (string), `finish_reason`, and token `usage_info`. Image inputs accept a base64 data URI. | [$0.40 per million input tokens and $3.50 per million output tokens](https://fal.ai/models/fal-ai/moondream3-preview/query). | Promptable visual reader with a distinct model family. It is a preview endpoint; invoice transcription and exact financial fields are unmeasured here. |
| [`openrouter/router/vision`](https://fal.ai/models/openrouter/router/vision/api) | Required `prompt` and `model`; optional `image_urls`, `pdf_urls`, `system_prompt`, `temperature`, and `max_tokens`. Response includes `output` (string) and `usage.cost`. Image/PDF inputs accept data URIs. | [Charged according to actual token usage of the selected model](https://fal.ai/models/openrouter/router/vision/api); there is no single endpoint-wide per-image price. | One route to a deliberately selected image model. Choosing Gemini through it provides another route to Gemini, not an independent visual reader. Model choice must be fixed before comparing results or cost. |
| [`fal-ai/got-ocr/v2`](https://fal.ai/models/fal-ai/got-ocr/v2/api) | `input_image_urls` (list of image URLs), optional `do_format` and `multi_page`; response `outputs` (list of strings). Image inputs accept a base64 data URI. | [$0.05 per image](https://fal.ai/models/fal-ai/got-ocr/v2). | Already evaluated on difficult development scans; its results do not support making it the default fallback for this corpus. |

All three endpoint guides document a client call that waits for completion and
also a queue flow: submit, retain `request_id`, check status, then retrieve the
result. The queue is important for a paid call that outlives an HTTP request or
worker restart. The documented data-URI support avoids publishing invoice
images at a public URL. These are published API contracts and prices, not
confirmation that a particular account has model access, predictable latency,
or stable pricing.

The existing [GOT comparison](ocr-comparison.md) used five difficult development
scans. With the then-current field parser, original pages yielded 12/47 matching
fields and corrected/cropped pages 29/47; the local route yielded 42/47 and the
Gemini experiment 46/47. Cropping excluded part of one header, and the sample
was selected for difficulty. The figures measure image reading **and** parsing
on those cases; they are neither a general model ranking nor a held-out result.

## Integration boundary

[`VisionFallback`](../../backend/app/features/ingestion/ocr/vision.py) currently
sends either a Gemini API request or an OpenAI-compatible `/chat/completions`
request. None of the three fal schemas is that request shape. Setting
`TRACEPAY_VLM_URL` to a fal endpoint would therefore not integrate it.
The locked backend already includes `fal-client`, and the
[`compare_fal_ocr` tool](../../backend/app/features/ingestion/tools/compare_fal_ocr.py)
shows queue submission and response recovery. A production adapter needs a
separate, opt-in fal provider choice and endpoint-specific response parsing;
it does not need a new Python dependency.

The first candidate to benchmark is Moondream 3 Preview, with one fixed
transcription prompt. Compare it with one explicitly selected OpenRouter visual
model as a second candidate. Leave the existing local and Gemini defaults
unchanged until a held-out evaluation shows a measurable benefit. A second
route to the same Gemini model cannot count as independent corroboration.

For an opt-in implementation:

1. Trigger fal only for a scan whose local evidence leaves specified critical
   fields missing or uncertain and whose configured visual path is unavailable
   or fails. Cap calls per page and per document; use the existing targeted
   field/crop budget rather than submitting the entire 500-file corpus.
2. Include endpoint ID, selected model, prompt version, page/crop hash, options,
   request ID, timestamps, status, and response in the provider journal. Persist
   the queue request ID immediately after submission. After a timeout or restart,
   retrieve that request instead of blindly submitting another paid call. If
   delivery is uncertain and no ID was recorded, surface the uncertainty for
   review rather than automatically resending.
3. Set explicit submission and result timeouts. Trace each `provider_call`,
   including cache/recovery, failures, latency, and reported usage/cost without
   exposing credentials or full document contents in traces. Preserve the
   original PDF, local candidates, all fal transcripts, and their provenance.
4. Parse the returned transcript through the existing invoice reader. Treat
   fal-only critical values as unverified proposals until independent evidence
   corroborates them; the remote model never approves payment or replaces
   stored evidence by itself.

Evaluate offline on saved, consented responses first. For any later explicit
paid benchmark, fix the document set and model versions, cap requests and spend,
save request IDs, and compare field-level exact matches, unsupported values,
uncertain-field recovery, final decision changes, latency, and observed cost
against the same human-reviewed reference. Include held-out scans, not only the
five development examples. Only promote a default after these results are
reviewed; no credentials or paid submissions are needed to implement the
adapter and its mocked tests.
