# [Capabilities](https://pydantic.dev/docs/ai/capabilities/overview/)

# Capabilities

A capability is a reusable, composable unit of agent behavior. Instead of threading multiple arguments through your `Agent` constructor -- [instructions](https://pydantic.dev/docs/ai/core-concepts/agent/#instructions) here, [model settings](https://pydantic.dev/docs/ai/core-concepts/agent/#model-run-settings) there, a [toolset](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/) somewhere else, a [history processor](https://pydantic.dev/docs/ai/core-concepts/message-history/#processing-message-history) on yet another parameter -- you can bundle related behavior into a single capability and pass it via the [`capabilities`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) parameter.

Capabilities can provide any combination of:

-   **Tools** -- via [toolsets](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/) or [native tools](https://pydantic.dev/docs/ai/tools-toolsets/native-tools/)
-   **Lifecycle hooks** -- intercept and modify model requests, tool calls, and the overall run
-   **Instructions** -- static or dynamic [instruction](https://pydantic.dev/docs/ai/core-concepts/agent/#instructions) additions
-   **Model settings** -- static or per-step [model settings](https://pydantic.dev/docs/ai/core-concepts/agent/#model-run-settings)
-   **Models** -- static or adaptive model selection and application-specific model ID resolution

This makes them the primary extension point for Pydantic AI. Whether you're building a memory system, a guardrail, a cost tracker, or an approval workflow, a capability is the right abstraction.

Capabilities can be always-on or [loaded by the model on demand](https://pydantic.dev/docs/ai/capabilities/on-demand/). The [capability index below](#available-capabilities) covers Pydantic AI and [Pydantic AI Harness](https://pydantic.dev/docs/ai/harness/). [Third-party packages](https://pydantic.dev/docs/ai/capabilities/third-party/) provide many more capabilities, and you can define your own [declaratively](#bundling-behavior-with-capability) or by [subclassing](https://pydantic.dev/docs/ai/capabilities/custom/). To run agents durably across failures, restarts, and long waits, see [Durable Execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/).

## Available capabilities

Capabilities come from two packages, and they compose with each other and with capabilities you define. Core (`pydantic-ai`) ships the capabilities that require model or framework support: provider-native tools, provider APIs, and deep loop integration. **[Pydantic AI Harness](https://pydantic.dev/docs/ai/harness/)**, the official capability library and harness for Pydantic AI, ships everything else, from single capabilities to [complete agents](https://pydantic.dev/docs/ai/harness/coder/). The **Package** column says which; every entry links to its documentation.

### Harnesses

Complete agent stacks as regular combined capabilities: one import gives you a working agent, and you can take either apart into the blocks below.

Harness

Package

What it provides

[Coder](https://pydantic.dev/docs/ai/harness/coder/)

Harness

A complete coding-agent stack: files, shell, repo context, planning, a read-only explorer sub-agent, and context controls

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

Generate and edit images; provider-native where supported, direct image-model fallback elsewhere

[Native Tool](https://pydantic.dev/docs/ai/tools-toolsets/native-tools/)

Core

Register any provider-native tool with the agent

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

[Browser Use](https://pydantic.dev/docs/ai/harness/browser-use/)

Harness

Hand web tasks to an autonomous [browser-use](https://github.com/browser-use/browser-use) agent driving a real browser

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

The model writes one Python script that calls many tools inside a [Monty](https://github.com/pydantic/monty) sandbox: one round-trip instead of N, and intermediate results never enter the context window

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

### Loop customization

Core also ships capabilities for customizing the agent loop itself, mostly for production servers:

Capability

Package

What it does

[Hooks](https://pydantic.dev/docs/ai/core-concepts/hooks/)

Core

Decorator-based lifecycle hook registration

[Select Model](https://pydantic.dev/docs/ai/capabilities/select-model/)

Core

Select a static or per-step model with a callable

[Resolve Model ID](https://pydantic.dev/docs/ai/capabilities/resolve-model-id/)

Core

Resolve custom, application-specific model IDs with a callable

[Prepare Tools / Prepare Output Tools](https://pydantic.dev/docs/ai/capabilities/prepare-tools/)

Core

Filter or modify function and [output tool](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.ToolOutput) definitions per step

[Prefix Tools](https://pydantic.dev/docs/ai/capabilities/prefix-tools/)

Core

Wrap a capability and prefix its tool names

[Include Tool Return Schemas](https://pydantic.dev/docs/ai/capabilities/include-tool-return-schemas/)

Core

Include return type schemas in tool definitions sent to the model

[Set Tool Metadata](https://pydantic.dev/docs/ai/capabilities/set-tool-metadata/)

Core

Merge metadata key-value pairs onto selected tools

[Raise Content Filter Error](https://pydantic.dev/docs/ai/capabilities/raise-content-filter-error/)

Core

Raise [`ContentFilterError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ContentFilterError) whenever a model response has `finish_reason='content_filter'`

[Reinject System Prompt](https://pydantic.dev/docs/ai/capabilities/reinject-system-prompt/)

Core

Reinject the configured system prompt when the incoming message history is missing one

[Process History](https://pydantic.dev/docs/ai/capabilities/process-history/)

Core

Wrap a [history processor](https://pydantic.dev/docs/ai/core-concepts/message-history/#processing-message-history)

[Process Event Stream](https://pydantic.dev/docs/ai/capabilities/process-event-stream/)

Core

Forward [agent stream events](https://pydantic.dev/docs/ai/capabilities/process-event-stream/) to a handler function

The authoring primitives, [`Capability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Capability) for [bundling behavior without subclassing](#bundling-behavior-with-capability) and [`Toolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Toolset) for wrapping an [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset), are covered below. [ACP](https://pydantic.dev/docs/ai/harness/acp/) _(experimental, Harness)_ serves any agent to editors like Zed over the [Agent Client Protocol](https://agentclientprotocol.com/). Capabilities that can be declared in [YAML/JSON agent specs](https://pydantic.dev/docs/ai/core-concepts/agent-spec/#capability-spec-syntax) are listed there.

native\_capabilities.py

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import Thinking, WebSearch

agent = Agent(
    'anthropic:claude-fable-5',
    instructions='You are a research assistant. Be thorough and cite sources.',
    capabilities=[
        Thinking(effort='high'),
        WebSearch(local='duckduckgo'),
    ],
)
```

[Instructions](https://pydantic.dev/docs/ai/core-concepts/agent/#instructions) and [model settings](https://pydantic.dev/docs/ai/core-concepts/agent/#model-run-settings) are configured directly via the `instructions` and `model_settings` parameters on `Agent` (or [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec)). Capabilities are for behavior that goes beyond simple configuration -- tools, lifecycle hooks, and custom extensions. They compose well, especially when you want to reuse the same configuration across multiple agents or load it from a [spec file](https://pydantic.dev/docs/ai/core-concepts/agent-spec/).

## Bundling behavior with `Capability`

You don't need a subclass to define a capability of your own: [`Capability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Capability) bundles instructions, function tools, and [toolsets](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/) declaratively -- think of it as defining a skill:

capability\_shorthand.py

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import Capability

refunds = Capability(
    id='refunds',
    description='Use for refund eligibility and refund status.',
    instructions='Always confirm the order ID before issuing a refund.',
)


@refunds.tool_plain
def refund_status(order_id: str) -> str:
    """Look up the refund status for an order."""
    return f'Order {order_id}: refund issued on 2026-05-01.'


agent = Agent('openai:gpt-5.6-sol', capabilities=[refunds])
```

Add `defer_loading=True` and the bundle becomes an [on-demand capability](https://pydantic.dev/docs/ai/capabilities/on-demand/) that stays collapsed to a one-line catalog entry until the model loads it -- like [Agent Skills](https://pydantic.dev/docs/ai/capabilities/on-demand/#loading-skills-from-markdown-files), which you can wrap in a `Capability` directly. See [The `Capability` convenience class](https://pydantic.dev/docs/ai/capabilities/on-demand/#the-capability-convenience-class) for the full API. For behavior beyond instructions, tools, and toolsets -- lifecycle hooks, model settings, native tools -- subclass [`AbstractCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability) as covered in [Building Custom Capabilities](https://pydantic.dev/docs/ai/capabilities/custom/).

## Capability events

Reusable capabilities can publish typed [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent)s for coordination and observability. Give an event family a stable namespace, define each payload as a dataclass, and emit it from an async capability hook or capability-contributed tool by awaiting [`ctx.emit()`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.emit):

capability\_events.py

```python
from dataclasses import dataclass
from typing import Any

from pydantic_ai import CapabilityEvent, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import AgentToolset, FunctionToolset

WORKSPACE = 'workspace'


@dataclass(kw_only=True)
class FileWriteEvent(CapabilityEvent, namespace=WORKSPACE):
    path: str
    bytes_written: int


workspace = FunctionToolset()


@workspace.tool
async def write_file(ctx: RunContext[Any], path: str, content: str) -> str:
    await ctx.emit(FileWriteEvent(path=path, bytes_written=len(content)))
    return f'Wrote {path}'


@dataclass
class Workspace(AbstractCapability[Any]):
    def get_toolset(self) -> AgentToolset[Any] | None:
        return workspace
```

_(This example is complete, it can be run "as is")_

Keep the namespace in a module-level constant and give it the capability's name or [`id`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.id): every event in the family repeats it, and it's the prefix subscribers match on.

A capability publishes capability events specifically, and emitting an application [`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent) from one raises a [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError); see [Which event type do I use?](https://pydantic.dev/docs/ai/core-concepts/agent/#which-event-type) for the split. The payload cannot use the field names the envelope needs for itself: `data`, `capability_id`, `tool_call_id`, `tool_name`, and `event_kind` are rejected when the class is defined.

Pydantic AI stamps the emitting capability's run id as `capability_id`. For a capability you gave an `id`, that is the `id`. For one you did not, it is a handle the framework mints for that run -- `'<file_reader:4f3a9c>'` -- which differs every run and must not be matched on; give the capability an explicit `id` if a subscriber needs to recognize it. Events emitted by its tools also receive `tool_call_id` and `tool_name`. They surface on the [agent run event stream](https://pydantic.dev/docs/ai/core-concepts/agent/#streaming-all-events) but are internal coordination signals, so UI adapters do not forward them by default. A protocol adapter can override [`handle_capability_event()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_capability_event) to map one onto its own protocol, building the payload itself as `CapabilityEvent` has no `to_payload()`. An application that wants to expose one to a frontend can instead listen for it with [`@agent.on_event`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.on_event) and emit an application `CustomEvent` carrying the public payload:

republish\_capability\_event.py

```python
from dataclasses import dataclass

from pydantic_ai import Agent, CapabilityEvent, CustomEvent, RunContext

SEARCH_INDEX = 'search_index'


@dataclass(kw_only=True)
class IndexRebuiltEvent(CapabilityEvent, namespace=SEARCH_INDEX):
    documents: int


@dataclass(kw_only=True)
class SearchReadyEvent(CustomEvent):
    documents: int


agent = Agent('test')


@agent.on_event(IndexRebuiltEvent)
async def republish(ctx: RunContext, event: IndexRebuiltEvent) -> None:
    await ctx.emit(SearchReadyEvent(documents=event.documents))
```

_(This example is complete, it can be run "as is")_

The listener belongs to the application rather than to a capability, so it is one of the places application `CustomEvent`s can be emitted. [`Hooks.on.event`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Hooks) does the same job when you want a `Hooks` capability anyway -- for the other [hook families](https://pydantic.dev/docs/ai/core-concepts/hooks/), or to choose where it sits among the other capabilities.

The namespace and event name form the serialized `kind` (for example, `workspace.file_read`), and the event name is derived from the class name unless you pass an explicit `name=`. A namespace is required: defining a `CapabilityEvent` subclass without one raises `TypeError` there and then, rather than letting an unnamespaced event reach the stream. You only give it once per family, though -- an event subclassing another capability event inherits its namespace and contributes just its own name, so a shared base is the tidiest way to define a family -- and a subclass can pass its own `namespace=` to move out of the one it inherited. Mark a base that only carries the namespace and fields common to the family `abstract=True`, and it stays out of the registry and can't be emitted itself, while its subclasses register as usual. Decorate it with `@dataclass` like any other event: an undecorated base contributes no fields at all, which is rejected rather than left to surface as a payload quietly missing them. The `kind` is the event's wire identifier, so renaming the class renames the tag with it, breaking compatibility wherever events outlive the emitting process -- [durable execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/) histories and caches, persisted event logs, subscribers matching on the kind. A capability published as a library should pin `name=` on each of its events. Kinds are registered when the class is defined and must be unique within the process; re-executing the same class definition (as when re-running a notebook cell) replaces the registration. Import the module defining an event before creating the adapter that deserializes it, as each pydantic `TypeAdapter` captures the kinds registered when it is created. Otherwise the event becomes an [`UnknownCapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UnknownCapabilityEvent) and a `UserWarning` is emitted, without losing payload fields; serializing it again preserves the wire representation so a later consumer can recover the typed event.

### Reacting to events

Use [`@on_event`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.on_event) on an async capability method to react to selected event classes. For example, a repository-context capability can enqueue instructions immediately after a file-system capability reports reading a repository guidance file:

react\_to\_capability\_events.py

```python
from dataclasses import dataclass
from typing import Any

from pydantic_ai import CapabilityEvent, RunContext
from pydantic_ai.capabilities import AbstractCapability, on_event

REPO_CONTEXT = 'repo_context'


@dataclass(kw_only=True)
class FileReadEvent(CapabilityEvent, namespace=REPO_CONTEXT):
    path: str


@dataclass(kw_only=True)
class DirectoryListedEvent(CapabilityEvent, namespace=REPO_CONTEXT):
    path: str


class RepoContext(AbstractCapability[Any]):
    @on_event(FileReadEvent, DirectoryListedEvent)
    async def _follow_discovered_instructions(
        self,
        ctx: RunContext[Any],
        event: FileReadEvent | DirectoryListedEvent,
    ) -> None:
        if event.path.endswith('AGENTS.md'):
            ctx.enqueue(f'Follow the instructions in {event.path}.')
```

Filtering is explicit: the decorator uses `isinstance` against the classes passed to it. A bare `@on_event` receives the full [`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent) union, including model response deltas, tool call and result events, deferred and [enqueued-message](https://pydantic.dev/docs/ai/core-concepts/message-history/#injecting-messages-mid-run) events, [custom events](https://pydantic.dev/docs/ai/core-concepts/agent/#custom-events), and capability events.

Name the classes when you can. Beyond narrowing the `event` argument for the type checker, the classes are what let dispatch skip a capability without descending into it: a capability is only woken for events one of its listeners accepts. A bare `@on_event` -- or an overridden [`on_event()`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.on_event), whose dispatch isn't knowable in advance -- opts that capability into every event, and a capability that combines others reports the union of its children's. If you override `on_event()` and can describe what it dispatches, override [`listens_to()`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.listens_to) alongside it to say so.

Listeners run sequentially in capability order, and marked methods within one capability run in definition order. The emitting capability also receives its own events. By default, listeners run when the event reaches its position in the stream, so listener ordering always matches stream ordering and listener work does not add to the emitter's latency. For events emitted during tool execution, listeners run before the next model request. An event emitted during `before_model_request` may only reach listeners after that request begins, with the same as-soon-as-possible timing as [`ctx.enqueue()`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue).

Decision events that need listener mutations before the emitter continues declare `dispatch='immediate'` on the event class:

Building on the workspace capability above, a write can announce itself before it happens and let a listener veto it:

cancellable\_capability\_event.py

```python
from dataclasses import dataclass
from typing import Any

from pydantic_ai import CapabilityEvent, RunContext
from pydantic_ai.capabilities import AbstractCapability, on_event
from pydantic_ai.toolsets import FunctionToolset

WORKSPACE = 'workspace'


@dataclass(kw_only=True)
class FileWriteStartEvent(
    CapabilityEvent, namespace=WORKSPACE, dispatch='immediate'
):
    path: str
    cancelled: bool = False
    cancel_reason: str | None = None

    def cancel(self, reason: str | None = None) -> None:
        self.cancelled = True
        self.cancel_reason = reason


workspace = FunctionToolset()


@workspace.tool
async def write_file(ctx: RunContext[Any], path: str, content: str) -> str:
    event = await ctx.emit(FileWriteStartEvent(path=path))  # (1)
    if event.cancelled:  # (2)
        return f'Refused to write {path}: {event.cancel_reason}'
    return f'Wrote {path}'


class ProtectGitDirectory(AbstractCapability[Any]):
    @on_event(FileWriteStartEvent)
    async def _veto_writes_to_git(
        self, ctx: RunContext[Any], event: FileWriteStartEvent
    ) -> None:
        if event.path.startswith('.git/'):
            event.cancel('.git/ is managed by the repository, not the agent')
```

`emit` returns only once every listener has run, and returns the same instance it was given.

So the decision is readable immediately after, on either the returned event or the emitter's own reference.

_(This example is complete, it can be run "as is")_

For immediate dispatch, Pydantic AI buffers the event before invoking listeners, but stream consumers only receive it once all listeners have run, so they never observe a decision half-made. Attribution is stamped on the event in place, so after `await ctx.emit(event)` the emitter can read `event.cancelled` off its own reference (the same instance `emit` returns), and an event emitted by a listener appears after the decision event in the stream. Inline events are still delivered exactly once, including when the same event instance is re-emitted. Stream-dispatch listeners run inside user-defined [`wrap_run_event_stream()`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.wrap_run_event_stream) wrappers.

Note

Any `on_event` listener automatically enables streaming for an otherwise non-streaming `agent.run()`: model requests are made with the provider's streaming API so events exist to listen to. Providers treat streaming and non-streaming requests the same in almost all respects, but if you need to guarantee non-streamed requests, don't attach listeners.

## Provider-adaptive tools

[`WebSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebSearch), [`WebFetch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebFetch), [`ImageGeneration`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ImageGeneration), [`XSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.XSearch), and [`MCP`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.MCP) each cover a single capability (web search, URL fetch, image generation, X search, MCP) across two implementations:

-   **Native** -- invoked by the model provider when the model supports it. The work happens on the provider's side (e.g. Anthropic's web search runs server-side, returning results inline).
-   **Local** -- runs in your Python process. Used when the model doesn't support the native tool; your code does the work (e.g. calling DuckDuckGo directly).

Capability

Local fallback

Notes

[`WebSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebSearch)

`local='duckduckgo'` or `local=True` (DuckDuckGo)

Requires the `duckduckgo` optional group

[`WebFetch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebFetch)

`local=True` (markdownify-based fetch)

Requires the `web-fetch` optional group

[`ImageGeneration`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ImageGeneration)

Direct model via `local=ImageGenerator(...)` or `fallback_image_model='provider:image-model'`, or subagent via `fallback_subagent_model=`

The direct routes use the [direct image-generation API](https://pydantic.dev/docs/ai/guides/image-generation/) without a subagent

[`XSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.XSearch)

Subagent via `fallback_subagent_model=`

No default non-xAI fallback; set `fallback_subagent_model` to an xAI model that supports [`XSearchTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.XSearchTool)

[`MCP`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.MCP)

Direct connection to the MCP server (the default)

Accepts any [`MCPToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset) input; transport is auto-detected from a URL

Because these capabilities contribute model-facing tools, their `id`, `description`, and `defer_loading` fields are meaningful: set `description` and `defer_loading` when that tool should stay hidden until the model loads the matching workflow with the `load_capability` tool. Each of these covers a single fixed concern, so `id` already defaults to a stable value (`'web_search'`, `'web_fetch'`, `'image_generation'`, `'x_search'`; `MCP` derives one from the server URL) -- which is what [durable execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/) identifies the toolset they contribute by, so it works unconfigured. Set `id` only to rename it, and see [building custom capabilities](https://pydantic.dev/docs/ai/capabilities/custom/) for what happens when two share one. This includes [`ImageGeneration`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ImageGeneration) when image generation should only be available for an image-specific workflow, whether it resolves to a native image tool, a direct image-model fallback, or the subagent fallback.

A [`Capability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Capability) contributing several [toolsets](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/) names each one `'{capability_id}_{index}'` -- those are the ids [durable execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/) registers them under.

Configure each side via the `native=` and `local=` kwargs. `native=` accepts `True` (use the capability's default [native tool](https://pydantic.dev/docs/ai/tools-toolsets/native-tools/) instance), `False` (disable native), an explicit instance like `WebSearchTool(...)` for fine-grained config, or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) that returns a native tool or `None` (see [Dynamic Configuration](https://pydantic.dev/docs/ai/tools-toolsets/native-tools/#dynamic-configuration)). A factory that returns `None` omits the native tool for that request. `local=` accepts `True` (the bundled local fallback, on capabilities that have one -- `WebSearch` and `WebFetch`), `False` (disable local), a named strategy string where supported, or any callable, [`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool), or [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset) -- and, on `ImageGeneration`, an [`ImageGenerator`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerator). Optional installs needed for the local fallback are opt-in -- the capability raises a [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) at construction (with an install hint) when you ask for a local strategy whose extra isn't installed.

`None` on a capability with a `fallback_subagent_model`

[`XSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.XSearch) and [`ImageGeneration`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ImageGeneration) route unsupported models to a subagent instead of a local tool. Once a `fallback_subagent_model` is set, a factory returning `None` no longer omits anything: the subagent tool stays offered to the model, even one that supports the native tool, and calling it raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) -- see [X Search](https://pydantic.dev/docs/ai/capabilities/x-search/) and [Image Generation](https://pydantic.dev/docs/ai/capabilities/image-generation/).

provider\_adaptive\_tools.py

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import MCP, ImageGeneration, WebFetch, WebSearch, XSearch

agent = Agent(
    'anthropic:claude-fable-5',
    capabilities=[
        # Native when supported; DuckDuckGo fallback on unsupported models
        WebSearch(local='duckduckgo'),
        # Native when supported; markdownify-based fallback on unsupported models
        WebFetch(local=True),
        # Native when supported; direct image-model fallback otherwise
        ImageGeneration(fallback_image_model='openai:gpt-image-1.5'),
        # Native on xAI; on other models, explicitly delegate to an xAI model
        XSearch(fallback_subagent_model='xai:grok-4.3'),
        # Runs the MCP server locally by default; pass `native=True` to also advertise native MCP
        MCP('https://mcp.example.com/api'),
    ],
)
```

`MCP` defaults the other way from the others: because MCP carries credentials, it runs locally by default and you opt into native MCP with `native=True`. The others default to native and you opt into local with `local=`.

[`XSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.XSearch) is slightly different from [`WebSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebSearch) and [`WebFetch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebFetch): there is no default non-xAI fallback. If your agent is not running on an xAI model, set `fallback_subagent_model` explicitly to an xAI model that supports [`XSearchTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.XSearchTool).

`fallback_model` is deprecated

On both [`XSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.XSearch) and [`ImageGeneration`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ImageGeneration), `fallback_model` is the former name of `fallback_subagent_model`. It keeps working -- in Python and in an [agent spec](https://pydantic.dev/docs/ai/core-concepts/agent-spec/) -- and warns; passing both names is refused: [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) when you construct the capability, and the `ValueError` the spec loader wraps it in when you load a spec. The new name says which fallback it configures: an extra agent run, as against a `local=` tool -- or, on `ImageGeneration`, a `fallback_image_model` -- running in your own process.

Some constraint fields require the native tool (the bundled local fallback can't enforce them) -- passing them locks the capability to the native path. If the model doesn't support the native tool, the capability raises a [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError).

constraints.py

```python
# Limit to 5 searches per run -- requires native (the local fallback can't track call count)
WebSearch(max_uses=5)

# Only fetch example.com -- enforced locally when native is unavailable
WebFetch(allowed_domains=['example.com'], local=True)
```

### Building your own

All five capabilities are subclasses of [`NativeOrLocalTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.NativeOrLocalTool), which you can use directly or subclass to build your own provider-adaptive tools. For example, to pair [`CodeExecutionTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.CodeExecutionTool) with a local fallback:

custom\_native\_or\_local.py

```python
from pydantic_ai.native_tools import CodeExecutionTool
from pydantic_ai.capabilities import NativeOrLocalTool

cap = NativeOrLocalTool(native=CodeExecutionTool(), local=my_local_executor)
```

## Third-party capabilities

Third-party packages publish capabilities of their own -- see [Third-Party Capabilities](https://pydantic.dev/docs/ai/capabilities/third-party/) for the ecosystem, and [Publishing capabilities](https://pydantic.dev/docs/ai/capabilities/custom/#publishing-capabilities) for making your own capability available to others.

---
