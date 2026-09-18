# [pydantic_ai.models.huggingface](https://pydantic.dev/docs/ai/api/models/huggingface/)

# pydantic\_ai.models.huggingface

## Setup

For details on how to set up authentication with this model, see [model configuration for Hugging Face](https://pydantic.dev/docs/ai/models/huggingface/).

### HuggingFaceModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings used for a Hugging Face model request.

### HuggingFaceModel

**Bases:** `Model[AsyncInferenceClient]`

A model that uses Hugging Face Inference Providers.

Internally, this uses the [HF Python client](https://github.com/huggingface/huggingface_hub) to interact with the API.

Apart from `__init__`, all methods are private or match those of the base class.

#### Attributes

##### base\_url

The base URL of the provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### model\_name

The model name.

**Type:** `HuggingFaceModelName`

##### system

The system / model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: str,
    *,
    provider: Literal['huggingface'] | Provider[AsyncInferenceClient] = 'huggingface',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize a Hugging Face model.

###### Parameters

**`model_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The name of the Model to use. You can browse available models [here](https://huggingface.co/models?pipeline_tag=text-generation&inference_provider=all&sort=trending).

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['huggingface'\] | `Provider`\[`AsyncInferenceClient`\] _Default:_ `'huggingface'`

The provider to use for Hugging Face Inference Providers. Can be either the string 'huggingface' or an instance of `Provider[AsyncInferenceClient]`. If not provided, the other parameters will be used.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

### HuggingFaceStreamedResponse

**Bases:** `StreamedResponse`

Implementation of `StreamedResponse` for Hugging Face models.

#### Attributes

##### model\_name

Get the model name of the response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_name

Get the provider name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_url

Get the provider base URL.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

### LatestHuggingFaceModelNames

Latest Hugging Face models.

**Default:** `Literal['deepseek-ai/DeepSeek-R1', 'meta-llama/Llama-3.3-70B-Instruct', 'meta-llama/Llama-4-Maverick-17B-128E-Instruct', 'meta-llama/Llama-4-Scout-17B-16E-Instruct', 'Qwen/QwQ-32B', 'Qwen/Qwen2.5-72B-Instruct', 'Qwen/Qwen3-235B-A22B', 'Qwen/Qwen3-32B']`

### HuggingFaceModelName

Possible Hugging Face model names.

You can browse available models [here](https://huggingface.co/models?pipeline_tag=text-generation&inference_provider=all&sort=trending).

**Default:** `str | LatestHuggingFaceModelNames`

---
