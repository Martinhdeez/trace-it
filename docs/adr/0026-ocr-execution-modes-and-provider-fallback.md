---
status: proposed
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
motivate bounded failover. See the [benchmark](../ingestion/benchmark-2026-09-19.md).

## Decision

1. Add explicit `local`, `api` and `hybrid` execution modes. Hybrid remains the
   default and preserves the invoice path. A request can override the configured
   default. Local mode disables provider stages; API mode does not load or inspect
   local OCR weights. Every mode can use deterministic native PDF text.
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

The [operator guide](../ingestion/providers-and-modes.md) documents model capability,
configuration examples, quota caveats, and monitoring. This extends the ingestion
evidence contract in ADR 0022 and retains the deterministic engine in ADR 0002.
