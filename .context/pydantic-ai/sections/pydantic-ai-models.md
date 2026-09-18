# [pydantic_ai.models](https://pydantic.dev/docs/ai/api/models/base/)

# pydantic\_ai.models

Logic related to making requests to an LLM.

The aim here is to make a common interface for different LLMs, so that the rest of the code can be agnostic to the specific LLM being used.

### ModelRequestParameters

Configuration for an agent's request to a model, specifically related to tools and output handling.

#### Attributes

##### tool\_visibility

Maps each function tool name to its resolved [`ToolVisibility`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ToolVisibility).

`None` on authored parameters; [`Model.prepare_request`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model.prepare_request) populates an entry for every function tool, so a resolved request always carries a dict -- empty exactly when there are no function tools. Output tools never get entries because they are always plain `tools` entries; [`visibility_of`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestParameters.visibility_of) treats their absent entries like `'visible'`. The no-defaults `repr` omits the field until resolution, so authored parameters print as authored and resolved state stays visible.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `ToolVisibility`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### revealed\_tool\_names

Names history has revealed so far, derived from the outgoing message list before each request.

Discovered means evidenced by history; revealed means represented on this request's wire state.

Input to visibility resolution: `ToolDefinition.defer_loading` records what the author asked for and stays set after a reveal, so this answers the separate question of what the model can see _now_. History can name tools that no longer exist in the current run's definitions; those are dropped where this is derived, so it is a subset of `function_tools`' names by construction.

**Type:** [`set`](https://docs.python.org/3/reference/expressions.html#set)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(set[str]), repr=False)`

##### deferred\_capability\_ids

IDs of the run's capabilities that defer their loading.

Read from the capability instances themselves, so it means what it says. It cannot be derived from the function tools: `ToolDefinition.capability_id` records which capability _contributed_ a tool, and `defer_loading` is set both by a deferred capability and by a search-gated tool inside an always-on one -- so the two cases are indistinguishable from the definitions alone.

Used to answer "may this tool be revealed yet?": a tool whose `capability_id` is in this set is gated on that capability being loaded, while one whose owner is absent here is gated only on its own discovery.

**Type:** [`set`](https://docs.python.org/3/reference/expressions.html#set)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(set[str]), repr=False)`

##### instruction\_parts

Structured instruction parts with metadata about their origin (static vs dynamic).

Static instructions (`dynamic=False`) come from literal strings passed to `Agent(instructions=...)`. Dynamic instructions (`dynamic=True`) come from `@agent.instructions` functions, `TemplateStr`, or toolset `get_instructions()` methods.

Models that support granular caching (e.g. Anthropic, Bedrock) use this to place cache boundaries at the static/dynamic instruction boundary.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`InstructionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### thinking

Resolved thinking/reasoning configuration for this request.

`None` means the model should use its default behavior. Set by the base `Model.prepare_request()` from the unified `thinking` field in `ModelSettings`, after checking that the model's profile supports thinking.

**Type:** `ThinkingLevel` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### declared\_tool\_defs

Definitions represented in the provider's ordinary `tools` collection.

The visibility filter applies to function tools only: output tools are always plain `tools` entries, so they are included unconditionally rather than keyed through a name-indexed filter a hidden function tool could shadow.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition)\]

##### declared\_function\_tools

Function tools represented in the provider's ordinary `tools` collection.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition)\]

#### Methods

##### visibility\_of

```python
def visibility_of(tool_name: str) -> ToolVisibility
```

The resolved [`ToolVisibility`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ToolVisibility) for `tool_name`.

For parameters constructed directly rather than resolved by [`Model.prepare_request`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model.prepare_request), deferred function tools default to `'withheld'` and every other name defaults to `'visible'`.

###### Returns

`ToolVisibility`

##### with\_default\_output\_mode

```python
def with_default_output_mode(
    output_mode: StructuredOutputMode,
) -> ModelRequestParameters
```

Set the default output mode if the current mode is 'auto', atomically updating allow\_text\_output.

No-op if the current output\_mode is not 'auto'. This ensures the two fields stay in sync -- output\_mode='tool' implies allow\_text\_output=False, while 'native' and 'prompted' imply allow\_text\_output=True.

###### Returns

`ModelRequestParameters`

### AbstractModel

**Bases:** `ABC`

Shared identity for request-response and realtime models.

#### Attributes

##### model\_name

The model name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The model provider, ex: openai.

Use to populate the `gen_ai.system` OpenTelemetry semantic convention attribute, so should use well-known values listed in [https://opentelemetry.io/docs/specs/semconv/attributes-registry/gen-ai/#gen-ai-system](https://opentelemetry.io/docs/specs/semconv/attributes-registry/gen-ai/#gen-ai-system) when applicable.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### base\_url

The base URL for the provider API, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### model\_id

The fully qualified model name in `'provider:model_name'` format.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### context\_window

The maximum number of tokens the model can handle at once, input and output combined, or `None` when unknown.

Models with a profile read it from the profile's `context_window`, which is filled from [genai-prices](https://github.com/pydantic/genai-prices) when no profile layer sets it. Wrapper models report their wrapped model's; a [`FallbackModel`](https://pydantic.dev/docs/ai/api/models/fallback/#pydantic_ai.models.fallback.FallbackModel) reports the smallest among its candidates.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### label

Human-friendly display label for the model.

Handles common patterns:

-   gpt-5 -> GPT 5
-   claude-sonnet-4-5 -> Claude Sonnet 4.5
-   gemini-2.5-pro -> Gemini 2.5 Pro
-   meta-llama/llama-3-70b -> Llama 3 70b (OpenRouter style)

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_aenter\_\_

`@async`

```python
def __aenter__() -> Self
```

Enter the model context.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self)

##### \_\_aexit\_\_

`@async`

```python
def __aexit__(
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: TracebackType | None,
) -> bool | None
```

Exit the model context.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### ModelRequestContext

Context for model request hooks.

Wrapping these parameters in a dataclass instead of a tuple makes the signature future-proof: new fields can be added without breaking existing implementations.

A [`before_model_request`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.before_model_request) hook returns a context, so modifying one is normally `dataclasses.replace(request_context, ...)`. Every field is therefore settable through `replace()`, including `model_id` and `streaming`: the agent graph sets those two immediately before calling the hook, and `replace()` re-initializes any `init=False` field to its default, so declaring them that way silently zeroed both for any hook that copied its context -- costing a streamed run its `streaming` flag and a durable-execution worker the selection token it re-resolves an aliased model from. They are still set by the graph rather than by a caller; passing either to a fresh `ModelRequestContext` is not meaningful.

#### Attributes

##### model\_request\_parameters

The tool, output, and instruction configuration for this request.

[`instruction_parts`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestParameters.instruction_parts) is the source of truth for the instructions in the agent flow: a [`before_model_request`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.before_model_request) hook that rewrites them changes what the model receives, and the [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest) recorded in message history is re-rendered from them afterwards, so history and traces keep showing what was sent. Assigning to that message's `instructions` instead is not propagated back into the parts, and so does not reach the model.

**Type:** `ModelRequestParameters`

##### model\_id

The model-name string this request's model was selected/resolved from, if any.

This is the _selection_ token -- e.g. `'openai:gpt-5.6-sol'`, or an alias like `'tenant-x'` that a [`resolve_model_id`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.resolve_model_id) capability turned into a concrete model -- so it can differ from the resolved model's own `model_id`. `None` when the model was supplied as an instance rather than resolved from a string.

Durable-execution capabilities carry this across the activity/step/task boundary in preference to the resolved model's own `model_id`, so an aliased model round-trips as the original string the worker-side resolution chain can re-resolve. Only meaningful while `model` is still the run's resolved model -- a model swapped in by a hook invalidates it.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### streaming

Whether the agent loop expects to iterate the model response as a stream.

Set for streamed runs -- `run_stream()`, `run_stream_events()`, `iter()`'s node streaming -- and for `run()` when an `event_stream_handler` is set or a capability overrides `wrap_run_event_stream` (e.g. `ProcessEventStream`, or a durability capability's `event_stream_handler=`). There is no separate `before_model_request_stream` hook -- streaming and non-streaming requests share the same hooks -- so this field is how a hook can tell them apart. Read-only from hooks: reassigning it doesn't change how the loop consumes the response.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

### ModelResolutionContext

**Bases:** `Generic[ModelContextDepsT]`

Context used to resolve a model ID before a model is available.

This is narrower than [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) because model resolution happens before a run context can contain its resolved model.

#### Attributes

##### agent

The agent whose model is being resolved.

**Type:** `AbstractAgent`\[`ModelContextDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### deps

The dependencies supplied for this run.

**Type:** `ModelContextDepsT`

### ModelSelectionContext

**Bases:** `ModelResolutionContext[ModelContextDepsT]`

Context used by a capability to select the model for a request step.

#### Attributes

##### model

The lower-precedence model on the first step, then the model used for the previous step.

**Type:** `Model` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### run\_step

The request step being selected, starting at `1`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### messages

The message history available before this request step.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### usage

Usage accumulated by the run before this request step.

**Type:** [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage)

### Model

**Bases:** [`AbstractModel`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.AbstractModel), `Generic[InterfaceClient]`

Abstract class for a model.

#### Attributes

##### supported\_tool\_deferral\_modes

`tool_deferral_mode` values this adapter's renderer implements.

A profile may claim a mode for the model family, but the claim only takes effect when the adapter class declares it here: `Model.tool_deferral_mode` intersects the two, so a `Model` subclass that declares nothing (the default) never resolves tools to a wire shape it cannot render, no matter what a pass-through vendor profile claims.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[`ToolDeferralMode`\] **Default:** `frozenset()`

##### supported\_tool\_addition\_modes

`tool_addition_mode` values this adapter's renderer implements. See `supported_tool_deferral_modes`.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[`ToolAdditionMode`\] **Default:** `frozenset()`

##### compaction\_requires\_encrypted\_content

Whether this adapter's API only honors a [`CompactionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CompactionPart) that carries encrypted content.

When set, a part without it isn't a wire boundary: the adapter would omit it, so letting it hide the earlier history would send nothing in its place.

Declared by the adapter rather than the model profile: how an API carries compaction state is a property of the API, not of the model behind it -- the same model reached through OpenAI's Chat Completions and Responses APIs answers differently, and eight providers route a profile of their own through `OpenAIResponsesModel`. Independent of `compaction_retains_standing_prompt`, which today's two adapters happen to answer the same way.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### compaction\_retains\_standing\_prompt

Whether this adapter's compaction item keeps serving the leading system items of the window it replaced.

When set, re-sending the standing prompt after the boundary would duplicate it. When not (the default), the standing prompt travels in a per-request channel rebuilt from those items, so the trim has to re-insert them or it is silently dropped from every subsequent request. See `compaction_requires_encrypted_content` for why this is declared here and not on the profile.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### provider

The provider for this model, if any.

**Type:** `Provider`\[`InterfaceClient`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### settings

Get the model settings.

**Type:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### tool\_deferral\_mode

The effective schema-deferral mode: the profile's claim, if this adapter renders it.

**Type:** `ToolDeferralMode` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### tool\_addition\_mode

The effective tool-addition mode: the profile's claim, if this adapter renders it.

**Type:** `ToolAdditionMode` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### context\_window

The resolved profile's [`context_window`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile.context_window).

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### profile

The model profile.

Resolution order (later layers override earlier ones):

1.  `DEFAULT_PROFILE` -- base values for every key in `ModelProfile`.
2.  The provider's `model_profile(model_name)` result -- provider-specific defaults for this model.
3.  A best-effort `context_window` value from [genai-prices](https://github.com/pydantic/genai-prices), unless the provider or a partial user profile explicitly set the field (including to `None`).
4.  The user's `profile=` argument -- partial dict merged on top, OR a callable `(default) -> profile` for full control.

After resolution we compute the intersection of the profile's `supported_native_tools` and the model class's implemented tools, ensuring `model.profile['supported_native_tools']` is the single source of truth for what's actually usable.

**Type:** [`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    settings: ModelSettings | None = None,
    profile: ModelProfileSpec | None = None,
) -> None
```

Initialize the model with optional settings and profile.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use.

##### \_\_aenter\_\_

`@async`

```python
def __aenter__() -> Self
```

Enter the model context, delegating to the provider to manage its HTTP client lifecycle.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self)

##### \_\_aexit\_\_

`@async`

```python
def __aexit__(
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: TracebackType | None,
) -> bool | None
```

Exit the model context, closing the provider's HTTP client if it owns one.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### resolve\_prompt\_cache\_retention

```python
def resolve_prompt_cache_retention(
    model_settings: ModelSettings | None,
) -> timedelta | None
```

Resolve prompt cache retention requested by provider-specific model settings.

The model's default settings are merged with the per-request `model_settings`. Only provider-specific settings are currently considered; a future unified cache setting is not yet an input. If multiple active settings request different retention periods, the longest period wins because any longer-lived cache breakpoint can keep the corresponding prompt prefix available. Models without a provider-specific retention setting return `None`.

###### Returns

`timedelta` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### request

`@abstractmethod`

`@async`

```python
def request(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> ModelResponse
```

Make a request to the model.

This is ultimately called by `pydantic_ai._agent_graph.ModelRequestNode._make_request(...)`.

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

##### count\_tokens

`@async`

```python
def count_tokens(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> RequestUsage
```

Make a request to the model for counting tokens.

###### Returns

[`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage)

##### compact\_messages

`@async`

```python
def compact_messages(
    request_context: ModelRequestContext,
    *,
    instructions: str | None = None,
) -> ModelResponse
```

Compact messages to reduce conversation context size.

This method is optional and only supported by specific providers (e.g. OpenAI Responses API). Providers that support compaction override this method with their implementation.

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

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

Make a request to the model and return a streaming response.

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[`StreamedResponse`\]

##### cancel\_suspended\_response

`@async`

```python
def cancel_suspended_response(response: ModelResponse) -> None
```

Cancel a server-side suspended/background response (e.g. an OpenAI background job).

Called when a continuation is abandoned via cancellation or error. No-op by default; model classes with cancellable server-side jobs override this.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### continuation\_delay

```python
def continuation_delay(response: ModelResponse) -> float | None
```

Seconds to wait before continuing a suspended response, or `None` to continue immediately.

Called between the segments of a suspended turn. `None` by default (e.g. Anthropic `pause_turn` continues immediately); a model that polls a server-side job (e.g. OpenAI background mode) overrides this to return a poll interval so the graph doesn't busy-poll.

###### Returns

[`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### customize\_request\_parameters

```python
def customize_request_parameters(
    model_request_parameters: ModelRequestParameters,
) -> ModelRequestParameters
```

Customize the request parameters for the model.

This method can be overridden by subclasses to modify the request parameters before sending them to the model. In particular, this method can be used to make modifications to the generated tool JSON schemas if necessary for vendor/model-specific reasons.

###### Returns

`ModelRequestParameters`

##### prepare\_request

```python
def prepare_request(
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> tuple[ModelSettings | None, ModelRequestParameters]
```

Prepare request inputs before they are passed to the provider.

This merges the given `model_settings` with the model's own `settings` attribute and ensures `customize_request_parameters` is applied to the resolved [`ModelRequestParameters`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestParameters). Subclasses can override this method if they need to customize the preparation flow further, but most implementations should simply call `self.prepare_request(...)` at the start of their `request` (and related) methods.

###### Returns

[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None), `ModelRequestParameters`\]

##### prepare\_messages

```python
def prepare_messages(
    messages: list[ModelMessage],
    model_request_parameters: ModelRequestParameters | None = None,
) -> list[ModelMessage]
```

Pre-process the message history before it's handed to the adapter's message-prep step.

Translates typed `NativeToolSearch*Part` instances carried over from a different provider (e.g. Anthropic to OpenAI Responses), or any native provider when the active model doesn't support `ToolSearchTool`, into the local-shape `ToolSearch*Part` instances. This splits the single `ModelResponse(call+return)` carrying the inline server-side result into `ModelResponse(call) + ModelRequest(return)` so the adapter can render the provider-agnostic exchange.

Also wraps non-leading `SystemPromptPart`s as `<system>`\-tagged `UserPromptPart`s when the profile's `supports_inline_system_prompts` is `False`, and converts `SpeechPart`s from realtime session history into `UserPromptPart`s / `TextPart`s that any model can consume.

Subclasses normally don't need to override this; the framework calls it on the agent's behalf in `_agent_graph._make_request` so per-adapter message-prep code sees a homogeneous shape regardless of which provider produced the prior turn.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

###### Parameters

**`messages`** : [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

The history to pre-process.

**`model_request_parameters`** : `ModelRequestParameters` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The parameters this history will be sent with. Optional, and only needed to render a `ToolAvailabilityDeltaPart` on a model with no native way to express one: whether that reveal has to be a mechanism or can just be a statement depends on whether any tool actually goes on the wire with its schema withheld, which the profile alone can't answer. Omitting it falls back to the adapter's effective mode, which differs only for a corpus mixing capability-gated and standalone deferred tools. Framework callers pass it.

##### supported\_native\_tools

`@classmethod`

```python
def supported_native_tools(cls) -> frozenset[type[AbstractNativeTool]]
```

Return the set of native tool types this model class can handle.

Subclasses should override this to reflect their actual capabilities. Default is empty set - subclasses must explicitly declare support.

###### Returns

[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

### StreamedResponse

**Bases:** `ABC`

Streamed response from an LLM when calling a tool.

#### Attributes

##### state

Lifecycle state of the response.

**Type:** [`ModelResponseState`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponseState) **Default:** `field(default='complete', init=False)`

##### usage

Get the usage of the response so far. This will not be the final usage until the stream is exhausted.

**Type:** [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage)

##### model\_name

Get the model name of the response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_name

Get the provider name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### provider\_url

Get the provider base URL.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

##### cancelled

Whether the stream has been cancelled via `cancel()`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### Methods

##### \_\_aiter\_\_

```python
def __aiter__() -> AsyncIterator[ModelResponseStreamEvent]
```

Stream the response as an async iterable of [`ModelResponseStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponseStreamEvent)s.

This proxies the `_event_iterator()` and emits all events, while also checking for matches on the result schema and emitting a [`FinalResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FinalResultEvent) if/when the first match is found.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[[`ModelResponseStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponseStreamEvent)\]

##### cancel

`@async`

```python
def cancel() -> None
```

Cancel local stream consumption and request provider shutdown.

Sets `self._cancelled = True` before delegating to `close_stream()` so the flag is visible to any iterator that observes the transport error raised when the underlying connection is torn down, even if `close_stream()` itself raises.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_stream\_cancel\_errors

```python
def get_stream_cancel_errors() -> tuple[type[BaseException], ...]
```

Return transport errors caused by `cancel()` tearing down the stream.

The default covers model classes whose SDKs iterate HTTP responses directly (Anthropic, OpenAI, Groq, Mistral, Google GenAI, and HuggingFace), since they let bare `httpx2` (or legacy `httpx`) errors propagate from chunk reads. Model classes that use other transports (for example gRPC or botocore) should override this method.

###### Returns

[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[[`BaseException`](https://docs.python.org/3/builtins/exceptions.html#BaseException)\], ...\]

##### close\_stream

`@async`

```python
def close_stream() -> None
```

Close the provider stream and any exposed HTTP or gRPC transport.

Model classes must override this to close the local stream and, where the provider SDK exposes one, its transport. Integrations that cannot support local cancellation should leave the default implementation so `cancel()` fails clearly.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get

```python
def get() -> ModelResponse
```

Build a [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse) from the data received from the stream so far.

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

##### time\_to\_first\_chunk

```python
def time_to_first_chunk(request_start: float) -> float | None
```

Seconds from `request_start` to the first chunk surfaced to the consumer, or `None` if nothing was yielded.

`request_start` must be a `time.perf_counter()` reading taken when the request was issued. The first-chunk instant is stamped on the first `async for` pull, so the result reflects when the consumer _received_ the first event: it includes any consumer-side iteration delay (debouncing, batching, or awaiting other work) on top of the chunk's transit time, which for eager consumers is negligible.

###### Returns

[`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### known\_model\_names

`@cached`

```python
def known_model_names() -> tuple[str, ...]
```

Return every model name known to [`KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName).

This is the public, stable way to enumerate the known model ids. Prefer it over introspecting the `KnownModelName` type alias directly (e.g. `get_args(KnownModelName.__value__)`), which is not part of the public API and would break if the alias were ever recomposed.

#### Returns

[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), ...\]

### check\_allow\_model\_requests

```python
def check_allow_model_requests() -> None
```

Check if model requests are allowed.

If you're defining your own models that have costs or latency associated with their use, you should call this at the top of each method that sends a request to the provider: [`Model.request`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model.request), [`Model.request_stream`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model.request_stream), [`Model.count_tokens`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model.count_tokens), [`Model.compact_messages`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model.compact_messages), [`EmbeddingModel.embed`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel.embed), [`EmbeddingModel.count_tokens`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel.count_tokens) and [`ImageGenerationModel.generate`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel.generate).

Methods that produce their result locally don't need it -- for example [`OpenAIEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.openai.OpenAIEmbeddingModel)'s `count_tokens`, which tokenizes with `tiktoken` and never calls the provider. Neither does [`Model.cancel_suspended_response`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model.cancel_suspended_response), which deliberately omits it so an already-started job can still be cancelled after the flag is flipped.

#### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Raises

-   `RuntimeError` -- If model requests are not allowed.

### infer\_model

```python
def infer_model(
    model: Model | KnownModelName | str,
    provider_factory: Callable[[str], Provider[Any]] = infer_provider,
) -> Model
```

Infer the model from the name.

#### Returns

`Model`

#### Parameters

**`model`** : `Model` | `KnownModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Model name to instantiate, in the format of `provider:model`. Use the string "test" to instantiate TestModel.

**`provider_factory`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], `Provider`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] _Default:_ `infer_provider`

Function that instantiates a provider object. The provider name is passed into the function parameter. Defaults to `provider.infer_provider`.

### download\_item

`@async`

```python
def download_item(
    item: FileUrl,
    data_format: Literal['bytes'],
    type_format: Literal['mime', 'extension'] = 'mime',
) -> DownloadedItem[bytes]
def download_item(
    item: FileUrl,
    data_format: Literal['base64', 'base64_uri', 'text'],
    type_format: Literal['mime', 'extension'] = 'mime',
) -> DownloadedItem[str]
```

Download an item by URL and return the content as a bytes object or a (base64-encoded) string.

This function includes SSRF (Server-Side Request Forgery) protection:

-   Only http:// and https:// protocols are allowed
-   Private/internal IP addresses are blocked by default
-   Cloud metadata endpoints (169.254.169.254) are always blocked
-   Hostnames are resolved before requests to prevent DNS rebinding
-   Response bodies are limited to 50 MiB

Set `item.force_download='allow-local'` to allow private IP addresses.

#### Returns

`DownloadedItem`\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | `DownloadedItem`\[[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes)\]

#### Parameters

**`item`** : [`FileUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl)

The item to download.

**`data_format`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['bytes', 'base64', 'base64\_uri', 'text'\] _Default:_ `'bytes'`

The format to return the content in:

-   `bytes`: The raw bytes of the content.
-   `base64`: The base64-encoded content.
-   `base64_uri`: The base64-encoded content as a data URI.
-   `text`: The content as a string.

**`type_format`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['mime', 'extension'\] _Default:_ `'mime'`

The format to return the media type in:

-   `mime`: The media type as a MIME type.
-   `extension`: The media type as an extension.

#### Raises

-   `UserError` -- If the URL points to a YouTube video.
-   `ValueError` -- If the URL uses an unsupported protocol or targets a private/internal IP address (unless allow-local is set), or the body exceeds 50 MiB.

### override\_allow\_model\_requests

```python
def override_allow_model_requests(allow_model_requests: bool) -> Generator[None]
```

Context manager to temporarily override [`ALLOW_MODEL_REQUESTS`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ALLOW_MODEL_REQUESTS).

#### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

#### Parameters

**`allow_model_requests`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

Whether to allow model requests within the context.

### KnownModelName

Known model names that can be used with the `model` parameter of [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent).

`KnownModelName` is provided as a concise way to specify a model.

**Default:** `TypeAliasType('KnownModelName', Literal['anthropic:claude-fable-5', 'anthropic:claude-fable-5-1', 'anthropic:claude-haiku-4-5', 'anthropic:claude-haiku-4-5-20251001', 'anthropic:claude-mythos-5', 'anthropic:claude-mythos-5-1', 'anthropic:claude-mythos-preview', 'anthropic:claude-opus-4-5', 'anthropic:claude-opus-4-5-20251101', 'anthropic:claude-opus-4-6', 'anthropic:claude-opus-4-7', 'anthropic:claude-opus-4-8', 'anthropic:claude-opus-5', 'anthropic:claude-sonnet-4-5', 'anthropic:claude-sonnet-4-5-20250929', 'anthropic:claude-sonnet-4-6', 'anthropic:claude-sonnet-5', 'bedrock-mantle:openai.gpt-5.4', 'bedrock-mantle:openai.gpt-5.4-2026-03-05', 'bedrock-mantle:openai.gpt-5.5', 'bedrock-mantle:openai.gpt-5.5-2026-04-23', 'bedrock-mantle:openai.gpt-5.6-luna', 'bedrock-mantle:openai.gpt-5.6-sol', 'bedrock-mantle:openai.gpt-5.6-terra', 'bedrock-mantle:openai.gpt-oss-120b', 'bedrock-mantle:openai.gpt-oss-20b', 'bedrock-mantle:openai.gpt-oss-safeguard-120b', 'bedrock-mantle:openai.gpt-oss-safeguard-20b', 'bedrock:amazon.titan-text-express-v1', 'bedrock:amazon.titan-text-lite-v1', 'bedrock:amazon.titan-tg1-large', 'bedrock:anthropic.claude-3-5-haiku-20241022-v1:0', 'bedrock:anthropic.claude-3-5-sonnet-20240620-v1:0', 'bedrock:anthropic.claude-3-5-sonnet-20241022-v2:0', 'bedrock:anthropic.claude-3-7-sonnet-20250219-v1:0', 'bedrock:anthropic.claude-3-haiku-20240307-v1:0', 'bedrock:anthropic.claude-3-opus-20240229-v1:0', 'bedrock:anthropic.claude-3-sonnet-20240229-v1:0', 'bedrock:anthropic.claude-haiku-4-5-20251001-v1:0', 'bedrock:anthropic.claude-instant-v1', 'bedrock:anthropic.claude-opus-4-20250514-v1:0', 'bedrock:anthropic.claude-sonnet-4-20250514-v1:0', 'bedrock:anthropic.claude-sonnet-4-5-20250929-v1:0', 'bedrock:anthropic.claude-sonnet-4-6', 'bedrock:anthropic.claude-v2', 'bedrock:anthropic.claude-v2:1', 'bedrock:cohere.command-light-text-v14', 'bedrock:cohere.command-r-plus-v1:0', 'bedrock:cohere.command-r-v1:0', 'bedrock:cohere.command-text-v14', 'bedrock:deepseek.r1-v1:0', 'bedrock:deepseek.v3.2', 'bedrock:eu.anthropic.claude-haiku-4-5-20251001-v1:0', 'bedrock:eu.anthropic.claude-sonnet-4-20250514-v1:0', 'bedrock:eu.anthropic.claude-sonnet-4-5-20250929-v1:0', 'bedrock:eu.anthropic.claude-sonnet-4-6', 'bedrock:global.amazon.nova-2-lite-v1:0', 'bedrock:global.anthropic.claude-fable-5', 'bedrock:global.anthropic.claude-fable-5-1', 'bedrock:global.anthropic.claude-opus-4-5-20251101-v1:0', 'bedrock:global.anthropic.claude-opus-4-6-v1', 'bedrock:global.anthropic.claude-opus-4-7', 'bedrock:global.anthropic.claude-opus-4-8', 'bedrock:global.anthropic.claude-opus-5', 'bedrock:global.anthropic.claude-sonnet-5', 'bedrock:google.gemma-3-12b-it', 'bedrock:google.gemma-3-27b-it', 'bedrock:google.gemma-3-4b-it', 'bedrock:meta.llama3-1-405b-instruct-v1:0', 'bedrock:meta.llama3-1-70b-instruct-v1:0', 'bedrock:meta.llama3-1-8b-instruct-v1:0', 'bedrock:meta.llama3-70b-instruct-v1:0', 'bedrock:meta.llama3-8b-instruct-v1:0', 'bedrock:minimax.minimax-m2', 'bedrock:minimax.minimax-m2.1', 'bedrock:minimax.minimax-m2.5', 'bedrock:mistral.devstral-2-123b', 'bedrock:mistral.magistral-small-2509', 'bedrock:mistral.ministral-3-14b-instruct', 'bedrock:mistral.ministral-3-3b-instruct', 'bedrock:mistral.ministral-3-8b-instruct', 'bedrock:mistral.mistral-7b-instruct-v0:2', 'bedrock:mistral.mistral-large-2402-v1:0', 'bedrock:mistral.mistral-large-2407-v1:0', 'bedrock:mistral.mistral-large-3-675b-instruct', 'bedrock:mistral.mistral-small-2402-v1:0', 'bedrock:mistral.mixtral-8x7b-instruct-v0:1', 'bedrock:mistral.pixtral-large-2502-v1:0', 'bedrock:moonshot.kimi-k2-thinking', 'bedrock:moonshotai.kimi-k2.5', 'bedrock:nvidia.nemotron-nano-12b-v2', 'bedrock:nvidia.nemotron-nano-3-30b', 'bedrock:nvidia.nemotron-nano-9b-v2', 'bedrock:nvidia.nemotron-super-3-120b', 'bedrock:qwen.qwen3-32b-v1:0', 'bedrock:qwen.qwen3-coder-30b-a3b-v1:0', 'bedrock:qwen.qwen3-coder-next', 'bedrock:qwen.qwen3-next-80b-a3b', 'bedrock:qwen.qwen3-vl-235b-a22b', 'bedrock:us.amazon.nova-2-lite-v1:0', 'bedrock:us.amazon.nova-lite-v1:0', 'bedrock:us.amazon.nova-micro-v1:0', 'bedrock:us.amazon.nova-premier-v1:0', 'bedrock:us.amazon.nova-pro-v1:0', 'bedrock:us.anthropic.claude-3-5-haiku-20241022-v1:0', 'bedrock:us.anthropic.claude-3-5-sonnet-20240620-v1:0', 'bedrock:us.anthropic.claude-3-5-sonnet-20241022-v2:0', 'bedrock:us.anthropic.claude-3-7-sonnet-20250219-v1:0', 'bedrock:us.anthropic.claude-3-haiku-20240307-v1:0', 'bedrock:us.anthropic.claude-3-opus-20240229-v1:0', 'bedrock:us.anthropic.claude-3-sonnet-20240229-v1:0', 'bedrock:us.anthropic.claude-fable-5', 'bedrock:us.anthropic.claude-fable-5-1', 'bedrock:us.anthropic.claude-haiku-4-5-20251001-v1:0', 'bedrock:us.anthropic.claude-opus-4-1-20250805-v1:0', 'bedrock:us.anthropic.claude-opus-4-20250514-v1:0', 'bedrock:us.anthropic.claude-opus-4-5-20251101-v1:0', 'bedrock:us.anthropic.claude-opus-4-6-v1', 'bedrock:us.anthropic.claude-opus-4-7', 'bedrock:us.anthropic.claude-opus-4-8', 'bedrock:us.anthropic.claude-opus-5', 'bedrock:us.anthropic.claude-sonnet-4-20250514-v1:0', 'bedrock:us.anthropic.claude-sonnet-4-5-20250929-v1:0', 'bedrock:us.anthropic.claude-sonnet-4-6', 'bedrock:us.anthropic.claude-sonnet-5', 'bedrock:us.meta.llama3-1-70b-instruct-v1:0', 'bedrock:us.meta.llama3-1-8b-instruct-v1:0', 'bedrock:us.meta.llama3-2-11b-instruct-v1:0', 'bedrock:us.meta.llama3-2-1b-instruct-v1:0', 'bedrock:us.meta.llama3-2-3b-instruct-v1:0', 'bedrock:us.meta.llama3-2-90b-instruct-v1:0', 'bedrock:us.meta.llama3-3-70b-instruct-v1:0', 'bedrock:us.meta.llama4-maverick-17b-instruct-v1:0', 'bedrock:us.meta.llama4-scout-17b-instruct-v1:0', 'bedrock:us.mistral.pixtral-large-2502-v1:0', 'bedrock:us.writer.palmyra-x4-v1:0', 'bedrock:us.writer.palmyra-x5-v1:0', 'bedrock:zai.glm-4.7', 'bedrock:zai.glm-4.7-flash', 'bedrock:zai.glm-5', 'cerebras:gemma-4-31b', 'cerebras:gpt-oss-120b', 'cerebras:zai-glm-4.7', 'cohere:c4ai-aya-expanse-32b', 'cohere:c4ai-aya-expanse-8b', 'cohere:command-nightly', 'cohere:command-r-08-2024', 'cohere:command-r-plus-08-2024', 'cohere:command-r7b-12-2024', 'crusoe:Qwen/Qwen3-235B-A22B-Instruct-2507', 'crusoe:deepseek-ai/DeepSeek-V3-0324', 'crusoe:deepseek-ai/DeepSeek-V4-Pro', 'crusoe:deepseek-ai/Deepseek-V4-Flash', 'crusoe:google/gemma-4-31b-it', 'crusoe:meta-llama/Llama-3.3-70B-Instruct', 'crusoe:moonshotai/Kimi-K2.6', 'crusoe:nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B', 'crusoe:nvidia/NVIDIA-Nemotron-3-Super-120B-A12B', 'crusoe:nvidia/Nemotron-3-Nano-Omni-Reasoning-30B-A3B', 'crusoe:nvidia/Nemotron-3.5-Lightning-30B-A3B', 'crusoe:openai/gpt-oss-120b', 'crusoe:yutori/n1.5', 'crusoe:zai/GLM-5.1', 'crusoe:zai/GLM-5.2', 'deepseek:deepseek-chat', 'deepseek:deepseek-reasoner', 'deepseek:deepseek-v4-flash', 'deepseek:deepseek-v4-pro', 'gateway/anthropic:claude-fable-5', 'gateway/anthropic:claude-fable-5-1', 'gateway/anthropic:claude-haiku-4-5', 'gateway/anthropic:claude-haiku-4-5-20251001', 'gateway/anthropic:claude-opus-4-5', 'gateway/anthropic:claude-opus-4-5-20251101', 'gateway/anthropic:claude-opus-4-6', 'gateway/anthropic:claude-opus-4-7', 'gateway/anthropic:claude-opus-4-8', 'gateway/anthropic:claude-opus-5', 'gateway/anthropic:claude-sonnet-4-5', 'gateway/anthropic:claude-sonnet-4-5-20250929', 'gateway/anthropic:claude-sonnet-4-6', 'gateway/anthropic:claude-sonnet-5', 'gateway/bedrock:anthropic.claude-3-haiku-20240307-v1:0', 'gateway/bedrock:deepseek.r1-v1:0', 'gateway/bedrock:deepseek.v3.2', 'gateway/bedrock:eu.anthropic.claude-haiku-4-5-20251001-v1:0', 'gateway/bedrock:eu.anthropic.claude-sonnet-4-20250514-v1:0', 'gateway/bedrock:eu.anthropic.claude-sonnet-4-5-20250929-v1:0', 'gateway/bedrock:eu.anthropic.claude-sonnet-4-6', 'gateway/bedrock:global.amazon.nova-2-lite-v1:0', 'gateway/bedrock:global.anthropic.claude-fable-5', 'gateway/bedrock:global.anthropic.claude-fable-5-1', 'gateway/bedrock:global.anthropic.claude-opus-4-5-20251101-v1:0', 'gateway/bedrock:global.anthropic.claude-opus-4-6-v1', 'gateway/bedrock:global.anthropic.claude-opus-4-7', 'gateway/bedrock:global.anthropic.claude-opus-4-8', 'gateway/bedrock:global.anthropic.claude-opus-5', 'gateway/bedrock:global.anthropic.claude-sonnet-5', 'gateway/bedrock:google.gemma-3-12b-it', 'gateway/bedrock:google.gemma-3-27b-it', 'gateway/bedrock:google.gemma-3-4b-it', 'gateway/bedrock:minimax.minimax-m2', 'gateway/bedrock:minimax.minimax-m2.1', 'gateway/bedrock:minimax.minimax-m2.5', 'gateway/bedrock:mistral.devstral-2-123b', 'gateway/bedrock:mistral.magistral-small-2509', 'gateway/bedrock:mistral.ministral-3-14b-instruct', 'gateway/bedrock:mistral.ministral-3-3b-instruct', 'gateway/bedrock:mistral.ministral-3-8b-instruct', 'gateway/bedrock:mistral.mistral-large-3-675b-instruct', 'gateway/bedrock:mistral.mistral-small-2402-v1:0', 'gateway/bedrock:mistral.pixtral-large-2502-v1:0', 'gateway/bedrock:moonshot.kimi-k2-thinking', 'gateway/bedrock:moonshotai.kimi-k2.5', 'gateway/bedrock:nvidia.nemotron-nano-12b-v2', 'gateway/bedrock:nvidia.nemotron-nano-3-30b', 'gateway/bedrock:nvidia.nemotron-nano-9b-v2', 'gateway/bedrock:nvidia.nemotron-super-3-120b', 'gateway/bedrock:qwen.qwen3-32b-v1:0', 'gateway/bedrock:qwen.qwen3-coder-30b-a3b-v1:0', 'gateway/bedrock:qwen.qwen3-coder-next', 'gateway/bedrock:qwen.qwen3-next-80b-a3b', 'gateway/bedrock:qwen.qwen3-vl-235b-a22b', 'gateway/bedrock:us.amazon.nova-premier-v1:0', 'gateway/bedrock:us.anthropic.claude-fable-5', 'gateway/bedrock:us.anthropic.claude-fable-5-1', 'gateway/bedrock:us.anthropic.claude-opus-4-1-20250805-v1:0', 'gateway/bedrock:us.anthropic.claude-opus-4-5-20251101-v1:0', 'gateway/bedrock:us.anthropic.claude-opus-4-6-v1', 'gateway/bedrock:us.anthropic.claude-opus-4-7', 'gateway/bedrock:us.anthropic.claude-opus-4-8', 'gateway/bedrock:us.anthropic.claude-opus-5', 'gateway/bedrock:us.anthropic.claude-sonnet-5', 'gateway/bedrock:us.meta.llama4-maverick-17b-instruct-v1:0', 'gateway/bedrock:us.meta.llama4-scout-17b-instruct-v1:0', 'gateway/bedrock:us.mistral.pixtral-large-2502-v1:0', 'gateway/bedrock:us.writer.palmyra-x4-v1:0', 'gateway/bedrock:us.writer.palmyra-x5-v1:0', 'gateway/bedrock:zai.glm-4.7', 'gateway/bedrock:zai.glm-4.7-flash', 'gateway/bedrock:zai.glm-5', 'gateway/google-cloud:gemini-2.5-flash', 'gateway/google-cloud:gemini-2.5-flash-image', 'gateway/google-cloud:gemini-2.5-flash-lite', 'gateway/google-cloud:gemini-2.5-pro', 'gateway/google-cloud:gemini-3-flash-preview', 'gateway/google-cloud:gemini-3-pro-image', 'gateway/google-cloud:gemini-3.1-flash-image', 'gateway/google-cloud:gemini-3.1-flash-lite', 'gateway/google-cloud:gemini-3.1-pro-preview', 'gateway/google-cloud:gemini-3.5-flash', 'gateway/google-cloud:gemini-3.5-flash-lite', 'gateway/google-cloud:gemini-3.6-flash', 'gateway/google-cloud:gemini-3.7-flash', 'gateway/google-cloud:gemini-3.8-flash', 'gateway/google:gemini-2.5-flash', 'gateway/google:gemini-2.5-flash-image', 'gateway/google:gemini-2.5-flash-lite', 'gateway/google:gemini-2.5-pro', 'gateway/google:gemini-3-flash-preview', 'gateway/google:gemini-3-pro-image', 'gateway/google:gemini-3.1-flash-image', 'gateway/google:gemini-3.1-flash-lite', 'gateway/google:gemini-3.1-pro-preview', 'gateway/google:gemini-3.5-flash', 'gateway/google:gemini-3.5-flash-lite', 'gateway/google:gemini-3.6-flash', 'gateway/google:gemini-3.7-flash', 'gateway/google:gemini-3.8-flash', 'gateway/groq:llama-3.1-8b-instant', 'gateway/groq:llama-3.3-70b-versatile', 'gateway/groq:openai/gpt-oss-120b', 'gateway/groq:openai/gpt-oss-20b', 'gateway/groq:openai/gpt-oss-safeguard-20b', 'gateway/openai:gpt-3.5-turbo', 'gateway/openai:gpt-3.5-turbo-0125', 'gateway/openai:gpt-3.5-turbo-1106', 'gateway/openai:gpt-4', 'gateway/openai:gpt-4-0613', 'gateway/openai:gpt-4-turbo', 'gateway/openai:gpt-4-turbo-2024-04-09', 'gateway/openai:gpt-4.1', 'gateway/openai:gpt-4.1-2025-04-14', 'gateway/openai:gpt-4.1-mini', 'gateway/openai:gpt-4.1-mini-2025-04-14', 'gateway/openai:gpt-4.1-nano', 'gateway/openai:gpt-4.1-nano-2025-04-14', 'gateway/openai:gpt-4o', 'gateway/openai:gpt-4o-2024-05-13', 'gateway/openai:gpt-4o-2024-08-06', 'gateway/openai:gpt-4o-2024-11-20', 'gateway/openai:gpt-4o-mini', 'gateway/openai:gpt-4o-mini-2024-07-18', 'gateway/openai:gpt-5', 'gateway/openai:gpt-5-2025-08-07', 'gateway/openai:gpt-5-mini', 'gateway/openai:gpt-5-mini-2025-08-07', 'gateway/openai:gpt-5-nano', 'gateway/openai:gpt-5-nano-2025-08-07', 'gateway/openai:gpt-5-pro', 'gateway/openai:gpt-5-pro-2025-10-06', 'gateway/openai:gpt-5.1', 'gateway/openai:gpt-5.1-2025-11-13', 'gateway/openai:gpt-5.2', 'gateway/openai:gpt-5.2-2025-12-11', 'gateway/openai:gpt-5.2-chat-latest', 'gateway/openai:gpt-5.2-pro', 'gateway/openai:gpt-5.2-pro-2025-12-11', 'gateway/openai:gpt-5.3-chat-latest', 'gateway/openai:gpt-5.4', 'gateway/openai:gpt-5.4-mini', 'gateway/openai:gpt-5.4-mini-2026-03-17', 'gateway/openai:gpt-5.4-nano', 'gateway/openai:gpt-5.4-nano-2026-03-17', 'gateway/openai:gpt-5.5', 'gateway/openai:gpt-5.5-2026-04-23', 'gateway/openai:gpt-5.5-pro', 'gateway/openai:gpt-5.5-pro-2026-04-23', 'gateway/openai:gpt-5.6-cyber', 'gateway/openai:gpt-5.6-luna', 'gateway/openai:gpt-5.6-sol', 'gateway/openai:gpt-5.6-terra', 'gateway/openai:gpt-6-astra', 'gateway/openai:gpt-daybreak-blue-latest', 'gateway/openai:gpt-daybreak-red-latest', 'gateway/openai:o1', 'gateway/openai:o1-2024-12-17', 'gateway/openai:o1-pro', 'gateway/openai:o1-pro-2025-03-19', 'gateway/openai:o3', 'gateway/openai:o3-2025-04-16', 'gateway/openai:o3-mini', 'gateway/openai:o3-mini-2025-01-31', 'gateway/openai:o3-pro', 'gateway/openai:o3-pro-2025-06-10', 'gateway/openai:o4-mini', 'gateway/openai:o4-mini-2025-04-16', 'google-cloud:gemini-2.0-flash', 'google-cloud:gemini-2.0-flash-lite', 'google-cloud:gemini-2.5-flash', 'google-cloud:gemini-2.5-flash-image', 'google-cloud:gemini-2.5-flash-lite', 'google-cloud:gemini-2.5-flash-preview-09-2025', 'google-cloud:gemini-2.5-pro', 'google-cloud:gemini-3-flash-preview', 'google-cloud:gemini-3-pro-image', 'google-cloud:gemini-3-pro-image-preview', 'google-cloud:gemini-3-pro-preview', 'google-cloud:gemini-3.1-flash-image', 'google-cloud:gemini-3.1-flash-image-preview', 'google-cloud:gemini-3.1-flash-lite', 'google-cloud:gemini-3.1-pro-preview', 'google-cloud:gemini-3.5-flash', 'google-cloud:gemini-3.5-flash-lite', 'google-cloud:gemini-3.6-flash', 'google-cloud:gemini-3.7-flash', 'google-cloud:gemini-3.8-flash', 'google-cloud:gemini-flash-latest', 'google-cloud:gemini-flash-lite-latest', 'google:gemini-2.0-flash', 'google:gemini-2.0-flash-lite', 'google:gemini-2.5-flash', 'google:gemini-2.5-flash-image', 'google:gemini-2.5-flash-lite', 'google:gemini-2.5-flash-preview-09-2025', 'google:gemini-2.5-pro', 'google:gemini-3-flash-preview', 'google:gemini-3-pro-image', 'google:gemini-3-pro-image-preview', 'google:gemini-3-pro-preview', 'google:gemini-3.1-flash-image', 'google:gemini-3.1-flash-image-preview', 'google:gemini-3.1-flash-lite', 'google:gemini-3.1-pro-preview', 'google:gemini-3.5-flash', 'google:gemini-3.5-flash-lite', 'google:gemini-3.6-flash', 'google:gemini-3.7-flash', 'google:gemini-3.8-flash', 'google:gemini-flash-latest', 'google:gemini-flash-lite-latest', 'groq:llama-3.1-8b-instant', 'groq:llama-3.3-70b-versatile', 'groq:meta-llama/llama-4-maverick-17b-128e-instruct', 'groq:meta-llama/llama-guard-4-12b', 'groq:meta-llama/llama-prompt-guard-2-22m', 'groq:meta-llama/llama-prompt-guard-2-86m', 'groq:openai/gpt-oss-120b', 'groq:openai/gpt-oss-20b', 'groq:openai/gpt-oss-safeguard-20b', 'groq:playai-tts', 'groq:playai-tts-arabic', 'groq:whisper-large-v3', 'groq:whisper-large-v3-turbo', 'heroku:claude-3-5-haiku', 'heroku:claude-3-5-sonnet-latest', 'heroku:claude-3-7-sonnet', 'heroku:claude-3-haiku', 'heroku:claude-4-5-haiku', 'heroku:claude-4-5-sonnet', 'heroku:claude-4-6-sonnet', 'heroku:claude-4-sonnet', 'heroku:claude-opus-4-5', 'heroku:claude-opus-4-6', 'heroku:deepseek-v3-2', 'heroku:glm-4-7', 'heroku:glm-4-7-flash', 'heroku:gpt-oss-120b', 'heroku:kimi-k2-5', 'heroku:kimi-k2-thinking', 'heroku:minimax-m2', 'heroku:minimax-m2-1', 'heroku:nova-2-lite', 'heroku:nova-lite', 'heroku:nova-pro', 'heroku:qwen3-235b', 'heroku:qwen3-coder-480b', 'huggingface:Qwen/QwQ-32B', 'huggingface:Qwen/Qwen2.5-72B-Instruct', 'huggingface:Qwen/Qwen3-235B-A22B', 'huggingface:Qwen/Qwen3-32B', 'huggingface:deepseek-ai/DeepSeek-R1', 'huggingface:meta-llama/Llama-3.3-70B-Instruct', 'huggingface:meta-llama/Llama-4-Maverick-17B-128E-Instruct', 'huggingface:meta-llama/Llama-4-Scout-17B-16E-Instruct', 'mistral:codestral-latest', 'mistral:mistral-large-latest', 'mistral:mistral-moderation-latest', 'mistral:mistral-small-latest', 'moonshotai:kimi-k2-0711-preview', 'moonshotai:kimi-k2.5', 'moonshotai:kimi-k2.6', 'moonshotai:kimi-k2.7-code', 'moonshotai:kimi-k2.7-code-highspeed', 'moonshotai:kimi-k3', 'moonshotai:kimi-latest', 'moonshotai:kimi-thinking-preview', 'moonshotai:moonshot-v1-128k', 'moonshotai:moonshot-v1-128k-vision-preview', 'moonshotai:moonshot-v1-32k', 'moonshotai:moonshot-v1-32k-vision-preview', 'moonshotai:moonshot-v1-8k', 'moonshotai:moonshot-v1-8k-vision-preview', 'moonshotai:moonshot-v1-auto', 'openai-chat:computer-use-preview', 'openai-chat:computer-use-preview-2025-03-11', 'openai-chat:gpt-3.5-turbo', 'openai-chat:gpt-3.5-turbo-0125', 'openai-chat:gpt-3.5-turbo-0301', 'openai-chat:gpt-3.5-turbo-1106', 'openai-chat:gpt-3.5-turbo-16k', 'openai-chat:gpt-4', 'openai-chat:gpt-4-0314', 'openai-chat:gpt-4-0613', 'openai-chat:gpt-4-turbo', 'openai-chat:gpt-4-turbo-2024-04-09', 'openai-chat:gpt-4.1', 'openai-chat:gpt-4.1-2025-04-14', 'openai-chat:gpt-4.1-mini', 'openai-chat:gpt-4.1-mini-2025-04-14', 'openai-chat:gpt-4.1-nano', 'openai-chat:gpt-4.1-nano-2025-04-14', 'openai-chat:gpt-4o', 'openai-chat:gpt-4o-2024-05-13', 'openai-chat:gpt-4o-2024-08-06', 'openai-chat:gpt-4o-2024-11-20', 'openai-chat:gpt-4o-audio-preview', 'openai-chat:gpt-4o-audio-preview-2024-12-17', 'openai-chat:gpt-4o-audio-preview-2025-06-03', 'openai-chat:gpt-4o-mini', 'openai-chat:gpt-4o-mini-2024-07-18', 'openai-chat:gpt-4o-mini-audio-preview', 'openai-chat:gpt-4o-mini-audio-preview-2024-12-17', 'openai-chat:gpt-4o-mini-search-preview', 'openai-chat:gpt-4o-mini-search-preview-2025-03-11', 'openai-chat:gpt-4o-search-preview', 'openai-chat:gpt-4o-search-preview-2025-03-11', 'openai-chat:gpt-5', 'openai-chat:gpt-5-2025-08-07', 'openai-chat:gpt-5-chat-latest', 'openai-chat:gpt-5-codex', 'openai-chat:gpt-5-mini', 'openai-chat:gpt-5-mini-2025-08-07', 'openai-chat:gpt-5-nano', 'openai-chat:gpt-5-nano-2025-08-07', 'openai-chat:gpt-5-pro', 'openai-chat:gpt-5-pro-2025-10-06', 'openai-chat:gpt-5.1', 'openai-chat:gpt-5.1-2025-11-13', 'openai-chat:gpt-5.1-chat-latest', 'openai-chat:gpt-5.1-codex', 'openai-chat:gpt-5.1-codex-max', 'openai-chat:gpt-5.2', 'openai-chat:gpt-5.2-2025-12-11', 'openai-chat:gpt-5.2-chat-latest', 'openai-chat:gpt-5.2-pro', 'openai-chat:gpt-5.2-pro-2025-12-11', 'openai-chat:gpt-5.3-chat-latest', 'openai-chat:gpt-5.4', 'openai-chat:gpt-5.4-mini', 'openai-chat:gpt-5.4-mini-2026-03-17', 'openai-chat:gpt-5.4-nano', 'openai-chat:gpt-5.4-nano-2026-03-17', 'openai-chat:gpt-5.5', 'openai-chat:gpt-5.5-2026-04-23', 'openai-chat:gpt-5.5-pro', 'openai-chat:gpt-5.5-pro-2026-04-23', 'openai-chat:gpt-5.6-cyber', 'openai-chat:gpt-5.6-luna', 'openai-chat:gpt-5.6-sol', 'openai-chat:gpt-5.6-terra', 'openai-chat:gpt-6-astra', 'openai-chat:gpt-daybreak-blue-latest', 'openai-chat:gpt-daybreak-red-latest', 'openai-chat:o1', 'openai-chat:o1-2024-12-17', 'openai-chat:o1-pro', 'openai-chat:o1-pro-2025-03-19', 'openai-chat:o3', 'openai-chat:o3-2025-04-16', 'openai-chat:o3-deep-research', 'openai-chat:o3-deep-research-2025-06-26', 'openai-chat:o3-mini', 'openai-chat:o3-mini-2025-01-31', 'openai-chat:o3-pro', 'openai-chat:o3-pro-2025-06-10', 'openai-chat:o4-mini', 'openai-chat:o4-mini-2025-04-16', 'openai-chat:o4-mini-deep-research', 'openai-chat:o4-mini-deep-research-2025-06-26', 'openai:computer-use-preview', 'openai:computer-use-preview-2025-03-11', 'openai:gpt-3.5-turbo', 'openai:gpt-3.5-turbo-0125', 'openai:gpt-3.5-turbo-0301', 'openai:gpt-3.5-turbo-1106', 'openai:gpt-4', 'openai:gpt-4-0314', 'openai:gpt-4-0613', 'openai:gpt-4-turbo', 'openai:gpt-4-turbo-2024-04-09', 'openai:gpt-4.1', 'openai:gpt-4.1-2025-04-14', 'openai:gpt-4.1-mini', 'openai:gpt-4.1-mini-2025-04-14', 'openai:gpt-4.1-nano', 'openai:gpt-4.1-nano-2025-04-14', 'openai:gpt-4o', 'openai:gpt-4o-2024-05-13', 'openai:gpt-4o-2024-08-06', 'openai:gpt-4o-2024-11-20', 'openai:gpt-4o-audio-preview', 'openai:gpt-4o-audio-preview-2024-12-17', 'openai:gpt-4o-audio-preview-2025-06-03', 'openai:gpt-4o-mini', 'openai:gpt-4o-mini-2024-07-18', 'openai:gpt-4o-mini-audio-preview', 'openai:gpt-4o-mini-audio-preview-2024-12-17', 'openai:gpt-5', 'openai:gpt-5-2025-08-07', 'openai:gpt-5-chat-latest', 'openai:gpt-5-codex', 'openai:gpt-5-mini', 'openai:gpt-5-mini-2025-08-07', 'openai:gpt-5-nano', 'openai:gpt-5-nano-2025-08-07', 'openai:gpt-5-pro', 'openai:gpt-5-pro-2025-10-06', 'openai:gpt-5.1', 'openai:gpt-5.1-2025-11-13', 'openai:gpt-5.1-chat-latest', 'openai:gpt-5.1-codex', 'openai:gpt-5.1-codex-max', 'openai:gpt-5.2', 'openai:gpt-5.2-2025-12-11', 'openai:gpt-5.2-chat-latest', 'openai:gpt-5.2-pro', 'openai:gpt-5.2-pro-2025-12-11', 'openai:gpt-5.3-chat-latest', 'openai:gpt-5.4', 'openai:gpt-5.4-mini', 'openai:gpt-5.4-mini-2026-03-17', 'openai:gpt-5.4-nano', 'openai:gpt-5.4-nano-2026-03-17', 'openai:gpt-5.5', 'openai:gpt-5.5-2026-04-23', 'openai:gpt-5.5-pro', 'openai:gpt-5.5-pro-2026-04-23', 'openai:gpt-5.6-cyber', 'openai:gpt-5.6-luna', 'openai:gpt-5.6-sol', 'openai:gpt-5.6-terra', 'openai:gpt-6-astra', 'openai:gpt-daybreak-blue-latest', 'openai:gpt-daybreak-red-latest', 'openai:o1', 'openai:o1-2024-12-17', 'openai:o1-pro', 'openai:o1-pro-2025-03-19', 'openai:o3', 'openai:o3-2025-04-16', 'openai:o3-deep-research', 'openai:o3-deep-research-2025-06-26', 'openai:o3-mini', 'openai:o3-mini-2025-01-31', 'openai:o3-pro', 'openai:o3-pro-2025-06-10', 'openai:o4-mini', 'openai:o4-mini-2025-04-16', 'openai:o4-mini-deep-research', 'openai:o4-mini-deep-research-2025-06-26', 'test', 'snowflake:claude-4-sonnet', 'snowflake:claude-fable-5', 'snowflake:claude-haiku-4-5', 'snowflake:claude-opus-4-5', 'snowflake:claude-opus-4-6', 'snowflake:claude-opus-4-7', 'snowflake:claude-opus-4-8', 'snowflake:claude-opus-5', 'snowflake:claude-sonnet-4-5', 'snowflake:claude-sonnet-4-6', 'snowflake:claude-sonnet-5', 'snowflake:deepseek-r1', 'snowflake:llama3.1-405b', 'snowflake:llama3.1-70b', 'snowflake:llama3.1-8b', 'snowflake:llama4-maverick', 'snowflake:mistral-7b', 'snowflake:mistral-large', 'snowflake:mistral-large2', 'snowflake:openai-gpt-4.1', 'snowflake:openai-gpt-5', 'snowflake:openai-gpt-5-6-luna', 'snowflake:openai-gpt-5-6-sol', 'snowflake:openai-gpt-5-6-terra', 'snowflake:openai-gpt-5-chat', 'snowflake:openai-gpt-5-mini', 'snowflake:openai-gpt-5-nano', 'snowflake:openai-gpt-5.1', 'snowflake:openai-gpt-5.2', 'snowflake:openai-gpt-5.4', 'snowflake:openai-gpt-5.5', 'snowflake:snowflake-llama-3.3-70b', 'xai:grok-3', 'xai:grok-3-fast', 'xai:grok-3-fast-latest', 'xai:grok-3-latest', 'xai:grok-3-mini', 'xai:grok-3-mini-fast', 'xai:grok-3-mini-fast-latest', 'xai:grok-4', 'xai:grok-4-0709', 'xai:grok-4-1-fast', 'xai:grok-4-1-fast-non-reasoning', 'xai:grok-4-1-fast-non-reasoning-latest', 'xai:grok-4-1-fast-reasoning', 'xai:grok-4-1-fast-reasoning-latest', 'xai:grok-4-fast', 'xai:grok-4-fast-non-reasoning', 'xai:grok-4-fast-non-reasoning-latest', 'xai:grok-4-fast-reasoning', 'xai:grok-4-fast-reasoning-latest', 'xai:grok-4-latest', 'xai:grok-4.20', 'xai:grok-4.20-0309', 'xai:grok-4.20-0309-non-reasoning', 'xai:grok-4.20-0309-reasoning', 'xai:grok-4.20-multi-agent', 'xai:grok-4.20-multi-agent-0309', 'xai:grok-4.20-multi-agent-latest', 'xai:grok-4.20-non-reasoning', 'xai:grok-4.20-non-reasoning-latest', 'xai:grok-4.20-reasoning-latest', 'xai:grok-4.3', 'xai:grok-4.3-latest', 'xai:grok-4.5', 'xai:grok-4.5-latest', 'xai:grok-4.6', 'xai:grok-build-0.1', 'xai:grok-code-fast-1', 'zai:autoglm-phone-multilingual', 'zai:glm-4-32b-0414-128k', 'zai:glm-4.5', 'zai:glm-4.5-air', 'zai:glm-4.5-airx', 'zai:glm-4.5-flash', 'zai:glm-4.5-x', 'zai:glm-4.5v', 'zai:glm-4.6', 'zai:glm-4.6v', 'zai:glm-4.6v-flash', 'zai:glm-4.6v-flashx', 'zai:glm-4.7', 'zai:glm-4.7-flash', 'zai:glm-4.7-flashx', 'zai:glm-5', 'zai:glm-5-turbo', 'zai:glm-5.1', 'zai:glm-5.2', 'zai:glm-5.3', 'zai:glm-5.3-flash', 'zai:glm-5v-turbo'])`

### ToolVisibility

How a function tool is represented on the request a provider actually receives.

-   `'visible'`: an ordinary entry in the provider's `tools` collection, schema included.
-   `'deferred'`: a declared `tools` entry whose schema is withheld behind the provider's schema-deferral flag until something reveals it.
-   `'withheld'`: absent from the request entirely.
-   `'via_history'`: absent from the `tools` collection; the full definition travels on the provider's mid-conversation tool-addition channel instead.

Resolved per tool name into [`ModelRequestParameters.tool_visibility`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestParameters.tool_visibility).

**Default:** `Literal['visible', 'deferred', 'withheld', 'via_history']`

### ALLOW\_MODEL\_REQUESTS

Whether to allow requests to models.

This global setting allows you to disable request to most models, e.g. to make sure you don't accidentally make costly requests to a model during tests.

The testing models [`TestModel`](https://pydantic.dev/docs/ai/api/models/test/#pydantic_ai.models.test.TestModel), [`FunctionModel`](https://pydantic.dev/docs/ai/api/models/function/#pydantic_ai.models.function.FunctionModel), [`TestEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.TestEmbeddingModel) and [`TestImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.TestImageGenerationModel) are not affected by this setting, nor is [`SentenceTransformerEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.sentence_transformers.SentenceTransformerEmbeddingModel), which runs inference locally and so has no per-call provider cost.

**Default:** `True`

---
