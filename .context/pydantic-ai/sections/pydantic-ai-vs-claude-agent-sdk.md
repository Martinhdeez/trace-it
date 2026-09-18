# [Pydantic AI vs Claude Agent SDK](https://pydantic.dev/docs/ai/comparisons/vs-claude-agent-sdk/)

# Pydantic AI vs Claude Agent SDK

The Claude Agent SDK gives you the agent loop behind Claude Code: a Python package that drives the bundled `claude` CLI, with Anthropic's built-in tools, permissions and sub-agents already wired up. Pydantic AI gives you the loop itself: a typed [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent) on [any model](https://pydantic.dev/docs/ai/models/overview/), and [`Coder`](https://pydantic.dev/docs/ai/harness/coder/) as a complete coding agent built from [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) you can swap, extend or leave out.

Pydantic AI is one part of a stack: the [Harness SDK](https://pydantic.dev/docs/ai/harness/) for capabilities and complete agents, [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/), [Pydantic Graph](https://pydantic.dev/docs/ai/graph/graph/), [Pydantic Logfire](https://pydantic.dev/logfire) for observability, and [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) itself for validation. The tables below cover the whole of it.

## Framework

Claude Agent SDK

Pydantic AI and [Harness SDK](https://pydantic.dev/docs/ai/harness/)

Language

Python SDK wrapping the TypeScript `claude` CLI

Python

License

MIT

MIT

Model providers

Claude (Anthropic, Bedrock, Vertex, Foundry)

[Many](https://pydantic.dev/docs/ai/models/overview/)

Extensibility

Hooks, `allowed_tools`

[Capabilities and toolsets](https://pydantic.dev/docs/ai/guides/extensibility/); [50+ with the Harness SDK](https://pydantic.dev/docs/ai/harness/)

Harnesses

Claude Code's; hooks extend it, you cannot recompose it

Built-in [`Coder`](https://pydantic.dev/docs/ai/harness/coder/) and [`Researcher`](https://pydantic.dev/docs/ai/harness/researcher/), or compose your own

Observability

OpenTelemetry from the CLI

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

Claude Agent SDK

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

No

[Web & research](https://pydantic.dev/docs/ai/harness/#web--research)

## FAQ

**Can I build my own coding agent harness?** Yes. Give your agent the [`Coder()`](https://pydantic.dev/docs/ai/harness/coder/) capability, or assemble your own from the same [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent); the harness repository has a [complete coding agent](https://github.com/pydantic/pydantic-ai-harness/blob/main/examples/coding_agent.py) built from the pieces `Coder` puts together.

**Can I run my agents in CI?** Yes. [GitHub Agentic Workflows](https://pydantic.dev/docs/ai/harness/gh-aw/) runs Pydantic AI agents from a Markdown workflow file in GitHub Actions, or run a Python script directly with `uv run`; nothing requires an Action.

---
