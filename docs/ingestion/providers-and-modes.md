# OCR modes, providers and billing

The invoice workflow remains the default. Change the execution mode without changing
the process symbols or rules. Native PDF text and spreadsheet parsing run locally in
every mode; an API mode replaces image recognition, not PDF decoding or business rules.

| Mode | Image readers | Remote field mapping / text judge | Model weights |
|---|---|---|---|
| `hybrid` (default) | Two local OCR readers, then configured visual providers when needed | Allowed when needed | Required for local recognition |
| `local` | Local OCR only | Disabled, even when credentials exist | Required for scans |
| `api` | Up to two distinct configured visual models | Allowed when needed | Not loaded or inspected |

One visual model produces proposals. Two distinct visual models may corroborate a
reading; conflicts and unreadable characters remain unresolved. A model's retry,
cached response, or rereading of a crop is not an independent vote. The text judge
only selects existing candidates and never verifies pixels or decides payment.
Coverage can differ by mode. Missing local weights do not silently enable paid APIs
in `local` mode.

## Choose a mode

Set the server default in the ignored root `.env`:

```dotenv
TRACEPAY_OCR_MODE=hybrid
TRACEPAY_OCR_PROFILE=verified
```

For an offline reader, use `TRACEPAY_OCR_MODE=local`. For hosted image models without
local weights, use `TRACEPAY_OCR_MODE=api`. Both alternative server configurations
also require `TRACEPAY_OCR_PROFILE=experimental`. The default `verified` profile
checks the evaluated local weights and Gemini/Jev primary readers before startup;
it cannot certify a different committee. For example, an API-only Helmcode server uses:

```dotenv
TRACEPAY_OCR_PROFILE=experimental
TRACEPAY_OCR_MODE=api
TRACEPAY_VISION_PROVIDERS=helmcode
TRACEPAY_TEXT_PROVIDERS=helmcode
HELMCODE_API_KEY=your_private_key
```

Restart the server after editing `.env`
(or recreate the Docker backend). This is separate from process field/rule updates,
which are read from the published process version on each request. Unpublished
edits do not change an active process's extraction contract.

Override the default for a particular request with multipart `mode=local`, `api`,
or `hybrid` on `/v1/extractions`, `/v1/batches`, or `/processes/{id}/files`:

```powershell
curl.exe http://127.0.0.1:8000/v1/extractions -H "X-User-Id: 1" -F "file=@invoice.pdf" -F "mode=local"
```

Pending-instance re-extraction accepts the same option in JSON:

```json
{"mode": "api"}
```

The mode is a request configuration, not a server authorization boundary: callers
allowed to extract can explicitly select another mode. The existing `vlm=false`
and `jev=false` switches still disable their stages. `ocr=false` disables local
recognition. Local mode always disables provider stages; API mode always disables
local recognition. Native evidence still works with every reader disabled.

`GET /v1/ocr/config` shows the default mode and configured model chains without
credentials. Configuration means a key/model is present, not that the provider
has granted access or has remaining quota.

## Provider order and Helmcode

```dotenv
# Existing providers remain first. Unconfigured entries are skipped.
TRACEPAY_VISION_PROVIDERS=compatible,gemini,helmcode
TRACEPAY_TEXT_PROVIDERS=jev,helmcode
TRACEPAY_GEMINI_MODEL=gemini-3.1-flash-lite
TRACEPAY_JEV_MODEL=jev-1.13.0
HELMCODE_API_KEY=your_private_key
TRACEPAY_HELMCODE_VISION_MODELS=qwen3.6,gemma4
TRACEPAY_HELMCODE_TEXT_MODEL=qwen3.6
TRACEPAY_PROVIDER_TIMEOUT_S=60
```

`compatible` uses the existing `TRACEPAY_VLM_URL`, `TRACEPAY_VLM_MODEL` and optional
`TRACEPAY_VLM_API_KEY`. The URL is a base ending in `/v1`; the adapter appends
`/chat/completions`. Helmcode defaults to `https://api.helmcode.com/v1` and accepts
an alternate base through `HELMCODE_URL`.

In hybrid mode, a successful first image reader ends the chain. An unavailable,
rate-limited, malformed or truncated response allows the next configured reader.
API mode collects at most two distinct successful visual models for corroboration.
With only Helmcode configured, Qwen and Gemma can supply these two readings.
To use only Helmcode remotely, set `TRACEPAY_VISION_PROVIDERS=helmcode` and
`TRACEPAY_TEXT_PROVIDERS=helmcode`. Fewer configured visual models can mean more
abstentions, not weaker verification.

`TRACEPAY_TEXT_PROVIDERS` controls the invoice candidate judge. Generic schema
mapping uses the visual provider order to select a provider for a **text-only**
request containing document lines and requested fields; Helmcode uses its text
model for this step. Jev's candidate-choice API cannot perform this quote-mapping
operation. Disabling `vlm` also disables schema mapping; local mode disables both.

Helmcode's documented image models are **Qwen 3.6** and **Gemma 4**. **GLM 5.3 is
text only** and cannot replace the image reader. It can be explicitly selected
for the text stage if the account has access. The official model pages have used
different GLM aliases; authenticated `/v1/models` on 2026-09-19 returned `glm5.3`,
`qwen3.6` and `gemma4`. Listing a model does not prove entitlement. See the
[model documentation](https://helmcode.com/docs/models) and
[authentication guide](https://helmcode.com/docs/authentication).

Qwen/Gemma requests use `reasoning_effort=none` for bounded transcription and
selection. Their documented default enables reasoning, which can consume the
output budget and add latency. The implementation still validates the returned
text or JSON; disabling reasoning is not a correctness guarantee.

The [three-scan probe](benchmark-2026-09-19.md#helmcode-probe) supports Qwen as
the first Helmcode reader. Gemma made many more digit errors in that small sample.
Do not replace corroboration with confidence in a model name.

## Usage, cost and latency

Read `/processes/{id}/metrics/ingestion` for provider/model/operation aggregates.
Inspect `provider_call` events for individual attempts, HTTP status, fallback,
tokens, duration and billing basis. Network calls, cached journal reads and
blocked uncertain calls are separate. Sum tokens/cost only for real network
attempts. A response rejected after HTTP 200 can still consume tokens.

Provider durations are nested inside image, text-judge and focused-reading spans.
Do not add parent and child durations to estimate wall time. Measure the outer
HTTP request for per-document latency and the whole pipeline for elapsed time.
Local OCR has no API token fee, but consumes CPU, memory and execution time.

The known Gemini/Jev tariffs are estimates at published standard API rates,
not account invoices. Gemini candidate output and thinking tokens are billed
together; OpenAI-compatible completion counts already include reasoning tokens.
Reported cached input is handled separately. Missing usage or an unknown tariff
remains unknown. The journal preserves safe usage metadata, including failed
requests, without credentials.

Helmcode may use a subscription, add-on allowance, or prepaid credits. A reported
600M-token allowance is account information, not a public per-token price, and
this application cannot infer the account's remaining balance. The default is:

```dotenv
TRACEPAY_HELMCODE_BILLING_MODE=unknown
```

After verifying that calls are included in the account's subscription, select
`included` to report zero **marginal API cost**, excluding the subscription fee.
For metered credit billing, configure the actual account tariff:

```dotenv
TRACEPAY_HELMCODE_BILLING_MODE=metered
TRACEPAY_HELMCODE_INPUT_USD_PER_M=0.00
TRACEPAY_HELMCODE_OUTPUT_USD_PER_M=0.00
```

Replace the example rates; zero is not an inferred Helmcode tariff. Published
[pricing](https://helmcode.com/pricing), [credit rules](https://helmcode.com/docs/credits)
and [rate limits](https://helmcode.com/docs/rate-limits) distinguish account quotas
from rate limits and model add-ons. GLM availability is not implied by a general
token allowance. No subscription is purchased or changed by this integration.

## Evidence and caches

The effective mode, configured reader chain/model, extraction fields, relevant
implementation and model identities participate in cache invalidation. Credentials
do not enter cache keys or public diagnostics. Rules that change without changing
required fields can reuse document readings. New fields invalidate field mapping
while reusable page evidence remains available.

Each provider request has a content-addressed journal. An uncertain request is
not blindly sent again; fallback uses another configured reader. Saved responses
do not become additional independent evidence. Keep originals, proposal values
and conflicts available for review, including after a provider fails.

See [ADR 0027](../adr/0027-ocr-execution-modes-and-provider-fallback.md), the
[API contract](api.md), and the [measured 500-document run](benchmark-2026-09-19.md).
