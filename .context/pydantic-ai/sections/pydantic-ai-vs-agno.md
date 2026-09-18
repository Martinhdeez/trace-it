# [Pydantic AI vs Agno](https://pydantic.dev/docs/ai/comparisons/vs-agno/)

# Pydantic AI vs Agno

Agno is a Python agent framework that optimizes for breadth: a very large tool catalogue, teams, step workflows, and AgentOS to run and watch them. Pydantic AI gives you that breadth on a typed core with strict Pydantic validation: [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) and the [Harness SDK](https://pydantic.dev/docs/ai/harness/) for the batteries, [sub-agents](https://pydantic.dev/docs/ai/harness/subagents/) for teams, [`pydantic-graph`](https://pydantic.dev/docs/ai/graph/graph/) for workflows, and [Pydantic Logfire](https://pydantic.dev/logfire) to run and watch them.

Pydantic AI is one part of a stack: the [Harness SDK](https://pydantic.dev/docs/ai/harness/) for capabilities and complete agents, [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/), [Pydantic Graph](https://pydantic.dev/docs/ai/graph/graph/), [Pydantic Logfire](https://pydantic.dev/logfire) for observability, and [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) itself for validation. The tables below cover the whole of it.

## Framework

Agno

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Language

Python

Python

License

Apache-2.0

MIT

Model providers

Many

[Many](https://pydantic.dev/docs/ai/models/overview/)

Extensibility

Tools, toolkits

[Capabilities and toolsets](https://pydantic.dev/docs/ai/guides/extensibility/); [50+ with the Harness SDK](https://pydantic.dev/docs/ai/harness/)

Harnesses

Build your own

Built-in [`Coder`](https://pydantic.dev/docs/ai/harness/coder/) and [`Researcher`](https://pydantic.dev/docs/ai/harness/researcher/), or compose your own

Observability

OpenTelemetry

[OpenTelemetry](https://pydantic.dev/docs/ai/integrations/logfire/#using-opentelemetry), including [Pydantic Logfire](https://pydantic.dev/logfire)

Durable execution

Yes

[5+ integrations](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/)

Interfaces

AG-UI, A2A, chat platforms

[CLI](https://pydantic.dev/docs/ai/integrations/cli/), [web chat](https://pydantic.dev/docs/ai/guides/web/), [AG-UI](https://pydantic.dev/docs/ai/integrations/ui/ag-ui/), [Vercel AI](https://pydantic.dev/docs/ai/integrations/ui/vercel-ai/), [ACP](https://pydantic.dev/docs/ai/harness/acp/) (experimental)

Realtime voice

No

[Realtime](https://pydantic.dev/docs/ai/realtime/overview/)

Evals

Yes

[Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/)

Image generation

Yes

[Image Generation](https://pydantic.dev/docs/ai/guides/image-generation/)

## Features

Agno

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Multi-agent

Yes

[Subagents](https://pydantic.dev/docs/ai/harness/subagents/), [delegation](https://pydantic.dev/docs/ai/guides/multi-agent-applications/), or [`pydantic-graph`](https://pydantic.dev/docs/ai/graph/graph/)

Planning

Teams only

[Planning](https://pydantic.dev/docs/ai/harness/planning/)

Skills

Yes

[Skills](https://pydantic.dev/docs/ai/harness/skills/)

Memory

Yes

[Memory](https://pydantic.dev/docs/ai/harness/memory/)

Compaction

History window, session summaries

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
