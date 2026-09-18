# [pydantic_ai.models.cerebras](https://pydantic.dev/docs/ai/api/models/cerebras/)

# pydantic\_ai.models.cerebras

## Setup

For details on how to set up authentication with this model, see [model configuration for Cerebras](https://pydantic.dev/docs/ai/models/cerebras/).

Cerebras model implementation using OpenAI-compatible API.

### CerebrasModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings used for a Cerebras model request.

ALL FIELDS MUST BE `cerebras_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

#### Attributes

##### cerebras\_disable\_reasoning

Disable reasoning for the model.

Deprecated: use the unified `thinking=False` setting instead.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### cerebras\_clear\_thinking

Whether Cerebras strips prior reasoning from earlier turns on multi-turn `zai`/GLM requests.

`True` (Cerebras's API default) drops thinking from previous turns before the next request; `False` preserves it, which improves multi-turn coherence and prompt-cache hit rates at the cost of more tokens. Pydantic AI sends `False` by default for `zai`/GLM models (which replay prior reasoning as `<think>` tags) so the replayed reasoning isn't stripped; set this explicitly to override. GLM-specific setting.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### CerebrasModel

**Bases:** `OpenAIChatModel`

A model that uses Cerebras's OpenAI-compatible API.

Cerebras provides ultra-fast inference powered by the Wafer-Scale Engine (WSE).

Apart from `__init__`, all methods are private or match those of the base class.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: CerebrasModelName,
    *,
    provider: Literal['cerebras'] | Provider[AsyncOpenAI] = 'cerebras',
    profile: ModelProfileSpec | None = None,
    settings: CerebrasModelSettings | None = None,
)
```

Initialize a Cerebras model.

###### Parameters

**`model_name`** : `CerebrasModelName`

The name of the Cerebras model to use.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['cerebras'\] | `Provider`\[`AsyncOpenAI`\] _Default:_ `'cerebras'`

The provider to use. Defaults to 'cerebras'.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile based on the model name.

**`settings`** : `CerebrasModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

### CerebrasModelName

Possible Cerebras model names.

Since Cerebras supports a variety of models and the list changes frequently, we explicitly list known models but allow any name in the type hints.

See [https://inference-docs.cerebras.ai/models/overview](https://inference-docs.cerebras.ai/models/overview) for an up to date list of models.

**Default:** `str | LatestCerebrasModelNames`

---
