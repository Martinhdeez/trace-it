# [pydantic_ai.durable_exec](https://pydantic.dev/docs/ai/api/pydantic-ai/durable_exec/)

# pydantic\_ai.durable\_exec

### PydanticAIWorkflow

Temporal Workflow base class that provides `__pydantic_ai_agents__` for direct agent registration.

Accepts any `AbstractAgent` -- either a regular `Agent` carrying a [`TemporalDurability`](https://pydantic.dev/docs/ai/api/pydantic-ai/durable_exec/#pydantic_ai.durable_exec.temporal.TemporalDurability) capability, or the deprecated [`TemporalAgent`](https://pydantic.dev/docs/ai/api/pydantic-ai/durable_exec/#pydantic_ai.durable_exec.temporal.TemporalAgent) wrapper. [`PydanticAIPlugin`](https://pydantic.dev/docs/ai/api/pydantic-ai/durable_exec/#pydantic_ai.durable_exec.temporal.PydanticAIPlugin) walks the sequence and registers each agent's activities with the worker.

### TemporalOperationNamer

**Bases:** `DurableOperationNamer`

Generate Temporal activity names that are persisted compatibility data.

These names must essentially never change. Changing them can strand in-flight workflows and recorded runs.

### LogfirePlugin

**Bases:** `SimplePlugin`

Temporal client plugin for Logfire.

#### Constructor Parameters

**`setup_logfire`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[\], `Logfire`\] _Default:_ `_default_setup_logfire`

Function that configures and returns a Logfire instance.

**`metrics`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to send Temporal metrics to Logfire.

**`metric_periodicity`** : `timedelta` _Default:_ `timedelta(seconds=60)`

How often to export Temporal metrics. Defaults to 60 seconds.

### PydanticAIPayloadConverter

**Bases:** `PydanticPayloadConverter`

Temporal Pydantic payload converter with memoized deserialization adapters.

Custom payload converters can inherit from this class to retain the adapter cache while replacing or extending other conversion behavior.

### TemporalRunContext

**Bases:** `RunContext[AgentDepsT]`

The [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) subclass to use to serialize and deserialize the run context for use inside a Temporal activity.

By default, only the `deps`, `run_id`, `conversation_id`, `metadata`, `retries`, `tool_call_id`, `tool_name`, `tool_call_approved`, `tool_call_metadata`, `retry`, `max_retries`, `run_step`, `usage`, `usage_limits`, `partial_output`, `trace_include_content`, `instrumentation_version`, `loaded_capability_ids`, `discovered_tool_names`, the private dispatch-only availability supplements, and `capability_active` attributes will be available. Reading any other attribute raises a `UserError` explaining how to make it available, rather than returning its default value, so a field that didn't cross the boundary can't be mistaken for real run state.

`agent` and `root_capability` are re-attached from the worker's agent instance, `pending_messages` holds a guard that makes [`enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue) raise inside an activity, and `tool_manager` and `realtime_session` are `None`: they hold live run state that isn't serializable (for `tool_manager`, `available_tool_names` returns the resolved snapshot serialized at activity dispatch time, falling back to `discovered_tool_names` if a custom subclass doesn't carry it; for `realtime_session`, `None` already means "not available here"). The `capabilities` registry is excluded for the same reason -- it holds live capability objects (toolsets, hooks, callables) -- so `active_capability_ids` likewise returns a snapshot serialized at dispatch time, which is what lets [`is_tool_available`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.is_tool_available) answer for a capability-owned tool inside an activity; reading `capabilities` itself still raises. `model` and `tracer` are excluded as live objects too. `messages` is excluded because the full history would be duplicated into every activity payload, and `prompt` is excluded because a multi-modal prompt can carry large `BinaryContent` that would likewise ride in every activity payload, risking Temporal's 2 MB limit. `model_settings` is excluded because it's only set for model requests, which receive it as their own activity parameter, and `validation_context` because it's an arbitrary user object with no serialization contract. To make another attribute available, create a `TemporalRunContext` subclass with a custom `serialize_run_context` class method that returns a dictionary that includes the attribute and pass it as the `run_context_type` argument to [`TemporalDurability`](https://pydantic.dev/docs/ai/api/pydantic-ai/durable_exec/#pydantic_ai.durable_exec.temporal.TemporalDurability). A subclass can use this escape hatch to opt in to carrying `prompt` if it knows its prompts are text-only.

#### Attributes

##### available\_tool\_names

The availability snapshot serialized at activity dispatch time.

Live tool state doesn't cross the activity boundary, but availability was already resolved when the activity was dispatched -- so the name form of [`is_tool_available`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.is_tool_available) answers correctly for always-visible tools too, instead of degrading to the `discovered_tool_names` fallback. Custom subclasses whose `serialize_run_context` doesn't carry the snapshot keep the base fallback behavior.

**Type:** [`set`](https://docs.python.org/3/reference/expressions.html#set)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### active\_capability\_ids

The set of active capability ids serialized at activity dispatch time.

The `capabilities` registry itself can't cross the boundary, but the ids it resolves to can, so [`is_tool_available`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.is_tool_available) still answers for a capability-owned tool instead of raising. Custom subclasses whose `serialize_run_context` doesn't carry the snapshot fall back to the base property, which reads the registry and raises inside an activity.

**Type:** [`set`](https://docs.python.org/3/reference/expressions.html#set)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

#### Methods

##### emit

`@async`

```python
def emit(event: CustomEventT, /) -> CustomEventT
def emit(event: CapabilityEventT, /) -> CapabilityEventT
```

Reject `emit` from inside a Temporal activity.

Tools and event stream handlers run inside activities where the run's event stream isn't reachable, so events emitted there can't currently flow back into the stream; raising beats silently dropping them. This covers a capability's own tools emitting a `CapabilityEvent`, which run in activities like any other tool. Events emitted workflow-side (e.g. from capability hooks) work as usual.

Lifting this needs a transport from the activity back to the workflow and a decision on what a retried attempt's events mean; tracked in [https://github.com/pydantic/pydantic-ai/issues/7971](https://github.com/pydantic/pydantic-ai/issues/7971).

###### Returns

[`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent) | [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent)

##### serialize\_run\_context

`@classmethod`

```python
def serialize_run_context(cls, ctx: RunContext[Any]) -> dict[str, Any]
```

Serialize the run context to a `dict[str, Any]`.

###### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### deserialize\_run\_context

`@classmethod`

```python
def deserialize_run_context(
    cls,
    ctx: dict[str, Any],
    deps: Any,
) -> TemporalRunContext[Any]
```

Deserialize the run context from a `dict[str, Any]`.

###### Returns

`TemporalRunContext`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

### TemporalAgent

**Bases:** `WrapperAgent[AgentDepsT, OutputDataT]`

#### Methods

##### \_\_init\_\_

```python
def __init__(
    wrapped: AbstractAgent[AgentDepsT, OutputDataT],
    *,
    name: str | None = None,
    models: Mapping[str, Model] | None = None,
    provider_factory: TemporalProviderFactory | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    activity_config: ActivityConfig | None = None,
    model_activity_config: ActivityConfig | None = None,
    toolset_activity_config: dict[str, ActivityConfig] | None = None,
    tool_activity_config: dict[str, dict[str, ActivityConfig | Literal[False]]] | None = None,
    run_context_type: type[TemporalRunContext[AgentDepsT]] = TemporalRunContext[AgentDepsT],
    temporalize_toolset_func: Callable[[AbstractToolset[AgentDepsT], str, ActivityConfig, dict[str, ActivityConfig | Literal[False]], type[AgentDepsT], type[TemporalRunContext[AgentDepsT]], AbstractAgent[AgentDepsT, Any] | None], AbstractToolset[AgentDepsT]] = temporalize_toolset,
)
```

Wrap an agent to enable it to be used inside a Temporal workflow, by automatically offloading model requests, tool calls, and MCP server communication to Temporal activities.

After wrapping, the original agent can still be used as normal outside of the Temporal workflow, but any changes to its model or toolsets after wrapping will not be reflected in the durable agent.

###### Parameters

**`wrapped`** : `AbstractAgent`\[`AgentDepsT`, `OutputDataT`\]

The agent to wrap.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional unique agent name to use in the Temporal activities' names. If not provided, the agent's `name` will be used.

**`models`** : [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `Model`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional mapping of model instances to register with the agent. Keys define the names that can be referenced at runtime and the values are `Model` instances. Registered model instances can be passed directly to `run(model=...)`. If the wrapped agent doesn't have a model set and none is provided to `run()`, the first model in this mapping will be used as the default.

**`provider_factory`** : `TemporalProviderFactory` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callable used when instantiating models from provider strings (those supplied at runtime). The callable receives the provider name and the current run context, allowing custom configuration such as injecting API keys stored on `deps`. Note: This factory is only used inside Temporal workflows. Outside workflows, model strings are resolved using the default provider behavior.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler to use instead of the one set on the wrapped agent.

**`activity_config`** : `ActivityConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base Temporal activity config to use for all activities. If no config is provided, a `start_to_close_timeout` of 60 seconds is used.

**`model_activity_config`** : `ActivityConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Temporal activity config to use for model request activities. This is merged with the base activity config.

**`toolset_activity_config`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `ActivityConfig`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Temporal activity config to use for get-tools and call-tool activities for specific toolsets identified by ID. This is merged with the base activity config.

**`tool_activity_config`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `ActivityConfig` | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\[[`False`](https://docs.python.org/3/builtins/constants.html#False)\]\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Temporal activity config to use for specific tool call activities identified by toolset ID and tool name. This is merged with the base and toolset-specific activity configs. If a tool does not use IO, you can specify `False` to disable using an activity. Note that the tool is required to be defined as an `async` function as non-async tools are run in threads which are non-deterministic and thus not supported outside of activities.

**`run_context_type`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`TemporalRunContext`\[`AgentDepsT`\]\] _Default:_ `TemporalRunContext[AgentDepsT]`

The `TemporalRunContext` subclass to use to serialize and deserialize the run context for use inside a Temporal activity. See [`TemporalRunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/durable_exec/#pydantic_ai.durable_exec.temporal.TemporalRunContext) for the attributes that are available by default. To make another attribute available, create a `TemporalRunContext` subclass with a custom `serialize_run_context` class method that returns a dictionary that includes the attribute.

**`temporalize_toolset_func`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `ActivityConfig`, [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `ActivityConfig` | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\[[`False`](https://docs.python.org/3/builtins/constants.html#False)\]\], [`type`](https://docs.python.org/3/glossary.html#term-type)\[`AgentDepsT`\], [`type`](https://docs.python.org/3/glossary.html#term-type)\[`TemporalRunContext`\[`AgentDepsT`\]\], `AbstractAgent`\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)\], [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] _Default:_ `temporalize_toolset`

Optional function to use to prepare "leaf" toolsets (i.e. those that implement their own tool listing and calling) for Temporal by wrapping them in a `TemporalWrapperToolset` that moves methods that require IO to Temporal activities. If not provided, only `FunctionToolset` and `MCPToolset` will be prepared for Temporal. The function takes the toolset, the activity name prefix, the toolset-specific activity config, the tool-specific activity configs and the run context type.

##### run

`@async`

```python
def run(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[OutputDataT]
def run(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[RunOutputDataT]
```

Run the agent with a user prompt in async mode.

This method builds an internal agent graph (using system prompts, tools and result schemas) and then runs the graph to completion. The result of the run is returned.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    agent_run = await agent.run('What is the capital of France?')
    print(agent_run.output)
    #> The capital of France is Paris.
```

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent. Inside workflows, only registered model instances, registered names, or provider strings are valid.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for Temporal durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler to use for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### run\_sync

```python
def run_sync(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[OutputDataT]
def run_sync(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[RunOutputDataT]
```

Synchronously run the agent with a user prompt.

This is a convenience method that wraps [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) with `loop.run_until_complete(...)`. You therefore can't use this method inside async code or if there's an active event loop.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

result_sync = agent.run_sync('What is the capital of Italy?')
print(result_sync.output)
#> The capital of Italy is Rome.
```

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for Temporal durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler to use for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### run\_stream

`@async`

```python
def run_stream(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[StreamedRunResult[AgentDepsT, OutputDataT]]
def run_stream(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[StreamedRunResult[AgentDepsT, RunOutputDataT]]
```

Run the agent with a user prompt in async mode, returning a streamed response.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    async with agent.run_stream('What is the capital of the UK?') as response:
        print(await response.get_output())
        #> The capital of the UK is London.
```

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[`StreamedRunResult`\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for Temporal durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler to use for this run. It will receive all the events up until the final result is found, which you can then read or stream from inside the context manager.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### run\_stream\_events

```python
def run_stream_events(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRunEvents[OutputDataT]]
def run_stream_events(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRunEvents[RunOutputDataT]]
```

Run the agent with a user prompt in async mode and stream events from the run.

This is a convenience method that wraps [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) and uses the `event_stream_handler` kwarg to get a stream of events from the run.

Example:

```python
from pydantic_ai import Agent, AgentRunResultEvent, AgentStreamEvent

agent = Agent('openai:gpt-5.2')

async def main():
    collected: list[AgentStreamEvent | AgentRunResultEvent] = []
    async with agent.run_stream_events('What is the capital of France?') as events:
        async for event in events:
            collected.append(event)
    print(collected)
    '''
    [
        PartStartEvent(index=0, part=TextPart(content='The capital of ')),
        FinalResultEvent(tool_name=None, tool_call_id=None),
        PartDeltaEvent(index=0, delta=TextPartDelta(content_delta='France is Paris. ')),
        PartEndEvent(
            index=0, part=TextPart(content='The capital of France is Paris. ')
        ),
        AgentRunResultEvent(
            result=AgentRunResult(output='The capital of France is Paris. ')
        ),
    ]
    '''
```

Arguments are the same as for [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run), except that `event_stream_handler` is now allowed.

###### Returns

`AbstractAsyncContextManager`\[[`AgentRunEvents`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRunEvents)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- An async context manager that yields an [`AgentRunEvents`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRunEvents) `AbstractAsyncContextManager`\[[`AgentRunEvents`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRunEvents)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- handle over `AgentStreamEvent`s ending with a final `AgentRunResultEvent` carrying the run result.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for Temporal durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### iter

`@async`

```python
def iter(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRun[AgentDepsT, OutputDataT]]
def iter(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRun[AgentDepsT, RunOutputDataT]]
```

A contextmanager which can be used to iterate over the agent graph's nodes as they are executed.

This method builds an internal agent graph (using system prompts, tools and output schemas) and then returns an `AgentRun` object. The `AgentRun` can be used to async-iterate over the nodes of the graph as they are executed. This is the API to use if you want to consume the outputs coming from each LLM model response, or the stream of events coming from the execution of tools.

The `AgentRun` also provides methods to access the full message history, new messages, and usage statistics, and the final result of the run once it has completed.

For more details, see the documentation of `AgentRun`.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    nodes = []
    async with agent.iter('What is the capital of France?') as agent_run:
        async for node in agent_run:
            nodes.append(node)
    print(nodes)
    '''
    [
        UserPromptNode(
            user_prompt='What is the capital of France?',
            instructions_functions=[],
            system_prompts=(),
            system_prompt_functions=[],
            system_prompt_dynamic_functions={},
        ),
        ModelRequestNode(
            request=ModelRequest(
                parts=[
                    UserPromptPart(
                        content='What is the capital of France?',
                        timestamp=datetime.datetime(...),
                    )
                ],
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        CallToolsNode(
            model_response=ModelResponse(
                parts=[TextPart(content='The capital of France is Paris.')],
                usage=RequestUsage(
                    cost=Decimal('0.000196'), input_tokens=56, output_tokens=7
                ),
                model_name='gpt-5.2',
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        End(data=FinalResult(output='The capital of France is Paris.')),
    ]
    '''
    print(agent_run.result.output)
    #> The capital of France is Paris.
```

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[[`AgentRun`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun)\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for Temporal durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### override

```python
def override(
    *,
    name: str | _utils.Unset = _utils.UNSET,
    deps: AgentDepsT | _utils.Unset = _utils.UNSET,
    model: models.Model | models.KnownModelName | str | _utils.Unset = _utils.UNSET,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | _utils.Unset = _utils.UNSET,
    tools: Sequence[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]] | _utils.Unset = _utils.UNSET,
    native_tools: Sequence[AgentNativeTool[AgentDepsT]] | _utils.Unset = _utils.UNSET,
    instructions: _instructions.AgentInstructions[AgentDepsT] | _utils.Unset = _utils.UNSET,
    metadata: AgentMetadata[AgentDepsT] | _utils.Unset = _utils.UNSET,
    model_settings: AgentModelSettings[AgentDepsT] | _utils.Unset = _utils.UNSET,
    retries: int | AgentRetries | _utils.Unset = _utils.UNSET,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> Generator[None]
```

Context manager to temporarily override agent configuration.

This is particularly useful when testing. You can find an example of this [here](https://pydantic.dev/docs/ai/guides/testing/#overriding-model-via-pytest-fixtures).

###### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The name to use instead of the name passed to the agent constructor and agent run.

**`deps`** : `AgentDepsT` | `_utils.Unset` _Default:_ `_utils.UNSET`

The dependencies to use instead of the dependencies passed to the agent run.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The model to use instead of the model passed to the agent run.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The toolsets to use instead of the toolsets passed to the agent constructor and agent run.

**`tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\] | `ToolFuncEither`\[`AgentDepsT`, ...\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The tools to use instead of the tools registered with the agent.

**`native_tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentNativeTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.AgentNativeTool)\[`AgentDepsT`\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The native tools to use instead of the agent's configured native tools.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The instructions to use instead of the instructions registered with the agent.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The metadata to use instead of the metadata passed to the agent constructor. When set, any per-run `metadata` argument is ignored.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The model settings to use instead of the model settings passed to the agent constructor. When set, any per-run `model_settings` argument is ignored.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | `_utils.Unset` _Default:_ `_utils.UNSET`

The retry budgets to use instead of the agent-level configuration. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). When set, any per-run `retries` argument is ignored.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply as overrides.

### TemporalDurability

**Bases:** `BaseDurabilityCapability[AgentDepsT]`

Capability that makes an agent durable by routing I/O through Temporal activities.

When added to an agent, this capability intercepts model requests and wraps toolsets to route their I/O through Temporal activities. Outside of workflows, the capability is transparent.

The capability discovers the agent's model, name, and toolsets automatically via `for_agent()`. Only Temporal-specific configuration needs to be passed to the constructor.

#### Attributes

##### run\_context\_type

The `TemporalRunContext` subclass used to serialize/deserialize the run context.

**Type:** [`type`](https://docs.python.org/3/glossary.html#term-type)\[`TemporalRunContext`\[`AgentDepsT`\]\] **Default:** `run_context_type`

##### activity\_config

Base Temporal activity config used for all activities.

**Type:** `ActivityConfig` **Default:** `activity_config`

##### temporal\_activities

All Temporal activities registered by this capability.

Register these with the Temporal worker, either directly or via `AgentPlugin`.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[..., [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    models: Mapping[str, Model] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    name: str | None = None,
    deps_type: type[AgentDepsT] | None = None,
    activity_config: ActivityConfig | None = None,
    model_activity_config: ActivityConfig | None = None,
    event_stream_handler_activity_config: ActivityConfig | None = None,
    toolset_activity_config: dict[str, ActivityConfig] | None = None,
    run_context_type: type[TemporalRunContext[AgentDepsT]] = TemporalRunContext[AgentDepsT],
)
```

Create a TemporalDurability capability.

The agent's model, name, and toolsets are discovered automatically when the capability is attached to an agent (via `for_agent()`).

###### Parameters

**`models`** : [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `Model`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional models keyed by ID for runtime model switching. The agent's primary model is always registered as `'default'`. A `Model` instance can't be serialized across the activity boundary, so a run-time model (via `agent.run(model=...)` / `agent.override(model=...)`, or swapped in by an outer capability) has to be registered here and referenced by key (or passed as the registered instance); an unregistered instance is rejected, because rebuilding it from its `model_id` would build a different model. Model-name strings never need registering: they cross as the string the caller wrote and are built on the worker by the agent's `resolve_model_id` capability chain, then `infer_model`. To build a specific instance on the worker from such a string -- a custom provider, or per-user credentials carried on `deps` -- use the [`ResolveModelId`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ResolveModelId) capability.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler. Model events are handled live inside model-request activities, and tool events are handled in per-event activities.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unique agent name used in the Temporal activity names. Defaults to the agent's `name` when the capability is bound.

**`deps_type`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The type of the agent's dependencies, needed for Temporal serialization of activity parameters. Defaults to the agent's own `deps_type`, discovered when the capability binds via `for_agent()`.

**`activity_config`** : `ActivityConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Base Temporal activity config for all activities. Defaults to a 60-second `start_to_close_timeout`.

**`model_activity_config`** : `ActivityConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Activity config merged on top of the base for model request activities.

**`event_stream_handler_activity_config`** : `ActivityConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Activity config merged on top of the base for event stream handler activities.

**`toolset_activity_config`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `ActivityConfig`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Per-toolset activity configs keyed by toolset ID, merged on top of the base config.

**`run_context_type`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`TemporalRunContext`\[`AgentDepsT`\]\] _Default:_ `TemporalRunContext[AgentDepsT]`

The `TemporalRunContext` subclass for run context serialization/deserialization.

##### wrap\_run

`@async`

```python
def wrap_run(
    ctx: RunContext[AgentDepsT],
    *,
    handler: WrapRunHandler,
) -> AgentRunResult[Any]
```

Disable threads inside Temporal workflows.

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

Explain a serialization failure raised while scheduling an activity.

This is the run's error-transformation hook: an exception raised from `wrap_run` would only be attached as the original error's `__context__`, never propagated.

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

### PydanticAIPlugin

**Bases:** `SimplePlugin`

Temporal client and worker plugin for Pydantic AI.

### AgentPlugin

**Bases:** `SimplePlugin`

Temporal worker plugin for a specific Pydantic AI agent.

Accepts either a regular `Agent` carrying a [`TemporalDurability`](https://pydantic.dev/docs/ai/api/pydantic-ai/durable_exec/#pydantic_ai.durable_exec.temporal.TemporalDurability) capability (whose chain is walked to find the bound capability), or the deprecated [`TemporalAgent`](https://pydantic.dev/docs/ai/api/pydantic-ai/durable_exec/#pydantic_ai.durable_exec.temporal.TemporalAgent) wrapper, and registers the agent's activities on the worker.

### DBOSOperationNamer

**Bases:** `JournalOperationNamer`

Generate DBOS step names that are persisted compatibility data.

These names must essentially never change. Changing them can strand in-flight workflows and recorded runs.

### StepConfig

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Configuration for a step in the DBOS workflow.

### DBOSModel

**Bases:** `WrapperModel`

A wrapper for Model that integrates with DBOS, turning request and request\_stream to DBOS steps.

### DBOSDurability

**Bases:** `BaseDurabilityCapability[AgentDepsT]`

Capability that makes an agent durable by routing I/O through DBOS steps.

The capability routes model requests, MCP I/O, and optionally event-stream handling through DBOS steps when the agent runs inside a DBOS workflow. Call `agent.run()` inside your own `@DBOS.workflow` to make that run durable; outside a workflow the capability is transparent and the run is a normal, non-durable agent run.

The capability discovers the agent's model, name, and toolsets automatically via `for_agent()`.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    models: Mapping[str, Model] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    name: str | None = None,
    model_step_config: StepConfig | None = None,
    event_stream_handler_step_config: StepConfig | None = None,
    mcp_step_config: StepConfig | None = None,
    parallel_execution_mode: DBOSParallelExecutionMode = 'parallel_ordered_events',
    register_legacy_workflows: bool = False,
)
```

Create a DBOSDurability capability.

The agent's model, name, and toolsets are discovered automatically.

###### Parameters

**`models`** : [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `Model`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional models keyed by ID for runtime model switching. The agent's primary model is always registered as `'default'`. A `Model` instance can't be serialized across the step boundary, so a run-time model (via `agent.run(model=...)` / `agent.override(model=...)`, or swapped in by an outer capability) has to be registered here and referenced by key (or passed as the registered instance); an unregistered instance is rejected, because rebuilding it from its `model_id` would build a different model. Model-name strings never need registering: they cross as the string the caller wrote and are built inside the step by the agent's `resolve_model_id` capability chain, then `infer_model`. To build a specific instance inside the step from such a string -- a custom provider, or per-user credentials carried on `deps` -- use the [`ResolveModelId`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ResolveModelId) capability.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler. Model events are handled live inside model-request steps, and each tool event is handled in its own event-handler step.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unique agent name used in the DBOS step names. Defaults to the agent's `name` when the capability is bound.

**`model_step_config`** : `StepConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

DBOS step config for model request steps.

**`event_stream_handler_step_config`** : `StepConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

DBOS step config for event stream handler steps.

**`mcp_step_config`** : `StepConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

DBOS step config for MCP server steps.

**`parallel_execution_mode`** : `DBOSParallelExecutionMode` _Default:_ `'parallel_ordered_events'`

Tool-call execution mode applied for the duration of every run. Defaults to `'parallel_ordered_events'` so events replay deterministically. Set to `'sequential'` for strict ordering.

**`register_legacy_workflows`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Register the workflow names used by the deprecated `DBOSAgent` so in-flight wrapper-era workflows can recover during migration.

##### wrap\_run

`@async`

```python
def wrap_run(
    ctx: RunContext[AgentDepsT],
    *,
    handler: WrapRunHandler,
) -> AgentRunResult[Any]
```

Apply the configured parallel-execution mode for every entry point.

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

### DBOSAgent

**Bases:** `WrapperAgent[AgentDepsT, OutputDataT]`, `DBOSConfiguredInstance`

#### Methods

##### \_\_init\_\_

```python
def __init__(
    wrapped: AbstractAgent[AgentDepsT, OutputDataT],
    *,
    name: str | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    mcp_step_config: StepConfig | None = None,
    model_step_config: StepConfig | None = None,
    parallel_execution_mode: DBOSParallelExecutionMode = 'parallel_ordered_events',
)
```

Wrap an agent to enable it with DBOS durable workflows, by automatically offloading model requests, tool calls, and MCP server communication to DBOS steps.

After wrapping, the original agent can still be used as normal outside of the DBOS workflow.

###### Parameters

**`wrapped`** : `AbstractAgent`\[`AgentDepsT`, `OutputDataT`\]

The agent to wrap.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional unique agent name to use as the DBOS configured instance name. If not provided, the agent's `name` will be used.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler to use instead of the one set on the wrapped agent.

**`mcp_step_config`** : `StepConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base DBOS step config to use for MCP server steps. If no config is provided, use the default settings of DBOS.

**`model_step_config`** : `StepConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The DBOS step config to use for model request steps. If no config is provided, use the default settings of DBOS.

**`parallel_execution_mode`** : `DBOSParallelExecutionMode` _Default:_ `'parallel_ordered_events'`

The mode for executing tool calls:

-   'parallel\_ordered\_events' (default): Run tool calls in parallel, but events are emitted in order, after all calls complete.
-   'sequential': Run tool calls one at a time in order.

##### run

`@async`

```python
def run(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[OutputDataT]
def run(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[RunOutputDataT]
```

Run the agent with a user prompt in async mode.

This method builds an internal agent graph (using system prompts, tools and result schemas) and then runs the graph to completion. The result of the run is returned.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    agent_run = await agent.run('What is the capital of France?')
    print(agent_run.output)
    #> The capital of France is Paris.
```

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for DBOS durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler to use for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### run\_sync

```python
def run_sync(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[OutputDataT]
def run_sync(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[RunOutputDataT]
```

Synchronously run the agent with a user prompt.

This is a convenience method that wraps [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) with `loop.run_until_complete(...)`. You therefore can't use this method inside async code or if there's an active event loop.

This method cannot be used inside a synchronous tool, output function, or other function called during an agent run.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

result_sync = agent.run_sync('What is the capital of Italy?')
print(result_sync.output)
#> The capital of Italy is Rome.
```

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for DBOS durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler to use for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### run\_stream

`@async`

```python
def run_stream(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[StreamedRunResult[AgentDepsT, OutputDataT]]
def run_stream(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    deps: AgentDepsT = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[StreamedRunResult[AgentDepsT, RunOutputDataT]]
```

Run the agent with a user prompt in async mode, returning a streamed response.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    async with agent.run_stream('What is the capital of the UK?') as response:
        print(await response.get_output())
        #> The capital of the UK is London.
```

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[`StreamedRunResult`\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for DBOS durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler to use for this run. It will receive all the events up until the final result is found, which you can then read or stream from inside the context manager.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### run\_stream\_events

```python
def run_stream_events(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRunEvents[OutputDataT]]
def run_stream_events(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRunEvents[RunOutputDataT]]
```

Run the agent with a user prompt in async mode and stream events from the run.

This is a convenience method that wraps [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) and uses the `event_stream_handler` kwarg to get a stream of events from the run.

Example:

```python
from pydantic_ai import Agent, AgentRunResultEvent, AgentStreamEvent

agent = Agent('openai:gpt-5.2')

async def main():
    collected: list[AgentStreamEvent | AgentRunResultEvent] = []
    async with agent.run_stream_events('What is the capital of France?') as events:
        async for event in events:
            collected.append(event)
    print(collected)
    '''
    [
        PartStartEvent(index=0, part=TextPart(content='The capital of ')),
        FinalResultEvent(tool_name=None, tool_call_id=None),
        PartDeltaEvent(index=0, delta=TextPartDelta(content_delta='France is Paris. ')),
        PartEndEvent(
            index=0, part=TextPart(content='The capital of France is Paris. ')
        ),
        AgentRunResultEvent(
            result=AgentRunResult(output='The capital of France is Paris. ')
        ),
    ]
    '''
```

Arguments are the same as for [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run), except that `event_stream_handler` is now allowed.

###### Returns

`AbstractAsyncContextManager`\[[`AgentRunEvents`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRunEvents)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- An async context manager that yields an [`AgentRunEvents`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRunEvents) `AbstractAsyncContextManager`\[[`AgentRunEvents`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRunEvents)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- handle over `AgentStreamEvent`s ending with a final `AgentRunResultEvent` carrying the run result.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for DBOS durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### iter

`@async`

```python
def iter(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRun[AgentDepsT, OutputDataT]]
def iter(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRun[AgentDepsT, RunOutputDataT]]
```

A contextmanager which can be used to iterate over the agent graph's nodes as they are executed.

This method builds an internal agent graph (using system prompts, tools and output schemas) and then returns an `AgentRun` object. The `AgentRun` can be used to async-iterate over the nodes of the graph as they are executed. This is the API to use if you want to consume the outputs coming from each LLM model response, or the stream of events coming from the execution of tools.

The `AgentRun` also provides methods to access the full message history, new messages, and usage statistics, and the final result of the run once it has completed.

For more details, see the documentation of `AgentRun`.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    nodes = []
    async with agent.iter('What is the capital of France?') as agent_run:
        async for node in agent_run:
            nodes.append(node)
    print(nodes)
    '''
    [
        UserPromptNode(
            user_prompt='What is the capital of France?',
            instructions_functions=[],
            system_prompts=(),
            system_prompt_functions=[],
            system_prompt_dynamic_functions={},
        ),
        ModelRequestNode(
            request=ModelRequest(
                parts=[
                    UserPromptPart(
                        content='What is the capital of France?',
                        timestamp=datetime.datetime(...),
                    )
                ],
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        CallToolsNode(
            model_response=ModelResponse(
                parts=[TextPart(content='The capital of France is Paris.')],
                usage=RequestUsage(
                    cost=Decimal('0.000196'), input_tokens=56, output_tokens=7
                ),
                model_name='gpt-5.2',
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        End(data=FinalResult(output='The capital of France is Paris.')),
    ]
    '''
    print(agent_run.result.output)
    #> The capital of France is Paris.
```

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[[`AgentRun`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun)\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for DBOS durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### override

```python
def override(
    *,
    name: str | _utils.Unset = _utils.UNSET,
    deps: AgentDepsT | _utils.Unset = _utils.UNSET,
    model: models.Model | models.KnownModelName | str | _utils.Unset = _utils.UNSET,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | _utils.Unset = _utils.UNSET,
    tools: Sequence[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]] | _utils.Unset = _utils.UNSET,
    native_tools: Sequence[AgentNativeTool[AgentDepsT]] | _utils.Unset = _utils.UNSET,
    instructions: _instructions.AgentInstructions[AgentDepsT] | _utils.Unset = _utils.UNSET,
    metadata: AgentMetadata[AgentDepsT] | _utils.Unset = _utils.UNSET,
    model_settings: AgentModelSettings[AgentDepsT] | _utils.Unset = _utils.UNSET,
    retries: int | AgentRetries | _utils.Unset = _utils.UNSET,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> Generator[None]
```

Context manager to temporarily override agent configuration.

This is particularly useful when testing. You can find an example of this [here](https://pydantic.dev/docs/ai/guides/testing/#overriding-model-via-pytest-fixtures).

###### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The name to use instead of the name passed to the agent constructor and agent run.

**`deps`** : `AgentDepsT` | `_utils.Unset` _Default:_ `_utils.UNSET`

The dependencies to use instead of the dependencies passed to the agent run.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The model to use instead of the model passed to the agent run.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The toolsets to use instead of the toolsets passed to the agent constructor and agent run.

**`tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\] | `ToolFuncEither`\[`AgentDepsT`, ...\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The tools to use instead of the tools registered with the agent.

**`native_tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentNativeTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.AgentNativeTool)\[`AgentDepsT`\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The native tools to use instead of the agent's configured native tools.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The instructions to use instead of the instructions registered with the agent.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The metadata to use instead of the metadata passed to the agent constructor. When set, any per-run `metadata` argument is ignored.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The model settings to use instead of the model settings passed to the agent constructor. When set, any per-run `model_settings` argument is ignored.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | `_utils.Unset` _Default:_ `_utils.UNSET`

The retry budgets to use instead of the agent-level configuration. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). When set, any per-run `retries` argument is ignored.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply as overrides.

### DBOSParallelExecutionMode

The mode for executing tool calls in DBOS durable workflows. This is a subset of the ParallelExecutionMode because 'parallel' cannot guarantee deterministic ordering.

**Default:** `Literal['sequential', 'parallel_ordered_events']`

### TaskConfig

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Configuration for a task in Prefect.

These options are passed to the `@task` decorator.

#### Attributes

##### retries

Maximum number of retries for the task.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### retry\_delay\_seconds

Delay between retries in seconds. Can be a single value or a list for custom backoff.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`float`](https://docs.python.org/3/builtins/functions.html#float)\]

##### retry\_condition\_fn

Predicate deciding whether a failed task should be retried.

**Type:** `RetryConditionCallable`

##### timeout\_seconds

Maximum time in seconds for the task to complete.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

##### cache\_policy

Prefect cache policy for the task.

**Type:** `CachePolicy`

##### persist\_result

Whether to persist the task result.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### result\_storage

Prefect result storage for the task. Should be a storage block or a block slug like `s3-bucket/my-storage`.

**Type:** `ResultStorage`

##### log\_prints

Whether to log print statements from the task.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### PrefectOperationNamer

**Bases:** `DurableOperationNamer`

Generate Prefect task names that are persisted compatibility data.

These names must essentially never change. Changing them can strand in-flight flows and recorded runs.

### PrefectDurability

**Bases:** `BaseDurabilityCapability[AgentDepsT]`

Capability that makes an agent durable by routing I/O through Prefect tasks.

Built on the declarative base: the base owns toolset/model/event assembly, and this capability contributes the Prefect operation backend, transparency gate, and task configuration.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    models: Mapping[str, Model] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    name: str | None = None,
    event_stream_handler_task_config: TaskConfig | None = None,
    model_task_config: TaskConfig | None = None,
    mcp_task_config: TaskConfig | None = None,
    tool_task_config: TaskConfig | None = None,
)
```

Create a PrefectDurability capability.

The agent's model, name, and toolsets are discovered automatically.

###### Parameters

**`models`** : [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `Model`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional models keyed by ID for runtime model switching. The agent's primary model is always registered as `'default'`. A `Model` instance can't be serialized across the task boundary, so a run-time model (via `agent.run(model=...)` / `agent.override(model=...)`, or swapped in by an outer capability) has to be registered here and referenced by key (or passed as the registered instance); an unregistered instance is rejected, because rebuilding it from its `model_id` would build a different model. Model-name strings never need registering: they cross as the string the caller wrote and are built inside the task by the agent's `resolve_model_id` capability chain, then `infer_model`. To build a specific instance inside the task from such a string -- a custom provider, or per-user credentials carried on `deps` -- use the [`ResolveModelId`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ResolveModelId) capability.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler. Model events are handled live inside model-request tasks, and tool events are handled in per-event tasks.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unique agent name used in the Prefect task names. Defaults to the agent's `name` when the capability is bound.

**`event_stream_handler_task_config`** : `TaskConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Prefect task config for event stream handler tasks.

**`model_task_config`** : `TaskConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Prefect task config for model request tasks.

**`mcp_task_config`** : `TaskConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Prefect task config for MCP server tasks.

**`tool_task_config`** : `TaskConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Default Prefect task config for tool call tasks. Per-tool overrides are configured via tool metadata, e.g. `@my_toolset.tool(metadata={'prefect': TaskConfig(...)})` (or `False` to skip task wrapping), or via the [`SetToolMetadata`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.SetToolMetadata) capability.

### PrefectModel

**Bases:** `WrapperModel`

A wrapper for Model that integrates with Prefect, turning request and request\_stream into Prefect tasks.

#### Methods

##### request

`@async`

```python
def request(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> ModelResponse
```

Make a model request, wrapped as a Prefect task when in a flow.

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

##### cancel\_suspended\_response

`@async`

```python
def cancel_suspended_response(response: ModelResponse) -> None
```

Cancel a server-side suspended/background response, wrapped as a Prefect task.

The teardown performs a raw HTTP call to the provider, so it runs as a task (durable, retried) rather than inline in the flow.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### request\_stream

`@async`

```python
def request_stream(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
    run_context: RunContext[Any] | None = None,
) -> AsyncGenerator[StreamedResponse]
```

Make a streaming model request.

When inside a Prefect flow, the stream is consumed within a task and a non-streaming response is returned. When not in a flow, behaves normally.

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[`StreamedResponse`\]

### PrefectFunctionToolset

**Bases:** `DurableFunctionToolset[AgentDepsT]`

A wrapper for `FunctionToolset` that runs tool calls as Prefect tasks inside flows.

### PrefectAgent

**Bases:** `WrapperAgent[AgentDepsT, OutputDataT]`

#### Methods

##### \_\_init\_\_

```python
def __init__(
    wrapped: AbstractAgent[AgentDepsT, OutputDataT],
    *,
    name: str | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    mcp_task_config: TaskConfig | None = None,
    model_task_config: TaskConfig | None = None,
    tool_task_config: TaskConfig | None = None,
    tool_task_config_by_name: dict[str, TaskConfig | None] | None = None,
    event_stream_handler_task_config: TaskConfig | None = None,
    prefectify_toolset_func: Callable[[AbstractToolset[AgentDepsT], TaskConfig, TaskConfig, dict[str, TaskConfig | None]], AbstractToolset[AgentDepsT]] = prefectify_toolset,
)
```

Wrap an agent to enable it with Prefect durable flows, by automatically offloading model requests, tool calls, and MCP server communication to Prefect tasks.

After wrapping, the original agent can still be used as normal outside of the Prefect flow.

###### Parameters

**`wrapped`** : `AbstractAgent`\[`AgentDepsT`, `OutputDataT`\]

The agent to wrap.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional unique agent name to use as the Prefect flow name prefix. If not provided, the agent's `name` will be used.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler to use instead of the one set on the wrapped agent.

**`mcp_task_config`** : `TaskConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base Prefect task config to use for MCP server tasks. If no config is provided, use the default settings of Prefect.

**`model_task_config`** : `TaskConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Prefect task config to use for model request tasks. If no config is provided, use the default settings of Prefect.

**`tool_task_config`** : `TaskConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The default Prefect task config to use for tool calls. If no config is provided, use the default settings of Prefect.

**`tool_task_config_by_name`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `TaskConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Per-tool task configuration. Keys are tool names, values are TaskConfig or None (None disables task wrapping for that tool).

**`event_stream_handler_task_config`** : `TaskConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Prefect task config to use for the event stream handler task. If no config is provided, use the default settings of Prefect.

**`prefectify_toolset_func`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\], `TaskConfig`, `TaskConfig`, [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `TaskConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None)\]\], [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] _Default:_ `prefectify_toolset`

Optional function to use to prepare toolsets for Prefect by wrapping them in a `PrefectWrapperToolset` that moves methods that require IO to Prefect tasks. If not provided, only `FunctionToolset` and `MCPToolset` will be prepared for Prefect. The function takes the toolset, the task config, the tool-specific task config, and the tool-specific task config by name.

##### run

`@async`

```python
def run(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[OutputDataT]
def run(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[RunOutputDataT]
```

Run the agent with a user prompt in async mode.

This method builds an internal agent graph (using system prompts, tools and result schemas) and then runs the graph to completion. The result of the run is returned.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    agent_run = await agent.run('What is the capital of France?')
    print(agent_run.output)
    #> The capital of France is Paris.
```

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for Prefect durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler to use for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### run\_sync

```python
def run_sync(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[OutputDataT]
def run_sync(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[RunOutputDataT]
```

Synchronously run the agent with a user prompt.

This is a convenience method that wraps [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) with `loop.run_until_complete(...)`. You therefore can't use this method inside async code or if there's an active event loop.

This method cannot be used inside a synchronous tool, output function, or other function called during an agent run.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

result_sync = agent.run_sync('What is the capital of Italy?')
print(result_sync.output)
#> The capital of Italy is Rome.
```

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for Prefect durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler to use for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### run\_stream

`@async`

```python
def run_stream(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[StreamedRunResult[AgentDepsT, OutputDataT]]
def run_stream(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[StreamedRunResult[AgentDepsT, RunOutputDataT]]
```

Run the agent with a user prompt in async mode, returning a streamed response.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    async with agent.run_stream('What is the capital of the UK?') as response:
        print(await response.get_output())
        #> The capital of the UK is London.
```

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[`StreamedRunResult`\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for Prefect durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional event stream handler to use for this run. It will receive all the events up until the final result is found, which you can then read or stream from inside the context manager.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### run\_stream\_events

```python
def run_stream_events(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRunEvents[OutputDataT]]
def run_stream_events(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRunEvents[RunOutputDataT]]
```

Run the agent with a user prompt in async mode and stream events from the run.

This is a convenience method that wraps [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) and uses the `event_stream_handler` kwarg to get a stream of events from the run.

Example:

```python
from pydantic_ai import Agent, AgentRunResultEvent, AgentStreamEvent

agent = Agent('openai:gpt-5.2')

async def main():
    collected: list[AgentStreamEvent | AgentRunResultEvent] = []
    async with agent.run_stream_events('What is the capital of France?') as events:
        async for event in events:
            collected.append(event)
    print(collected)
    '''
    [
        PartStartEvent(index=0, part=TextPart(content='The capital of ')),
        FinalResultEvent(tool_name=None, tool_call_id=None),
        PartDeltaEvent(index=0, delta=TextPartDelta(content_delta='France is Paris. ')),
        PartEndEvent(
            index=0, part=TextPart(content='The capital of France is Paris. ')
        ),
        AgentRunResultEvent(
            result=AgentRunResult(output='The capital of France is Paris. ')
        ),
    ]
    '''
```

Arguments are the same as for [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run), except that `event_stream_handler` is now allowed.

###### Returns

`AbstractAsyncContextManager`\[[`AgentRunEvents`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRunEvents)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- An async context manager that yields an [`AgentRunEvents`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRunEvents) `AbstractAsyncContextManager`\[[`AgentRunEvents`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRunEvents)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- handle over `AgentStreamEvent`s ending with a final `AgentRunResultEvent` carrying the run result.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for Prefect durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### iter

`@async`

```python
def iter(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRun[AgentDepsT, OutputDataT]]
def iter(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRun[AgentDepsT, RunOutputDataT]]
```

A contextmanager which can be used to iterate over the agent graph's nodes as they are executed.

This method builds an internal agent graph (using system prompts, tools and output schemas) and then returns an `AgentRun` object. The `AgentRun` can be used to async-iterate over the nodes of the graph as they are executed. This is the API to use if you want to consume the outputs coming from each LLM model response, or the stream of events coming from the execution of tools.

The `AgentRun` also provides methods to access the full message history, new messages, and usage statistics, and the final result of the run once it has completed.

For more details, see the documentation of `AgentRun`.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    nodes = []
    async with agent.iter('What is the capital of France?') as agent_run:
        async for node in agent_run:
            nodes.append(node)
    print(nodes)
    '''
    [
        UserPromptNode(
            user_prompt='What is the capital of France?',
            instructions_functions=[],
            system_prompts=(),
            system_prompt_functions=[],
            system_prompt_dynamic_functions={},
        ),
        ModelRequestNode(
            request=ModelRequest(
                parts=[
                    UserPromptPart(
                        content='What is the capital of France?',
                        timestamp=datetime.datetime(...),
                    )
                ],
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        CallToolsNode(
            model_response=ModelResponse(
                parts=[TextPart(content='The capital of France is Paris.')],
                usage=RequestUsage(
                    cost=Decimal('0.000196'), input_tokens=56, output_tokens=7
                ),
                model_name='gpt-5.2',
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        End(data=FinalResult(output='The capital of France is Paris.')),
    ]
    '''
    print(agent_run.result.output)
    #> The capital of France is Paris.
```

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[[`AgentRun`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun)\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Unsupported for Prefect durable execution; passing one raises `UserError`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### override

```python
def override(
    *,
    name: str | _utils.Unset = _utils.UNSET,
    deps: AgentDepsT | _utils.Unset = _utils.UNSET,
    model: models.Model | models.KnownModelName | str | _utils.Unset = _utils.UNSET,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | _utils.Unset = _utils.UNSET,
    tools: Sequence[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]] | _utils.Unset = _utils.UNSET,
    native_tools: Sequence[AgentNativeTool[AgentDepsT]] | _utils.Unset = _utils.UNSET,
    instructions: _instructions.AgentInstructions[AgentDepsT] | _utils.Unset = _utils.UNSET,
    metadata: AgentMetadata[AgentDepsT] | _utils.Unset = _utils.UNSET,
    model_settings: AgentModelSettings[AgentDepsT] | _utils.Unset = _utils.UNSET,
    retries: int | AgentRetries | _utils.Unset = _utils.UNSET,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> Generator[None]
```

Context manager to temporarily override agent configuration.

This is particularly useful when testing. You can find an example of this [here](https://pydantic.dev/docs/ai/guides/testing/#overriding-model-via-pytest-fixtures).

###### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The name to use instead of the name passed to the agent constructor and agent run.

**`deps`** : `AgentDepsT` | `_utils.Unset` _Default:_ `_utils.UNSET`

The dependencies to use instead of the dependencies passed to the agent run.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The model to use instead of the model passed to the agent run.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The toolsets to use instead of the toolsets passed to the agent constructor and agent run.

**`tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\] | `ToolFuncEither`\[`AgentDepsT`, ...\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The tools to use instead of the tools registered with the agent.

**`native_tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentNativeTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.AgentNativeTool)\[`AgentDepsT`\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The native tools to use instead of the agent's configured native tools.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The instructions to use instead of the instructions registered with the agent.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The metadata to use instead of the metadata passed to the agent constructor. When set, any per-run `metadata` argument is ignored.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The model settings to use instead of the model settings passed to the agent constructor. When set, any per-run `model_settings` argument is ignored.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | `_utils.Unset` _Default:_ `_utils.UNSET`

The retry budgets to use instead of the agent-level configuration. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). When set, any per-run `retries` argument is ignored.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply as overrides.

### PrefectMCPToolset

**Bases:** `DurableMCPToolset[AgentDepsT]`

A wrapper for `MCPToolset` that runs tool calls as Prefect tasks inside flows.

---
