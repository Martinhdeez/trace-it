---
status: accepted
---

# Build every agent on PydanticAI

## Context
The agents (compilers A and B and the escalation assistant) first called LLMs through our
own client over LiteLLM, with a model per role in an `llm_config` table. Each agent
validated structured output by hand and had its own repair loop; tests monkeypatched the
client; two concurrent agents sharing one database session needed an identity-map
workaround just to read their model name. We want the same things in every agent: typed
output, bounded retries that return the error to the model, cost per call and tests
without network. We must not depend on one provider, and control of the flow must stay in
our code: the instance and rule state machines, the manager's queue and idempotency live
in PostgreSQL.

## Alternatives considered
- **Raw LiteLLM (the first version).**
  - Pros: one interface for all providers; it worked.
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
- `pydantic-ai-slim[anthropic,google,openai]>=2`, pinned by `uv.lock`.
- One `Agent` per agent type (`compiler.tester`, `compiler.coder`, `compiler.reviewer`,
  `assistant.assistant`), created once with its instructions and `output_type`; the model
  is chosen per run from the role's setting (`TRACE_COMPILER_MODEL`, `TRACE_TESTER_MODEL`,
  `TRACE_ASSISTANT_MODEL`, `provider:model` names; `helmcode:<model>` is resolved to an
  OpenAI-compatible model in `llm.resolve`).
- `ModelRetry` only where the error helps the model fix itself, in output validators:
  tester (well-formed tests over known symbols) and coder (sandbox check), `retries=2`, assistant (decision must
  be a process type, `retries=1`). Never in extraction (ADR 0010).
- A single entry point (`agents/llm.run`) runs an agent for a role and returns the output
  with a trace (role, model that answered, requests, retries, tokens, cost, latency) that
  the caller records as an event. Every PydanticAI failure becomes one `AgentError` (502).
- Not used yet: `FallbackModel` chains, `UsageLimits`, graphs or deferred tools. Flow, state
  and approval are ours.

## Consequences
- `features/llm`, the `llm_config` table and `/llm/config` are gone; a model change is an
  environment variable and a restart. Versioned agent configuration stays proposed
  (ADR 0011).
- When the model fails or gives nothing valid within the retries, the agent fails closed:
  the rule stays a draft, the assistant answers 502, no decision changes.
- Tests never need a key: `tests/support/models.py` scripts a `FunctionModel` per role.

## Evidence
- `agents/llm.py`, `agents/compiler.py`, `agents/assistant.py`; 3 compiler tests and 5
  assistant tests on scripted models (`agents/tests/`), including one self-repair round and
  the 502 after the retries run out.
- Real-model runs are opt-in: `make eval-compiler` compiles the 16 invoice rules and
  compares them with the hand-written code (`backend/evals/`). Not run yet without keys.

## Related
ADR 0002, 0004, 0010, 0011. The earlier migration plan is archived in
`.artifacts/archive/agents-plan.md`.
