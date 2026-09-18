# [Pydantic AI vs LangChain & LangGraph](https://pydantic.dev/docs/ai/comparisons/vs-langchain-langgraph/)

# Pydantic AI vs LangChain & LangGraph

LangChain is a large Python ecosystem: LangGraph underneath it for graph-based control flow, `deepagents` for its coding harness, and a large catalogue of integrations. Pydantic AI does it from one typed [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent) with plain Python control flow: [`pydantic-graph`](https://pydantic.dev/docs/ai/graph/graph/) when you want an explicit graph, a [Harness SDK](https://pydantic.dev/docs/ai/harness/) of ready-made capabilities and complete agents, and validation from the library you already use.

Pydantic AI is one part of a stack: the [Harness SDK](https://pydantic.dev/docs/ai/harness/) for capabilities and complete agents, [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/), [Pydantic Graph](https://pydantic.dev/docs/ai/graph/graph/), [Pydantic Logfire](https://pydantic.dev/logfire) for observability, and [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) itself for validation. The tables below cover the whole of it.

## Framework

LangChain & LangGraph

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Language

Python

Python

License

MIT

MIT

Model providers

Many

[Many](https://pydantic.dev/docs/ai/models/overview/)

Extensibility

Middleware, callbacks

[Capabilities and toolsets](https://pydantic.dev/docs/ai/guides/extensibility/); [50+ with the Harness SDK](https://pydantic.dev/docs/ai/harness/)

Harnesses

`deepagents`, or your own on LangGraph

Built-in [`Coder`](https://pydantic.dev/docs/ai/harness/coder/) and [`Researcher`](https://pydantic.dev/docs/ai/harness/researcher/), or compose your own

Observability

OpenTelemetry via LangSmith

[OpenTelemetry](https://pydantic.dev/docs/ai/integrations/logfire/#using-opentelemetry), including [Pydantic Logfire](https://pydantic.dev/logfire)

Durable execution

Yes

[5+ integrations](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/)

Interfaces

LangSmith Agent Server, Fleet

[CLI](https://pydantic.dev/docs/ai/integrations/cli/), [web chat](https://pydantic.dev/docs/ai/guides/web/), [AG-UI](https://pydantic.dev/docs/ai/integrations/ui/ag-ui/), [Vercel AI](https://pydantic.dev/docs/ai/integrations/ui/vercel-ai/), [ACP](https://pydantic.dev/docs/ai/harness/acp/) (experimental)

Realtime voice

No

[Realtime](https://pydantic.dev/docs/ai/realtime/overview/)

Evals

Yes

[Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/)

Image generation

Provider-hosted tools only

[Image Generation](https://pydantic.dev/docs/ai/guides/image-generation/)

## Features

LangChain & LangGraph

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Multi-agent

Yes

[Subagents](https://pydantic.dev/docs/ai/harness/subagents/), [delegation](https://pydantic.dev/docs/ai/guides/multi-agent-applications/), or [`pydantic-graph`](https://pydantic.dev/docs/ai/graph/graph/)

Planning

Yes

[Planning](https://pydantic.dev/docs/ai/harness/planning/)

Skills

Yes

[Skills](https://pydantic.dev/docs/ai/harness/skills/)

Memory

Yes

[Memory](https://pydantic.dev/docs/ai/harness/memory/)

Compaction

Yes

[Compaction](https://pydantic.dev/docs/ai/capabilities/compaction/)

Guardrails

Yes

[Guardrails](https://pydantic.dev/docs/ai/harness/guardrails/)

Code sandboxes

Yes

[Execution environments](https://pydantic.dev/docs/ai/harness/#execution-environments)

Browser use

Provider-hosted tools only

[Web & research](https://pydantic.dev/docs/ai/harness/#web--research)

## FAQ

**Do you have a graph library?** Yes. [`pydantic-graph`](https://pydantic.dev/docs/ai/graph/graph/): typed nodes, edges from return types, and persistence for pausing and resuming. Reach for it when the control flow is a real state machine; plain Python and [sub-agents](https://pydantic.dev/docs/ai/harness/subagents/) cover the rest.

---
