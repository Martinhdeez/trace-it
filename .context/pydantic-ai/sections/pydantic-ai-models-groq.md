# [pydantic_ai.models.groq](https://pydantic.dev/docs/ai/api/models/groq/)

# pydantic\_ai.models.groq

## Setup

For details on how to set up authentication with this model, see [model configuration for Groq](https://pydantic.dev/docs/ai/models/groq/).

### GroqModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings used for a Groq model request.

#### Attributes

##### groq\_reasoning\_format

The format of the reasoning output.

See [the Groq docs](https://console.groq.com/docs/reasoning#reasoning-format) for more details.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['hidden', 'raw', 'parsed'\]

##### groq\_reasoning\_effort

The reasoning effort level.

See [the Groq docs](https://console.groq.com/docs/reasoning#reasoning-effort) for more details.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['none', 'default', 'low', 'medium', 'high'\]

### GroqModel

**Bases:** `Model[AsyncGroq]`

A model that uses the Groq API.

Internally, this uses the [Groq Python client](https://github.com/groq/groq-python) to interact with the API.

Apart from `__init__`, all methods are private or match those of the base class.

#### Attributes

##### model\_name

The model name.

**Type:** `GroqModelName`

##### system

The model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: GroqModelName,
    *,
    provider: Literal['groq', 'gateway'] | Provider[AsyncGroq] = 'groq',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize a Groq model.

###### Parameters

**`model_name`** : `GroqModelName`

The name of the Groq model to use. List of model names available [here](https://console.groq.com/docs/models).

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['groq', 'gateway'\] | `Provider`\[`AsyncGroq`\] _Default:_ `'groq'`

The provider to use for authentication and API access. Can be either the string 'groq' or an instance of `Provider[AsyncGroq]`. If not provided, a new provider will be created using the other parameters.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

##### supported\_native\_tools

`@classmethod`

```python
def supported_native_tools(cls) -> frozenset[type[AbstractNativeTool]]
```

Return the set of builtin tool types this model can handle.

###### Returns

[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

### GroqStreamedResponse

**Bases:** `StreamedResponse`

Implementation of `StreamedResponse` for Groq models.

#### Attributes

##### model\_name

Get the model name of the response.

**Type:** `GroqModelName`

##### provider\_name

Get the provider name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_url

Get the provider base URL.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

### ProductionGroqModelNames

Production Groq models from [https://console.groq.com/docs/models#production-models](https://console.groq.com/docs/models#production-models).

**Default:** `Literal['llama-3.1-8b-instant', 'llama-3.3-70b-versatile', 'meta-llama/llama-guard-4-12b', 'openai/gpt-oss-120b', 'openai/gpt-oss-20b', 'whisper-large-v3', 'whisper-large-v3-turbo']`

### PreviewGroqModelNames

Preview Groq models from [https://console.groq.com/docs/models#preview-models](https://console.groq.com/docs/models#preview-models).

**Default:** `Literal['meta-llama/llama-4-maverick-17b-128e-instruct', 'meta-llama/llama-prompt-guard-2-22m', 'meta-llama/llama-prompt-guard-2-86m', 'openai/gpt-oss-safeguard-20b', 'playai-tts', 'playai-tts-arabic']`

### GroqModelName

Possible Groq model names.

Since Groq supports a variety of models and the list changes frequently, we explicitly list the named models as of 2025-03-31 but allow any name in the type hints.

See [https://console.groq.com/docs/models](https://console.groq.com/docs/models) for an up to date list of models and more details.

**Default:** `str | ProductionGroqModelNames | PreviewGroqModelNames`

---
