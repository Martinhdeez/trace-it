# [pydantic_ai.tools](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/)

# pydantic\_ai.tools

### DeferredToolRequests

Tool calls that require approval or external execution.

This can be used as an agent's `output_type` and will be used as the output of the agent run if the model called any deferred tools.

Results can be passed to the next agent run using a [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) object with the same tool call IDs.

See [deferred tools docs](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#deferred-tools) for more information.

#### Attributes

##### calls

Tool calls that require external execution.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart)\] **Default:** `field(default_factory=(list[ToolCallPart]))`

##### approvals

Tool calls that require human-in-the-loop approval.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart)\] **Default:** `field(default_factory=(list[ToolCallPart]))`

##### metadata

Metadata for deferred tool calls, keyed by `tool_call_id`.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] **Default:** `field(default_factory=(dict[str, dict[str, Any]]))`

#### Methods

##### build\_results

```python
def build_results(
    *,
    approvals: dict[str, bool | DeferredToolApprovalResult] | None = None,
    calls: dict[str, DeferredToolCallResult | Any] | None = None,
    metadata: dict[str, dict[str, Any]] | None = None,
    approve_all: bool = False,
) -> DeferredToolResults
```

Create a [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) for these requests.

###### Returns

[`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults)

###### Parameters

**`approvals`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | `DeferredToolApprovalResult`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Results for tool calls that required approval. Keys must match `tool_call_id`s in `self.approvals`.

**`calls`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `DeferredToolCallResult` | [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Results for tool calls that required external execution. Keys must match `tool_call_id`s in `self.calls`.

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Per-call metadata, keyed by `tool_call_id`.

**`approve_all`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

If `True`, every approval-requesting call not already listed in `approvals` is approved (with default `ToolApproved()`).

###### Raises

-   `ValueError` -- If a key in `approvals`/`calls` doesn't match a pending request of the appropriate kind.

##### remaining

```python
def remaining(results: DeferredToolResults) -> DeferredToolRequests | None
```

Return unresolved requests after applying results, or `None` if all resolved.

###### Returns

[`DeferredToolRequests`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolRequests) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### ToolApproved

Indicates that a tool call has been approved and that the tool function should be executed.

#### Attributes

##### override\_args

Optional tool call arguments to use instead of the original arguments.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### ToolDenied

Indicates that a tool call has been denied and that a denial message should be returned to the model.

#### Attributes

##### message

The message to return to the model.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'The tool call was denied.'`

### RunContext

**Bases:** `Generic[RunContextAgentDepsT]`

Information about the current call.

#### Attributes

##### deps

Dependencies for the agent.

**Type:** `RunContextAgentDepsT`

##### model

The active model, which is a `RealtimeModel` during a realtime session.

**Type:** [`AbstractModel`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.AbstractModel)

##### usage

LLM usage associated with the run.

**Type:** [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage)

##### usage\_limits

The [`UsageLimits`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.UsageLimits) enforced for this run.

During a run this is always set: if no limits were passed, the run enforces the default [`UsageLimits()`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.UsageLimits) (e.g. `request_limit=50`). It is only `None` on a bare/synthetic `RunContext` that isn't backed by a run.

This reflects the limits the run is already enforcing, so tools and capabilities can disclose or adapt to the run's budget (e.g. a budget-disclosure capability) without having to be configured with a duplicate copy. Combine it with [`usage`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.usage) to compute how much budget remains. Treat it as read-only: it is the live object the run enforces against, so mutating a field here _would_ change what the run enforces on subsequent requests.

**Type:** [`UsageLimits`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.UsageLimits) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### agent

The agent running this context, or `None` if not set.

**Type:** [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent)\[`RunContextAgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, repr=False)`

##### prompt

The original user prompt passed to the run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### messages

Messages exchanged in the conversation so far.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\] **Default:** `field(default_factory=(list[_messages.ModelMessage]))`

##### validation\_context

Pydantic [validation context](https://docs.pydantic.dev/latest/concepts/validators/#validation-context) for tool args and run outputs.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) **Default:** `None`

##### tracer

The tracer to use for tracing the run.

**Type:** `Tracer` **Default:** `field(default_factory=NoOpTracer)`

##### trace\_include\_content

Whether to include the content of the messages in the trace.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### instrumentation\_version

Instrumentation settings version, if instrumentation is enabled.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `DEFAULT_INSTRUMENTATION_VERSION`

##### retries

Number of retries for each tool so far.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`int`](https://docs.python.org/3/builtins/functions.html#int)\] **Default:** `field(default_factory=(dict[str, int]))`

##### tool\_call\_id

The ID of the tool call.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_name

Name of the tool being called.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### retry

Number of retries so far.

For tool calls, this is the number of retries of the specific tool. For output validation, this is the number of output validation retries.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### max\_retries

The maximum number of retries allowed.

For tool calls, this is the maximum retries for the specific tool. For output validation, this is the maximum output validation retries.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### run\_step

The current step in the run.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### tool\_call\_approved

Whether a tool call that required approval has now been approved.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### tool\_call\_metadata

Metadata from `DeferredToolResults.metadata[tool_call_id]`, available when `tool_call_approved=True`.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) **Default:** `None`

##### partial\_output

Whether the output passed to an output validator is partial.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### run\_id

"Unique identifier for the agent run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### conversation\_id

Unique identifier for the conversation this run belongs to.

A conversation spans potentially multiple agent runs that share message history. Resolved at the start of `Agent.run` (etc.) from the explicit `conversation_id` argument, the most recent `conversation_id` on `message_history`, or a fresh UUID7.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### metadata

Metadata associated with this agent run, if configured.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### model\_settings

The resolved model settings for the current run step.

Populated before each model request, after all model settings layers (model defaults, agent-level, capability, and run-level) have been merged. Available in model request hooks (`before_model_request`, `wrap_model_request`, `after_model_request`). Currently `None` in tool hooks, output validators, and during agent construction.

During a realtime session this holds the merged [`RealtimeModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings) the session was opened with, for the whole session (realtime settings are fixed at connect time).

**Type:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | `RealtimeModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### pending\_messages

Queue read and mutated by the internal `PendingMessageDrainCapability`.

Set to the run's live queue during an agent run; `None` in synthetic contexts that aren't backed by a running agent (e.g. the `RunContext` built by `Agent.system_prompt_parts`), where [`enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue) would have nowhere to drain to and so raises. Managed by the framework: read it if useful, but use [`enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue) to add messages rather than mutating it directly.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`PendingMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, repr=False)`

##### tool\_manager

The tool manager for the current run step.

Provides access to tool validation and execution, including tracing and capability hooks. Useful for toolsets that need to dispatch tool calls programmatically (e.g. code execution sandboxes).

Not available in `TemporalRunContext` -- it is not serializable across Temporal activity boundaries.

**Type:** `ToolManager`\[`RunContextAgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### realtime\_session

The [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) this run is, once it is connected.

`None` in classic runs, and during the parts of a realtime run that precede the connection: `before_run`, `wrap_run` before `handler()` starts the session, and instruction resolution. Use [`realtime`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.realtime) to detect a realtime run in those stages. Tools and hooks that run during the live session can use it to e.g. [`interrupt()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.interrupt) playback or [`send()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send) follow-up content, or call [`close()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.close) to hang up.

**Type:** `RealtimeSession` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, repr=False)`

##### root\_capability

The effective root capability for this run.

Reflects the merged capability chain (agent-level + per-run extras) that is driving model requests, hooks, and toolsets for the current run. Capability implementations can use this to validate per-run additions (e.g. detect runtime-added capabilities that require worker registration).

Not part of the Temporal activity-boundary serialization (capabilities don't round-trip), but populated on the activity side from the bound agent's `root_capability`.

**Type:** `AbstractCapability`\[`RunContextAgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### capabilities

All capabilities registered for the current run, including deferred ones.

A capability that declares an `id` is keyed by it. One that does not is keyed by a synthetic handle the framework mints for this run -- `'<thinking:4f3a9c>'` -- which is not an `id`, is not the same from one run to the next, and must not be written down anywhere. Match on the values instead, or give the capability an explicit `id`; a capability that needs a stable name across runs (any `defer_loading=True` one) is already required to have one.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `AbstractCapability`\[`RunContextAgentDepsT`\]\] **Default:** `field(default_factory=(lambda: {}))`

##### loaded\_capability\_ids

IDs of the deferred capabilities the model has explicitly loaded via the `load_capability` tool.

The capability-side mirror of `discovered_tool_names`: the runtime-revealed subset. Derived from message history (`parse_loaded_capabilities`) before each request, so a capability loaded during a step appears from the _next_ one -- the same step that first carries its instructions to the model, and therefore the first on which its tools can be called. Use `active_capability_ids` for the full set of currently-active capabilities (auto/always-on plus these). Managed by the framework: safe to read, but don't mutate it directly.

**Type:** [`set`](https://docs.python.org/3/reference/expressions.html#set)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(set[str]))`

##### capability\_active

Whether the capability whose hook or callback is currently running is active right now.

_Active_, not _available_ and not _loaded_: see [`active_capability_ids`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.active_capability_ids) for why capabilities use "active" while tools use "available".

An always-on capability is active for the whole run, so this reads `True` inside its hooks although nothing ever loaded it. A deferred capability has to be loaded before it becomes active, and its hooks are skipped until then -- so it reads `True` there too. What it answers is "may this capability act now?", not "was it selected?"; for the latter, look an id up in [`loaded_capability_ids`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.loaded_capability_ids).

This is `None` outside capability dispatch, where there is no current capability.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### discovered\_tool\_names

Names of deferred function tools named by durable message history.

Raw evidence, not a verdict: it collects every name tool-search returns and `ToolAvailabilityDeltaPart`s mention -- including deltas from any tool's `ToolReturn.tools` and from `load_capability` -- without checking that the tool still exists or that its owner is loaded. Read by `is_tool_available` and the reveal builders, which apply those checks. Populated during run preparation from message history. Use `available_tool_names` for the full set of currently-callable tools (always-visible plus these). Managed by the framework: safe to read, but don't mutate it directly.

**Type:** [`set`](https://docs.python.org/3/reference/expressions.html#set)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(set[str]))`

##### model\_id

The identifier from which the run's active `model` was resolved.

This is `None` when the model was passed as an instance instead of being resolved from an identifier. The property is read-only; Pydantic AI manages the selection token internally.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### capability\_loaded

Whether the capability whose hook or callback is currently running is active right now.

Deprecated: use [`capability_active`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.capability_active). This never meant "loaded" -- it is `True` for an always-on capability nothing ever loaded.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### realtime

Whether this run is a realtime session, i.e. `model` is the connected `RealtimeModel`.

Reliable from `before_run` through session close, including instruction resolution -- unlike [`realtime_session`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.realtime_session), which is only set once the session is connected. The class is looked up through `sys.modules` rather than imported: if the realtime package was never imported, no realtime model can exist, and a classic run should not pay for (or cycle into) that import.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### last\_attempt

Whether this is the last attempt at running this tool before an error is raised.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### context\_window\_used

Fraction of the model's context window occupied as of the most recent model response.

Computed as the latest response's reported `total_tokens` (input, including cached tokens, plus output) over the active model's [`context_window`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.AbstractModel.context_window). This estimates how full the next request may be; history processing and newly added content can change its actual size, and the value can exceed `1.0` when the last response came from a model with a larger window. Useful to trigger history compaction, e.g. in a [history processor](https://pydantic.dev/docs/ai/message-history#processing-message-history).

Returns `None` -- never a misleading `0.0` -- when the ratio cannot be calculated: when the context window, usage, or message history is unavailable, or before the first model response. A [`FallbackModel`](https://pydantic.dev/docs/ai/api/models/fallback/#pydantic_ai.models.fallback.FallbackModel) measures against the smallest of its candidates' windows.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### active\_capability\_ids

IDs of the capabilities whose contributions are live to the model right now.

_Active_, deliberately not _available_: a capability is not something the model calls, so "available" would read as "offered in the catalog, there for the loading" -- which is the opposite set, the deferred ones that are **not** yet contributing. Active means the capability's instructions, tools, settings and hooks are in force on this step: non-deferred capabilities (`defer_loading` not `True`) plus the deferred ones the model has loaded, so `active_capability_ids - loaded_capability_ids` is the auto/always-on subset.

Tools keep the word _available_ because for them there is only one question -- may the model call this now? -- and no catalog sense to collide with. So `is_tool_available` reads "revealed, and its owning capability is active".

Two axes, deliberately not mixed. _Configuration_ is set once by the author: a capability is either **deferred** (`defer_loading=True`) or **always-on**. _Runtime_ is derived per step: **loaded** records what the model asked for, **active** what is in force. So "always-on" is the antonym of "deferred", never of "active" -- an always-on capability is always active, and a deferred one becomes active once loaded.

Distinct from `capabilities`, the full registry (including deferred ones not yet loaded). See `loaded_capability_ids` for the subset the model explicitly loaded.

Reliable from `before_run` onwards: the `capabilities` registry is seeded once at run start, and `loaded_capability_ids` is refreshed from history before each model request, so the loaded subset grows across steps as the model loads capabilities. Because it grows step by step, where you read it in the [hook order](https://pydantic.dev/docs/ai/core-concepts/hooks/#hook-ordering) determines what you see -- e.g. a capability loaded during one step is not reflected until the next step's hooks.

**Type:** [`set`](https://docs.python.org/3/reference/expressions.html#set)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### available\_capability\_ids

IDs of the capabilities whose contributions are live to the model right now.

Deprecated: use [`active_capability_ids`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.active_capability_ids).

**Type:** [`set`](https://docs.python.org/3/reference/expressions.html#set)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### available\_tool\_names

Names of function tools the model can call on the current turn.

The visible subset of [`tools`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.tools): always-visible tools, tools revealed via [tool search](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#tool-search), and tools owned by loaded deferred capabilities.

Only fully populated once the turn's tools have been resolved during model-request preparation, so it is reliable in model-request hooks (`before_model_request`, `wrap_model_request`, `after_model_request`) and tool hooks. In earlier hooks like `before_run` it falls back to `discovered_tool_names` (reconstructed from history). See [hook ordering](https://pydantic.dev/docs/ai/core-concepts/hooks/#hook-ordering) for how timing affects what you see.

**Type:** [`set`](https://docs.python.org/3/reference/expressions.html#set)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### tools

All tool definitions present this turn, keyed by name (includes still-deferred ones). Index `available_tool_names` into this for the callable subset.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition)\]

#### Methods

##### is\_tool\_available

```python
def is_tool_available(tool: str | ToolDefinition) -> bool
```

Whether a function tool is currently available to the model.

Pass a [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) when checking a definition held by a toolset, especially inside `get_tools`. This form evaluates the definition's own fields against the reveal state recorded in history, so it remains reliable when a wrapping toolset has removed the definition from the resolved tool set.

Pass a tool name where [`tools`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.tools) is reliable, such as model-request hooks or ordinary tool execution. The name form looks up the current definition in `tools`; when live tool state is unavailable (including inside a Temporal activity), it falls back to `available_tool_names`. An unknown name returns `False`. See [`available_tool_names`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.available_tool_names) for the timing caveat, and [`ModelRequestParameters.revealed_tool_names`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestParameters.revealed_tool_names) for the reveal state sent through the model-request pipeline.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### emit

`@async`

```python
def emit(event: CustomEventT, /) -> CustomEventT
def emit(event: CapabilityEventT, /) -> CapabilityEventT
```

Emit a custom or capability event into the current run's event stream.

Application code emits an instance of an application-defined [`CustomEvent` subclass](https://pydantic.dev/docs/ai/core-concepts/agent/#custom-events) with typed payload fields. Capability hooks and capability-contributed tools instead emit a typed [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent).

This method must be awaited, so it's available from async tools, capability hooks, history processors, and async output validators. Sync tools cannot emit events; write async tools instead. It's async rather than sync like [`enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue) because immediate dispatch (below) awaits listeners before returning, and because widening a sync signature to async later would break every caller. The event reaches the run's `event_stream_handler`, [`Agent.run_stream_events`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run_stream_events), [`Agent.iter`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.iter) streaming, and the UI adapters.

When emitted from within a tool call and the event doesn't already set a [`tool_call_id`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent.tool_call_id), the current [`tool_call_id`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.tool_call_id) and [`tool_name`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.tool_name) are stamped on the event in place so consumers can attribute it to the originating tool call.

By default, capability and application listeners run when the event's stream position is consumed, and this method returns without awaiting them. For tool-execution emissions this happens before the next model request. An event emitted during `before_model_request` may reach listeners only after that request begins, with the same as-soon-as-possible timing as [`RunContext.enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue). That is a statement about _when_ listeners run, not about order: every consumer sees events in emission order either way.

A [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent) class declared with `dispatch='immediate'` changes one thing -- listeners are awaited before this method returns, so the emitter can read decision fields they set (this is what makes a cancelable event possible). Everything else is the same: the event still takes the stream position it would have taken, the same listeners run in the same order, and it is delivered exactly once. What stream consumers gain is that they never observe such an event mid-decision -- the stream waits for its listeners to settle before yielding it, so the values they read are final.

###### Returns

`_messages.CustomEvent` | `_messages.CapabilityEvent` -- The same event instance, with any attribution fields stamped. For an immediately dispatched `_messages.CustomEvent` | `_messages.CapabilityEvent` -- decision event, both the return value and the passed reference reflect listener decisions.

###### Parameters

**`event`** : `_messages.CustomEvent` | `_messages.CapabilityEvent`

The [`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent) or [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent) to emit.

###### Raises

-   `UserError` -- If this `RunContext` isn't backed by a running agent's event stream, or the event family doesn't belong to the current emitter.

##### enqueue

```python
def enqueue(
    *content: EnqueueContent,
    priority: PendingMessagePriority = 'asap',
) -> str | None
```

Enqueue content to be injected into the conversation.

Safe to call from anywhere a `RunContext` is available -- async tools, sync tools (auto-wrapped in a thread executor by Pydantic AI), and capability hooks. The drain only iterates the queue between graph nodes (in `before_model_request` and `after_node_run`), never concurrently with the tool body, so `list.append` from a worker thread doesn't race the drain.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- The `enqueue_id` of the queued message, echoed on the [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- [`EnqueuedMessagesEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.EnqueuedMessagesEvent) emitted when it's [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- delivered, or `None` when there was nothing to enqueue (an empty call).

###### Parameters

**`*content`** : `EnqueueContent` _Default:_ `()`

One or more [`EnqueueContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.EnqueueContent) items. Adjacent [`UserContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserContent) (a `str` or multi-modal content like an [`ImageUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ImageUrl)) is gathered into one [`UserPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserPromptPart), and each [`ModelRequestPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequestPart) (e.g. a [`SystemPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SystemPromptPart)) is coalesced with adjacent part-style items into one [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest); a complete [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest) or [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse) is kept as its own message. The assembled sequence must end in a request. Calling with no positional args is a no-op.

**`priority`** : `PendingMessagePriority` _Default:_ `'asap'`

When to deliver: `'asap'` (default) -- at the earliest opportunity (next model request, or a redirect if the agent would otherwise end). In a realtime session, an active assistant response is allowed to finish before the content is sent; otherwise it is sent immediately. `'when_idle'` -- only when the agent would otherwise end, after `'asap'` messages. In a realtime session, this means after the next response completes. Either way the model gets a turn on the delivered content, a `SystemPromptPart` included: it marks provenance, not silence.

###### Raises

-   `UserError` -- If this `RunContext` isn't backed by a running agent's queue (e.g. the synthetic context from `Agent.system_prompt_parts`), since there'd be nowhere to deliver the message.

##### cancel

```python
def cancel() -> None
```

Cancel the agent run this context belongs to.

Safe to call from anywhere a `RunContext` is available -- tools, `event_stream_handler`s, and capability hooks. This _requests_ cancellation: it returns normally, and the calling code keeps running until its next `await`, where the cancellation is delivered -- so the caller can still do cleanup, but its return value (e.g. a tool's result) is discarded. The run then stops what it is doing (the in-flight model request is torn down, sibling tool tasks are cancelled and drained, a suspended server-side job is best-effort cancelled) and ends with [`RunCancelled`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled), preserving everything that completed before the cancellation took effect in message history. Idempotent; a no-op once the run has finished. Cancellation is terminal: capability hooks may observe it and clean up, but cannot recover the run to success. Cancellation cannot forcibly stop synchronous code running in a worker thread; it may continue and perform side effects, although its result is discarded.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Raises

-   `UserError` -- If this `RunContext` isn't backed by a running agent (e.g. the synthetic context from `Agent.system_prompt_parts`, or across a durable-execution serialization boundary such as a Temporal activity).

### DeferredToolResults

Results for deferred tool calls from a previous run that required approval or external execution.

The tool call IDs need to match those from the [`DeferredToolRequests`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolRequests) output object from the previous run.

See [deferred tools docs](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#deferred-tools) for more information.

#### Attributes

##### calls

Map of tool call IDs to results for tool calls that required external execution.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `DeferredToolCallResult` | [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] **Default:** `field(default_factory=(dict[str, DeferredToolCallResult | Any]))`

##### approvals

Map of tool call IDs to results for tool calls that required human-in-the-loop approval.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `StrictBool` | `DeferredToolApprovalResult`\] **Default:** `field(default_factory=(dict[str, StrictBool | DeferredToolApprovalResult]))`

##### metadata

Metadata for deferred tool calls, keyed by `tool_call_id`. Each value will be available in the tool's RunContext as `tool_call_metadata`.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] **Default:** `field(default_factory=(dict[str, dict[str, Any]]))`

#### Methods

##### update

```python
def update(other: DeferredToolResults) -> None
```

Update this `DeferredToolResults` with entries from another, in-place.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### to\_tool\_call\_results

```python
def to_tool_call_results() -> dict[str, DeferredToolResult]
```

Convert results into the internal per-call format used by the tool-execution pipeline.

Normalizes `True`/`False` approvals to `ToolApproved`/`ToolDenied`, and wraps plain external-call values in `ToolReturn`.

###### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `DeferredToolResult`\]

### Tool

**Bases:** `Generic[ToolAgentDepsT]`

A tool function for an agent.

#### Attributes

##### function\_schema

The base JSON schema for the tool's parameters.

This schema may be modified by the `prepare` function or by the Model class prior to including it in an API request.

**Type:** `_function_schema.FunctionSchema` **Default:** `function_schema or _function_schema.function_schema(function, schema_generator, tool_name=(self.name), takes_ctx=takes_ctx, docstring_format=docstring_format, require_parameter_descriptions=require_parameter_descriptions)`

#### Methods

##### \_\_init\_\_

```python
def __init__(
    function: ToolFuncEither[ToolAgentDepsT, ToolParams],
    *,
    takes_ctx: bool | None = None,
    max_retries: int | None = None,
    name: str | None = None,
    description: str | None = None,
    prepare: ToolPrepareFunc[ToolAgentDepsT] | None = None,
    args_validator: ArgsValidatorFunc[ToolAgentDepsT, ToolParams] | None = None,
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
    function_schema: _function_schema.FunctionSchema | None = None,
)
```

Create a new tool instance.

Example usage:

```python
from pydantic_ai import Agent, RunContext, Tool

async def my_tool(ctx: RunContext[int], x: int, y: int) -> str:
    return f'{ctx.deps} {x} {y}'

agent = Agent('test', tools=[Tool(my_tool)])
```

or with a custom prepare method:

```python

from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.tools import ToolDefinition

async def my_tool(ctx: RunContext[int], x: int, y: int) -> str:
    return f'{ctx.deps} {x} {y}'

async def prep_my_tool(
    ctx: RunContext[int], tool_def: ToolDefinition
) -> ToolDefinition | None:
    # only register the tool if `deps == 42`
    if ctx.deps == 42:
        return tool_def

agent = Agent('test', tools=[Tool(my_tool, prepare=prep_my_tool)])
```

###### Parameters

**`function`** : `ToolFuncEither`\[`ToolAgentDepsT`, `ToolParams`\]

The Python function to call as the tool.

**`takes_ctx`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether the function takes a [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) first argument, this is inferred if unset.

**`max_retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Maximum number of retries allowed for this tool, set to the agent default if `None`.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Name of the tool, inferred from the function if `None`.

**`description`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Description of the tool, inferred from the function if `None`.

**`prepare`** : `ToolPrepareFunc`\[`ToolAgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to prepare the tool definition for each step, return `None` to omit this tool from a given step. This is useful if you want to customise a tool at call time, or omit it completely from a step. See [`ToolPrepareFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolPrepareFunc).

**`args_validator`** : `ArgsValidatorFunc`\[`ToolAgentDepsT`, `ToolParams`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to validate tool arguments after schema validation has passed, before execution. The validator receives the already-validated and type-converted parameters, with `RunContext` as the first argument. Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to ask the model to correct the arguments and try again, or [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed) to report a terminal failure the model should adapt to instead of retrying. Return `None` on success. See [`ArgsValidatorFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ArgsValidatorFunc).

**`docstring_format`** : `DocstringFormat` _Default:_ `'auto'`

The format of the docstring, see [`DocstringFormat`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DocstringFormat). Defaults to `'auto'`, such that the format is inferred from the structure of the docstring.

**`require_parameter_descriptions`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

If True, raise an error if a parameter description is missing. Defaults to False.

**`schema_generator`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`GenerateJsonSchema`\] _Default:_ `GenerateToolJsonSchema`

The JSON schema generator class to use. Defaults to `GenerateToolJsonSchema`.

**`strict`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to enforce (vendor-specific) strict schema adherence for tool calls (supported by OpenAI, Anthropic, Google, and Bedrock). See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info.

**`sequential`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether this tool acts as a barrier that runs alone, not overlapping with other tool calls. See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info. Defaults to False.

**`requires_approval`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether this tool requires human-in-the-loop approval. Defaults to False. See the [tools documentation](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval) for more info.

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization.

**`timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model. Defaults to None (no timeout).

**`defer_loading`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether to hide this tool until it's revealed by tool search, `load_capability`, or another tool's `ToolReturn.tools`. Defaults to False. See [Tool Search](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#tool-search) for more info.

**`include_return_schema`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to include the return schema in the tool definition sent to the model. If `None`, defaults to `False` unless the [`IncludeToolReturnSchemas`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.IncludeToolReturnSchemas) capability is used.

**`function_schema`** : `_function_schema.FunctionSchema` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The function schema to use for the tool. If not provided, it will be generated.

##### from\_schema

`@classmethod`

```python
def from_schema(
    cls,
    function: Callable[..., Any],
    name: str,
    description: str | None,
    json_schema: JsonSchemaValue,
    takes_ctx: bool = False,
    sequential: bool = False,
    args_validator: ArgsValidatorFunc[Any, ...] | None = None,
) -> Self
```

Creates a Pydantic tool from a function and a JSON schema.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self) -- A Pydantic tool that calls the function

###### Parameters

**`function`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[..., [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

The function to call. This will be called with keywords only. Schema validation of the arguments is skipped, but a custom `args_validator` will still run if provided.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The unique name of the tool that clearly communicates its purpose

**`description`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

Used to tell the model how/when/why to use the tool. You can provide few-shot examples as a part of the description.

**`json_schema`** : `JsonSchemaValue`

The schema for the function arguments

**`takes_ctx`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

An optional boolean parameter indicating whether the function accepts the context object as an argument.

**`sequential`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether this tool acts as a barrier that runs alone, not overlapping with other tool calls. See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info. Defaults to False.

**`args_validator`** : `ArgsValidatorFunc`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any), ...\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to validate tool arguments after schema validation has passed, before execution. The validator receives the already-validated and type-converted parameters, with `RunContext` as the first argument. Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to ask the model to correct the arguments and try again, or [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed) to report a terminal failure the model should adapt to instead of retrying. Return `None` on success. See [`ArgsValidatorFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ArgsValidatorFunc).

##### prepare\_tool\_def

`@async`

```python
def prepare_tool_def(ctx: RunContext[ToolAgentDepsT]) -> ToolDefinition | None
```

Get the tool definition.

By default, this method creates a tool definition, then either returns it, or calls `self.prepare` if it's set.

###### Returns

[`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- return a `ToolDefinition` or `None` if the tools should not be registered for this run.

### ToolDefinition

Definition of a tool passed to a model.

This is used for both function tools and output tools.

#### Attributes

##### name

The name of the tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### parameters\_json\_schema

The JSON schema for the tool's parameters.

**Type:** `ObjectJsonSchema` **Default:** `field(default_factory=(lambda: {'type': 'object', 'properties': {}}))`

##### description

The description of the tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### outer\_typed\_dict\_key

The key in the outer \[TypedDict\] that wraps an output tool.

This will only be set for output tools which don't have an `object` JSON schema.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### strict

Whether to enforce (vendor-specific) strict schema adherence for tool calls.

Setting this to `True` while using a supported model requests the provider's native schema-enforcement feature. On some providers that imposes restrictions on the tool's JSON schema (e.g. every property required, `additionalProperties: false`) in exchange for constrained generation; on Google it maps to Gemini's `VALIDATED` function-calling mode, which needs no schema rewrites.

When `False`, never use strict mode for the tool. On Google, any function or output tool with `strict=False` keeps the whole request on `AUTO` (Gemini's mode is request-wide, not per-tool). When `None` (the default), the value is inferred per provider: OpenAI enables strict mode when the `parameters_json_schema` is strict-compatible; Google defaults to `VALIDATED` on supported models (Gemini 2.5+); Anthropic and Bedrock leave it off unless you explicitly set `strict=True`.

Note: this is currently supported by OpenAI, Anthropic, Google, and Bedrock models. See [Strict Mode](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#strict-mode) for the full per-provider table.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### sequential

Whether this tool acts as a barrier that runs alone, not overlapping with other tool calls.

A `sequential=True` tool acts as a barrier: it runs alone, with tools the model emitted before it completing first and tools emitted after it starting only once it finishes. Other tools still run in parallel around it. To run an entire run's tools serially, use [`ToolManager.parallel_execution_mode('sequential')`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tool_manager.ToolManager.parallel_execution_mode) instead.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### kind

The kind of tool:

-   `'function'`: a tool that will be executed by Pydantic AI during an agent run and has its result returned to the model
-   `'output'`: a tool that passes through an output value that ends the run
-   `'external'`: a tool whose result will be produced outside of the Pydantic AI agent run in which it was called, because it depends on an upstream service (or user) or could take longer to generate than it's reasonable to keep the agent process running. See the [tools documentation](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#deferred-tools) for more info.
-   `'unapproved'`: a tool that requires human-in-the-loop approval. See the [tools documentation](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval) for more info.

**Type:** `ToolKind` **Default:** `field(default='function')`

##### metadata

Tool metadata that can be set by the toolset this tool came from. It is not sent to the model, but can be used for filtering and tool behavior customization.

For MCP tools, this contains the `meta` and `annotations` fields from the tool definition, as well as a `task` flag indicating whether the toolset will use task-augmented execution for the tool.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### timeout

Timeout in seconds for tool execution.

If the tool takes longer than this, a retry prompt is returned to the model. Defaults to None (no timeout).

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### defer\_loading

Whether this tool should be hidden from the model until something explicitly surfaces it.

Set on `Tool(defer_loading=True)` (or via a custom toolset) to opt this tool into deferred loading. This author intent remains stable after the tool is revealed; current wire placement is tracked separately by [`ModelRequestParameters.tool_visibility`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestParameters.tool_visibility).

See [Tool Search](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#tool-search) for more info.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### unless\_native

If set, this tool is dropped from the wire when the named native tool is supported by the model.

Generic version of the old `prefer_builtin` flag: a function tool carrying `unless_native='web_search'` is treated as a local fallback for the [`WebSearchTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.WebSearchTool) native tool and silently removed from the request whenever the model handles `WebSearchTool` natively. It stays in the request when the native tool isn't supported.

**Type:** [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None), `Field`(`validation_alias`\=(`AliasChoices`(`unless_native`, `prefer_native`, `prefer_builtin`)))\] **Default:** `None`

##### with\_native

If set, this tool is a member of a corpus the named native tool manages.

Symmetric pair with `unless_native`:

-   `unless_native='X'` -- drop me from the wire when X is supported (local fallback).
-   `with_native='X'` -- I belong to X's corpus, so X's adapter decides my wire format.

Set by `ToolSearchToolset` on the deferred tools the model may search for, and only those: a tool an on-demand capability gates is deferred without being searchable, and carries `defer_loading` alone. When the named native tool isn't supported by the model, this is cleared -- a corpus with no manager is not a corpus -- which is independent of whether the tool stays on the wire; that's `defer_loading`'s question.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_kind

Discriminator for a cross-provider typed call/return shape (e.g. `'tool-search'`).

Set by the framework when a tool emits parts that should be promoted to a typed subclass (such as [`ToolSearchCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchCallPart) and [`ToolSearchReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchReturnPart)). Leave as `None` for user-defined function tools -- they go through the standard [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart) / [`ToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturnPart) shapes.

To detect a tool-search part regardless of execution path (native server-side vs. local fallback), check `part.tool_kind == 'tool-search'` -- this works across both call/return and both server/local variants.

Distinct from [`kind`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition.kind), which is about invocation semantics (`'function'` / `'output'` / `'external'` / `'unapproved'`).

**Type:** `ToolPartKind` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### return\_schema

The JSON schema for the tool's return value.

For models that natively support return schemas (e.g. Google Gemini), this is passed as a structured field in the API request. For other models, it is injected into the tool's description as JSON text. Only included when `include_return_schema` resolves to `True`.

**Type:** `ObjectJsonSchema` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### include\_return\_schema

Whether to include the return schema in the tool definition sent to the model.

When `True`, the `return_schema` will be preserved and sent to the model. When `False`, the `return_schema` will be cleared before sending. When `None` (default), defaults to `False` unless the [`IncludeToolReturnSchemas`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.IncludeToolReturnSchemas) capability is used.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### toolset\_id

The ID of the toolset that this tool belongs to.

Set automatically when tools are collected from toolsets. Can be used by capabilities (e.g. durable execution) to apply per-toolset configuration to tool operations.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### capability\_id

The id of the capability that contributed this tool, or `None` if the tool is not owned by a capability.

Assigned once when the run's capabilities are set up and then carried on the `ToolDefinition` for the rest of that run -- it does not change or reset between steps. For a tool owned by a deferred capability it gates visibility: the tool is revealed once that capability's id appears in [`RunContext.loaded_capability_ids`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.loaded_capability_ids).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### function\_signature

The function signature shape for this tool.

Lazily computed from `parameters_json_schema` and `return_schema` on first access. Name and description are not stored on the signature -- pass them at render time via `sig.render(body, name=td.name, description=td.description)`.

**Type:** `FunctionSignature`

##### defer

Whether calls to this tool will be deferred.

See the [tools documentation](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#deferred-tools) for more info.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### Methods

##### render\_signature

```python
def render_signature(body: str, **kwargs: Any) -> str
```

Render the function signature with this tool's name and description.

Convenience wrapper around `self.function_signature.render()` that supplies `name` and `description` from this tool definition.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### matches\_tool\_selector

`@async`

```python
def matches_tool_selector(
    selector: ToolSelector[AgentDepsT],
    ctx: RunContext[AgentDepsT],
    tool_def: ToolDefinition,
) -> bool
```

Check whether a tool definition matches a [`ToolSelector`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolSelector).

#### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool) -- `True` if the tool matches the selector.

#### Parameters

**`selector`** : `ToolSelector`\[`AgentDepsT`\]

The selector to check against.

**`ctx`** : [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]

The current run context.

**`tool_def`** : [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition)

The tool definition to test.

### AgentDepsT

Type variable for agent dependencies.

**Default:** `TypeVar('AgentDepsT', default=object, contravariant=True)`

### ToolParams

Retrieval function param spec.

**Default:** `ParamSpec('ToolParams', default=...)`

### SystemPromptFunc

A function that may or may not take `RunContext` as an argument, and may or may not be async.

Functions which return None are excluded from model requests.

Usage `SystemPromptFunc[AgentDepsT]`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[RunContext[AgentDepsT]], str | None] | Callable[[RunContext[AgentDepsT]], Awaitable[str | None]] | Callable[[], str | None] | Callable[[], Awaitable[str | None]]`

### ToolFuncContext

A tool function that takes `RunContext` as the first argument.

Usage `ToolContextFunc[AgentDepsT, ToolParams]`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[Concatenate[RunContext[AgentDepsT], ToolParams], Any]`

### ToolFuncPlain

A tool function that does not take `RunContext` as the first argument.

Usage `ToolPlainFunc[ToolParams]`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[ToolParams, Any]`

### ToolFuncEither

Either kind of tool function.

This is just a union of [`ToolFuncContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolFuncContext) and [`ToolFuncPlain`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolFuncPlain).

Usage `ToolFuncEither[AgentDepsT, ToolParams]`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `ToolFuncContext[AgentDepsT, ToolParams] | ToolFuncPlain[ToolParams]`

### ArgsValidatorFunc

A function that validates tool arguments before execution.

The validator receives the same typed parameters as the tool function, with [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) as the first argument for dependency access.

Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to ask the model to correct the arguments and try again, or [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed) to report a terminal failure the model should adapt to instead of retrying. Return `None` on success.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[Concatenate[RunContext[AgentDepsT], ToolParams], Awaitable[None]] | Callable[Concatenate[RunContext[AgentDepsT], ToolParams], None]`

### ToolPrepareFunc

Definition of a function that can prepare a tool definition at call time. Both sync and async functions are accepted.

See [tool docs](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#tool-prepare) for more information.

Example -- here `only_if_42` is valid as a `ToolPrepareFunc`:

```python
from pydantic_ai import RunContext, Tool
from pydantic_ai.tools import ToolDefinition

def only_if_42(
    ctx: RunContext[int], tool_def: ToolDefinition
) -> ToolDefinition | None:
    if ctx.deps == 42:
        return tool_def

def hitchhiker(ctx: RunContext[int], answer: str) -> str:
    return f'{ctx.deps} {answer}'

hitchhiker = Tool(hitchhiker, prepare=only_if_42)
```

Usage `ToolPrepareFunc[AgentDepsT]`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[RunContext[AgentDepsT], 'ToolDefinition'], Union[Awaitable['ToolDefinition | None'], 'ToolDefinition', None]]`

### ToolsPrepareFunc

Definition of a function that can prepare the tool definition of all tools for each step. This is useful if you want to customize the definition of multiple tools or you want to register a subset of tools for a given step. Both sync and async functions are accepted.

Example -- here `turn_on_strict_if_openai` is valid as a `ToolsPrepareFunc`:

```python
from dataclasses import replace

from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import PrepareTools
from pydantic_ai.tools import ToolDefinition


def turn_on_strict_if_openai(
    ctx: RunContext, tool_defs: list[ToolDefinition]
) -> list[ToolDefinition]:
    if ctx.model.system == 'openai':
        return [replace(tool_def, strict=True) for tool_def in tool_defs]
    return tool_defs

agent = Agent('openai:gpt-5.2', capabilities=[PrepareTools(turn_on_strict_if_openai)])
```

Usage `ToolsPrepareFunc[AgentDepsT]`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[RunContext[AgentDepsT], list['ToolDefinition']], Awaitable[list['ToolDefinition']] | list['ToolDefinition']]`

### ToolSelectorFunc

A callable that decides whether a tool matches a selection criterion.

Receives the run context and a tool definition, returns `True` if the tool is selected. Both sync and async functions are accepted.

Usage `ToolSelectorFunc[AgentDepsT]`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[RunContext[AgentDepsT], 'ToolDefinition'], bool | Awaitable[bool]]`

### ToolSelector

Specifies which tools a capability or toolset wrapper should apply to.

-   `'all'`: matches every tool (default for most capabilities).
-   `Sequence[str]`: matches tools whose names are in the sequence.
-   `dict[str, Any]`: matches tools whose [`metadata`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition.metadata) contains all the specified key-value pairs (deep inclusion check -- nested dicts are compared recursively, and the tool's metadata may have additional keys).
-   `Callable[[RunContext, ToolDefinition], bool | Awaitable[bool]]`: custom sync or async predicate.

The first three forms are serializable for use in agent specs (YAML/JSON).

Usage `ToolSelector[AgentDepsT]`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['all'] | Sequence[str] | dict[str, Any] | ToolSelectorFunc[AgentDepsT]`

### NativeToolFunc

Definition of a function that can prepare a native tool at call time.

This is useful if you want to customize the native tool based on the run context (e.g. user dependencies), or omit it completely from a step.

Returning `None` omits the tool. The one exception is a [`NativeOrLocalTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.NativeOrLocalTool) capability that routes native configuration into a `fallback_subagent_model` subagent, where the subagent has already been invoked and cannot omit; see [`XSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.XSearch) and [`ImageGeneration`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ImageGeneration).

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[RunContext[AgentDepsT]], Awaitable[AbstractNativeTool | None] | AbstractNativeTool | None]`

### AgentNativeTool

A native tool or a function that dynamically produces one.

This is a convenience alias for `AbstractNativeTool | NativeToolFunc[AgentDepsT]`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `AbstractNativeTool | NativeToolFunc[AgentDepsT]`

### DocstringFormat

Supported docstring formats.

-   `'google'` -- [Google-style](https://google.github.io/styleguide/pyguide.html#381-docstrings) docstrings.
-   `'numpy'` -- [Numpy-style](https://numpydoc.readthedocs.io/en/latest/format.html) docstrings.
-   `'sphinx'` -- [Sphinx-style](https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html#the-sphinx-docstring-format) docstrings.
-   `'auto'` -- Automatically infer the format based on the structure of the docstring.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['google', 'numpy', 'sphinx', 'auto']`

### ToolAgentDepsT

Type variable for agent dependencies for a tool.

**Default:** `TypeVar('ToolAgentDepsT', default=object, contravariant=True)`

### ObjectJsonSchema

Type representing JSON schema of an object, e.g. where `"type": "object"`.

This type is used to define tools parameters (aka arguments) in [ToolDefinition](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition).

With PEP-728 this should be a TypedDict with `type: Literal['object']`, and `extra_parts=Any`

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `dict[str, Any]`

### ToolKind

Kind of tool.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['function', 'output', 'external', 'unapproved']`

### ParallelExecutionMode

How tool calls from a single model response are executed -- see [`ToolManager.parallel_execution_mode`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tool_manager.ToolManager.parallel_execution_mode).

**Default:** `Literal['parallel', 'sequential', 'parallel_ordered_events']`

### ToolManager

**Bases:** `Generic[AgentDepsT]`

Manages tools for an agent run step. It caches the agent run's toolset's tool definitions and handles calling tools and retries.

#### Methods

##### parallel\_execution\_mode

`@classmethod`

```python
def parallel_execution_mode(
    cls,
    mode: ParallelExecutionMode = 'parallel',
) -> Generator[None]
```

Set the parallel execution mode during the context.

###### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

###### Parameters

**`mode`** : `ParallelExecutionMode` _Default:_ `'parallel'`

The execution mode for tool calls:

-   'parallel': Run tool calls in parallel, yielding events as they complete (default).
-   'sequential': Run tool calls one at a time in order.
-   'parallel\_ordered\_events': Run tool calls in parallel, but events are emitted in order, after all calls complete.

---
