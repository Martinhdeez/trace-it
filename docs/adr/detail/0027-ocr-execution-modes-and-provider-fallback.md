---
status: accepted
---

# Explicit OCR execution modes and bounded provider fallback

## Context

The invoice OCR path combines local recognizers, a visual provider and a textual
candidate selector. The process field contract is dynamic, but the previous
reader configuration did not offer an explicit local/API/hybrid choice or an
OCR fallback chain. Agent-model fallback (ADR 0019) does not apply to ingestion.

A full 500-document production API run preserved all 471 native golden decisions.
It also observed a Gemini response rejected after HTTP 200 and a separate HTTP
503. The measured, token-attributed API cost was USD 0.02768012; one failed request
had unknown usage. Failures and latency, rather than an assumed high token price,
motivate bounded failover. See the [benchmark](../../ingestion/benchmark-2026-09-19.md).

## Decision

1. Add explicit `local`, `api` and `hybrid` execution modes. Hybrid remains the
   default and preserves the invoice path. A request can override the configured
   default. Local mode disables provider stages; API mode does not load or inspect
   local OCR weights. Every mode can use deterministic native PDF text. Preserve
   the verified startup profile from `dev`; alternative server committees require
   `TRACEPAY_OCR_PROFILE=experimental` and are not labelled verified.
2. Configure ordered visual and textual provider chains. Keep existing providers
   first. Add Helmcode Qwen 3.6 as the first Helmcode visual/text fallback, with
   Gemma 4 as another visual option. GLM 5.3 is text only and requires explicit
   selection and account access. Never infer image capability from coding scores.
3. In API mode, collect at most two distinct successful visual models. One model
   supplies a proposal; compatible independent readings may corroborate a value.
   A crop, retry or journal replay is not an additional independent reader.
   Textual recommendations never become visual votes or payment decisions.
4. Preserve strict response validation, document instruction isolation, candidate
   provenance, unreadability and conflict handling. Failed providers cannot weaken
   acceptance criteria or silently fill missing values from reference sources.
5. Keep content-addressed provider journals and bounded fallback. Preserve usage
   even when a billed response fails local validation. Do not blindly repeat an
   uncertain delivered request. Provider/model and effective mode participate in
   extraction identity; model credentials do not.
6. Expose the effective configuration without secrets and report network attempts,
   replays, failures, tokens, provider latency and the cost basis. Snapshot known
   tariffs when calls happen. Unknown billing remains unknown; a subscription's
   included marginal cost excludes its fixed fee and does not prove remaining quota.

## Consequences

An offline deployment can use the same contracts with local readers. An API-only
deployment avoids local model weights but may have more abstentions or different
latency. The default invoice evaluation does not acquire a dependency on Helmcode:
the fallback is available only when configured and used when necessary.

Provider settings from `.env` require a server restart. Per-request modes and
published process symbol/rule definitions take effect on the next request. These
are separate configuration mechanisms; this ADR does not promise hot reload of
environment variables or rewrite historical decisions.

**Update (2026-09-19).** Gemini's free quota ran out, so Helmcode became the primary
visual reader. The default chains are now `TRACEPAY_VISION_PROVIDERS=helmcode` (Qwen 3.6,
then Gemma 4) and `TRACEPAY_TEXT_PROVIDERS=jev,helmcode`; Gemini is retired and used only
when listed explicitly. The default profile is `experimental`: the historical `verified`
profile requires Gemini first and cannot certify this committee. A published version pins
one visual reader, one text judge and the mode at publication, with no deployment
fallback (`processes/execution.py`). Under it, process uploads use the pinned mode, the
two-model API corroboration does not apply, and `.env` changes take effect only after a
new version is published. The per-request mode override still applies to `/v1` requests.

The [operator guide](../../ingestion/providers-and-modes.md) documents model capability,
configuration examples, quota caveats, and monitoring. This extends the ingestion
evidence contract in ADR 0022 and retains the deterministic engine in ADR 0002.

**API default update (2026-09-19).** The server and example environment now default
to `TRACEPAY_OCR_MODE=api`, using the configured provider keys without loading local
OCR weights. Local and hybrid modes require explicit selection. Existing published
versions retain their pinned mode until a new version is validated and published.
