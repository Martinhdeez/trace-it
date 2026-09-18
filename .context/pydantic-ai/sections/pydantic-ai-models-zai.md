# [pydantic_ai.models.zai](https://pydantic.dev/docs/ai/api/models/zai/)

# pydantic\_ai.models.zai

## Setup

For details on how to set up authentication with this model, see [model configuration for Z.AI](https://pydantic.dev/docs/ai/models/zai/).

Z.AI (Zhipu AI) model implementation using OpenAI-compatible API.

### ZaiModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings used for a Z.AI model request.

ALL FIELDS MUST BE `zai_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

#### Attributes

##### zai\_clear\_thinking

Whether to clear historical thinking content from prior turns.

Defaults to `False` (preserved thinking) on thinking-capable models, retaining reasoning content from prior assistant responses for improved multi-turn coherence and consistency with other providers. Set to `True` to clear it instead.

Only affects cross-turn historical thinking blocks; it does not change whether the model generates thinking in the current turn (controlled by the unified `thinking` setting).

When using preserved thinking, you must return the complete, unmodified `reasoning_content` back to the API. All consecutive `reasoning_content` blocks must exactly match the original sequence.

See [the Z.AI docs](https://docs.z.ai/guides/capabilities/thinking-mode#preserved-thinking) for more details.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### ZaiModel

**Bases:** `OpenAIChatModel`

A model that uses Z.AI's OpenAI-compatible API.

Z.AI (Zhipu AI) provides GLM models with support for thinking/reasoning mode and preserved thinking across turns.

Apart from `__init__`, all methods are private or match those of the base class.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: ZaiModelName,
    *,
    provider: Literal['zai'] | Provider[AsyncOpenAI] = 'zai',
    profile: ModelProfileSpec | None = None,
    settings: ZaiModelSettings | None = None,
)
```

Initialize a Z.AI model.

###### Parameters

**`model_name`** : `ZaiModelName`

The name of the Z.AI model to use.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['zai'\] | `Provider`\[`AsyncOpenAI`\] _Default:_ `'zai'`

The provider to use. Defaults to 'zai'.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile based on the model name.

**`settings`** : `ZaiModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

### ZaiStreamedResponse

**Bases:** `OpenAIStreamedResponse`

Implementation of `StreamedResponse` for Z.AI models.

Streamed chunks need no widened type: the openai SDK builds them leniently, so Z.AI's non-standard `finish_reason` reaches us as-is and only the mapping below has to know about it.

### ZaiModelName

Possible Z.AI model names.

Since Z.AI supports a variety of models and the list changes frequently, we explicitly list known models but allow any name in the type hints.

See [https://docs.z.ai/](https://docs.z.ai/) for an up to date list of models.

**Default:** `str | LatestZaiModelNames`

---
