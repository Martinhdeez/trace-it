# [Pydantic AI vs Google ADK](https://pydantic.dev/docs/ai/comparisons/vs-google-adk/)

# Pydantic AI vs Google ADK

Google's Agent Development Kit is an agent platform built around Gemini and Vertex AI: workflow graphs, evaluation, a dev UI, and deploy commands for Cloud Run, GKE, Docker and Agent Engine. Pydantic AI is a provider-agnostic library you run on your own infrastructure, with [`pydantic-graph`](https://pydantic.dev/docs/ai/graph/graph/) for workflows, [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/), a [web chat UI](https://pydantic.dev/docs/ai/guides/web/), and [Pydantic Logfire](https://pydantic.dev/logfire) to watch it all run.

Pydantic AI is one part of a stack: the [Harness SDK](https://pydantic.dev/docs/ai/harness/) for capabilities and complete agents, [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/), [Pydantic Graph](https://pydantic.dev/docs/ai/graph/graph/), [Pydantic Logfire](https://pydantic.dev/logfire) for observability, and [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) itself for validation. The tables below cover the whole of it.

## Framework

Google ADK

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Language

Python

Python

License

Apache-2.0

MIT

Model providers

Gemini first (`LiteLlm`, `AnthropicLlm` exist)

[Many](https://pydantic.dev/docs/ai/models/overview/)

Extensibility

Tools, plugins

[Capabilities and toolsets](https://pydantic.dev/docs/ai/guides/extensibility/); [50+ with the Harness SDK](https://pydantic.dev/docs/ai/harness/)

Harnesses

Build your own; shell, file tools, sandboxes and compaction ship

Built-in [`Coder`](https://pydantic.dev/docs/ai/harness/coder/) and [`Researcher`](https://pydantic.dev/docs/ai/harness/researcher/), or compose your own

Observability

OpenTelemetry

[OpenTelemetry](https://pydantic.dev/docs/ai/integrations/logfire/#using-opentelemetry), including [Pydantic Logfire](https://pydantic.dev/logfire)

Durable execution

Yes

[5+ integrations](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/)

Interfaces

CLI, web, A2A

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

Google ADK

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Multi-agent

Yes

[Subagents](https://pydantic.dev/docs/ai/harness/subagents/), [delegation](https://pydantic.dev/docs/ai/guides/multi-agent-applications/), or [`pydantic-graph`](https://pydantic.dev/docs/ai/graph/graph/)

Planning

Prompt-level only

[Planning](https://pydantic.dev/docs/ai/harness/planning/)

Skills

Yes (experimental)

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

Yes

[Web & research](https://pydantic.dev/docs/ai/harness/#web--research)

## FAQ

**Can I build a coding agent on Pydantic AI?** Yes. Give your agent the [`Coder()`](https://pydantic.dev/docs/ai/harness/coder/) capability, or assemble your own from the same [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent); the harness repository has a [complete coding agent](https://github.com/pydantic/pydantic-ai-harness/blob/main/examples/coding_agent.py) built from the pieces `Coder` puts together.

**Can I run my agents in CI?** Yes. [GitHub Agentic Workflows](https://pydantic.dev/docs/ai/harness/gh-aw/) runs Pydantic AI agents from a Markdown workflow file in GitHub Actions, or run a Python script directly with `uv run`; nothing requires an Action.

---
