---
status: accepted
---

# Move to the next model of a per-role chain when a provider fails

## Context
Every agent (normalizer, tester, compiler, assistant) runs on one model per use case and
role (ADR 0011). When that provider fails (5xx, 429 after the SDK's own retries, a timeout,
a refused connection) the run fails closed: the rule is `blocked` with the error (ADR 0020), the
assistant answers 502 (ADR 0006). Nothing wrong is decided, but a norm that arrives during
an outage is not compiled until someone retries. The jury scores resilience and wants to
see a provider failure handled. The Helmcode key serves several flat-rate models
(`deepseek-v4-flash`, `glm5.3`, `glm5.3-flash`, `qwen3.6`, `gemma4`); paid models answer
"prepaid credit".

## Alternatives considered
- **Retry the same model only.**
  - Pros: nothing new; the OpenAI SDK already retries 429 and 5xx twice.
  - Cons: a provider that is down stays down for every retry; a rate limit is extended by
    hammering it.
- **Fallback chain per use case and role (chosen).**
  - Pros: PydanticAI's `FallbackModel` does it; a list in the existing `AgentSettings`, so
    it is versioned and changed at runtime like the model; no new state.
  - Cons: the fallback may be a weaker model: its output still passes the same validators,
    tests and impact check before anything becomes active.
- **Queue the run and resume when the provider is back.**
  - Pros: always the preferred model.
  - Cons: a job queue, persistence and a resume path for a weekend MVP; the manager waits.

## Decision
- `AgentSettings` gets `fallback_models: list[str]` (same `provider:model` / `helmcode:`
  strings, resolved by `llm.resolve`) and `timeout_seconds` (per request to the provider,
  passed as the model setting `timeout`).
- `llm.run` always runs a `FallbackModel` of the role's model followed by its fallbacks.
  A `ModelAPIError` (HTTP 4xx/5xx, connection, timeout) or an answer cut by the
  output-token limit (`finish_reason == "length"`, a response handler of `fallback_on`)
  moves to the next model. An answer a validator rejects (`ModelRetry`) is retried on the
  same chain from the first model, never counted as a failure.
- The `llm_run` span records `chain`, `failed_attempts` (`[{model, error}]`, every
  provider failure of the run, including those before a model answered) and `model`, the
  one that answered.
- All models fail: `AgentError` 502 "every model failed: m1: ...; m2: ...", and the
  existing fail-closed path applies (the rule ends `blocked` with that error and every
  instance escalates with `RULE_COMPILE_FAILED`, ADR 0020; `draft` before 2026-09-19).
- Invoice use case: every role starts on `deepseek-v4-flash`; compiler and normalizer fall
  back to `glm5.3` then `qwen3.6`, the tester to `qwen3.6` then `glm5.3` (a different
  family from the compiler's first fallback, ADR 0004). Timeouts: 180 s compiler and
  tester, 300 s normalizer (it writes the whole norm), 120 s assistant. The assistant runs
  the compiler's chain. `max_tokens` per role, about twice the largest output measured
  (docs/scale-and-cost.md): normalizer and tester 8000, compiler 6000, assistant 4000.

## Consequences
- The OpenAI SDK retries twice before an error reaches the chain, so a hung provider costs
  up to three timeouts before the fallback; a refused connection falls back in seconds.
- Every request of a run starts at the first model again: while the primary is down, each
  request records one failed attempt. Accepted: it recovers by itself when the primary
  returns.
- A database loaded before this change gets the new invoice settings as an inactive
  version (ADR 0011): a manager activates it.
- A cut answer used to raise `UnexpectedModelBehavior` after the model generated up to the
  provider's own limit (85 s once, docs/scale-and-cost.md) and the chain never switched.
  Now `max_tokens` stops it sooner and the next model answers; the cut attempt is in
  `failed_attempts` as "output token limit hit". Every response ending `length` is
  rejected, even a non-empty one: a structured answer cut short is not usable.

## Evidence
- Tests (`agents/tests/test_llm.py`, scripted `FunctionModel`s): primary 503 -> the fallback
  answers and the span shows both; a `ModelRetry` stays on the primary; every model
  failing is a 502 naming both; a primary answer ending `length` -> the fallback answers;
  through the API, a rule whose chain all fails ends `blocked` with that error.
- The assistant on the invoice use case's settings answered one real suggestion through
  Helmcode: `deepseek-v4-flash`, 6.3 s, 2.2k / 0.8k tokens, 1 validator retry.
- Each fallback model answered a structured output through Helmcode (one call each):
  `deepseek-v4-flash` 2.1 s, `gemma4` 2.6 s, `qwen3.6` 2.8 s, `glm5.3` 7.8 s,
  `glm5.3-flash` 7.9 s.
- `make demo-llm-down` (primary sent to `http://127.0.0.1:9/v1`):
  ```
  chain: ["deepseek-v4-flash", "glm5.3", "qwen3.6"]
  failed_attempts: [{"model": "deepseek-v4-flash", "error": "ModelAPIError: Connection error."}]
  model: "glm5.3"
  ```

## Related
ADR 0004, 0006 (fallback chains were listed as not used yet), 0011, 0013 (the ERP side of
resilience), 0018.
