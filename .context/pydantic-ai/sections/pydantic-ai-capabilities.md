# [pydantic_ai.capabilities](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/)

# pydantic\_ai.capabilities

### Toolset

**Bases:** `AbstractCapability[AgentDepsT]`

A capability that provides a toolset.

### SelectModel

**Bases:** `AbstractCapability[AgentDepsT]`

Select a model before each logical model request step.

The selector receives a [`ModelSelectionContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelSelectionContext) containing the run dependencies, message history, accumulated usage, and lower-precedence model. It may be synchronous or asynchronous and return either a model instance or model ID.

### Thinking

**Bases:** `AbstractCapability[Any]`

Enables and configures model thinking/reasoning.

Uses the unified `thinking` setting in [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) to work portably across providers. Provider-specific thinking settings (e.g., `anthropic_thinking`, `openai_reasoning_effort`) take precedence when both are set.

#### Attributes

##### effort

The thinking effort level.

-   `True`: Enable thinking with the provider's default effort.
-   `False`: Disable thinking (silently ignored on always-on models).
-   `'minimal'`/`'low'`/`'medium'`/`'high'`/`'xhigh'`: Enable thinking at a specific effort level.

**Type:** `ThinkingLevel` **Default:** `True`

##### id

One-off: an agent has a single thinking configuration, so the id is fixed by default.

Two of them resolve to one via [`combine`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.combine), which keeps the last. Pass a distinct `id` to keep both, or `id=None` for derived ids.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `'thinking'`

### PrepareTools

**Bases:** `AbstractCapability[AgentDepsT]`

Capability that filters or modifies function tool definitions using a callable.

Wraps a [`ToolsPrepareFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolsPrepareFunc) as a capability. Filters/modifies **function** tools only; for output tools use [`PrepareOutputTools`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.PrepareOutputTools).

```python
from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import PrepareTools
from pydantic_ai.tools import ToolDefinition


async def hide_admin_tools(
    ctx: RunContext, tool_defs: list[ToolDefinition]
) -> list[ToolDefinition]:
    return [td for td in tool_defs if not td.name.startswith('admin_')]


agent = Agent('openai:gpt-5', capabilities=[PrepareTools(hide_admin_tools)])
```

### HandleDeferredToolCalls

**Bases:** `AbstractCapability[AgentDepsT]`

Resolves deferred tool calls inline during an agent run using a handler function.

When tools require approval or external execution, the agent normally pauses the run and returns [`DeferredToolRequests`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolRequests) as output. This capability intercepts deferred tool calls, calls the provided handler to resolve them, and continues the agent run automatically.

The handler receives the [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) and the [`DeferredToolRequests`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolRequests). It may return [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) with results for some or all pending calls, or return `None` to decline handling (the next capability in the chain gets a chance, otherwise the calls bubble up as `DeferredToolRequests` output).

#### Attributes

##### handler

The handler function that resolves deferred tool requests.

Receives the run context and the deferred tool requests, and returns [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) with results for some or all pending calls, or `None` to decline handling. Can be sync or async.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\], [`DeferredToolRequests`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolRequests)\], [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) | [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[[`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None)\]\]

### IncludeToolReturnSchemas

**Bases:** `AbstractCapability[AgentDepsT]`

Capability that includes return schemas for selected tools.

When added to an agent's capabilities, this sets [`include_return_schema`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition.include_return_schema) to `True` on matching tool definitions, causing the model to receive return type information for those tools.

For models that natively support return schemas (e.g. Google Gemini), the schema is passed as a structured field. For other models, it is injected into the tool description as JSON text.

Per-tool overrides (`Tool(..., include_return_schema=False)`) take precedence -- this capability only sets the flag on tools that haven't explicitly opted out.

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import IncludeToolReturnSchemas

agent = Agent('openai:gpt-5', capabilities=[IncludeToolReturnSchemas()])
```

#### Attributes

##### tools

Which tools should have their return schemas included.

-   `'all'` (default): every tool gets its return schema included.
-   `Sequence[str]`: only tools whose names are listed.
-   `dict[str, Any]`: matches tools whose metadata deeply includes the specified key-value pairs.
-   Callable `(ctx, tool_def) -> bool`: custom sync or async predicate.

**Type:** `ToolSelector`\[`AgentDepsT`\] **Default:** `'all'`

### PrefixTools

**Bases:** `WrapperCapability[AgentDepsT]`

A capability that wraps another capability and prefixes its tool names.

Only the wrapped capability's tools are prefixed; other agent tools are unaffected.

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import PrefixTools, Toolset
from pydantic_ai.toolsets import FunctionToolset

toolset = FunctionToolset()

agent = Agent(
    'openai:gpt-5',
    capabilities=[
        PrefixTools(
            wrapped=Toolset(toolset),
            prefix='ns',
        ),
    ],
)
```

#### Methods

##### from\_spec

`@classmethod`

```python
def from_spec(cls, *, prefix: str, capability: CapabilitySpec) -> PrefixTools[Any]
```

Create from spec with a nested capability specification.

###### Returns

`PrefixTools`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

###### Parameters

**`prefix`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The prefix to add to tool names (e.g. `'mcp'` turns `'search'` into `'mcp_search'`).

**`capability`** : `CapabilitySpec`

A capability spec (same format as entries in the `capabilities` list).

### WebFetch

**Bases:** `NativeOrLocalTool[AgentDepsT]`

URL fetching capability.

Uses the model's native URL fetching and raises `UserError` on models that don't support it natively. Pass `local=True` to opt into a local fallback (requires the `web-fetch` optional group):

Terminal

```bash
pip install "pydantic-ai-slim[web-fetch]"
```

#### Attributes

##### id

One-off: an agent searches, fetches or generates one way, so the id is fixed.

Declared here rather than only as an `__init__` default so the class states it where `_declares_default_id` -- and a reader -- can see it.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `id`

##### allowed\_domains

Only fetch from these domains. Enforced locally when native is unavailable.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `allowed_domains`

##### blocked\_domains

Never fetch from these domains. Enforced locally when native is unavailable.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `blocked_domains`

##### max\_uses

Maximum number of fetches per run. Requires native support.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `max_uses`

##### enable\_citations

Enable citations for fetched content. Native-only; ignored by local tools.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `enable_citations`

##### max\_content\_tokens

Maximum content length in tokens. Native-only; ignored by local tools.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `max_content_tokens`

### RaiseContentFilterError

**Bases:** `AbstractCapability[AgentDepsT]`

Raises `ContentFilterError` when a model response has `finish_reason='content_filter'`.

Add this capability to opt into treating content-filtered responses as run-ending errors, even when the provider returns partial text or refusal text. The full [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse) is serialized into [`ContentFilterError.body`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UnexpectedModelBehavior.body) so callers can inspect any partial content.

#### Attributes

##### id

One-off: the capability takes no configuration, so a second instance can only duplicate the first, so the id is fixed by default.

Two of them resolve to one via [`combine`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.combine), which keeps the last. Pass a distinct `id` to keep both, or `id=None` for derived ids.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `'raise_content_filter_error'`

### SetToolMetadata

**Bases:** `AbstractCapability[AgentDepsT]`

Capability that merges metadata key-value pairs onto selected tools.

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import SetToolMetadata

agent = Agent('openai:gpt-5', capabilities=[SetToolMetadata(code_mode=True)])
```

### UseThreadExecutor

**Bases:** `AbstractCapability[Any]`

Use a custom executor for running sync functions in threads.

By default, sync tool functions and other sync callbacks are run in threads using `anyio.to_thread.run_sync`, which creates ephemeral threads. In long-running servers (e.g. FastAPI), this can lead to thread accumulation under sustained load.

This capability provides a bounded [`ThreadPoolExecutor`](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor) (or any [`Executor`](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Executor)) to use instead, scoped to agent runs:

```python
from concurrent.futures import ThreadPoolExecutor

from pydantic_ai import Agent
from pydantic_ai.capabilities import UseThreadExecutor

executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix='agent-worker')
agent = Agent('openai:gpt-5.2', capabilities=[UseThreadExecutor(executor)])
```

To set an executor for all agents globally, use [`Agent.using_thread_executor()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.using_thread_executor).

#### Attributes

##### executor

The executor to use for running sync functions.

**Type:** `Executor`

##### id

One-off: exactly one executor is in effect for a run, so the id is fixed by default.

`wrap_run` sets a context variable, so a second one nested inside the first shadows it and the outer executor is never used. Naming them the same makes that resolution explicit rather than an accident of nesting order.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `'use_thread_executor'`

### NativeTool

**Bases:** `AbstractCapability[AgentDepsT]`

A capability that registers a native tool with the agent.

Wraps a single [`AgentNativeTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.AgentNativeTool) -- either a static [`AbstractNativeTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.AbstractNativeTool) instance or a callable that dynamically produces one.

Equivalent to passing the tool through `Agent(capabilities=[NativeTool(my_tool)])`. For provider-adaptive use (with a local fallback), see [`NativeOrLocalTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.NativeOrLocalTool) or its subclasses like [`WebSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebSearch).

#### Methods

##### from\_spec

`@classmethod`

```python
def from_spec(
    cls,
    tool: AbstractNativeTool | None = None,
    **kwargs: Any,
) -> NativeTool[Any]
```

Create from spec.

Supports two YAML forms:

-   Flat: `{NativeTool: {kind: web_search, search_context_size: high}}`
-   Explicit: `{NativeTool: {tool: {kind: web_search}}}`

###### Returns

`NativeTool`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

### ReinjectSystemPrompt

**Bases:** `AbstractCapability[AgentDepsT]`

Capability that reinjects the agent's configured `system_prompt` when missing from history.

Ensures the agent's configured `system_prompt` is present at the head of the first `ModelRequest` on every model request.

Intended for callers that reconstruct a `message_history` from a source that doesn't round-trip system prompts -- UI frontends, database persistence layers, conversation compaction pipelines. By default, if any `SystemPromptPart` is already present anywhere in the history (for example, preserved from a prior run or handed off from another agent), this capability leaves the messages untouched so that existing system prompts remain authoritative. Set `replace_existing=True` to instead strip any existing `SystemPromptPart`s before prepending the agent's configured prompt -- useful when the history comes from an untrusted source (such as a UI frontend) and the server's prompt must win.

The UI adapters automatically add this capability in `manage_system_prompt='server'` mode with `replace_existing=True`. Add it explicitly with `Agent(..., capabilities=[ReinjectSystemPrompt()])` or per-run via the `capabilities=` argument on [`Agent.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) to get the same behavior anywhere.

#### Attributes

##### replace\_existing

If `True`, strip any existing `SystemPromptPart`s from the history before prepending the agent's configured prompt. If `False` (the default), the capability is a no-op when any `SystemPromptPart` is already present.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### id

One-off: an agent reinjects the system prompt one way, so the id is fixed by default.

Two of them resolve to one via [`combine`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.combine), which keeps the last. Pass a distinct `id` to keep both, or `id=None` for derived ids.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `'reinject_system_prompt'`

### WebSearch

**Bases:** `NativeOrLocalTool[AgentDepsT]`

Web search capability.

Uses the model's native web search and raises `UserError` on models that don't support it natively. Pass `local='duckduckgo'` (or `local=True`) to opt into a local DuckDuckGo fallback -- requires the `duckduckgo` optional group:

Terminal

```bash
pip install "pydantic-ai-slim[duckduckgo]"
```

`local=` also accepts any callable, `Tool`, or `AbstractToolset` for a custom fallback.

#### Attributes

##### id

One-off: an agent searches, fetches or generates one way, so the id is fixed.

Declared here rather than only as an `__init__` default so the class states it where `_declares_default_id` -- and a reader -- can see it.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `id`

##### search\_context\_size

Controls how much context is retrieved from the web. Native-only; ignored by local tools.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['low', 'medium', 'high'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `search_context_size`

##### user\_location

Localize search results based on user location. Native-only; ignored by local tools.

**Type:** [`WebSearchUserLocation`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.WebSearchUserLocation) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `user_location`

##### blocked\_domains

Domains to exclude from results. Requires native support.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `blocked_domains`

##### allowed\_domains

Only include results from these domains. Requires native support.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `allowed_domains`

##### max\_uses

Maximum number of web searches per run. Requires native support.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `max_uses`

##### external\_web\_access

Whether OpenAI Responses may fetch live web content. `False` requires native support.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `external_web_access`

### ResolveModelId

**Bases:** `AbstractCapability[AgentDepsT]`

Resolve model IDs with a user-provided sync or async callable.

The callable receives a [`ModelResolutionContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelResolutionContext) followed by the selected model ID. Return `None` to let a later capability or the default [`infer_model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.infer_model) behavior handle the ID.

### DynamicCapability

**Bases:** `AbstractCapability[AgentDepsT]`

A capability that builds another capability dynamically using a function that takes the run context.

The factory is called once per agent run from [`for_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.for_run). The returned capability's instructions, model settings, native tools, and hooks flow through normally; its toolset is exposed through a stable dynamic toolset contributed at agent construction time, which reuses the run's resolved capability instance.

Under durable execution, a stable `id` is required on `DynamicCapability`: it names the durable units (activities/steps/tasks) that list and call the contributed tools. The factory itself runs in workflow/flow code, which durable engines re-execute on replay, recovery, or flow retry, so it must be deterministic given the run's dependencies; leave I/O to the toolset it returns, whose use is checkpointed inside the durable units. In-process engines (DBOS, Prefect) reuse the run's resolved capability inside those units; Temporal re-runs the factory inside its activities (the activity boundary can't carry the resolved instance).

Pass a [`CapabilityFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.CapabilityFunc) directly to `Agent(capabilities=[...])` or `agent.run(capabilities=[...])` and it will be wrapped in a `DynamicCapability` automatically.

`defer_loading` on the wrapper itself is rejected because `for_run` replaces the wrapper with the factory's return value. Set it on the returned capability instead. For history replay, set a stable `id` on the capability the factory returns rather than on the wrapper.

#### Attributes

##### capability\_func

The function that takes the run context and returns a capability or `None`.

**Type:** [`CapabilityFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.CapabilityFunc)\[`AgentDepsT`\]

### NativeOrLocalTool

**Bases:** `AbstractCapability[AgentDepsT]`

Capability that pairs a provider-native tool with a local fallback.

When the model supports the native tool, the local fallback is removed. When the model doesn't support the native tool, it is removed and the local tool stays.

Can be used directly:

```python
from pydantic_ai.capabilities import NativeOrLocalTool

cap = NativeOrLocalTool(native=WebSearchTool(), local=my_search_func)
```

Or subclassed to set defaults by overriding `_default_native`, `_default_local`, `_has_local_fallback`, and `_requires_native`. The built-in [`WebSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebSearch), [`WebFetch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebFetch), and [`ImageGeneration`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ImageGeneration) capabilities are all subclasses.

#### Attributes

##### native

Configure the provider-native tool.

-   `True` (default): use the default native tool configuration (subclasses only).
-   `False`: disable the native tool; always use the local tool.
-   An `AbstractNativeTool` instance: use this specific configuration.
-   A callable (`NativeToolFunc`): dynamically create the native tool per-run via `RunContext`. Returning `None` omits the native tool.

**Type:** [`AgentNativeTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.AgentNativeTool)\[`AgentDepsT`\] | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `native`

##### local

Configure the local fallback tool.

-   `None` (default): auto-detect a local fallback via `_default_local`.
-   `True`: opt in to the default local fallback (resolved via `_resolve_local_strategy`).
-   `False`: disable the local fallback; only use the native tool.
-   A named strategy (e.g. `'duckduckgo'`): resolved via `_resolve_local_strategy` in subclasses.
-   A `Tool` or `AbstractToolset` instance: use this specific local tool.
-   A bare callable: automatically wrapped in a `Tool`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\] | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[..., [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\] | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `local`

#### Methods

##### combine

`@classmethod`

```python
def combine(
    cls,
    capabilities: Sequence[AbstractCapability[AgentDepsT]],
) -> AbstractCapability[AgentDepsT]
```

Merge the declared configuration, then rebuild the native tool from the result.

`__post_init__` copies this capability's configuration into the native tool it builds, and that tool -- not the capability -- is what reaches the provider. Merging the capability's fields alone would leave a merged `allowed_domains` beside a native tool still carrying one instance's, so a composed restriction would read as applied while the request went out without it. Anything `_default_native` produced is therefore produced again from the merged configuration.

A native tool the user passed in is left alone: it states its own configuration, and rebuilding would discard it. Two of those take the later, like any other value the merge cannot reconcile.

The merged instance is validated the way a constructed one is. `replace_no_init` skips `__post_init__`, and a merge can reach a combination no constructor would accept -- a `native=False` instance beside one carrying native-only constraints leaves a capability that contributes neither the native tool nor a local fallback. Re-running the check turns that into the same `UserError` writing it by hand would raise.

###### Returns

`AbstractCapability`\[`AgentDepsT`\]

### ProcessEventStream

**Bases:** `AbstractCapability[AgentDepsT]`

A capability that forwards the agent's event stream to a user-provided async handler.

The handler receives the stream of [`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent)s emitted during classic model streaming and tool execution, or the shared and realtime-only events emitted by a realtime session. Two forms are supported:

-   An [`EventStreamHandler`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.EventStreamHandler) -- an `async def` returning `None`. Events are forwarded to the handler while also being passed through unchanged to the rest of the capability chain, so multiple handlers (and the top-level `event_stream_handler` argument) can all see the same stream without changing each other's view. A handler that returns early stops receiving events but does not affect downstream consumers; a handler that raises propagates the exception to the rest of the run. Events are delivered synchronously, so a slow handler back-pressures the rest of the stream.
    
-   An `EventStreamProcessor` -- an async generator yielding [`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent)s. The events it yields replace the inner stream for downstream wrappers and consumers, so it can modify, drop, or add events.
    
    This replacement is global, not a private view for event-stream handlers: the run has one event stream and a processor shapes all of it. Dropping or rewriting a [`PartDeltaEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartDeltaEvent) therefore also changes what [`stream_text()`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.stream_text) yields to a `run_stream()` caller.
    
    Some events are also control signals: [`FinalResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FinalResultEvent) is what tells [`agent.run_stream()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run_stream) that the final output has started, so dropping it makes `run_stream()` wait for the whole model response before handing back the result instead of streaming it. Filter deliberately.
    
    None of this changes the run's output: the [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse) is accumulated from the raw model stream before a processor sees the events, so [`stream_output()`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.stream_output) and the final validated output are unaffected (dropping events can only change when a partial snapshot is emitted, not its content). Use the observer form if you only want to watch events.
    
    In a realtime session, this is likewise only a consumer-facing view. Transforming or dropping events does not affect session history or tool execution.
    

When this capability is registered, `agent.run()` and [`AgentRun.next()`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.next) automatically enable streaming so the handler fires without requiring an explicit `event_stream_handler` argument. The handler sees the same events however the run is driven, including under [`agent.iter()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.iter) and when you stream a node yourself with `node.stream()`.

Durable execution

Under the durable-execution capabilities ([`TemporalDurability`](https://pydantic.dev/docs/ai/api/pydantic-ai/durable_exec/#pydantic_ai.durable_exec.temporal.TemporalDurability), [`DBOSDurability`](https://pydantic.dev/docs/ai/api/pydantic-ai/durable_exec/#pydantic_ai.durable_exec.dbos.DBOSDurability), [`PrefectDurability`](https://pydantic.dev/docs/ai/api/pydantic-ai/durable_exec/#pydantic_ai.durable_exec.prefect.PrefectDurability)), this capability's handler always runs in workflow or flow code and must be deterministic because it re-runs on workflow replay. Tool-call and final-output events arrive live; model events are the real captured events replayed after each model-request activity, step, or task completes. For handler I/O that must run exactly once inside a durable boundary, pass `event_stream_handler=` to the durability capability instead.

### XSearch

**Bases:** `NativeOrLocalTool[AgentDepsT]`

X (Twitter) search capability.

On xAI models, uses the native X search directly with no extra configuration.

On non-xAI models, you must explicitly set `fallback_subagent_model` to an xAI model (e.g. `'xai:grok-4.3'`) to enable a subagent-based fallback. There is no default subagent model -- attempting to use `XSearch` on a non-xAI model without `fallback_subagent_model` will error.

#### Attributes

##### id

One-off: an agent searches, fetches or generates one way, so the id is fixed.

Declared here rather than only as an `__init__` default so the class states it where `_declares_default_id` -- and a reader -- can see it.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `id`

##### fallback\_subagent\_model

Model for a subagent to run when the agent's model doesn't support X search natively.

Required for non-xAI models; leave as `None` (the default) when running on an xAI model. Must be a model that supports X search via the [`XSearchTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.XSearchTool) native tool (i.e. an xAI model), for example `'xai:grok-4.3'`.

Can be a model name string, `Model` instance, or a callable taking `RunContext` that returns a `Model` instance or model name string.

**Type:** `XSearchFallbackModel` **Default:** `fallback_model if fallback_model is not None else fallback_subagent_model`

##### allowed\_x\_handles

If provided, only posts from these X handles will be included (max 20).

Honored by the native X search tool, whether used directly on an xAI model or via the `fallback_subagent_model` subagent.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `allowed_x_handles`

##### excluded\_x\_handles

If provided, posts from these X handles will be excluded (max 20).

Honored by the native X search tool, whether used directly on an xAI model or via the `fallback_subagent_model` subagent.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `excluded_x_handles`

##### from\_date

If provided, only posts created on or after this datetime will be included.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `from_date`

##### to\_date

If provided, only posts created on or before this datetime will be included.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `to_date`

##### enable\_image\_understanding

Enable image analysis from X posts. When unset, inherits the native tool's default (`False`).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `enable_image_understanding`

##### enable\_video\_understanding

Enable video analysis from X content. When unset, inherits the native tool's default (`False`).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `enable_video_understanding`

##### include\_output

Include raw X search results in the response as [`NativeToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolReturnPart).

When unset, inherits the native tool's default (`False`).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `include_output`

##### fallback\_model

Deprecated alias for [`fallback_subagent_model`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.XSearch.fallback_subagent_model).

**Type:** `XSearchFallbackModel`

### ProcessHistory

**Bases:** `AbstractCapability[AgentDepsT]`

A capability that processes message history before model requests.

### MCP

**Bases:** `NativeOrLocalTool[AgentDepsT]`

MCP server capability.

The primary entry point for using MCP servers with Pydantic AI. Runs the MCP server locally -- keeps credentials, hooks, and tracing under your control -- and accepts any [`MCPToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset) input (URL, `fastmcp.Client`, transport, in-process `FastMCP` server, script path, etc.) directly via `local=`.

Pass `url=` for HTTP-based servers; the same URL can also be advertised to providers that support native MCP via `native=True`. For non-URL local clients, omit `url=` and pass the client/toolset as `local=`. Pass `native=True, local=False` for strict native-only (no local at all -- works without the `mcp` extra).

#### Attributes

##### url

The URL of the MCP server.

Required when using native MCP. Optional when using a local-only client via `local=`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `url`

##### authorization\_token

Authorization header value for MCP server requests. Passed to both native and local.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `authorization_token`

##### headers

HTTP headers for MCP server requests. Passed to both native and local.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `headers`

##### allowed\_tools

Filter to only these tools. Applied to both native and local.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `allowed_tools`

##### description

Description of the MCP server. Native-only; ignored by local tools.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `description`

#### Methods

##### from\_spec

`@classmethod`

```python
def from_spec(
    cls,
    url: str,
    *,
    native: MCPServerTool | bool = False,
    local: str | bool | None = None,
    id: str | None = None,
    authorization_token: str | None = None,
    headers: dict[str, str] | None = None,
    allowed_tools: list[str] | None = None,
    description: str | None = None,
    defer_loading: bool = False,
) -> MCP[AgentDepsT]
```

Construct an `MCP` capability from spec-serializable args.

Restricts the runtime-wide `local=` union to the JSON/YAML-serializable subset (`str | bool | None`) so `AgentSpec` schema generation works, and requires `url=` (which is optional at runtime when `local=` is a concrete non-URL client). Non-serializable runtime values like `fastmcp.Client`, `ClientTransport`, or pre-built `MCPToolset` instances can still be passed to `MCP(...)` directly -- they just can't roundtrip through a spec file.

###### Returns

`MCP`\[`AgentDepsT`\]

### ToolSearch

**Bases:** `AbstractCapability[AgentDepsT]`

Capability that provides tool discovery for large toolsets.

Tools marked with `defer_loading=True` are hidden from the model until discovered. Auto-injected into every agent -- zero overhead when no deferred tools exist.

When the model supports native tool search (Anthropic BM25/regex, OpenAI Responses), discovery is handled by the provider: the deferred tools are sent with `defer_loading` on the wire and the provider exposes them once they've been discovered. Otherwise, discovery happens locally via a `search_tools` function that the model can call.

On providers that support a native "client-executed" surface (Anthropic, OpenAI), the discovery message is delivered append-only -- prompt cache is preserved across discovery turns, so growing the message history with discovered-tool results does not invalidate the cached prefix.

```python
from collections.abc import Sequence

from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.capabilities import ToolSearch
from pydantic_ai.tools import ToolDefinition


# Tools become deferred via `defer_loading=True`. They stay hidden from the model
# until tool search discovers them.
def get_weather(city: str) -> str:
    ...


weather_tool = Tool(get_weather, defer_loading=True)

# Default: native search on supporting providers, local keyword matching elsewhere.
agent = Agent('anthropic:claude-sonnet-4-6', tools=[weather_tool], capabilities=[ToolSearch()])

# Force a specific Anthropic native strategy; errors on providers that can't honor it.
agent = Agent(
    'anthropic:claude-sonnet-4-6',
    tools=[weather_tool],
    capabilities=[ToolSearch(strategy='regex')],
)

# Always run the local keyword-overlap algorithm, regardless of provider.
agent = Agent(
    'anthropic:claude-sonnet-4-6',
    tools=[weather_tool],
    capabilities=[ToolSearch(strategy='keywords')],
)

# Custom search function -- used locally, and by provider-native "client-executed"
# modes when supported.
def my_search(
    ctx: RunContext, queries: Sequence[str], tools: Sequence[ToolDefinition]
) -> list[str]:
    return [
        t.name
        for t in tools
        if any(q.lower() in (t.description or '').lower() for q in queries)
    ]

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    tools=[weather_tool],
    capabilities=[ToolSearch(strategy=my_search)],
)
```

#### Attributes

##### strategy

The search strategy to use.

-   `None` (default): let Pydantic AI pick the best strategy for the current provider -- native on supporting models (Anthropic BM25, OpenAI server-executed tool search), local keyword matching elsewhere. The choice may change in future versions.
-   `'keywords'`: always use the local keyword-overlap algorithm. Still prompt-cache compatible on providers that expose a "client-executed" native surface (Anthropic, OpenAI): the algorithm rides the same `defer_loading` wire as a custom callable, so the tool list stays stable across discovery rounds and the cached prefix is preserved.
-   `'bm25'` / `'regex'`: force a specific Anthropic native strategy. Raises on providers that can't honor the choice (including OpenAI, which has no named native strategies).
-   Callable `(ctx, queries, tools) -> names`: custom search function (sync or async). Used locally, and by the native "client-executed" surface on providers that support it (Anthropic custom tool-reference blocks, OpenAI `execution='client'`).

**Type:** `ToolSearchStrategy`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_results

Maximum number of matches returned by the local search algorithm.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `10`

##### tool\_description

Custom description for the model-facing search tool when search runs on our side.

Used for the local `search_tools` fallback and for providers with client-executed native tool search.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### parameter\_description

Custom description for the `queries` parameter when search runs on our side.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### id

One-off: an agent has a single tool-discovery configuration, so the id is fixed by default.

Two of them resolve to one via [`combine`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.combine). Pass a distinct `id` to keep both, or `id=None` for derived ids.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `'tool_search'`

##### function\_tool\_name

Reserved name of the local function tool used when tool search runs client-side.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'search_tools'`

#### Methods

##### before\_model\_request

`@async`

```python
def before_model_request(
    ctx: RunContext[AgentDepsT],
    request_context: ModelRequestContext,
) -> ModelRequestContext
```

Record tools unlocked by a capability load.

###### Returns

[`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

### Capability

**Bases:** `AbstractCapability[AgentDepsT]`

Convenience capability for bundling instructions, tools, and toolsets without subclassing.

This groups related instructions, descriptions, function tools, and toolsets under a capability identity. Instructions passed via `instructions=` are available through `get_instructions()`; [`instructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Capability.instructions) is the decorator for registering instruction functions. The constructor accepts static or callable `description=` values. For model settings, lifecycle hooks, native tools, wrapper toolsets, or custom per-run logic, subclass [`AbstractCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability).

#### Attributes

##### description

Static description mirrored on the instance.

The constructor also accepts callable descriptions, stored internally and returned from `get_description()`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `description if isinstance(description, str) else None`

##### toolsets

Toolsets to register with the agent. Combined via [`CombinedToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.CombinedToolset) when more than one is provided.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AgentToolset)\[`AgentDepsT`\]\] **Default:** `resolved_toolsets`

##### tools

Function tools to register with the agent.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\] | `ToolFuncEither`\[`AgentDepsT`, ...\]\] **Default:** `tools`

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    instructions: AgentInstructions[AgentDepsT] | None = None,
    toolsets: Sequence[AgentToolset[AgentDepsT]] | None = None,
    tools: Sequence[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]] = (),
    id: str | None = None,
    description: CapabilityDescription[AgentDepsT] | None = None,
    defer_loading: bool = False,
) -> None
```

Build a capability from instructions, tools, toolsets, and an optional description.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`instructions`** : `AgentInstructions`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Static instructions and/or instruction function(s), available via `get_instructions()`. Pass an [`InstructionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart) to declare a part's [`name`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart.name) or mark it [`dynamic`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart.dynamic). Register more with the [`instructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Capability.instructions) decorator.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AgentToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Toolsets to register with the agent.

**`tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\] | `ToolFuncEither`\[`AgentDepsT`, ...\]\] _Default:_ `()`

Function tools to register with the agent.

**`id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Stable identifier for the capability. Required when `defer_loading=True`, so the model's `load_capability` call can reference it.

**`description`** : `CapabilityDescription`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Static string or callable description, returned from `get_description()`. For a deferred capability it is shown to the model so it can decide whether to load it.

**`defer_loading`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

When `True`, the capability's tools and instructions stay hidden until the model loads it on demand via the `load_capability` tool; requires `id`.

##### tool\_plain

```python
def tool_plain(func: ToolFuncPlain[ToolParams], /) -> ToolFuncPlain[ToolParams]
def tool_plain(
    *,
    name: str | None = None,
    description: str | None = None,
    retries: int | None = None,
    prepare: ToolPrepareFunc[AgentDepsT] | None = None,
    args_validator: ArgsValidatorFunc[AgentDepsT, ToolParams] | None = None,
    docstring_format: DocstringFormat = 'auto',
    require_parameter_descriptions: bool = False,
    schema_generator: type[GenerateJsonSchema] = GenerateToolJsonSchema,
    strict: bool | None = None,
    sequential: bool = False,
    requires_approval: bool = False,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
    defer_loading: bool = False,
    include_return_schema: bool | None = None,
) -> Callable[[ToolFuncPlain[ToolParams]], ToolFuncPlain[ToolParams]]
```

Decorator to register a plain (no-[`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)) function tool on this capability.

Mirrors [`Agent.tool_plain`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.tool_plain): the tool is added to this capability's function toolset and registered with the agent whenever the capability is active.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### tool

```python
def tool(
    func: ToolFuncContext[AgentDepsT, ToolParams],
    /,
) -> ToolFuncContext[AgentDepsT, ToolParams]
def tool(
    *,
    name: str | None = None,
    description: str | None = None,
    retries: int | None = None,
    prepare: ToolPrepareFunc[AgentDepsT] | None = None,
    args_validator: ArgsValidatorFunc[AgentDepsT, ToolParams] | None = None,
    docstring_format: DocstringFormat = 'auto',
    require_parameter_descriptions: bool = False,
    schema_generator: type[GenerateJsonSchema] = GenerateToolJsonSchema,
    strict: bool | None = None,
    sequential: bool = False,
    requires_approval: bool = False,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
    defer_loading: bool = False,
    include_return_schema: bool | None = None,
) -> Callable[[ToolFuncContext[AgentDepsT, ToolParams]], ToolFuncContext[AgentDepsT, ToolParams]]
```

Decorator to register a function tool (taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)) on this capability.

Mirrors [`Agent.tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.tool): the tool is added to this capability's function toolset and registered with the agent whenever the capability is active.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### instructions

```python
def instructions(
    func: Callable[[RunContext[AgentDepsT]], str | None],
    /,
) -> Callable[[RunContext[AgentDepsT]], str | None]
def instructions(
    func: Callable[[RunContext[AgentDepsT]], Awaitable[str | None]],
    /,
) -> Callable[[RunContext[AgentDepsT]], Awaitable[str | None]]
def instructions(func: Callable[[], str | None], /) -> Callable[[], str | None]
def instructions(
    func: Callable[[], Awaitable[str | None]],
    /,
) -> Callable[[], Awaitable[str | None]]
def instructions(
    *,
    name: str | None = None,
) -> Callable[[SystemPromptFunc[AgentDepsT]], SystemPromptFunc[AgentDepsT]]
```

Decorator to register an instructions function on this capability.

Mirrors `Agent.instructions`: the function may take [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) (or no arguments), may be sync or async, and is appended to any instructions provided via the `instructions=` field.

Example:

```python
from pydantic_ai import RunContext
from pydantic_ai.capabilities import Capability

cap = Capability[str](instructions='base instructions')

@cap.instructions
async def dynamic(ctx: RunContext[str]) -> str:
    return f'extra: {ctx.deps}'
```

###### Returns

[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`SystemPromptFunc`\[`AgentDepsT`\]\], `SystemPromptFunc`\[`AgentDepsT`\]\] | `SystemPromptFunc`\[`AgentDepsT`\]

###### Parameters

**`func`** : `SystemPromptFunc`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The instructions function to register.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An optional name for the instruction part this function produces, keyed as `'capability:<capability id>:<name>'` on [`InstructionPart.id`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart.id) so an application can address this part specifically, where the capability's own key addresses everything it contributes. Requires the capability to have an [`id`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.id) -- without one there is no source key to qualify the name against, so the part stays unaddressable. See [instruction parts](https://pydantic.dev/docs/ai/core-concepts/agent/#instruction-parts).

### PrepareOutputTools

**Bases:** `AbstractCapability[AgentDepsT]`

Capability that filters or modifies output tool definitions using a callable.

Mirrors [`PrepareTools`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.PrepareTools) for [output tools](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.ToolOutput). `ctx.retry`/`ctx.max_retries` reflect the **output** retry budget (`max_output_retries`), matching the output hook lifecycle.

```python
from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import PrepareOutputTools
from pydantic_ai.output import ToolOutput
from pydantic_ai.tools import ToolDefinition


async def only_after_first_step(
    ctx: RunContext, tool_defs: list[ToolDefinition]
) -> list[ToolDefinition]:
    return tool_defs if ctx.run_step > 0 else []


agent = Agent(
    'openai:gpt-5',
    output_type=ToolOutput(str),
    capabilities=[PrepareOutputTools(only_after_first_step)],
)
```

### CombinedCapability

**Bases:** `AbstractCapability[AgentDepsT]`

A capability that combines multiple capabilities.

When any child returns a fresh instance from [`for_agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.for_agent) or [`for_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.for_run), the container is rebound via `_rebound`: a shallow copy holding the new children, with subclass state carried over verbatim and `__init__`/`__post_init__` not re-run. Compute values derived from `capabilities` on access (e.g. via a property) rather than caching them at construction, so they can't go stale across a rebind. `_instruction_sources` is the one thing that can't be -- flattening destroys what it records -- so it's carried across by `_rebound` instead, and swapping children any other way (`replace()`) silently rebuilds it from the flattened list.

#### Methods

##### visit\_and\_replace

```python
def visit_and_replace(
    visitor: Callable[[AbstractCapability[AgentDepsT]], AbstractCapability[AgentDepsT] | None],
) -> AbstractCapability[AgentDepsT] | None
```

Visit each child and rebuild the container from the survivors.

A child the visitor removed is reported to `_rebound` so the composition view drops it too; see [`AbstractCapability.visit_and_replace`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.visit_and_replace) for the tree-walking contract.

###### Returns

`AbstractCapability`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### WrapperCapability

**Bases:** `AbstractCapability[AgentDepsT]`

A capability that wraps another capability and delegates all methods.

Analogous to [`WrapperToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.WrapperToolset) for toolsets. Subclass and override specific methods to modify behavior while delegating the rest.

When the wrapped capability returns a fresh instance from [`for_agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.for_agent) or [`for_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.for_run), the wrapper is rebound as a shallow copy holding the new `wrapped`: subclass state is carried over verbatim and `__init__`/`__post_init__` are not re-run. Compute values derived from `wrapped` on access (e.g. via a property) rather than caching them at construction, so they can't go stale across a rebind.

#### Methods

##### visit\_and\_replace

```python
def visit_and_replace(
    visitor: Callable[[AbstractCapability[AgentDepsT]], AbstractCapability[AgentDepsT] | None],
) -> AbstractCapability[AgentDepsT] | None
```

Visit the wrapper first; a replaced or removed wrapper takes its subtree with it.

When the wrapper survives, the visit descends into `wrapped` and this wrapper is rebuilt around whatever remains; see [`AbstractCapability.visit_and_replace`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.visit_and_replace) for the tree-walking contract.

###### Returns

`AbstractCapability`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### Instrumentation

**Bases:** `AbstractCapability[Any]`

Capability that instruments agent runs with OpenTelemetry/Logfire tracing.

When added to an agent via `capabilities=[Instrumentation(...)]`, this capability creates OpenTelemetry spans for the agent run, model requests, and tool executions.

Other capabilities can add attributes to these spans using the OpenTelemetry API (`opentelemetry.trace.get_current_span().set_attribute(key, value)`).

#### Attributes

##### settings

OTel/Logfire instrumentation settings. Defaults to `InstrumentationSettings()`, which uses the global `TracerProvider` (typically configured by `logfire.configure()`).

**Type:** [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) **Default:** `field(default_factory=(lambda: _default_settings()))`

##### id

One-off: an agent has a single instrumentation configuration, so the id is fixed by default.

Two of them resolve to one via [`combine`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.combine), which keeps the last. Pass a distinct `id` to keep both, or `id=None` for derived ids.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `'instrumentation'`

#### Methods

##### from\_spec

`@classmethod`

```python
def from_spec(
    cls,
    *,
    include_binary_content: bool = True,
    include_content: bool = True,
    include_model_request_parameters: bool = True,
    version: Literal[2, 3, 4, 5, 6] = DEFAULT_INSTRUMENTATION_VERSION,
    use_aggregated_usage_attribute_names: bool = True,
) -> Instrumentation
```

Build an `Instrumentation` capability from a YAML/JSON spec.

Accepts every serializable [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) option. The OTel `tracer_provider` and `meter_provider` fields can't be expressed in YAML and default to the global providers (typically configured via `logfire.configure()`).

`id` is deliberately not accepted. An agent has one instrumentation configuration -- which is what the class-level default `id` says -- so there is nothing for a spec to name, and two `Instrumentation` capabilities resolve to one rather than colliding.

YAML form:

capabilities:

-   Instrumentation: {} # default settings
-   Instrumentation: version: 2 include\_content: false

###### Returns

`Instrumentation`

##### for\_run

`@async`

```python
def for_run(ctx: RunContext[Any]) -> Instrumentation
```

Return a fresh copy for per-run state isolation.

###### Returns

`Instrumentation`

##### on\_tool\_validate\_error

`@async`

```python
def on_tool_validate_error(
    ctx: RunContext[AgentDepsT],
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: RawToolArgs,
    error: ValidationError | ModelRetry,
) -> ValidatedToolArgs
```

Emit an error span for a tool call whose argument validation failed.

Runs only after every other capability has declined to recover the error, so a recovered validation failure produces no span. The span keeps the `execute_tool` operation name so tracing backends group it with other tool spans, and sets `pydantic_ai.tool.failure_stage: 'validation'` to distinguish it from execution failures.

With content capture enabled, the span records the retry prompt built from the error as the tool result. That is the exact message the model receives when the agent loop handles the failure; raw-mode callers (e.g. sandboxed dispatch via `handle_call(wrap_validation_errors=False)`) surface the raw exception to the calling code instead, and the recorded prompt is just the rendered description of the failure.

###### Returns

`ValidatedToolArgs`

##### wrap\_output\_process

`@async`

```python
def wrap_output_process(
    ctx: RunContext[AgentDepsT],
    *,
    output_context: OutputContext,
    output: Any,
    handler: WrapOutputProcessHandler,
) -> Any
```

Emit a span for output-function execution.

Output processing for plain validation (no function) is not span-worthy -- the validated value is the model's response itself, no user code ran. We open a span only when an output function will execute, regardless of whether the output arrived via a tool call. The span name reflects the function (or tool name when the function name is unavailable, e.g. union processors).

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### HookTimeoutError

**Bases:** [`AgentRunError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.AgentRunError), [`TimeoutError`](https://docs.python.org/3/builtins/exceptions.html#TimeoutError)

Raised when a hook function exceeds its configured timeout.

### ImageGeneration

**Bases:** `NativeOrLocalTool[AgentDepsT]`

Image generation capability.

Uses the model's native image generation when available. When the model doesn't support it, the [direct image generation API](https://pydantic.dev/docs/ai/guides/image-generation/) can take over. Which field it goes on follows what you hand over: an `ImageGenerator` carries settings of its own, so it goes on `local` beside the other implementations you supply; a bare `ImageGenerationModel` or a `'provider:model'` name goes on `fallback_image_model`.

The `fallback_subagent_model` path is the other way to cover such a model: it runs an additional agent on an image-capable conversational model, so the image comes from that model's native `ImageGenerationTool`. Use it when you want those native tool semantics. `local` also takes a fallback tool you write yourself. The three fields are alternatives: stating more than one raises `UserError`.

Portable `dimensions` and `aspect_ratio` settings are applied to the direct fallback using `ImageGenerationSettings`. Other fields configure the native `ImageGenerationTool`; configure provider-specific direct settings on an explicit `ImageGenerator` or `ImageGenerationModel`.

When passing a custom `native` instance or factory, its settings are also used for the `fallback_subagent_model` subagent; capability-level fields override any `native` settings. A static instance's `aspect_ratio` is also inherited by the direct fallback.

#### Attributes

##### id

One-off: an agent searches, fetches or generates one way, so the id is fixed.

Declared here rather than only as an `__init__` default so the class states it where `_declares_default_id` -- and a reader -- can see it.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `id`

##### fallback\_subagent\_model

Model for a subagent to run when the agent's model doesn't support image generation natively.

Must be a model that supports image generation via the [`ImageGenerationTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.ImageGenerationTool) native tool. This requires a conversational model with image generation support, not a dedicated image-only API. Examples:

-   `'openai-responses:gpt-5.4'` -- OpenAI model with image generation support
-   `'google:gemini-3-pro-image'` -- Google image generation model

Can be a model name string, `Model` instance, or a callable taking `RunContext` that returns a `Model` instance or model name string.

**Type:** `ImageGenerationFallbackModel` **Default:** `fallback_model if fallback_model is not None else fallback_subagent_model`

##### fallback\_image\_model

Direct image model to generate with when the agent's model doesn't support it natively.

Takes an [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) or a `'provider:model'` string; a string without a provider prefix raises `UserError`, and so does an [`ImageGenerator`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerator), which carries settings of its own and belongs on `local`. The tool calls the [direct image generation API](https://pydantic.dev/docs/ai/guides/image-generation/) rather than running a second agent, which is what `fallback_subagent_model` does.

Note which of the two image-model fields applies to which path: `image_model` names the model _within_ the provider's native tool and is unprefixed (`'gpt-image-2'`), while this one selects the direct model and carries the provider (`'openai:gpt-image-2'`). The direct fallback ignores `image_model` with a warning.

The model is kept as declared; the `generate_image` tool is derived from it and the capability's settings each time the toolset is requested.

**Type:** [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `fallback_image_model`

##### action

Whether to generate a new image or edit an existing image.

Supported by: OpenAI Responses. Default: `'auto'`.

The direct generator receives no reference images, so `'edit'` raises `UserError`: at construction with `native=False`, and when the tool runs otherwise.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['generate', 'edit', 'auto'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `action`

##### background

Background type for the generated image.

Supported by: OpenAI Responses.

The direct generator ignores it; set the provider-prefixed equivalent on the generator instead.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['transparent', 'opaque', 'auto'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `background`

##### input\_fidelity

Input fidelity for matching style/features of input images.

Supported by: OpenAI Responses. Default: `'low'`.

The direct generator ignores it; set the provider-prefixed equivalent on the generator instead.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['high', 'low'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `input_fidelity`

##### moderation

Moderation level for the generated image.

Supported by: OpenAI Responses.

The direct generator ignores it; set the provider-prefixed equivalent on the generator instead.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['auto', 'low'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `moderation`

##### image\_model

The image generation model to use.

Supported by: OpenAI Responses.

The direct fallback ignores it with a warning, because the generator on `local` or the model on `fallback_image_model` already names the model it generates with. `image_model` is unprefixed and names the model inside the native tool.

**Type:** `ImageGenerationModelName` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `image_model`

##### output\_compression

Compression level for the output image.

Supported by: OpenAI Responses (jpeg/webp, default: 100), Google Cloud (jpeg, default: 75).

The direct generator ignores it; set the provider-prefixed equivalent on the generator instead.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `output_compression`

##### output\_format

Output format of the generated image.

Supported by: OpenAI Responses (default: `'png'`), Google Cloud.

The direct generator ignores it; set the provider-prefixed equivalent on the generator instead.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['png', 'webp', 'jpeg'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `output_format`

##### quality

Quality of the generated image.

Supported by: OpenAI Responses.

The direct generator ignores it; set the provider-prefixed equivalent on the generator instead.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['low', 'medium', 'high', 'auto'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `quality`

##### size

Size of the generated image for the native tool.

Supported by: OpenAI Responses (`'auto'`, `'1024x1024'`, `'1024x1536'`, `'1536x1024'`), Google Gemini 3 Pro Image and later (`'512'` on Gemini 3.1 Flash Image only, `'1K'`, `'2K'`, `'4K'`).

Direct image APIs use provider-prefixed size or resolution settings.

**Type:** `ImageSize` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `size`

##### dimensions

Exact direct-model output dimensions as `(width, height)` in pixels.

This is mutually exclusive with `aspect_ratio`: passing both alongside a direct generator raises `UserError` at construction. Only the direct generator can apply it, so pass `native=False` to guarantee it takes effect: with the default `native=True` the direct generator is dropped whenever the conversational model generates images natively, and the native tool has no equivalent -- that request warns. The `fallback_subagent_model` path ignores it with a warning. Supported shapes are model-specific; see the [Image Generation guide](https://pydantic.dev/docs/ai/guides/image-generation/#supported-exact-dimensions).

**Type:** `ImageDimensions` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `dimensions`

##### aspect\_ratio

Aspect ratio for generated images.

Supported by: Google image-generation models (Gemini), OpenAI Responses (maps `'1:1'`, `'2:3'`, `'3:2'` to sizes).

Direct adapters map this to a canonical geometry supported by the selected model. Ratios the native tool also accepts apply on either path; the rest need the direct generator, so pass `native=False` to guarantee them, as for `dimensions`, and a request that takes the native path instead warns. Ratios outside the native vocabulary are ignored by the `fallback_subagent_model` path with a warning. See the [ratio-to-dimensions matrix](https://pydantic.dev/docs/ai/guides/image-generation/#canonical-dimensions-for-aspect_ratio).

**Type:** `ImageGenerationAspectRatio` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `aspect_ratio`

##### local

Configure the local fallback tool.

Takes an [`ImageGenerator`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerator), which generates through the [direct image generation API](https://pydantic.dev/docs/ai/guides/image-generation/), or the `Tool`, toolset and callable shapes [`NativeOrLocalTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.NativeOrLocalTool) accepts, for a fallback you implement yourself. A generator carries settings of its own, which is why it belongs here; a bare [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) does not, and goes to `fallback_image_model` -- passing one here raises `UserError`. Every string and `local=True` raise `UserError` too: there is no named local strategy, and a direct image model _name_ is `fallback_image_model`'s to take.

A generator is kept as declared; the `generate_image` tool is derived from it and the capability's settings each time the toolset is requested.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`ImageGenerator`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerator) | [`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\] | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[..., [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\] | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `local`

##### fallback\_model

Deprecated alias for [`fallback_subagent_model`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ImageGeneration.fallback_subagent_model).

**Type:** `ImageGenerationFallbackModel`

#### Methods

##### combine

`@classmethod`

```python
def combine(
    cls,
    capabilities: Sequence[AbstractCapability[AgentDepsT]],
) -> AbstractCapability[AgentDepsT]
```

Merge like `NativeOrLocalTool`, except that `dimensions` is one value, not a collection.

The default merge unions two sequences, and a `(width, height)` pair's entries are not independent: `(1024, 1024)` beside `(1536, 1024)` unions to `(1024, 1536)`, a flipped orientation neither instance asked for, and two disjoint pairs union to a three-element tuple that is no size at all. It takes the later stated value instead, the rule the scalar fields already get.

Applied after the base merge because `__post_init__` reads only whether `dimensions` is set, never what it is, and a merge never turns a stated pair into `None`.

###### Returns

`AbstractCapability`\[`AgentDepsT`\]

##### from\_spec

`@classmethod`

```python
def from_spec(
    cls,
    *,
    native: ImageGenerationTool | bool = True,
    local: Literal[False] | None = None,
    fallback_subagent_model: KnownModelName | str | None = None,
    fallback_image_model: str | None = None,
    action: Literal['generate', 'edit', 'auto'] | None = None,
    background: Literal['transparent', 'opaque', 'auto'] | None = None,
    input_fidelity: Literal['high', 'low'] | None = None,
    moderation: Literal['auto', 'low'] | None = None,
    image_model: ImageGenerationModelName | None = None,
    output_compression: int | None = None,
    output_format: Literal['png', 'webp', 'jpeg'] | None = None,
    quality: Literal['low', 'medium', 'high', 'auto'] | None = None,
    size: ImageSize | None = None,
    dimensions: ImageDimensions | None = None,
    aspect_ratio: ImageGenerationAspectRatio | None = None,
    id: str | None = 'image_generation',
    defer_loading: bool = False,
    description: str | None = None,
    fallback_model: KnownModelName | str | None = None,
) -> ImageGeneration[AgentDepsT]
```

Construct from the JSON/YAML-serializable subset of the runtime API.

Runtime objects, such as the `ImageGenerationModel` that `fallback_image_model` also takes and the `ImageGenerator`, `Tool`, toolset and callables `local` takes, can be passed to `ImageGeneration(...)` directly but cannot be represented in an agent spec. A direct image model name is serializable and can be passed as `fallback_image_model='provider:model'`.

###### Returns

`ImageGeneration`\[`AgentDepsT`\]

### CapabilityOrdering

Ordering constraints for a capability within a combined capability chain.

Capabilities follow middleware semantics: the first capability in the list is the **outermost** layer, wrapping all others. Declare ordering constraints via [`get_ordering`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.get_ordering) to control a capability's position in the chain regardless of how the user lists them.

When a [`CombinedCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.CombinedCapability) is constructed, it topologically sorts its children to satisfy these constraints, preserving user-provided order as a tiebreaker.

#### Attributes

##### position

Fixed position in the chain, or `None` for user-provided order.

**Type:** `CapabilityPosition` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### wraps

This capability wraps around (is outside of) these capabilities in the middleware chain.

Each entry can be a capability **type** (matches all instances of that type via `issubclass`) or a specific capability **instance** (matches by identity via `is`).

Note: instance refs use identity (`is`) matching, so if a capability's [`for_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.for_run) returns a new instance, refs to the original will no longer match. Use type refs when the target capability uses per-run state isolation.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`CapabilityRef`\] **Default:** `()`

##### wrapped\_by

This capability is wrapped by (is inside of) these capabilities in the middleware chain.

Each entry can be a capability **type** (matches all instances of that type via `issubclass`) or a specific capability **instance** (matches by identity via `is`).

Note: instance refs use identity (`is`) matching, so if a capability's [`for_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.for_run) returns a new instance, refs to the original will no longer match. Use type refs when the target capability uses per-run state isolation.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`CapabilityRef`\] **Default:** `()`

##### requires

These types must be present in the chain (no ordering implied).

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractCapability`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]\] **Default:** `()`

### AbstractCapability

**Bases:** `ABC`, `Generic[AgentDepsT]`

Abstract base class for agent capabilities.

A capability is a reusable, composable unit of agent behavior that can provide instructions, model settings, tools, and request/response hooks.

Lifecycle: capabilities are passed to an [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent) at construction time, where most `get_*` methods are called to collect static configuration (instructions, model settings, toolsets, native tools). When [`for_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.for_run) returns a replacement instance, that configuration is re-extracted from the replacement at run setup. The exception is [`get_wrapper_toolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.get_wrapper_toolset), which is always called per-run during toolset assembly. Then, on each model request during a run, the [`before_model_request`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.before_model_request) and [`after_model_request`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.after_model_request) hooks are called to allow dynamic adjustments.

See the [capabilities documentation](https://pydantic.dev/docs/ai/capabilities/overview/) for built-in capabilities.

[`get_serialization_name`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.get_serialization_name) and [`from_spec`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.from_spec) support YAML/JSON specs (via `Agent.from_spec`); they have sensible defaults and typically don't need to be overridden.

#### Attributes

##### id

Optional identifier used to reference this capability within a run.

Must be unique within a run, not per instance: it identifies the capability across the run -- including the fresh instance a [`for_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.for_run) override may return -- rather than a specific object.

Required when `defer_loading=True`. If omitted for an always-on capability, the run derives a local id from the class name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### description

Description of the capability.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### defer\_loading

If True, model-facing tools and instructions are hidden until the model explicitly loads the capability via the `load_capability` tool.

Model settings and lifecycle hooks are registered during run setup, but only apply or fire once the capability is loaded.

Requires a stable [`id`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.id) so message history can identify the capability. A [`description`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.description) or [`get_description`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.get_description) override is optional and only adds routing context to the load catalog.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### has\_wrap\_node\_run

Whether this capability (or any sub-capability) overrides wrap\_node\_run.

Deprecated: `wrap_node_run` runs under every way of driving a run, so there is nothing left to test for.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### has\_wrap\_run\_event\_stream

Whether this capability (or any sub-capability) overrides wrap\_run\_event\_stream.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### has\_on\_event

Whether this capability handles run events dynamically or with marked methods.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### has\_resolve\_model\_id

Whether this capability or a wrapped capability overrides `resolve_model_id`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### Methods

##### combine

`@classmethod`

```python
def combine(
    cls,
    capabilities: Sequence[AbstractCapability[AgentDepsT]],
) -> AbstractCapability[AgentDepsT]
```

Combine capabilities that resolved to the same `id` into the one the run will use.

Two capabilities under one `id` name the same thing, so exactly one of them can be what that `id` refers to. The default merges them field by field: a value only one of them states is kept, and a value both state takes the later one.

That default needs no thought from most capabilities, because it follows from the `id`. Declaring a default `id` _is_ the statement that an agent has one of these, so a repeat is one configuration stated twice and merging is what it meant. A capability that can legitimately appear several times declares no default `id` instead -- and then this is never reached, because the run tells anonymous capabilities apart itself, and an `id` the _user_ passed to such a capability is a name they chose, so passing it twice is reported as a collision rather than merged.

Override it when composing takes more than merging fields: `NativeOrLocalTool` rebuilds its native tool from the merged configuration, because that tool, not the capability, is what reaches the provider.

Only reached _within_ one layer: a capability supplied for a run overrides its agent-level namesake outright rather than composing with it.

###### Returns

`AbstractCapability`\[`AgentDepsT`\] -- The single capability the `id` refers to for this run.

###### Parameters

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`AbstractCapability`\[`AgentDepsT`\]\]

The two or more capabilities sharing an `id`, in application order. All are instances of `cls`; a shared `id` across _different_ classes is always rejected, since no one class can say how it composes.

##### apply

```python
def apply(visitor: Callable[[AbstractCapability[AgentDepsT]], None]) -> None
```

Run a visitor function on all leaf capabilities in this tree.

For a single capability, calls the visitor on itself. Overridden by [`CombinedCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.CombinedCapability) to recursively visit all child capabilities.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### visit\_and\_replace

```python
def visit_and_replace(
    visitor: Callable[[AbstractCapability[AgentDepsT]], AbstractCapability[AgentDepsT] | None],
) -> AbstractCapability[AgentDepsT] | None
```

Run a visitor function on the same capabilities as `apply`, and replace them in this tree with its result.

Analogous to [`AbstractToolset.visit_and_replace`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset.visit_and_replace), except that returning `None` removes the visited capability instead of replacing it.

Rewrites in place: containers and wrappers rebuild only the branches that changed, so what survives keeps its position in the hierarchy and a wrapper goes on wrapping whatever is left of its subtree. Rebuilding a tree from the flat list `apply` produces does neither: it loses the nesting, and re-adds a container's children next to the wrapper that already contributes them.

Returns `self` when nothing changed, and `None` when the visitor removed everything.

For a single capability, returns the visitor's result for itself. Overridden by [`CombinedCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.CombinedCapability) and [`WrapperCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WrapperCapability) to rebuild their children; a custom capability that overrides `apply` because it holds children of its own should override this alongside it, or those children are invisible to callers rewriting the tree.

###### Returns

`AbstractCapability`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### listens\_to

```python
def listens_to(event: AgentStreamEvent) -> bool
```

Whether [`on_event`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.on_event) would reach a listener for `event`.

Dispatch asks this before descending, so a capability that listens to a few event classes isn't woken for every event in the run. The default reports `True` for any event a [`@on_event`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.on_event)\-marked method accepts, and for every event when `on_event` is overridden directly, since what an override dispatches to isn't knowable here. Override this alongside `on_event` when you can report something narrower.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### get\_serialization\_name

`@classmethod`

```python
def get_serialization_name(cls) -> str | None
```

Return the name used for spec serialization (CamelCase class name by default).

Return None to opt out of spec-based construction.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### from\_spec

`@classmethod`

```python
def from_spec(cls, *args: Any, **kwargs: Any) -> AbstractCapability[Any]
```

Create from spec arguments. Default: `cls(*args, **kwargs)`.

Override when `__init__` takes non-serializable types.

###### Returns

`AbstractCapability`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### get\_ordering

```python
def get_ordering() -> CapabilityOrdering | None
```

Return ordering constraints for this capability, or `None` for default behavior.

Override to declare a fixed position (`'outermost'` / `'innermost'`), relative ordering (`wraps` / `wrapped_by` other capability types or instances), or dependency requirements (`requires`).

[`CombinedCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.CombinedCapability) uses these to topologically sort its children at construction time.

###### Returns

`CapabilityOrdering` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### for\_agent

```python
def for_agent(agent: AbstractAgent[AgentDepsT, Any]) -> AbstractCapability[AgentDepsT]
```

Return the capability instance to use with an agent.

Called after the agent's own configuration is available and before capability contributions are extracted. Constructor capabilities are bound once during agent construction; static run capabilities are bound once per run. Override this to inspect the agent and return an agent-bound copy. The default returns `self`.

A [`CapabilityFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.CapabilityFunc) result is also bound before its own [`for_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.for_run) hook. A specialized run-bound value returned by an ordinary capability's `for_run()` is not bound again.

Capabilities in the `innermost` ordering tier (see [`get_ordering`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.get_ordering)), i.e. durability capabilities, bind in a second phase, after the other capabilities' contributed toolsets have been extracted, so `agent.toolsets` is complete when their `for_agent` wraps it. The flip side is that `innermost` capabilities can't contribute toolsets of their own.

###### Returns

`AbstractCapability`\[`AgentDepsT`\]

##### for\_run

`@async`

```python
def for_run(ctx: RunContext[AgentDepsT]) -> AbstractCapability[AgentDepsT]
```

Return the capability instance to use for this agent run.

Called once per run, before `get_*()` re-extraction and before any hooks fire. Override to return a fresh instance for per-run state isolation. Under durable execution, worker processes re-derive this instance from the deserialized run context, so all per-run state must be derivable from `ctx`. Default: return `self` (shared across runs).

###### Returns

`AbstractCapability`\[`AgentDepsT`\]

##### get\_instructions

```python
def get_instructions() -> AgentInstructions[AgentDepsT] | None
```

Return instructions to include in the system prompt, or None.

Return static instruction text, a dynamic instruction callable, or a sequence containing either. For dynamic per-request behavior, return a callable that receives [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) or a `TemplateStr` -- not a dynamic string.

When [`defer_loading`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.defer_loading) is True, these instructions are resolved only after the model calls the `load_capability` tool for this capability.

###### Returns

`AgentInstructions`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_description

```python
def get_description() -> CapabilityDescription[AgentDepsT] | None
```

Return a human-readable description of this capability, or None.

Surfaced to the model in the catalog shown with the `load_capability` tool when [`defer_loading`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.defer_loading) is True.

Return a static description string or a callable that receives [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) (or no arguments) when the deferred capability catalog is rendered. Default: return the static `description` field.

###### Returns

`CapabilityDescription`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_model\_settings

```python
def get_model_settings() -> AgentModelSettings[AgentDepsT] | None
```

Return model settings to merge into the agent's defaults, or None.

Return a static `ModelSettings` dict when the settings don't change between requests. Return a callable that receives [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) when settings need to vary per step (e.g. based on `ctx.run_step` or `ctx.deps`).

When the callable is invoked, `ctx.model_settings` contains the merged result of all layers resolved before this capability (model defaults and agent-level settings). The returned dict is merged on top of that.

When [`defer_loading`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.defer_loading) is True, these settings are registered up front but merge as an empty dict until the model calls the `load_capability` tool for this capability.

###### Returns

[`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_model

```python
def get_model() -> AgentModel[AgentDepsT] | None
```

Return a static model, a per-step model selector, or `None` to make no selection.

A selector receives [`ModelSelectionContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelSelectionContext) and may be synchronous or asynchronous. Static selections are resolved once per run; selectors are evaluated before each new logical model request step. When several capabilities contribute a model, the last non-`None` selection wins. This differs from [`resolve_model_id()`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.resolve_model_id), where the first resolver to return a model wins.

See [Selecting the model](https://pydantic.dev/docs/ai/capabilities/custom/#selecting-the-model) for precedence, bootstrap, and deferred-capability semantics.

###### Returns

`AgentModel`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### resolve\_model\_id

`@async`

```python
def resolve_model_id(
    ctx: ModelResolutionContext[AgentDepsT],
    *,
    model_id: KnownModelName | str,
) -> Model | None
```

Resolve a model ID, or return `None` to defer.

Capabilities are tried in user-supplied order. When every capability returns `None`, the ID is passed to [`infer_model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.infer_model). The context provides the agent and actual run dependencies, so resolution can configure tenant-specific providers or look up models in a registry.

###### Returns

`Model` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_toolset

```python
def get_toolset() -> AgentToolset[AgentDepsT] | None
```

Return a toolset to register with the agent, or None.

###### Returns

[`AgentToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AgentToolset)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_native\_tools

```python
def get_native_tools() -> Sequence[AgentNativeTool[AgentDepsT]]
```

Return native tools to register with the agent.

###### Returns

[`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentNativeTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.AgentNativeTool)\[`AgentDepsT`\]\]

##### get\_wrapper\_toolset

```python
def get_wrapper_toolset(
    toolset: AbstractToolset[AgentDepsT],
) -> AbstractToolset[AgentDepsT] | None
```

Wrap the agent's assembled toolset, or return None to leave it unchanged.

Called per-run with the combined non-output toolset (after the [`prepare_tools`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.prepare_tools) hook has already wrapped it). Output tools are added separately and are not included.

Unlike value-contribution methods such as [`get_instructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.get_instructions), this receives the already assembled toolset and is called each run (after [`for_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.for_run)). When multiple capabilities provide wrappers, they follow middleware semantics: the first capability in the list wraps outermost (matching `wrap_*` hooks).

Use this to apply cross-cutting toolset wrappers like [`PreparedToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.PreparedToolset), [`FilteredToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.FilteredToolset), or custom [`WrapperToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.WrapperToolset) subclasses.

###### Returns

[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### prepare\_tools

`@async`

```python
def prepare_tools(
    ctx: RunContext[AgentDepsT],
    tool_defs: list[ToolDefinition],
) -> list[ToolDefinition]
```

Filter or modify function tool definitions for this step.

Receives **function** tools only. For [output tools](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.ToolOutput), override [`prepare_output_tools`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.prepare_output_tools) -- it runs separately, with `ctx.retry`/`ctx.max_retries` reflecting the **output** retry budget instead of the function-tool budget.

Return a filtered or modified list. The result flows into both the model's request parameters and `ToolManager.tools`, so filtering also blocks tool execution.

On a deferred capability this runs only once the capability is loaded, and then receives every function tool, as an always-on capability does. There is nothing to govern before that: an unloaded capability's tools are neither advertised to the model nor callable, so no filtering here could change what the model can reach.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition)\]

##### prepare\_output\_tools

`@async`

```python
def prepare_output_tools(
    ctx: RunContext[AgentDepsT],
    tool_defs: list[ToolDefinition],
) -> list[ToolDefinition]
```

Filter or modify output tool definitions for this step.

Receives only [output tools](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.ToolOutput). `ctx.retry` and `ctx.max_retries` reflect the **output** retry budget (agent-level `max_output_retries`), matching the output hook lifecycle.

Return a filtered or modified list. The result flows into both the model's request parameters and `ToolManager.tools`, so filtering also blocks tool execution.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition)\]

##### before\_run

`@async`

```python
def before_run(ctx: RunContext[AgentDepsT]) -> None
```

Called before the agent run starts. Observe-only; use `wrap_run` for modification.

A realtime session is a run. ContextVars set here are ambient in its instruction resolution, pump and tool tasks, and the caller's `async with` block.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### after\_run

`@async`

```python
def after_run(
    ctx: RunContext[AgentDepsT],
    *,
    result: AgentRunResult[Any],
) -> AgentRunResult[Any]
```

Called after the agent run produces a result. Can modify the result.

Not called when the run ends without a result (e.g. a cancellation that nothing recovered from). It IS called when a result was produced while a cancellation was pending or absorbed upstream -- but before the backstop's cancellation re-check, so the cancellation still propagates after this hook returns and the run still ends cancelled. Put cancellation-safe cleanup in [`wrap_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.wrap_run) (a `try`/`finally` around `handler()`), which does observe the `CancelledError`.

For a realtime session, the result is produced when the session closes; a transformed result becomes `session.result` before the caller leaves the `async with` boundary.

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### wrap\_run

`@async`

```python
def wrap_run(
    ctx: RunContext[AgentDepsT],
    *,
    handler: WrapRunHandler,
) -> AgentRunResult[Any]
```

Wraps the entire agent run. `handler()` executes the run.

If `handler()` raises and this method catches the exception and returns a result instead, the error is suppressed and the recovery result is used.

If this method does not call `handler()` (short-circuit), the run is skipped and the returned result is used directly.

Note: if the caller cancels the run (e.g. by breaking out of an `iter()` loop), this method receives an `asyncio.CancelledError`. Implementations that hold resources should handle cleanup accordingly. Cancellation is terminal: the hook may observe it and clean up, but cannot recover the run to success.

A realtime session is a run: `handler()` resolves when the session closes. ContextVars set before calling it are ambient in instruction resolution, pumps, tool tasks, and the caller's block. Downward ContextVar propagation is one-way; keep bidirectional per-run state on the `for_run` copy's instance attributes. Suppression and result transformation apply at the session's `async with` boundary, after the caller may have observed events in real time.

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### on\_run\_error

`@async`

```python
def on_run_error(
    ctx: RunContext[AgentDepsT],
    *,
    error: BaseException,
) -> AgentRunResult[Any]
```

Called when the agent run fails with an exception.

This is the error counterpart to [`after_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.after_run): while `after_run` is called on success, `on_run_error` is called on failure (after [`wrap_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.wrap_run) has had its chance to recover).

**Raise** the original `error` (or a different exception) to propagate it. **Return** an [`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult) to suppress the error and recover the run.

Cancellation is terminal: the hook may observe it and clean up, but cannot recover the run to success.

Not called for `GeneratorExit` or `KeyboardInterrupt`.

For a realtime session, returning a recovery result sets `session.result` and suppresses the error at the caller's `async with` boundary, after events may already have been observed.

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### before\_node\_run

`@async`

```python
def before_node_run(
    ctx: RunContext[AgentDepsT],
    *,
    node: AgentNode[AgentDepsT],
) -> AgentNode[AgentDepsT]
```

Called before each graph node executes. Can observe or replace the node.

###### Returns

`AgentNode`\[`AgentDepsT`\]

##### after\_node\_run

`@async`

```python
def after_node_run(
    ctx: RunContext[AgentDepsT],
    *,
    node: AgentNode[AgentDepsT],
    result: NodeResult[AgentDepsT],
) -> NodeResult[AgentDepsT]
```

Called after each graph node succeeds. Can modify the result (next node or `End`).

Not called for a node interrupted by cancellation -- including a cancellation the node itself absorbed and completed through, which the framework re-asserts at the node boundary: cancellation skips downstream hooks. Put cancellation-safe cleanup in [`wrap_node_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.wrap_node_run) (a `try`/`finally` around `handler()`), which does observe the `CancelledError`. (A hook that catches the `CancelledError` _and_ calls `Task.uncancel()` takes over the cancellation bookkeeping for that boundary, so this hook does fire for that node -- the run itself still ends cancelled at the next boundary.)

###### Returns

`NodeResult`\[`AgentDepsT`\]

##### wrap\_node\_run

`@async`

```python
def wrap_node_run(
    ctx: RunContext[AgentDepsT],
    *,
    node: AgentNode[AgentDepsT],
    handler: WrapNodeRunHandler[AgentDepsT],
) -> NodeResult[AgentDepsT]
```

Wraps execution of each agent graph node (run step).

Called for every node in the agent graph (`UserPromptNode`, `ModelRequestNode`, `CallToolsNode`). `handler(node)` executes the node and returns the next node (or `End`).

Override to inspect or modify nodes before execution, inspect or modify the returned next node, call `handler` multiple times (retry), or return a different node to redirect graph progression.

Note: this hook fires however the run is driven -- [`agent.run()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run), [`agent.run_stream()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run_stream), an [`agent.iter()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.iter) run advanced with [`agent_run.next()`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.next), and a bare `async for node in agent_run:` loop, which advances through `next()` too. The one exception is the final [`ModelRequestNode`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.ModelRequestNode) under `run_stream()`, which hands back the result mid-stream and so only fires `before_node_run`.

When using `agent.run()` with `event_stream_handler`, the handler wraps both streaming and graph advancement (i.e. the model call happens inside the wrapper). When using `agent.run_stream()`, the handler wraps only graph advancement -- streaming happens before the wrapper because `run_stream()` must yield the stream to the caller while the stream context is still open, which cannot happen from inside a callback.

A cancelled run delivers `asyncio.CancelledError` through `handler()`. Cancellation is terminal: the hook may observe it and clean up, but cannot recover the run to success -- even a returned `End` result is discarded once a cancellation is pending.

###### Returns

`NodeResult`\[`AgentDepsT`\]

##### on\_node\_run\_error

`@async`

```python
def on_node_run_error(
    ctx: RunContext[AgentDepsT],
    *,
    node: AgentNode[AgentDepsT],
    error: Exception,
) -> NodeResult[AgentDepsT]
```

Called when a graph node fails with an exception.

This is the error counterpart to [`after_node_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.after_node_run).

**Raise** the original `error` (or a different exception) to propagate it. **Return** a next node or `End` to recover and continue the graph.

Useful for recovering from [`UnexpectedModelBehavior`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UnexpectedModelBehavior) by redirecting to a different node (e.g. retry with different model settings).

###### Returns

`NodeResult`\[`AgentDepsT`\]

##### on\_event

`@async`

```python
def on_event(ctx: RunContext[AgentDepsT], *, event: AgentStreamEvent) -> None
```

React to every event in the run's event stream.

This includes model response stream events, tool events, deferred and enqueued-message events, [`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent)s, and [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent)s. The default implementation dispatches to methods marked with [`on_event`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.on_event), in definition order.

Override this method for fully dynamic handling. Call `super().on_event(...)` to retain marked method dispatch. A capability receives events it emits itself. Events emitted by a listener enter the stream after the event being handled.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### wrap\_run\_event\_stream

`@async`

```python
def wrap_run_event_stream(
    ctx: RunContext[AgentDepsT],
    *,
    stream: AsyncIterable[AgentStreamEvent],
) -> AsyncIterable[AgentStreamEvent]
```

Wrap a run or realtime session's consumer-facing event stream.

For classic runs, the wrapper is applied where each node's stream is produced, so it fires however the run is driven -- including under [`agent.iter()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.iter) and when the caller streams a node itself with `node.stream()`. For realtime sessions, it wraps the `async for event in session` view. A wrapper must yield events appropriate for the stream it wraps.

Transformations affect only what the stream consumer sees. They never change realtime session history, tool execution, or the classic run's accumulated response and output.

Note: when this method is overridden (or [`Hooks.on.event`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Hooks.on) / [`Hooks.on.run_event_stream`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Hooks.on) are registered), `agent.run()` and [`AgentRun.next()`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.next) automatically enable streaming mode so this hook fires even without an explicit `event_stream_handler`.

###### Returns

[`AsyncIterable`](https://docs.python.org/3/library/typing.html#typing.AsyncIterable)\[[`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent)\]

##### before\_model\_request

`@async`

```python
def before_model_request(
    ctx: RunContext[AgentDepsT],
    request_context: ModelRequestContext,
) -> ModelRequestContext
```

Called before each model request. Can modify messages, settings, and parameters.

[`model_request_parameters.instruction_parts`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestParameters.instruction_parts) is the source of truth for the instructions: rewriting them here changes what the model receives, and the request recorded in message history is re-rendered from them afterwards. Assigning to a [`ModelRequest.instructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest) in `request_context.messages` is not propagated the other way, so it does not reach the model.

###### Returns

[`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

##### after\_model\_request

`@async`

```python
def after_model_request(
    ctx: RunContext[AgentDepsT],
    *,
    request_context: ModelRequestContext,
    response: ModelResponse,
) -> ModelResponse
```

Called after each model response. Can modify the response before further processing.

Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to reject the response and ask the model to try again. The original response is still appended to message history so the model can see what it said. Retries count against the output side of the agent's retry budget.

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

##### wrap\_model\_request

`@async`

```python
def wrap_model_request(
    ctx: RunContext[AgentDepsT],
    *,
    request_context: ModelRequestContext,
    handler: WrapModelRequestHandler,
) -> ModelResponse
```

Wraps the model request. handler() calls the model.

Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to skip `on_model_request_error` and directly retry the model request with a retry prompt. If the handler was called, the model response is preserved in history for context (same as `after_model_request`).

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

##### on\_model\_request\_error

`@async`

```python
def on_model_request_error(
    ctx: RunContext[AgentDepsT],
    *,
    request_context: ModelRequestContext,
    error: Exception,
) -> ModelResponse
```

Called when a model request fails with an exception.

This is the error counterpart to [`after_model_request`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.after_model_request).

**Raise** the original `error` (or a different exception) to propagate it. **Return** a [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse) to suppress the error and use the response as if the model call succeeded. **Raise** [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to retry the model request with a retry prompt instead of recovering or propagating.

Not called for [`SkipModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.SkipModelRequest) or [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry).

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

##### before\_tool\_validate

`@async`

```python
def before_tool_validate(
    ctx: RunContext[AgentDepsT],
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: RawToolArgs,
) -> RawToolArgs
```

Modify raw args before validation.

Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to skip validation and ask the model to redo the tool call.

A tool call can only be deferred once its arguments have been validated, so raising [`CallDeferred`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.CallDeferred) or [`ApprovalRequired`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ApprovalRequired) here is a `UserError`. Defer from [`after_tool_validate`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.after_tool_validate), a tool's `args_validator`, or [`before_tool_execute`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.before_tool_execute).

###### Returns

`RawToolArgs`

##### after\_tool\_validate

`@async`

```python
def after_tool_validate(
    ctx: RunContext[AgentDepsT],
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: ValidatedToolArgs,
) -> ValidatedToolArgs
```

Modify validated args. Called only on successful validation.

Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to reject the validated args and ask the model to redo the tool call.

The arguments are valid by this point, so raising [`CallDeferred`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.CallDeferred) or [`ApprovalRequired`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ApprovalRequired) here defers the call -- the tool isn't executed, and the deferral joins the run's [`DeferredToolRequests`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolRequests) with the validated arguments.

This hook also runs when the tool's `args_validator` (or `wrap_tool_validate`) already deferred the call, so it stays a reliable gate on validated arguments: rejecting here wins over that deferral, deferring here replaces it, and the args returned here are the ones the deferred call carries.

###### Returns

`ValidatedToolArgs`

##### wrap\_tool\_validate

`@async`

```python
def wrap_tool_validate(
    ctx: RunContext[AgentDepsT],
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: RawToolArgs,
    handler: WrapToolValidateHandler,
) -> ValidatedToolArgs
```

Wraps tool argument validation. handler() runs the validation.

Deferring with [`CallDeferred`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.CallDeferred) or [`ApprovalRequired`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ApprovalRequired) is allowed _after_ `handler()` has returned, when the arguments are known to be valid; raising one before that is a `UserError`.

###### Returns

`ValidatedToolArgs`

##### on\_tool\_validate\_error

`@async`

```python
def on_tool_validate_error(
    ctx: RunContext[AgentDepsT],
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: RawToolArgs,
    error: ValidationError | ModelRetry,
) -> ValidatedToolArgs
```

Called when tool argument validation fails.

This is the error counterpart to [`after_tool_validate`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.after_tool_validate). Fires for `ValidationError` (schema mismatch) and [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) (custom validator rejection).

**Raise** the original `error` (or a different exception) to propagate it. **Return** validated args to suppress the error and continue as if validation passed.

Not called for [`SkipToolValidation`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.SkipToolValidation), or when a tool's `args_validator` raises [`CallDeferred`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.CallDeferred) or [`ApprovalRequired`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ApprovalRequired) -- those are control flow, not errors, and the call is deferred instead of executed.

Raising a deferral _from this hook_ is a `UserError`: it only runs because validation failed, so there are no valid arguments to show whoever would resolve the deferral.

###### Returns

`ValidatedToolArgs`

##### before\_tool\_execute

`@async`

```python
def before_tool_execute(
    ctx: RunContext[AgentDepsT],
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: ValidatedToolArgs,
) -> ValidatedToolArgs
```

Modify validated args before execution.

Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to skip execution and ask the model to redo the tool call.

This is the hook to defer from: raising [`ApprovalRequired`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ApprovalRequired) or [`CallDeferred`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.CallDeferred) here defers the call _before_ the tool function runs, so nothing happens until it's resolved.

###### Returns

`ValidatedToolArgs`

##### after\_tool\_execute

`@async`

```python
def after_tool_execute(
    ctx: RunContext[AgentDepsT],
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: ValidatedToolArgs,
    result: Any,
) -> Any
```

Modify result after execution.

Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to reject the tool result and ask the model to redo the tool call.

Deferring from here is accepted but rarely what you want: the tool function has already run, so its side effects happened and `result` is discarded. Defer from [`before_tool_execute`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.before_tool_execute) instead.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### wrap\_tool\_execute

`@async`

```python
def wrap_tool_execute(
    ctx: RunContext[AgentDepsT],
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: ValidatedToolArgs,
    handler: WrapToolExecuteHandler,
) -> Any
```

Wraps tool execution. handler() runs the tool.

Defer before calling `handler()`: a deferral raised after it has returned is accepted, but the tool function already ran and its result is discarded. Defer from [`before_tool_execute`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.before_tool_execute) instead.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### on\_tool\_execute\_error

`@async`

```python
def on_tool_execute_error(
    ctx: RunContext[AgentDepsT],
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: ValidatedToolArgs,
    error: Exception,
) -> Any
```

Called when tool execution fails with an exception.

This is the error counterpart to [`after_tool_execute`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.after_tool_execute).

**Raise** the original `error` (or a different exception) to propagate it. **Return** any value to suppress the error and use it as the tool result. **Raise** [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to ask the model to redo the tool call instead of recovering or propagating.

Not called for control flow exceptions ([`SkipToolExecution`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.SkipToolExecution), [`CallDeferred`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.CallDeferred), [`ApprovalRequired`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ApprovalRequired)), retry signals ([`ToolRetryError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolRetryError) from [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry)), or failure signals ([`ToolFailedError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailedError) from [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed)). Use [`wrap_tool_execute`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.wrap_tool_execute) to intercept retries or failures.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### before\_output\_validate

`@async`

```python
def before_output_validate(
    ctx: RunContext[AgentDepsT],
    *,
    output_context: OutputContext,
    output: RawOutput,
) -> RawOutput
```

Modify raw model output before validation/parsing.

The primary hook for pre-parse repair and normalization of model output. Fires only for structured output that requires parsing: prompted, native, tool, and union output. Does **not** fire for plain text or image output.

For structured text output, `output` is the raw text string from the model. For tool output, `output` is the raw tool arguments (string or dict).

Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to skip validation and ask the model to try again with a custom message.

During streaming, this hook fires on every partial validation attempt as well as the final result. Check `ctx.partial_output` to distinguish and avoid expensive work on partial results.

###### Returns

`RawOutput`

##### after\_output\_validate

`@async`

```python
def after_output_validate(
    ctx: RunContext[AgentDepsT],
    *,
    output_context: OutputContext,
    output: Any,
) -> Any
```

Modify validated output after successful parsing. Called only on success.

`output` is the **semantic value** the model was asked to produce -- e.g., a `MyModel` instance for `output_type=MyModel`, or `42` for `output_type=int`, or the input to a single-arg output function. For multi-arg output functions, this is the `dict` of arguments (the genuine multi-value input).

Note: this differs from _tool_ hooks (`after_tool_validate`), which always see `dict[str, Any]` -- tool args follow the schema contract. Output hooks see the semantic output value, regardless of how it's internally represented during validation.

Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to reject the validated output and ask the model to try again.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### wrap\_output\_validate

`@async`

```python
def wrap_output_validate(
    ctx: RunContext[AgentDepsT],
    *,
    output_context: OutputContext,
    output: RawOutput,
    handler: WrapOutputValidateHandler,
) -> Any
```

Wraps output validation. handler(output) performs the validation.

[`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) from within the handler goes to [`on_output_validate_error`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.on_output_validate_error). `ModelRetry` raised directly (not from the handler) bypasses the error hook.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### on\_output\_validate\_error

`@async`

```python
def on_output_validate_error(
    ctx: RunContext[AgentDepsT],
    *,
    output_context: OutputContext,
    output: RawOutput,
    error: ValidationError | ModelRetry,
) -> Any
```

Called when output validation fails.

This is the error counterpart to [`after_output_validate`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.after_output_validate).

**Raise** the original `error` (or a different exception) to propagate it. **Return** validated output to suppress the error and continue.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### before\_output\_process

`@async`

```python
def before_output_process(
    ctx: RunContext[AgentDepsT],
    *,
    output_context: OutputContext,
    output: Any,
) -> Any
```

Modify validated output before processing (extraction, output function call).

`output` is the **semantic value** -- e.g., a `MyModel` instance or `42`, matching `after_output_validate`. For multi-arg output functions, it's the `dict` of args. See [`after_output_validate`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.after_output_validate) for a full explanation of the semantic-value contract.

Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to skip processing and ask the model to try again.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### after\_output\_process

`@async`

```python
def after_output_process(
    ctx: RunContext[AgentDepsT],
    *,
    output_context: OutputContext,
    output: Any,
) -> Any
```

Modify result after output processing.

Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to reject the result and ask the model to try again.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### wrap\_output\_process

`@async`

```python
def wrap_output_process(
    ctx: RunContext[AgentDepsT],
    *,
    output_context: OutputContext,
    output: Any,
    handler: WrapOutputProcessHandler,
) -> Any
```

Wraps output processing. handler(output) runs extraction + output function call.

[`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) bypasses [`on_output_process_error`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.on_output_process_error) (treated as control flow, not an error).

During streaming, this fires only when partial validation succeeds, and on the final result. Check `ctx.partial_output` to skip expensive work on partial results.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### on\_output\_process\_error

`@async`

```python
def on_output_process_error(
    ctx: RunContext[AgentDepsT],
    *,
    output_context: OutputContext,
    output: Any,
    error: Exception,
) -> Any
```

Called when output processing fails with an exception.

This is the error counterpart to [`after_output_process`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.after_output_process).

**Raise** the original `error` (or a different exception) to propagate it. **Return** any value to suppress the error and use it as the output.

Not called for retry signals ([`ToolRetryError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolRetryError) from [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry)).

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### handle\_deferred\_tool\_calls

`@async`

```python
def handle_deferred_tool_calls(
    ctx: RunContext[AgentDepsT],
    *,
    requests: DeferredToolRequests,
) -> DeferredToolResults | None
```

Handle deferred tool calls (approval-required or externally-executed) inline during an agent run.

Called by `ToolManager` when:

-   a tool raises [`ApprovalRequired`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ApprovalRequired) or [`CallDeferred`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.CallDeferred) during execution, or
-   the model calls a tool registered with `requires_approval=True` (see [Human-in-the-Loop Tool Approval](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval)) or a tool backed by [external execution](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#external-tool-execution).

Uses accumulation dispatch: each capability in the chain receives remaining unresolved requests and can resolve some or all of them. Results are merged and unresolved calls are passed to the next capability.

**Return** a [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) to resolve some or all calls. **Return** `None` to leave all calls unresolved.

###### Returns

[`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### prefix\_tools

```python
def prefix_tools(prefix: str) -> PrefixTools[AgentDepsT]
```

Returns a new capability that wraps this one and prefixes its tool names.

Only this capability's tools are prefixed; other agent tools are unaffected.

###### Returns

`PrefixTools`\[`AgentDepsT`\]

### OutputContext

Context about the output being processed, passed to output hooks.

#### Attributes

##### mode

The schema's output mode ('text', 'native', 'prompted', 'tool', 'image', 'auto').

This reflects the configured schema, not the format of this particular response. For example, a `ToolOutputSchema` with a `text_processor` (hybrid mode) reports `'tool'` even if the model returned text -- check [`tool_call`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.OutputContext.tool_call) to distinguish.

**Type:** `OutputMode`

##### output\_type

The resolved output type (e.g. MyModel, str). For output functions, the function's input type (what the model produces).

**Type:** [`type`](https://docs.python.org/3/glossary.html#term-type)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### object\_def

The output object definition (schema, name, description), if structured output.

**Type:** `OutputObjectDefinition` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### has\_function

Whether there's an output function to call in the execute step.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### function\_name

Name of the output function that will run, when known. `None` for union processors that dispatch by output subtype, or when the schema has no function.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_call

The tool call part, for tool-based output. `None` when the current output did not arrive via a tool call (text or image).

**Type:** [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_def

The tool definition, for tool-based output. `None` when the current output did not arrive via a tool call.

**Type:** [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### allows\_text

Whether the schema accepts text output (including via a `text_processor` on a `ToolOutputSchema`).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### allows\_image

Whether the schema accepts image output.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### allows\_deferred\_tools

Whether the schema accepts deferred tool requests as output.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

### Hooks

**Bases:** `AbstractCapability[AgentDepsT]`

Register hook functions via decorators or constructor kwargs.

For extension developers building reusable capabilities, subclass [`AbstractCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability) directly. For application code that needs a few hooks without the ceremony of a subclass, use `Hooks`.

Example using decorators:

```python
hooks = Hooks()

@hooks.on.before_model_request
async def log_request(ctx, request_context):
    print(f'Request: {request_context}')
    return request_context

agent = Agent('openai:gpt-5', capabilities=[hooks])
```

Example using constructor kwargs:

```python
agent = Agent('openai:gpt-5', capabilities=[
    Hooks(before_model_request=log_request)
])
```

#### Attributes

##### on

Decorator namespace for registering hook functions.

**Type:** `_HookRegistration`\[`AgentDepsT`\]

### on\_event

```python
def on_event(
    func: _EventMethod[CapabilityT, AgentStreamEvent],
    /,
) -> _OnEventMethod[CapabilityT, AgentStreamEvent]
def on_event(
    *event_types: type[EventT],
) -> Callable[[_EventMethod[CapabilityT, EventT]], _OnEventMethod[CapabilityT, EventT]]
```

Mark an async capability method as an event listener.

Pass event classes to filter with `isinstance`, or use the decorator bare to receive every [`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent).

Naming the classes is also what lets dispatch skip the capability entirely for events it doesn't listen to, so prefer it over a bare marker when you know the types.

#### Returns

`_OnEventMethod`\[`CapabilityT`, [`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent)\] | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`_EventMethod`\[`CapabilityT`, `EventT`\]\], `_OnEventMethod`\[`CapabilityT`, `EventT`\]\]

### ModelIdResolver

A sync or async model ID resolver.

**Default:** `Callable[[ModelResolutionContext[AgentDepsT], str], Model | None] | Callable[[ModelResolutionContext[AgentDepsT], str], Awaitable[Model | None]]`

### CapabilityFunc

A sync/async function which takes a run context and returns a capability.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[RunContext[AgentDepsT]], AbstractCapability[AgentDepsT] | None | Awaitable[AbstractCapability[AgentDepsT] | None]]`

### HistoryProcessor

A function that processes a list of model messages and returns a list of model messages.

Can optionally accept a `RunContext` as a parameter.

**Default:** `_HistoryProcessorSync | _HistoryProcessorAsync | _HistoryProcessorSyncWithCtx[DepsT] | _HistoryProcessorAsyncWithCtx[DepsT]`

### ToolSearchNativeStrategy

Named provider-native tool search strategy.

`'bm25'` and `'regex'` correspond to Anthropic's server-side tool search variants. OpenAI's Responses API does not expose distinct named native strategies, so these values are rejected by the OpenAI adapter.

**Default:** `Literal['bm25', 'regex']`

### ToolSearchLocalStrategy

Named local tool search strategy.

`'keywords'` opts into the built-in keyword-overlap algorithm explicitly -- use this to lock in the current local algorithm rather than the `None` default (which lets Pydantic AI pick the best algorithm per provider and may change over time).

Future local strategies (e.g. local BM25, TF-IDF, regex) will join this Literal as they're added; the single-member shape today is forward-compat scaffolding.

**Default:** `Literal['keywords']`

### AgentNode

Type alias for an agent graph node (`UserPromptNode`, `ModelRequestNode`, `CallToolsNode`).

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `'_agent_graph.AgentNode[AgentDepsT, Any]'`

### ToolSearchFunc

Custom search function for [`ToolSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ToolSearch)'s `strategy` field.

Takes the run context, the list of search queries, and the deferred tool definitions, and returns the matching tool names ordered by relevance. Both sync and async implementations are accepted.

Usage `ToolSearchFunc[AgentDepsT]`.

**Default:** `Callable[[RunContext[AgentDepsT], Sequence[str], Sequence['ToolDefinition']], Sequence[str] | Awaitable[Sequence[str]]]`

### AgentCapability

A capability or a [`CapabilityFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.CapabilityFunc) that takes a run context and returns one.

Use as the item type for `Agent(capabilities=[...])` and `agent.run(capabilities=[...])`. Functions are wrapped in a [`DynamicCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.DynamicCapability) automatically.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `AbstractCapability[AgentDepsT] | CapabilityFunc[AgentDepsT]`

### NodeResult

Type alias for the result of executing an agent graph node: either the next node or `End`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `'_agent_graph.AgentNode[AgentDepsT, Any] | End[FinalResult[Any]]'`

### WrapRunHandler

Handler type for [`wrap_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.wrap_run).

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `'Callable[[], Awaitable[AgentRunResult[Any]]]'`

### WrapNodeRunHandler

Handler type for [`wrap_node_run`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.wrap_node_run).

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `'Callable[[_agent_graph.AgentNode[AgentDepsT, Any]], Awaitable[_agent_graph.AgentNode[AgentDepsT, Any] | End[FinalResult[Any]]]]'`

### CAPABILITY\_TYPES

Registry of all capability types that have a serialization name, mapping name to class.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractCapability`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]\] **Default:** `{name: cls for cls in (NativeTool, RaiseContentFilterError, ImageGeneration, IncludeToolReturnSchemas, Instrumentation, MCP, PrefixTools, PrepareTools, ProcessHistory, ReinjectSystemPrompt, SetToolMetadata, Thinking, ToolSearch, Toolset, WebFetch, WebSearch, XSearch) if (name := (cls.get_serialization_name())) is not None}`

### WrapModelRequestHandler

Handler type for [`wrap_model_request`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.wrap_model_request).

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `'Callable[[ModelRequestContext], Awaitable[ModelResponse]]'`

### ToolSearchStrategy

Strategy value accepted by [`ToolSearch.strategy`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ToolSearch.strategy).

-   `'keywords'`: force the local keyword-overlap algorithm regardless of provider.
-   `'bm25'` / `'regex'`: force a specific provider-native strategy (Anthropic). The request fails on providers that can't honor the choice.
-   Callable `(ctx, queries, tools) -> names`: custom search function. Used locally, and also by the native "client-executed" surface on providers that support it (Anthropic custom tool-reference blocks, OpenAI `ToolSearchToolParam(execution='client')`).

`None` is not part of the union -- it's accepted as the default on the [`ToolSearch.strategy`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ToolSearch.strategy) field and means "let Pydantic AI pick"; see that field's docstring for details.

**Default:** `Union[ToolSearchFunc[AgentDepsT], ToolSearchLocalStrategy, ToolSearchNativeStrategy]`

### ModelSelection

A concrete model selection, before model ID resolution.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `'Model | KnownModelName | str'`

### ModelSelector

A sync or async per-step model selector.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `'Callable[[ModelSelectionContext[AgentDepsT]], ModelSelection | Awaitable[ModelSelection]]'`

### AgentModel

A static model selection or a callable evaluated for every request step.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `'ModelSelection | ModelSelector[AgentDepsT]'`

### RawToolArgs

Type alias for raw (pre-validation) tool arguments.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `str | dict[str, Any]`

### ValidatedToolArgs

Type alias for validated tool arguments.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `dict[str, Any]`

### WrapToolValidateHandler

Handler type for [`wrap_tool_validate`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.wrap_tool_validate).

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[RawToolArgs], Awaitable[ValidatedToolArgs]]`

### WrapToolExecuteHandler

Handler type for [`wrap_tool_execute`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.wrap_tool_execute).

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[ValidatedToolArgs], Awaitable[Any]]`

### RawOutput

Type alias for raw output data (text or tool args).

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `str | dict[str, Any]`

### WrapOutputValidateHandler

Handler type for wrap\_output\_validate.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[RawOutput], Awaitable[Any]]`

### WrapOutputProcessHandler

Handler type for wrap\_output\_process.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[Any], Awaitable[Any]]`

### CapabilityPosition

Position tier for a capability in the middleware chain.

-   `'outermost'`: in the outermost tier, before all non-outermost capabilities. Multiple capabilities can declare `'outermost'`; original list order breaks ties within the tier, and `wraps`/`wrapped_by` edges refine order further.
-   `'innermost'`: in the innermost tier, after all non-innermost capabilities. Same tie-breaking rules apply.

**Default:** `Literal['outermost', 'innermost']`

### CapabilityRef

Reference to a capability -- either a type (matches all instances of that type) or a specific instance (matches by identity).

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `'type[AbstractCapability[Any]] | AbstractCapability[Any]'`

### CapabilityDescription

Capability description: a static string, or a function (sync/async, with or without [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)) that returns one.

For dynamic descriptions, return a callable from [`get_description`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.get_description) rather than having the method itself take `RunContext`.

**Default:** `str | SystemPromptFunc[AgentDepsT]`

---
