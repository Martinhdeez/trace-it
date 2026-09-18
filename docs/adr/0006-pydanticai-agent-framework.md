---
status: accepted  # implementation in progress (docs/agents-plan.md §9, tasks 1-8)
---

# Build every agent on PydanticAI

## Context
The agents (compilers A and B, escalation assistant, symbol extractors, and later a
corrector) call LLMs through our own client over LiteLLM (`features/llm/cliente.py`).
Each agent validates structured output by hand and has its own repair loop; there is no
fallback when a provider fails (a 502); tests monkeypatch the client. We want the same
things in every agent: typed output, bounded retries that return the error to the model,
a model fallback chain, usage limits, cost per call and tests without network. We must not
depend on one provider (P22), and control of the flow must stay in our code: the instance
and rule state machines, the manager's queue and idempotency already live in PostgreSQL.

## Alternatives considered
- **Raw LiteLLM (current).**
  - Pros: one interface for all providers; already working.
  - Cons: validation, retry-with-error, fallback, limits and test doubles written per agent;
    we already had two different repair loops.
- **LangGraph.**
  - Pros: stateful graphs, persistence, human-in-the-loop.
  - Cons: duplicates the state we keep in PostgreSQL and moves flow control out of our code.
- **Claude Agent SDK / OpenAI Agents SDK.**
  - Pros: first-class support for their own models.
  - Cons: each is built around one provider; conflicts with P22 and with paired roles using
    different providers.
- **CrewAI.**
  - Pros: quick multi-agent setups with roles and tasks.
  - Cons: agents that coordinate themselves; ours never talk to each other and the LLM
    never decides (ADR 0002).
- **PydanticAI v2 (chosen).**
  - Pros: typed `output_type`; `output_validator` + `ModelRetry`; `FallbackModel`;
    `UsageLimits`; `result.usage.cost`; `FunctionModel`/`TestModel` and `agent.override`
    for tests; provider-agnostic `provider:model` names.
  - Cons: a fast-moving dependency; its comparison pages are written by Pydantic.

## Decision
- `pydantic-ai-slim[openai,anthropic,google]>=2.45,<3`, pinned by `uv.lock`.
- One `Agent` per agent type; model, settings, retries and prompt come from the active
  configuration version of its role (ADR 0011) on every call.
- `ModelRetry` only where the error helps the model fix itself: compiler (sandbox and its
  own tests), assistant (decision must be a process type). **Never in extraction**
  (ADR 0010).
- A single entry point (`llm.ejecutar`) runs agents and writes one trace event per run:
  config version, role, model that actually answered, prompt hash, tokens, cost, latency,
  retries, result.
- Not used: graphs, durable execution, deferred tools with human approval. Flow, state
  and approval are ours.

## Consequences
- `features/llm/client.py`, `llm_config` and `/llm/config` go away; the frontend moves to
  `/agents/.../config`. Model names change from `anthropic/x` to `anthropic:x`.
- If every model in a chain fails, the agent fails closed: rule stays draft, instance stays
  in REVIEW, never a decision.
- Behaviour marked "unconfirmed" in `docs/agents-plan.md` §11 (e.g. whether timeouts reach
  `FallbackModel` as `ModelAPIError`) must be checked by tests in task 2.

## Evidence
- APIs checked against the local PydanticAI v2 docs (`.context/pydantic-ai/`), references
  in `docs/agents-plan.md` §12.
- Cost and latency per stage will come from `GET /processes/{id}/metrics` over `events`
  (plan §7.4); not measured yet.

## Related
ADR 0002, 0004, 0010, 0011, 0013 (resilience). Plan P22, P23; `docs/agents-plan.md`.
