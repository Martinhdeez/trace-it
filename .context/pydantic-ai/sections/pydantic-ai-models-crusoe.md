# [pydantic_ai.models.crusoe](https://pydantic.dev/docs/ai/api/models/crusoe/)

# pydantic\_ai.models.crusoe

## Setup

For details on how to set up authentication with this model, see [model configuration for Crusoe](https://pydantic.dev/docs/ai/models/crusoe/).

Crusoe model implementation using OpenAI-compatible API.

### CrusoeModel

**Bases:** `OpenAIChatModel`

A model that uses Crusoe's OpenAI-compatible Serverless Inference API.

Crusoe serves open-weight models from many labs behind one endpoint, so the model family -- and with it the profile [`CrusoeProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.crusoe.CrusoeProvider) resolves -- is derived from the vendor prefix on the model name (`zai/`, `deepseek-ai/`, `meta-llama/`, ...).

Every model is served with guided decoding, so [`NativeOutput`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.NativeOutput) works across the catalog, including for families whose own profiles don't claim native structured output support. Thinking is returned in a non-standard field (`reasoning`, or `reasoning_content` for DeepSeek), both of which `OpenAIChatModel` reads.

Apart from `__init__`, all methods are inherited from the base class.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: CrusoeModelName,
    *,
    provider: Literal['crusoe'] | Provider[AsyncOpenAI] = 'crusoe',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize a Crusoe model.

###### Parameters

**`model_name`** : `CrusoeModelName`

The name of the Crusoe model to use, including the vendor prefix (e.g. `'zai/GLM-5.2'`).

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['crusoe'\] | `Provider`\[`AsyncOpenAI`\] _Default:_ `'crusoe'`

The provider to use. Defaults to `'crusoe'`.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

### CrusoeModelName

Possible Crusoe model names.

Since Crusoe supports a variety of models and the list changes frequently, we explicitly list known models but allow any name in the type hints.

See [https://docs.crusoecloud.com/serverless-inference/overview](https://docs.crusoecloud.com/serverless-inference/overview) for an up to date list of models.

**Default:** `str | LatestCrusoeModelNames`

---
