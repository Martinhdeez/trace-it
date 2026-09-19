---
status: proposed
---

# Evaluate fal.ai visual readers before selecting a production fallback

## Context

The OCR committee can lose its visual reader when a provider is unavailable or
the document remains unreadable. The team requested a review of fal.ai models as
an additional API fallback. Available endpoints alone do not establish better
recognition. The existing five-scan GOT-OCR experiment performed below local OCR
and Gemini on the measured fields, including the parser's effects.

## Alternatives considered

- Keep the current providers: no integration cost; no additional visual route.
- Make GOT-OCR v2 the default: its dedicated OCR interface is convenient, but the
  repository's measured sample does not support the change.
- Evaluate Moondream3 Preview Query: another model family and a transcription
  prompt, with preview stability and financial-field accuracy still unmeasured.
- Evaluate one fixed model through fal's OpenRouter Vision: broader model choice,
  but extra routing and model-dependent cost. Routing the same Gemini model through
  another service is not independent corroboration.

## Proposed decision

Evaluate Moondream3 Preview and one explicitly selected OpenRouter visual model
against stored baseline responses and a held-out invoice set. Use exact fields,
unsupported values, recovery, final decision changes, latency and observed cost,
not a general model leaderboard. Record the document hashes, versions, prompt,
request IDs and all responses. Do not change the production default on API
availability or marketing claims alone.

If the evaluation supports integration, add an explicit opt-in fal adapter with
the same evidence policy as ADR 0022. Restrict requests to unresolved documents or
crops after the configured visual path fails; bound calls and timeouts. Save queue
request IDs before polling and resume them rather than resubmit after a timeout.
Uncertain delivery without an ID must remain visible. Every operation must have a
`provider_call` trace and a journal entry; keep reported usage separate from replay.

## Consequences and status

This is a proposed extension, not an implemented production route. `FAL_KEY`
continues to serve the explicit comparison tool only. The existing `fal-client`
dependency can support an adapter, but setting `TRACEPAY_VLM_URL` to a fal endpoint
cannot: the request and response schemas differ. No new paid requests were made
for this investigation, and no accuracy improvement is claimed.

## Evidence

The dated [fal.ai API review](../../ingestion/fal-fallback.md) records official endpoint
schemas, source links, published prices, the historical five-scan comparison and
the proposed evaluation procedure. API access, live model behavior and quality on
held-out invoices remain unverified.

## Related

ADRs 0002, 0008, 0018, 0019 and 0022.
