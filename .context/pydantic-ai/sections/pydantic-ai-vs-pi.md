# [Pydantic AI vs Pi](https://pydantic.dev/docs/ai/comparisons/vs-pi/)

# Pydantic AI vs Pi

Pi is a TypeScript coding agent from Earendil Works: a terminal agent you extend with hooks, skills and packages, or embed through `createAgentSession`. In Pydantic AI, a [coding agent](https://pydantic.dev/docs/ai/harness/coder/) is one [configuration](https://pydantic.dev/docs/ai/capabilities/overview/) of a general [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent), and the [skills](https://pydantic.dev/docs/ai/harness/skills/), [sandbox](https://pydantic.dev/docs/ai/harness/#execution-environments) and [sub-agents](https://pydantic.dev/docs/ai/harness/subagents/) are each a capability you can swap.

Pydantic AI is one part of a stack: the [Harness SDK](https://pydantic.dev/docs/ai/harness/) for capabilities and complete agents, [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/), [Pydantic Graph](https://pydantic.dev/docs/ai/graph/graph/), [Pydantic Logfire](https://pydantic.dev/logfire) for observability, and [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) itself for validation. The tables below cover the whole of it.

## Framework

Pi

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Language

TypeScript

Python

License

MIT

MIT

Model providers

Many

[Many](https://pydantic.dev/docs/ai/models/overview/)

Extensibility

Extensions, skills, `pi install`

[Capabilities and toolsets](https://pydantic.dev/docs/ai/guides/extensibility/); [50+ with the Harness SDK](https://pydantic.dev/docs/ai/harness/)

Harnesses

Pi itself; extend it or embed it

Built-in [`Coder`](https://pydantic.dev/docs/ai/harness/coder/) and [`Researcher`](https://pydantic.dev/docs/ai/harness/researcher/), or compose your own

Observability

Telemetry contract, no exporter

[OpenTelemetry](https://pydantic.dev/docs/ai/integrations/logfire/#using-opentelemetry), including [Pydantic Logfire](https://pydantic.dev/logfire)

Durable execution

No

[5+ integrations](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/)

Interfaces

CLI

[CLI](https://pydantic.dev/docs/ai/integrations/cli/), [web chat](https://pydantic.dev/docs/ai/guides/web/), [AG-UI](https://pydantic.dev/docs/ai/integrations/ui/ag-ui/), [Vercel AI](https://pydantic.dev/docs/ai/integrations/ui/vercel-ai/), [ACP](https://pydantic.dev/docs/ai/harness/acp/) (experimental)

Realtime voice

No

[Realtime](https://pydantic.dev/docs/ai/realtime/overview/)

Evals

No

[Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/)

Image generation

No

[Image Generation](https://pydantic.dev/docs/ai/guides/image-generation/)

## Features

Pi

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Multi-agent

No

[Subagents](https://pydantic.dev/docs/ai/harness/subagents/), [delegation](https://pydantic.dev/docs/ai/guides/multi-agent-applications/), or [`pydantic-graph`](https://pydantic.dev/docs/ai/graph/graph/)

Planning

No

[Planning](https://pydantic.dev/docs/ai/harness/planning/)

Skills

Yes

[Skills](https://pydantic.dev/docs/ai/harness/skills/)

Memory

No

[Memory](https://pydantic.dev/docs/ai/harness/memory/)

Compaction

Yes

[Compaction](https://pydantic.dev/docs/ai/capabilities/compaction/)

Guardrails

Yes (`tool_call` hook)

[Guardrails](https://pydantic.dev/docs/ai/harness/guardrails/)

Code sandboxes

No

[Execution environments](https://pydantic.dev/docs/ai/harness/#execution-environments)

Browser use

No

[Web & research](https://pydantic.dev/docs/ai/harness/#web--research)

## FAQ

**Can I build a coding agent like this in Python?** Yes. Give your agent the [`Coder()`](https://pydantic.dev/docs/ai/harness/coder/) capability, or start from the harness repository's [complete coding agent](https://github.com/pydantic/pydantic-ai-harness/blob/main/examples/coding_agent.py), built from the pieces `Coder` puts together.

---
