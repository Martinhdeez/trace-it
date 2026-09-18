# [pydantic_ai.models.openai](https://pydantic.dev/docs/ai/api/models/openai/)

# pydantic\_ai.models.openai

## Setup

For details on how to set up authentication with this model, see [model configuration for OpenAI](https://pydantic.dev/docs/ai/models/openai/).

### OpenAIPromptCacheOptions

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Options for OpenAI prompt caching on GPT-5.6 models.

#### Attributes

##### mode

Whether OpenAI may create an implicit cache breakpoint. Defaults to `implicit`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['implicit', 'explicit'\]

##### ttl

The minimum lifetime for cache breakpoints. Defaults to `30m`, the only currently supported value.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['30m'\]

### OpenAIChatModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings used for an OpenAI model request.

#### Attributes

##### openai\_reasoning\_effort

Constrains effort on reasoning for [reasoning models](https://platform.openai.com/docs/guides/reasoning).

Currently supported values are `low`, `medium`, and `high`. Reducing reasoning effort can result in faster responses and fewer tokens used on reasoning in a response.

**Type:** `ReasoningEffort`

##### openai\_logprobs

Include log probabilities in the response.

For Chat models, these will be included in `ModelResponse.provider_details['logprobs']`. For Responses models, these will be included in the response output parts `TextPart.provider_details['logprobs']`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_top\_logprobs

Include log probabilities of the top n tokens in the response.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### openai\_store

Whether or not to store the output of this request in OpenAI's systems.

If `False`, OpenAI will not store the request for its own internal review or training. See [OpenAI API reference](https://platform.openai.com/docs/api-reference/chat/create#chat-create-store).

When used with `OpenAIResponsesModel`, stored responses appear in OpenAI's dashboard and can be referenced via [`openai_previous_response_id`](https://pydantic.dev/docs/ai/api/models/openai/#pydantic_ai.models.openai.OpenAIResponsesModelSettings.openai_previous_response_id). Pair this with `openai_previous_response_id='auto'` to avoid storing duplicate copies of the conversation history across retries and subsequent requests within the same run.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### openai\_user

A unique identifier representing the end-user, which can help OpenAI monitor and detect abuse.

See [OpenAI's safety best practices](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids) for more details.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### openai\_moderation

Run moderation on the input and output of the request, e.g. `{'model': 'omni-moderation-latest'}`.

Supported by both the Chat Completions API and the Responses API. In both cases, the moderation results returned by the API are exposed in [`ModelResponse.provider_details`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse.provider_details) under the `'moderation'` key.

See the [OpenAI moderation documentation](https://platform.openai.com/docs/guides/moderation) for more details.

**Type:** `Moderation`

##### openai\_service\_tier

The service tier to use for the model request.

Currently supported values are `auto`, `default`, `flex`, and `priority`. For more information, see [OpenAI's service tiers documentation](https://platform.openai.com/docs/api-reference/chat/object#chat/object-service_tier).

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['auto', 'default', 'flex', 'priority'\]

##### openai\_prediction

Enables [predictive outputs](https://platform.openai.com/docs/guides/predicted-outputs).

This feature is currently only supported for some OpenAI models.

**Type:** `ChatCompletionPredictionContentParam`

##### openai\_prompt\_cache\_key

Used by OpenAI to cache responses for similar requests to optimize your cache hit rates.

See the [OpenAI Prompt Caching documentation](https://platform.openai.com/docs/guides/prompt-caching#how-it-works) for more information.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### openai\_prompt\_cache\_retention

The retention policy for the prompt cache. Set to 24h to enable extended prompt caching, which keeps cached prefixes active for longer, up to a maximum of 24 hours.

For GPT-5.6 and later models, OpenAI deprecates this field in favor of the `ttl` in `openai_prompt_cache_options`; earlier models keep using this field. The two are independent and do not interact: this field expresses a maximum retention policy, while `ttl` expresses a minimum cache lifetime.

See the [OpenAI Prompt Caching documentation](https://platform.openai.com/docs/guides/prompt-caching#how-it-works) for more information.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['in\_memory', '24h'\]

##### openai\_prompt\_cache\_options

Controls implicit and explicit prompt cache breakpoints, supported by GPT-5.6 and later models.

Explicit breakpoints are added to user content with [`CachePoint`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CachePoint). OpenAI applies the request-wide `ttl` to every breakpoint and ignores `CachePoint.ttl`. The `ttl` here is independent of the `openai_prompt_cache_retention` setting, which OpenAI deprecates for GPT-5.6 and later models.

See the [OpenAI prompt caching documentation](https://developers.openai.com/api/docs/guides/prompt-caching) for more information.

**Type:** `OpenAIPromptCacheOptions`

##### openai\_continuous\_usage\_stats

When True, enables continuous usage statistics in streaming responses.

When enabled, the API returns cumulative usage data with each chunk rather than only at the end. This setting correctly handles the cumulative nature of these stats by using only the final usage values rather than summing all intermediate values.

See [OpenAI's streaming documentation](https://platform.openai.com/docs/api-reference/chat/create#stream_options) for more information.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### OpenAIResponsesModelSettings

**Bases:** `OpenAIChatModelSettings`

Settings used for an OpenAI Responses model request.

ALL FIELDS MUST BE `openai_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

#### Attributes

##### openai\_native\_tools

The provided OpenAI built-in tools to use.

See [OpenAI's built-in tools](https://platform.openai.com/docs/guides/tools?api-mode=responses) for more details.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`FileSearchToolParam` | `WebSearchToolParam` | `ComputerToolParam`\]

##### openai\_reasoning\_mode

The reasoning mode to use, for models that support it (currently the GPT-5.6 family).

`standard` is the default. `pro` performs more model work to improve reliability on difficult tasks, at the cost of higher latency and token usage. Reasoning mode is independent of [`openai_reasoning_effort`](https://pydantic.dev/docs/ai/api/models/openai/#pydantic_ai.models.openai.OpenAIChatModelSettings.openai_reasoning_effort), and the unified [`thinking`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings.thinking) setting only influences the effort, never the mode. This setting is ignored when the resolved model profile does not support reasoning mode ([`OpenAIModelProfile.openai_responses_supports_reasoning_mode`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.openai.OpenAIModelProfile.openai_responses_supports_reasoning_mode)).

See [OpenAI's reasoning mode documentation](https://developers.openai.com/api/docs/guides/reasoning#reasoning-mode) for more details.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['standard', 'pro'\]

##### openai\_reasoning\_context

The reasoning context to use, for models that support it.

Controls which prior-turn reasoning items the model can use when sampling: `auto` defers to the model's own default (OpenAI treats it exactly like not sending the field), `current_turn` makes only the active turn's reasoning available, and `all_turns` renders compatible reasoning items from earlier turns into the next sample (requires access to earlier response items via `previous_response_id`, a conversation, or replayed history).

When this setting is omitted, Pydantic AI sends `all_turns` on models that support it, so that earlier-turn reasoning stays available by default. Set `auto` explicitly to defer to OpenAI's own per-model default instead.

`auto` and `current_turn` are sent to any model that supports reasoning. `all_turns` is sent only to models whose profile sets [`OpenAIModelProfile.openai_responses_supports_reasoning_context`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.openai.OpenAIModelProfile.openai_responses_supports_reasoning_context) (currently the GPT-5.4, GPT-5.5, and GPT-5.6 families). A value the resolved profile doesn't support is ignored.

See [OpenAI's reasoning context documentation](https://developers.openai.com/api/docs/guides/reasoning#preserve-reasoning-across-calls) for more details.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['auto', 'current\_turn', 'all\_turns'\]

##### openai\_reasoning\_summary

A summary of the reasoning performed by the model.

This can be useful for debugging and understanding the model's reasoning process. One of `concise`, `detailed`, or `auto`.

Check the [OpenAI Reasoning documentation](https://platform.openai.com/docs/guides/reasoning?api-mode=responses#reasoning-summaries) for more details.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['detailed', 'concise', 'auto'\]

##### openai\_send\_reasoning\_ids

Whether to send the unique IDs of reasoning, text, and function call parts from the message history to the model. Enabled by default for reasoning models.

This can result in errors like `"Item 'rs_123' of type 'reasoning' was provided without its required following item."` if the message history you're sending does not match exactly what was received from the Responses API in a previous response, for example if you're using a [history processor](https://pydantic.dev/docs/ai/core-concepts/message-history/#processing-message-history). In that case, you'll want to disable this.

Most server-side tool items (web search, code interpreter, image generation) are replayed _by_ their ID, so disabling this also stops them from being sent back entirely. Hosted tool-search items are the exception: they carry their state (the query and discovered tools) inline, so they are still replayed with the IDs omitted, and previously discovered tools stay callable.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_truncation

The truncation strategy to use for the model response.

It can be either:

-   `disabled` (default): If a model response will exceed the context window size for a model, the request will fail with a 400 error.
-   `auto`: If the context of this response and previous ones exceeds the model's context window size, the model will truncate the response to fit the context window by dropping input items in the middle of the conversation.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['disabled', 'auto'\]

##### openai\_text\_verbosity

Constrains the verbosity of the model's text response.

Lower values will result in more concise responses, while higher values will result in more verbose responses. Currently supported values are `low`, `medium`, and `high`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['low', 'medium', 'high'\]

##### openai\_previous\_response\_id

Reference a prior OpenAI response to continue a conversation server-side, omitting already-stored messages from the input.

-   `'auto'`: chain to the most recent `provider_response_id` in the message history. If the history contains no such response, no `previous_response_id` is sent.
-   A concrete response ID string: use it as the seed for the first request in the run (e.g. to continue from a prior turn). On subsequent in-run requests (retries, tool-call continuations), the most recent `provider_response_id` from the message history takes precedence so the chain extends correctly without re-sending messages that are already server-side.

In both cases, messages that precede the chosen response in the history are omitted from the input, since OpenAI reconstructs them from server-side state.

Requires the referenced response to have been stored (see `openai_store`, which defaults to `True` on OpenAI's side). Not compatible with Zero Data Retention.

See the [OpenAI Responses API documentation](https://platform.openai.com/docs/guides/reasoning#keeping-reasoning-items-in-context) for more information.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['auto'\] | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### openai\_conversation\_id

Reference an OpenAI conversation to continue durable conversation state server-side.

-   `'auto'`: use the most recent OpenAI conversation ID from `ModelResponse.provider_details['conversation_id']` in the message history with the same Pydantic AI `conversation_id`, when available. If the history contains no such response, no `conversation` is sent.
-   A concrete conversation ID string: use it as the OpenAI Responses API `conversation` parameter.

When a matching conversation ID is found in message history, messages that precede that response are omitted from the input, since OpenAI reconstructs them from the server-side conversation.

Not compatible with [`openai_previous_response_id`](https://pydantic.dev/docs/ai/api/models/openai/#pydantic_ai.models.openai.OpenAIResponsesModelSettings.openai_previous_response_id).

See the [OpenAI conversation state documentation](https://platform.openai.com/docs/guides/conversation-state) for more information.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['auto'\] | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### openai\_include\_code\_execution\_outputs

Whether to include the code execution results in the response.

Corresponds to the `code_interpreter_call.outputs` value of the `include` parameter in the Responses API.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_include\_web\_search\_sources

Whether to include the web search results in the response.

Corresponds to the `web_search_call.action.sources` value of the `include` parameter in the Responses API.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_include\_file\_search\_results

Whether to include the file search results in the response.

Corresponds to the `file_search_call.results` value of the `include` parameter in the Responses API.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_include\_raw\_annotations

Whether to include the raw annotations in `TextPart.provider_details`.

When enabled, any annotations (e.g., citations from web search) will be available in the `provider_details['annotations']` field of text parts. This is opt-in since there may be overlap with native annotation support once added via [https://github.com/pydantic/pydantic-ai/issues/3126](https://github.com/pydantic/pydantic-ai/issues/3126).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_context\_management

Context management configuration for the request.

This enables OpenAI's server-side automatic compaction inside the regular `/responses` call, as opposed to the standalone `/responses/compact` endpoint. See [OpenAI's compaction guide](https://developers.openai.com/api/docs/guides/compaction) for details.

The [`OpenAICompaction`](https://pydantic.dev/docs/ai/api/models/openai/#pydantic_ai.models.openai.OpenAICompaction) capability sets this automatically in its default (stateful) mode.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ContextManagement`\]

##### openai\_background

Enable background mode for long-running requests.

When enabled, this setting passes `background=True` to the Responses API and opts into automatic polling for completion. If the response is still pending (`'queued'` or `'in_progress'`), the agent automatically polls for completion using `retrieve()`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### OpenAIChatModel

**Bases:** `Model[AsyncOpenAI]`

A model that uses the OpenAI API.

Internally, this uses the [OpenAI Python client](https://github.com/openai/openai-python) to interact with the API.

Apart from `__init__`, all methods are private or match those of the base class.

#### Attributes

##### model\_name

The model name.

**Type:** `OpenAIModelName`

##### system

The model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### profile

The model profile.

WebSearchTool is only supported if openai\_chat\_supports\_web\_search is True.

**Type:** `OpenAIModelProfile`

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: OpenAIModelName,
    *,
    provider: OpenAIChatCompatibleProvider | Literal['openai', 'openai-chat', 'gateway'] | Provider[AsyncOpenAI] = 'openai',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize an OpenAI model.

###### Parameters

**`model_name`** : `OpenAIModelName`

The name of the OpenAI model to use. List of model names available [here](https://github.com/openai/openai-python/blob/v1.54.3/src/openai/types/chat_model.py#L7) (Unfortunately, despite being ask to do so, OpenAI do not provide `.inv` files for their API).

**`provider`** : `OpenAIChatCompatibleProvider` | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['openai', 'openai-chat', 'gateway'\] | `Provider`\[`AsyncOpenAI`\] _Default:_ `'openai'`

The provider to use. Defaults to `'openai'`.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Default model settings for this model instance.

##### resolve\_prompt\_cache\_retention

```python
def resolve_prompt_cache_retention(
    model_settings: ModelSettings | None,
) -> timedelta | None
```

Resolve the extended prompt cache retention requested by OpenAI settings.

###### Returns

`timedelta` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### supported\_native\_tools

`@classmethod`

```python
def supported_native_tools(cls) -> frozenset[type[AbstractNativeTool]]
```

Return the set of builtin tool types this model can handle.

###### Returns

[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

### OpenAIResponsesModel

**Bases:** `Model[AsyncOpenAI]`

A model that uses the OpenAI Responses API.

The [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses) is the new API for OpenAI models.

If you are interested in the differences between the Responses API and the Chat Completions API, see the [OpenAI API docs](https://platform.openai.com/docs/guides/responses-vs-chat-completions).

#### Attributes

##### model\_name

The model name.

**Type:** `OpenAIModelName`

##### system

The model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: OpenAIModelName,
    *,
    provider: OpenAIResponsesCompatibleProvider | Literal['openai', 'gateway'] | Provider[AsyncOpenAI] = 'openai',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize an OpenAI Responses model.

###### Parameters

**`model_name`** : `OpenAIModelName`

The name of the OpenAI model to use.

**`provider`** : `OpenAIResponsesCompatibleProvider` | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['openai', 'gateway'\] | `Provider`\[`AsyncOpenAI`\] _Default:_ `'openai'`

The provider to use. Defaults to `'openai'`.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Default model settings for this model instance.

##### resolve\_prompt\_cache\_retention

```python
def resolve_prompt_cache_retention(
    model_settings: ModelSettings | None,
) -> timedelta | None
```

Resolve the extended prompt cache retention requested by OpenAI settings.

###### Returns

`timedelta` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### cancel\_suspended\_response

`@async`

```python
def cancel_suspended_response(response: ModelResponse) -> None
```

Cancel a suspended background response by cancelling its server-side job.

`responses.cancel` only applies to background responses; calling it on an ordinary (foreground) response returns a 400. The `provider_details['background']` marker is stamped from the API's own `response.background` field (see `_process_response` and `OpenAIResponsesStreamedResponse._track_background`), so it explicitly and reliably distinguishes a cancellable background job from a normal streamed response that happens to be interrupted by `cancel()` -- no need to infer background mode from the `continuation_delay` poll interval.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### supported\_native\_tools

`@classmethod`

```python
def supported_native_tools(cls) -> frozenset[type[AbstractNativeTool]]
```

Return the set of builtin tool types this model can handle.

###### Returns

[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

##### compact\_messages

`@async`

```python
def compact_messages(
    request_context: ModelRequestContext,
    *,
    instructions: str | None = None,
) -> ModelResponse
```

Compact messages using the OpenAI Responses compaction endpoint.

This calls OpenAI's `responses.compact` API to produce an encrypted compaction that summarizes the conversation history. The returned `ModelResponse` contains a single `CompactionPart` that must be round-tripped in subsequent requests.

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse) -- A `ModelResponse` with a single `CompactionPart` containing the encrypted compaction data.

###### Parameters

**`request_context`** : [`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

The model request context containing messages, settings, and parameters.

**`instructions`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional custom instructions for the compaction summarization. If provided, these override the agent-level instructions.

### OpenAIStreamedResponse

**Bases:** `StreamedResponse`

Implementation of `StreamedResponse` for OpenAI models.

#### Attributes

##### model\_name

Get the model name of the response.

**Type:** `OpenAIModelName`

##### provider\_name

Get the provider name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_url

Get the provider base URL.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

### OpenAIResponsesStreamedResponse

**Bases:** `StreamedResponse`

Implementation of `StreamedResponse` for OpenAI Responses API.

#### Attributes

##### model\_name

Get the model name of the response.

**Type:** `OpenAIModelName`

##### provider\_name

Get the provider name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_url

Get the provider base URL.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

### OpenAICompaction

**Bases:** `AbstractCapability[AgentDepsT]`

Compaction capability for OpenAI Responses API.

Automatically compacts conversation history to keep long-running agent runs within manageable context limits. Two modes are supported, selected by the `stateless` flag:

-   **Stateful mode** (default, `stateless=False`): configures [OpenAI's server-side auto-compaction](https://developers.openai.com/api/docs/guides/compaction) via the `context_management` field on the regular `/responses` request. The server triggers compaction when input tokens cross a threshold, and the compacted item is returned alongside the normal response. On subsequent requests, only that item and the content after it are sent. Compatible with [`openai_previous_response_id='auto'`](https://pydantic.dev/docs/ai/api/models/openai/#pydantic_ai.models.openai.OpenAIResponsesModelSettings.openai_previous_response_id) and server-side conversation state.
    
    Configurable with `token_threshold` (`compact_threshold` on the API). If omitted, OpenAI picks a server-side default.
    
-   **Stateless mode** (`stateless=True`): calls the stateless `/responses/compact` endpoint from a `before_model_request` hook when your trigger condition is met. Use this in [ZDR](https://openai.com/enterprise-privacy/) environments where OpenAI must not retain conversation data, when you set `openai_store=False`, or when you need explicit out-of-band control over when compaction runs.
    
    Requires either `message_count_threshold` or a custom `trigger` callable.
    

If `stateless` is not set, it is inferred from which parameters you provide: passing any stateless-only parameter (`message_count_threshold` or `trigger`) implies `stateless=True`; otherwise stateful mode is used.

Example usage:

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAICompaction

# Stateful mode with OpenAI's server-side default threshold:
agent = Agent(
    'openai-responses:gpt-5.2',
    capabilities=[OpenAICompaction()],
)

# Stateful mode with a custom token threshold:
agent = Agent(
    'openai-responses:gpt-5.2',
    capabilities=[OpenAICompaction(token_threshold=100_000)],
)

# Stateless mode for ZDR environments or explicit control:
agent = Agent(
    'openai-responses:gpt-5.2',
    capabilities=[OpenAICompaction(message_count_threshold=20)],
)
```

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    stateless: bool | None = None,
    token_threshold: int | None = None,
    message_count_threshold: int | None = None,
    trigger: Callable[[list[ModelMessage]], bool] | None = None,
) -> None
```

Initialize the OpenAI compaction capability.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`stateless`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Select the compaction mode explicitly. If `None` (the default), the mode is inferred from the other parameters: passing any stateless-only parameter (`message_count_threshold` or `trigger`) implies `stateless=True`; otherwise stateful mode is used.

**`token_threshold`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Stateful-mode only. Input token threshold at which OpenAI's server-side compaction is triggered. Corresponds to `compact_threshold` in the `context_management` API field. If `None`, OpenAI picks a server-side default.

**`message_count_threshold`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Stateless-mode only. Compact when the message count exceeds this threshold.

**`trigger`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]\], [`bool`](https://docs.python.org/3/builtins/functions.html#bool)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Stateless-mode only. Custom callable that decides whether to compact based on the current messages. Takes precedence over `message_count_threshold`.

### DEPRECATED\_OPENAI\_MODELS

Models that are deprecated or don't exist but are still present in the OpenAI SDK's type definitions.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `frozenset({'chatgpt-4o-latest', 'codex-mini-latest', 'gpt-3.5-turbo-0613', 'gpt-3.5-turbo-16k-0613', 'gpt-4-0125-preview', 'gpt-4-1106-preview', 'gpt-4-turbo-preview', 'gpt-4-32k', 'gpt-4-32k-0314', 'gpt-4-32k-0613', 'gpt-4-vision-preview', 'gpt-4o-audio-preview-2024-10-01', 'gpt-5.1-mini', 'o1-mini', 'o1-mini-2024-09-12', 'o1-preview', 'o1-preview-2024-09-12'})`

### OpenAIModelName

Possible OpenAI model names.

Since OpenAI supports a variety of date-stamped models, we explicitly list the latest models but allow any name in the type hints. See [the OpenAI docs](https://platform.openai.com/docs/models) for a full list.

Using this more broad type for the model name instead of the ChatModel definition allows this model to be used more easily with other model types (ie, Ollama, Deepseek).

The ids in the local `Literal` are bridged because `AllModels` doesn't list them at the floor the `openai` extra declares; they arrived in `openai` 3.1.0 ([https://github.com/openai/openai-python/pull/3617](https://github.com/openai/openai-python/pull/3617)). Drop them once the floor is bumped past it.

**Default:** `str | AllModels | Literal['gpt-5.5-2026-04-23', 'gpt-5.5-pro', 'gpt-5.5-pro-2026-04-23']`

### MCP\_SERVER\_TOOL\_CONNECTOR\_URI\_SCHEME

Prefix for OpenAI connector IDs. OpenAI supports either a URL or a connector ID when passing MCP configuration to a model, by using that prefix like `x-openai-connector:<connector-id>` in a URL, you can pass a connector ID to a model.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['x-openai-connector'\] **Default:** `'x-openai-connector'`

---
