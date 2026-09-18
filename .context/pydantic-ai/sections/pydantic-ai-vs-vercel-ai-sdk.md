# [Pydantic AI vs Vercel AI SDK](https://pydantic.dev/docs/ai/comparisons/vs-vercel-ai-sdk/)

# Pydantic AI vs Vercel AI SDK

The Vercel AI SDK adds model calls, tool loops and streaming chat to a TypeScript app, with `useChat` hooks and a broad provider registry; [Eve](https://eve.dev/), a separate Apache-2.0 package, adds an agent harness on top. Pydantic AI is the Python back end for that UI: a typed [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent), the [Harness SDK](https://pydantic.dev/docs/ai/harness/), and a [Vercel AI stream adapter](https://pydantic.dev/docs/ai/integrations/ui/vercel-ai/) so `useChat` renders our agents.

Pydantic AI is one part of a stack: the [Harness SDK](https://pydantic.dev/docs/ai/harness/) for capabilities and complete agents, [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/), [Pydantic Graph](https://pydantic.dev/docs/ai/graph/graph/), [Pydantic Logfire](https://pydantic.dev/logfire) for observability, and [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) itself for validation. The tables below cover the whole of it.

## Framework

Vercel AI SDK

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Language

TypeScript

Python

License

Apache-2.0

MIT

Model providers

Many

[Many](https://pydantic.dev/docs/ai/models/overview/)

Extensibility

Middleware, tools

[Capabilities and toolsets](https://pydantic.dev/docs/ai/guides/extensibility/); [50+ with the Harness SDK](https://pydantic.dev/docs/ai/harness/)

Harnesses

[Eve](https://eve.dev/), a separate package; adapters drive external harnesses

Built-in [`Coder`](https://pydantic.dev/docs/ai/harness/coder/) and [`Researcher`](https://pydantic.dev/docs/ai/harness/researcher/), or compose your own

Observability

OpenTelemetry

[OpenTelemetry](https://pydantic.dev/docs/ai/integrations/logfire/#using-opentelemetry), including [Pydantic Logfire](https://pydantic.dev/logfire)

Durable execution

Yes

[5+ integrations](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/)

Interfaces

React chat UI, stream protocol

[CLI](https://pydantic.dev/docs/ai/integrations/cli/), [web chat](https://pydantic.dev/docs/ai/guides/web/), [AG-UI](https://pydantic.dev/docs/ai/integrations/ui/ag-ui/), [Vercel AI](https://pydantic.dev/docs/ai/integrations/ui/vercel-ai/), [ACP](https://pydantic.dev/docs/ai/harness/acp/) (experimental)

Realtime voice

Yes (experimental)

[Realtime](https://pydantic.dev/docs/ai/realtime/overview/)

Evals

No

[Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/)

Image generation

Yes

[Image Generation](https://pydantic.dev/docs/ai/guides/image-generation/)

## Features

Vercel AI SDK

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Multi-agent

Yes (Eve)

[Subagents](https://pydantic.dev/docs/ai/harness/subagents/), [delegation](https://pydantic.dev/docs/ai/guides/multi-agent-applications/), or [`pydantic-graph`](https://pydantic.dev/docs/ai/graph/graph/)

Planning

Yes (Eve)

[Planning](https://pydantic.dev/docs/ai/harness/planning/)

Skills

Yes (Eve); provider-hosted in the SDK

[Skills](https://pydantic.dev/docs/ai/harness/skills/)

Memory

No

[Memory](https://pydantic.dev/docs/ai/harness/memory/)

Compaction

Yes (Eve); `pruneMessages` in the SDK

[Compaction](https://pydantic.dev/docs/ai/capabilities/compaction/)

Guardrails

Yes

[Guardrails](https://pydantic.dev/docs/ai/harness/guardrails/)

Code sandboxes

Yes (experimental)

[Execution environments](https://pydantic.dev/docs/ai/harness/#execution-environments)

Browser use

No

[Web & research](https://pydantic.dev/docs/ai/harness/#web--research)

---
