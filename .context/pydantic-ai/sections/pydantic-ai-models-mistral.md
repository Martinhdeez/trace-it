# [pydantic_ai.models.mistral](https://pydantic.dev/docs/ai/api/models/mistral/)

# pydantic\_ai.models.mistral

## Setup

For details on how to set up authentication with this model, see [model configuration for Mistral](https://pydantic.dev/docs/ai/models/mistral/).

### MistralModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings used for a Mistral model request.

#### Attributes

##### mistral\_prompt\_cache\_key

Used by Mistral to improve cache hit rates for similar requests, mirroring `openai_prompt_cache_key`.

See the [Mistral prompt caching documentation](https://docs.mistral.ai/studio-api/conversations/advanced/prompt-caching) for more information.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### MistralModel

**Bases:** `Model[Mistral]`

A model that uses Mistral.

Internally, this uses the [Mistral Python client](https://github.com/mistralai/client-python) to interact with the API.

[API Documentation](https://docs.mistral.ai/)

#### Attributes

##### model\_name

The model name.

**Type:** `MistralModelName`

##### system

The model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: MistralModelName,
    *,
    provider: Literal['mistral'] | Provider[Mistral] = 'mistral',
    profile: ModelProfileSpec | None = None,
    json_mode_schema_prompt: str = 'Answer in JSON Object, respect the format:\n```\n{schema}\n```\n',
    settings: ModelSettings | None = None,
)
```

Initialize a Mistral model.

###### Parameters

**`model_name`** : `MistralModelName`

The name of the model to use.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['mistral'\] | `Provider`\[`Mistral`\] _Default:_ `'mistral'`

The provider to use for authentication and API access. Can be either the string 'mistral' or an instance of `Provider[Mistral]`. If not provided, a new provider will be created using the other parameters.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`json_mode_schema_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'Answer in JSON Object, respect the format:\n```\n{schema}\n```\n'`

The prompt to show when the model expects a JSON object as input.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

##### request

`@async`

```python
def request(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> ModelResponse
```

Make a non-streaming request to the model from Pydantic AI call.

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

Make a streaming request to the model from Pydantic AI call.

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[`StreamedResponse`\]

### MistralStreamedResponse

**Bases:** `StreamedResponse`

Implementation of `StreamedResponse` for Mistral models.

#### Attributes

##### model\_name

Get the model name of the response.

**Type:** `MistralModelName`

##### provider\_name

Get the provider name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_url

Get the provider base URL.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

### LatestMistralModelNames

Latest Mistral models.

**Default:** `Literal['mistral-large-latest', 'mistral-small-latest', 'codestral-latest', 'mistral-moderation-latest']`

### MistralModelName

Possible Mistral model names.

Since Mistral supports a variety of date-stamped models, we explicitly list the most popular models but allow any name in the type hints. Since [the Mistral docs](https://docs.mistral.ai/getting-started/models/models_overview/) for a full list.

**Default:** `str | LatestMistralModelNames`

---
