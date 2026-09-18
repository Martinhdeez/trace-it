# [pydantic_ai.models.cohere](https://pydantic.dev/docs/ai/api/models/cohere/)

# pydantic\_ai.models.cohere

## Setup

For details on how to set up authentication with this model, see [model configuration for Cohere](https://pydantic.dev/docs/ai/models/cohere/).

### CohereModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings used for a Cohere model request.

### CohereModel

**Bases:** `Model[AsyncClientV2]`

A model that uses the Cohere API.

Internally, this uses the [Cohere Python client](https://github.com/cohere-ai/cohere-python) to interact with the API.

Apart from `__init__`, all methods are private or match those of the base class.

#### Attributes

##### model\_name

The model name.

**Type:** `CohereModelName`

##### system

The model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: CohereModelName,
    *,
    provider: Literal['cohere'] | Provider[AsyncClientV2] = 'cohere',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize an Cohere model.

###### Parameters

**`model_name`** : `CohereModelName`

The name of the Cohere model to use. List of model names available [here](https://docs.cohere.com/docs/models#command).

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['cohere'\] | `Provider`\[`AsyncClientV2`\] _Default:_ `'cohere'`

The provider to use for authentication and API access. Can be either the string 'cohere' or an instance of `Provider[AsyncClientV2]`. If not provided, a new provider will be created using the other parameters.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

### LatestCohereModelNames

Latest Cohere models.

**Default:** `Literal['c4ai-aya-expanse-32b', 'c4ai-aya-expanse-8b', 'command-nightly', 'command-r-08-2024', 'command-r-plus-08-2024', 'command-r7b-12-2024']`

### CohereModelName

Possible Cohere model names.

Since Cohere supports a variety of date-stamped models, we explicitly list the latest models but allow any name in the type hints. See [Cohere's docs](https://docs.cohere.com/v2/docs/models) for a list of all available models.

**Default:** `str | LatestCohereModelNames`

---
