# [Pydantic AI Harness](https://pydantic.dev/docs/ai/harness/)

> Your agent's favorite harness, built on Pydantic AI: 30+ capabilities and complete agents assembled from them, from a coding agent to your own custom stack.

# Pydantic AI Harness

_Your agent's favorite harness, built on Pydantic AI_

[![Join Slack](https://img.shields.io/badge/Slack-Join%20Slack-4A154B?logo=slack)](https://logfire.pydantic.dev/docs/join-slack/)

**Pydantic AI Harness** is the official [capability](https://pydantic.dev/docs/ai/capabilities/overview/) and harness library for [Pydantic AI](https://pydantic.dev/docs/ai/). Every Pydantic AI agent already has a light harness: the typed agent loop, [any model](https://pydantic.dev/docs/ai/models/overview/), your own tools, structured output. For simple agents that's enough. But set an agent loose on complex, long-running work (fix a codebase, research a question, run for hours unattended) and what it needs around the model grows: a [workspace](https://pydantic.dev/docs/ai/harness/filesystem/) to act in, a [plan](https://pydantic.dev/docs/ai/harness/planning/) it keeps current, [memory](https://pydantic.dev/docs/ai/harness/memory/) that carries across sessions, [sub-agents](https://pydantic.dev/docs/ai/harness/subagents/) to hand work to, [context management](https://pydantic.dev/docs/ai/harness/compaction/) that holds up in hour ten, and [durable execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/) that survives a restart. **Pydantic AI Harness** ships that harness.

Everything here is one primitive: a [capability](https://pydantic.dev/docs/ai/capabilities/overview/), a self-contained unit of agent behavior you add to `capabilities=[...]` on any agent. There are [30+ of them](#capabilities), and complete agents like [Coder](https://pydantic.dev/docs/ai/harness/coder/) and [Researcher](https://pydantic.dev/docs/ai/harness/researcher/) are themselves capabilities combined: they come apart the way they went together. Snap on a single block, compose your own stack, or start from the whole coding agent and take it apart later.

## Quick start

Install with [`uv`](https://docs.astral.sh/uv/):

-   [pip](#tab-panel-126)
-   [uv](#tab-panel-127)

Terminal

```bash
pip install "pydantic-ai-harness[anthropic]"
```

Terminal

```bash
uv add "pydantic-ai-harness[anthropic]"
```

```python
from pydantic_ai import Agent
from pydantic_ai_harness import Coder

agent = Agent('anthropic:claude-fable-5', capabilities=[Coder()])

result = agent.run_sync('Find out why tests/test_parser.py fails and fix the bug it caught.')
print(result.output)
#> Found it: `parse()` returned None on empty input instead of raising. Fixed in src/parser.py; tests pass now.
```

Coder provides six tools: `read_file`, `write_file`, `edit_file`, `list_files`, `grep`, and `shell`, plus repository context and context controls. Shell commands are unrestricted and can persist beyond individual runs. Default instructions guide autonomous investigation, editing, and verification; pass `instructions=` to add your own guidance.

Terminal

```bash
uvx --with "pydantic-ai-harness[coder]" clai -a pydantic_ai_harness.coder:coder_agent -m anthropic:claude-fable-5
```

Every model works: swap the string for [any provider's](https://pydantic.dev/docs/ai/models/overview/). Need more? Add capabilities to the list; here's the same coder on `gpt-5.6-sol`, with web search and cross-session memory:

-   [pip](#tab-panel-128)
-   [uv](#tab-panel-129)

Terminal

```bash
pip install "pydantic-ai-slim[openai]"
```

Terminal

```bash
uv add "pydantic-ai-slim[openai]"
```

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import WebSearch
from pydantic_ai_harness import Coder, Memory
from pydantic_ai_harness.memory import FileStore

agent = Agent(
    'openai:gpt-5.6-sol',
    capabilities=[
        Coder(),
        WebSearch(),  # look up docs and error messages on the web
        Memory(FileStore('.agent-memory')),  # remembers across sessions
    ],
)
```

[Skills](https://pydantic.dev/docs/ai/harness/skills/) (your `SKILL.md` procedures, loaded on demand; point it at a `skills/` directory and add the `skills` extra), [Web Fetch](https://pydantic.dev/docs/ai/capabilities/web-fetch/), [Guardrails](https://pydantic.dev/docs/ai/harness/guardrails/), and [Dynamic Workflow](https://pydantic.dev/docs/ai/harness/dynamic-workflow/) slot in the same way; the [Coder page](https://pydantic.dev/docs/ai/harness/coder/#not-included-by-default) lists what pairs well.

## No magic: it's capabilities all the way down

`Coder` is a regular combined capability with six coding tools, autonomous engineering guidance, repository context, and context limits. Its private tools and JSON repair ship together; standalone capabilities remain independently available.

```python
from pydantic_ai import Agent
from pydantic_ai_harness.coder import Coder

agent = Agent(
    'anthropic:claude-fable-5',
    name='coder',
    capabilities=[Coder('.')],
)
```

See the Coder documentation for tool signatures, persistent shell lifecycle, and migration from the previous planning/delegation composition.

## Capabilities

Every capability is a self-contained unit you drop into `capabilities=[...]`, and they all compose, with each other and with your own. Some come with [`pydantic-ai`](https://pydantic.dev/docs/ai/) itself, the rest with this package; the **Package** column says which. 50+ in all, grouped by what they give your agent:

### Harnesses

Complete agent stacks as regular combined capabilities: one import gives you a working agent, and you can take either apart into the blocks below.

Harness

Package

What it provides

[Coder](https://pydantic.dev/docs/ai/harness/coder/)

Harness

Six coding tools, persistent shell commands, autonomous guidance, and context controls

[Researcher](https://pydantic.dev/docs/ai/harness/researcher/)

Harness

A complete web-research stack: search, page fetching, a delegated sub-researcher, and bounded tool output

### Execution environments

The workspace the agent acts in: the files it edits and the commands it runs, local or isolated.

Capability

Package

What it does

[FileSystem](https://pydantic.dev/docs/ai/harness/filesystem/)

Harness

Read, write, edit, search files under a root; path-traversal and symlink safe, secrets read-only

[Shell](https://pydantic.dev/docs/ai/harness/shell/)

Harness

Command execution with allowlists, denylists, timeouts, and credential-stripping

[Modal Sandbox](https://pydantic.dev/docs/ai/harness/modal-sandbox/)

Harness

Commands and files in an isolated [Modal](https://modal.com/) cloud sandbox

### Tools & native abilities

Connections to systems outside the agent's workspace, and abilities the provider executes natively.

Capability

Package

What it does

[MCP](https://pydantic.dev/docs/ai/capabilities/mcp/)

Core

Connect any MCP server's tools; local by default, provider-native connectors opt-in

[Image Generation](https://pydantic.dev/docs/ai/capabilities/image-generation/)

Core

Generate and edit images; provider-native where supported, sub-agent fallback elsewhere

[StackOne](https://pydantic.dev/docs/ai/harness/stackone/)

Harness

Act on linked SaaS accounts (HRIS, ATS, CRM, ...) via [StackOne](https://www.stackone.com/)

[LocalStack](https://pydantic.dev/docs/ai/harness/localstack/)

Harness

An emulated AWS environment with AWS CLI tools

[Macroscope](https://pydantic.dev/docs/ai/harness/macroscope/)

Harness

Run a local [Macroscope](https://docs.macroscope.com/cli) code review and hand the findings to the agent

### Web & research

Finding and reading things on the open web.

Capability

Package

What it does

[Web Search](https://pydantic.dev/docs/ai/capabilities/web-search/)

Core

Provider-native search where available, local DuckDuckGo fallback everywhere

[Web Fetch](https://pydantic.dev/docs/ai/capabilities/web-fetch/)

Core

Fetch and read URLs, native or local

[X Search](https://pydantic.dev/docs/ai/capabilities/x-search/)

Core

Search X; native on xAI, subagent fallback elsewhere

[Exa Search](https://pydantic.dev/docs/ai/harness/exa-search/)

Harness

Web research via [Exa](https://exa.ai/): excerpted search, full-page reads, opt-in cited deep search

[Exa Agent](https://pydantic.dev/docs/ai/harness/exa-search/)

Harness

Delegate open-ended research to the Exa Agent API

[You.com Search](https://pydantic.dev/docs/ai/harness/youdotcom/)

Harness

Web search and page reads via [You.com](https://you.com/): query-relevant excerpts or full-page markdown

[You.com Research](https://pydantic.dev/docs/ai/harness/youdotcom/)

Harness

Cited answers and multi-step research via the You.com Answer, Research, and Finance Research APIs

[Browser Use](https://pydantic.dev/docs/ai/harness/browser-use/)

Harness

Hand web tasks to an autonomous [browser-use](https://github.com/browser-use/browser-use) agent driving a real browser

[Playwright Browser](https://pydantic.dev/docs/ai/harness/playwright/)

Harness

Drive a real Chromium page yourself: navigate, click, type, read, and inspect what the page did

### Reasoning, planning & delegation

How the agent thinks and divides the work.

Capability

Package

What it does

[Thinking](https://pydantic.dev/docs/ai/capabilities/thinking/)

Core

Provider-adaptive extended thinking at configurable effort

[Planning](https://pydantic.dev/docs/ai/harness/planning/)

Harness

Model-owned task plans with a cache-safe live reminder

[Subagents](https://pydantic.dev/docs/ai/harness/subagents/)

Harness

Delegate self-contained tasks to named child agents

[Dynamic Workflow](https://pydantic.dev/docs/ai/harness/dynamic-workflow/)

Harness

The model orchestrates sub-agents from one Python script: fan-out, chain, vote in a single tool call, with hard `max_agent_calls` budgets

[Advisor](https://pydantic.dev/docs/ai/harness/advisor/)

Harness

Let an executor consult a stronger model mid-run

### Context management

How the agent spends its context window: the difference between an agent that degrades over a long run and one that doesn't, and between paying for tokens N times or once.

Capability

Package

What it does

[Code Mode](https://pydantic.dev/docs/ai/harness/code-mode/)

Harness

The model writes one Python script that calls many tools inside a [Monty](https://github.com/pydantic/monty) sandbox: one round-trip instead of N, and intermediate results never enter the context window. The answer to tool-call token bloat

[Tool Search](https://pydantic.dev/docs/ai/capabilities/tool-search/)

Core

Load tool definitions on demand instead of carrying hundreds in every prompt

[Compaction](https://pydantic.dev/docs/ai/capabilities/compaction/)

Core

Provider-native compaction on OpenAI and Anthropic; the provider summarizes history server-side

[Compaction](https://pydantic.dev/docs/ai/harness/compaction/)

Harness

Model-agnostic strategies: tool-result clearing, sliding-window trimming, LLM summarization, tiered; all window-relative, with live usage reporting

[Tool Output Limits](https://pydantic.dev/docs/ai/harness/tool-output-limits/)

Harness

Truncate, spill to a queryable file, or summarize oversized tool returns at the source

[Warn On Cache Busts](https://pydantic.dev/docs/ai/harness/warn-on-cache-busts/)

Harness

Detect prompt-cache prefix collapses between requests, from the provider's own numbers

### Knowledge & memory

What the agent knows and remembers, loaded when relevant instead of carried in every prompt.

Capability

Package

What it does

[Memory](https://pydantic.dev/docs/ai/harness/memory/)

Harness

A persistent, namespaced notebook: bounded prompt injection, on-demand search; in-memory/file/Postgres stores

[Conversation Search](https://pydantic.dev/docs/ai/harness/conversation-search/)

Harness

BM25 search over stored history, including turns compaction dropped

[Skills](https://pydantic.dev/docs/ai/harness/skills/)

Harness

Load [Agent Skill](https://pydantic.dev/docs/ai/capabilities/on-demand/) (`SKILL.md`) instructions on demand

[Repo Context](https://pydantic.dev/docs/ai/harness/repo-context/)

Harness

Start runs oriented: `AGENTS.md`/`CLAUDE.md` + repository structure

[Pydantic AI Docs](https://pydantic.dev/docs/ai/harness/pydantic-ai-docs/)

Harness

On-demand Pydantic AI documentation lookup

### Control & safety

Bounding what the agent may do, and keeping it on-instructions.

Capability

Package

What it does

[Guardrails](https://pydantic.dev/docs/ai/harness/guardrails/)

Harness

Validate/block/redact user input, tool calls, tool results, and output, including secret masking and parallel async guards

[Prompt Injection Defender](https://pydantic.dev/docs/ai/harness/prompt-injection-defender/)

Harness

Classify local tool results for indirect prompt injection and optionally withhold high-risk results

[Spend Limits](https://pydantic.dev/docs/ai/harness/spend/)

Harness

Cross-window USD/token budgets and per-response cost tracking, per model and per tenant

[Tool approval](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval)

Core

Flag tool calls that need human approval before they run

[Handle Deferred Tool Calls](https://pydantic.dev/docs/ai/capabilities/handle-deferred-tool-calls/)

Core

Resolve approval-deferred tool calls programmatically

[System Reminders](https://pydantic.dev/docs/ai/harness/system-reminders/)

Harness

Cache-safe re-injection of guidance mid-run to counter instruction fade

[Trajectory Judge](https://pydantic.dev/docs/ai/harness/trajectory-judge/)

Harness

A second model reviews the live run every N requests over a sliding token window and steers it mid-run

### Self-extension

Capability

Package

What it does

[Capability Creation](https://pydantic.dev/docs/ai/harness/capability-creation/)

Harness

The agent writes, validates, and persists _new capabilities_ during a run, loaded on the next run: self-extension with typed, inspectable units instead of arbitrary code

### Execution runtime

Outside the loop: how runs persist, survive failures, and get observed and configured in production.

Capability

Package

What it does

[Durable execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/)

Core

Runs that survive restarts and failures on [Temporal](https://pydantic.dev/docs/ai/capabilities/durable_execution/temporal/), [DBOS](https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/), or [Prefect](https://pydantic.dev/docs/ai/capabilities/durable_execution/prefect/), with [Restate](https://pydantic.dev/docs/ai/capabilities/durable_execution/restate/), [Kitaru](https://pydantic.dev/docs/ai/capabilities/durable_execution/kitaru/), and [Airflow](https://pydantic.dev/docs/ai/capabilities/durable_execution/airflow/) integrations

[AWS Lambda durability](https://pydantic.dev/docs/ai/harness/aws-lambda/)

Harness

Checkpoint model requests and tool calls into AWS Lambda durable function steps

[Step Persistence](https://pydantic.dev/docs/ai/harness/step-persistence/)

Harness

Save, restore, resume (`continue_run`), and fork (`fork_run`) runs; file/SQLite/Mongo backends

[Instrumentation](https://pydantic.dev/docs/ai/capabilities/instrumentation/)

Core

OpenTelemetry GenAI spans for every model and tool call; the raw material for [Logfire](https://pydantic.dev/logfire) traces

[Managed Prompt](https://pydantic.dev/docs/ai/harness/managed-prompt/)

Harness

Back instructions with a [Logfire](https://pydantic.dev/logfire)\-managed prompt; version and roll out without redeploying

[Thread Executor](https://pydantic.dev/docs/ai/capabilities/thread-executor/)

Core

Run sync tools on a shared thread pool

Core also ships loop-customization capabilities for production servers: [Select Model](https://pydantic.dev/docs/ai/capabilities/select-model/), [Resolve Model ID](https://pydantic.dev/docs/ai/capabilities/resolve-model-id/), [Prepare Tools / Prepare Output Tools](https://pydantic.dev/docs/ai/capabilities/prepare-tools/), [Prefix Tools](https://pydantic.dev/docs/ai/capabilities/prefix-tools/), [Set Tool Metadata](https://pydantic.dev/docs/ai/capabilities/set-tool-metadata/), [Include Tool Return Schemas](https://pydantic.dev/docs/ai/capabilities/include-tool-return-schemas/), [Process History](https://pydantic.dev/docs/ai/capabilities/process-history/), [Process Event Stream](https://pydantic.dev/docs/ai/capabilities/process-event-stream/), [Reinject System Prompt](https://pydantic.dev/docs/ai/capabilities/reinject-system-prompt/), and [Raise Content Filter Error](https://pydantic.dev/docs/ai/capabilities/raise-content-filter-error/).

And the agent plugs into any interface: [ACP](https://pydantic.dev/docs/ai/harness/acp/) _(experimental, Harness)_ serves it to editors like Zed over the [Agent Client Protocol](https://agentclientprotocol.com/), and core ships the [web chat UI](https://pydantic.dev/docs/ai/guides/web/), [CLI](https://pydantic.dev/docs/ai/integrations/cli/), [frontend adapters](https://pydantic.dev/docs/ai/integrations/ui/overview/) (AG-UI, Vercel AI), and [realtime voice](https://pydantic.dev/docs/ai/realtime/overview/).

Community packages extend the same capability system further; see [third-party capabilities](https://pydantic.dev/docs/ai/capabilities/third-party/).

## When do you need the Harness?

"Harness" is the field's term for everything around the model that turns it into an agent: the loop, the tools, the context management. Reach for this package when your agent should _do_ more than core's lean harness covers: touch files, run code, browse, remember, delegate, or stay coherent through hours-long runs. The boundary between the packages is mechanical, not a maturity tier: core ships the capabilities that require model or framework support (provider-native tools like [image generation](https://pydantic.dev/docs/ai/capabilities/image-generation/), provider APIs like [compaction](https://pydantic.dev/docs/ai/capabilities/compaction/), deep loop integration like [tool search](https://pydantic.dev/docs/ai/capabilities/tool-search/), and fundamentals like [thinking](https://pydantic.dev/docs/ai/capabilities/thinking/), [MCP](https://pydantic.dev/docs/ai/capabilities/mcp/), and [web search](https://pydantic.dev/docs/ai/capabilities/web-search/)) and the Harness ships everything else, as a separate package so capabilities can iterate at the speed the field moves while Pydantic AI itself stays lean.

## Installation

-   [pip](#tab-panel-130)
-   [uv](#tab-panel-131)

Terminal

```bash
pip install pydantic-ai-harness
```

Terminal

```bash
uv add pydantic-ai-harness
```

This installs [`pydantic-ai-slim`](https://pydantic.dev/docs/ai/overview/install/) with it, so it works on its own; you don't need to install Pydantic AI separately. Model providers and the CLI come via extras that pass through to Pydantic AI: `pydantic-ai-harness[anthropic]`, `[cli]`. Some capabilities need their own extra for optional dependencies; each capability's page gives its exact install line. Requires Python 3.10+.

New to Pydantic AI itself? Start with [its docs](https://pydantic.dev/docs/ai/): the agent you mount these capabilities on is defined there.

## Observability

Everything the harness does is observable: core's [Instrumentation](https://pydantic.dev/docs/ai/capabilities/instrumentation/) capability (or `logfire.instrument_pydantic_ai()`) emits a full trace of every run: every model call and tool call, with token and cost tracking. It's standard OpenTelemetry, so any OTLP backend works; [Logfire](https://pydantic.dev/logfire) is the easiest way to see it during development.

## Build your own

[Capabilities](https://pydantic.dev/docs/ai/capabilities/custom/) are the primary extension point for Pydantic AI, and every capability in this library doubles as a worked example. Publishing a standalone package? Use the `pydantic-ai-<name>` naming convention; see [Publishing capability packages](https://pydantic.dev/docs/ai/guides/extensibility/#publishing-capability-packages).

## Version policy

Pydantic AI Harness uses **0.x versioning**, and that's a statement about API stability, not maturity: these capabilities are tested end-to-end and meant for production use, but their APIs may still move between minor releases (0.1 -> 0.2): renamed parameters, changed defaults, restructured APIs, always with deprecation warnings where practical. Patch releases will not intentionally break existing behavior, and every breaking change is documented in release notes with migration guidance your agent can follow. Keeping the Harness a separate package from [Pydantic AI](https://github.com/pydantic/pydantic-ai), which has a [stricter version policy](https://pydantic.dev/docs/ai/project/version-policy/), is what lets capabilities iterate at the speed the field moves.

## Pydantic AI references

-   [Capabilities](https://pydantic.dev/docs/ai/capabilities/overview/): what capabilities are, built-in capabilities, building your own
-   [Hooks](https://pydantic.dev/docs/ai/core-concepts/hooks/): lifecycle hooks reference, ordering, error handling
-   [Extensibility](https://pydantic.dev/docs/ai/guides/extensibility/): publishing packages, third-party ecosystem
-   [Toolsets](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/): building tools for capabilities
-   [API reference](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/): full API docs

---
