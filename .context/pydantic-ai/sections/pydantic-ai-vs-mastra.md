# [Pydantic AI vs Mastra](https://pydantic.dev/docs/ai/comparisons/vs-mastra/)

# Pydantic AI vs Mastra

Mastra is a TypeScript agent framework with step workflows, memory, processors, evals, a local playground and a hosted Studio. Pydantic AI is that stack in Python, composed from [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) rather than fixed constructs: a typed [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent), [memory](https://pydantic.dev/docs/ai/harness/memory/), [guardrails](https://pydantic.dev/docs/ai/harness/guardrails/), [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/) and a [web chat UI](https://pydantic.dev/docs/ai/guides/web/).

Pydantic AI is one part of a stack: the [Harness SDK](https://pydantic.dev/docs/ai/harness/) for capabilities and complete agents, [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/), [Pydantic Graph](https://pydantic.dev/docs/ai/graph/graph/), [Pydantic Logfire](https://pydantic.dev/logfire) for observability, and [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) itself for validation. The tables below cover the whole of it.

## Framework

Mastra

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Language

TypeScript

Python

License

Apache-2.0 (core); EE for some features

MIT

Model providers

Many

[Many](https://pydantic.dev/docs/ai/models/overview/)

Extensibility

Tools, processors, scorers, workflows

[Capabilities and toolsets](https://pydantic.dev/docs/ai/guides/extensibility/); [50+ with the Harness SDK](https://pydantic.dev/docs/ai/harness/)

Harnesses

Mastra Code, or your own

Built-in [`Coder`](https://pydantic.dev/docs/ai/harness/coder/) and [`Researcher`](https://pydantic.dev/docs/ai/harness/researcher/), or compose your own

Observability

OpenTelemetry

[OpenTelemetry](https://pydantic.dev/docs/ai/integrations/logfire/#using-opentelemetry), including [Pydantic Logfire](https://pydantic.dev/logfire)

Durable execution

Yes

[5+ integrations](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/)

Interfaces

Playground, Studio

[CLI](https://pydantic.dev/docs/ai/integrations/cli/), [web chat](https://pydantic.dev/docs/ai/guides/web/), [AG-UI](https://pydantic.dev/docs/ai/integrations/ui/ag-ui/), [Vercel AI](https://pydantic.dev/docs/ai/integrations/ui/vercel-ai/), [ACP](https://pydantic.dev/docs/ai/harness/acp/) (experimental)

Realtime voice

Yes

[Realtime](https://pydantic.dev/docs/ai/realtime/overview/)

Evals

Yes

[Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/)

Image generation

No

[Image Generation](https://pydantic.dev/docs/ai/guides/image-generation/)

## Features

Mastra

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

Token limit: truncate or abort

[Compaction](https://pydantic.dev/docs/ai/capabilities/compaction/)

Guardrails

Yes

[Guardrails](https://pydantic.dev/docs/ai/harness/guardrails/)

Code sandboxes

Yes

[Execution environments](https://pydantic.dev/docs/ai/harness/#execution-environments)

Browser use

Yes

[Web & research](https://pydantic.dev/docs/ai/harness/#web--research)

---
