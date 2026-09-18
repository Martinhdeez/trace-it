# [pydantic_ai.models.xai](https://pydantic.dev/docs/ai/api/models/xai/)

# pydantic\_ai.models.xai

## Setup

For details on how to set up authentication with this model, see [model configuration for xAI](https://pydantic.dev/docs/ai/models/xai/).

xAI model implementation using [xAI SDK](https://github.com/xai-org/xai-sdk-python).

### XaiModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings specific to xAI models.

See [xAI SDK documentation](https://docs.x.ai/docs) for more details on these parameters.

#### Attributes

##### xai\_logprobs

Whether to return log probabilities of the output tokens or not.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### xai\_top\_logprobs

An integer between 0 and 20 specifying the number of most likely tokens to return at each position.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### xai\_user

A unique identifier representing your end-user, which can help xAI to monitor and detect abuse.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### xai\_store\_messages

Whether to store messages on xAI's servers for conversation continuity.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### xai\_previous\_response\_id

The ID of the previous response to continue the conversation.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### xai\_include\_encrypted\_content

Whether to include the encrypted content in the response.

Corresponds to the `use_encrypted_content` value of the model settings in the Responses API.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### xai\_include\_code\_execution\_output

Whether to include the code execution results in the response.

Corresponds to the `code_interpreter_call.outputs` value of the `include` parameter in the Responses API.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### xai\_include\_web\_search\_output

Whether to include the web search results in the response.

Corresponds to the `web_search_call.action.sources` value of the `include` parameter in the Responses API.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### xai\_include\_inline\_citations

Whether to include inline citations in the response.

Corresponds to the `inline_citations` option in the xAI `include` parameter.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### xai\_include\_mcp\_output

Whether to include the MCP results in the response.

Corresponds to the `mcp_call.outputs` value of the `include` parameter in the Responses API.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### xai\_include\_x\_search\_output

Whether to include the X search results in the response.

Corresponds to the `x_search_call.outputs` value of the `include` parameter in the Responses API.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### xai\_include\_collections\_search\_output

Whether to include the collections search results in the response.

Corresponds to the `collections_search_call.outputs` value of the `include` parameter in the Responses API.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### xai\_include\_attachment\_search\_output

Whether to include the attachment search results in the response.

Defaults to `False`.

Corresponds to `INCLUDE_OPTION_ATTACHMENT_SEARCH_CALL_OUTPUT` in the xAI SDK.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### xai\_reasoning\_effort

Reasoning effort level for Grok reasoning models.

See [https://docs.x.ai](https://docs.x.ai/) for details.

**Type:** `GrokReasoningEffort`

##### xai\_max\_turns

Maximum number of agentic turns xAI's server-side tool loop may take.

Only affects requests that use xAI's server-side native tools (e.g. web search, code execution, X search): xAI iterates up to this many turns -- calling those server-side tools and processing their results -- before returning a final response. It has no effect on ordinary client-side tools or on Pydantic AI's own agent loop; use [`UsageLimits`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.UsageLimits) to bound those.

With parallel tool calls enabled, multiple tool calls can occur within a single turn, so `xai_max_turns` does not necessarily equal the total number of tool calls made.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### xai\_agent\_count

Number of agents for xAI multi-agent models (e.g. `grok-4.20-multi-agent`).

Forwarded to `chat.create(agent_count=...)`. Documented values are `4` and `16`; more agents increase token usage and latency. Only affects multi-agent models; other models ignore it. The multi-agent API is in beta, so the accepted values may change.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

### XaiModel

**Bases:** `Model[AsyncClient]`

A model that uses the xAI SDK to interact with xAI models.

#### Attributes

##### model\_name

The model name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: XaiModelName,
    *,
    provider: Literal['xai'] | Provider[AsyncClient] = 'xai',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize the xAI model.

###### Parameters

**`model_name`** : `XaiModelName`

The name of the xAI model to use (e.g., "grok-4.3")

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['xai'\] | `Provider`\[`AsyncClient`\] _Default:_ `'xai'`

The provider to use for API calls. Defaults to `'xai'`.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model profile specification. Defaults to a profile picked by the provider based on the model name.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model settings.

##### supported\_native\_tools

`@classmethod`

```python
def supported_native_tools(cls) -> frozenset[type[AbstractNativeTool]]
```

Return the set of builtin tool types this model can handle.

###### Returns

[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

##### request

`@async`

```python
def request(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> ModelResponse
```

Make a request to the xAI model.

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

Make a streaming request to the xAI model.

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[`StreamedResponse`\]

### XaiStreamedResponse

**Bases:** `StreamedResponse`

Implementation of `StreamedResponse` for xAI SDK.

#### Attributes

##### system

The model provider system name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_url

Get the provider base URL.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### model\_name

Get the model name of the response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_name

The model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

### XaiModelName

Possible xAI model names.

The ids in the local `Literal` are bridged because `xai_sdk`'s `ChatModel` doesn't list them at the floor the `xai` extra declares: `grok-build-0.1` arrived in 1.15.0, `grok-4.5`/`grok-4.5-latest` in 1.17.1, and `grok-4.6` in 1.18.0. Drop each once the floor is bumped past the release that adds it to `ChatModel`. [https://github.com/xai-org/xai-sdk-python/blob/main/CHANGELOG.md](https://github.com/xai-org/xai-sdk-python/blob/main/CHANGELOG.md)

**Default:** `str | ChatModel | Literal['grok-4.5', 'grok-4.5-latest', 'grok-4.6', 'grok-build-0.1']`

---
