# [pydantic_ai.models.openai_codex](https://pydantic.dev/docs/ai/api/models/openai_codex/)

# pydantic\_ai.models.openai\_codex

## Setup

For details on how to set up authentication with this model, see [model configuration for OpenAI Codex](https://pydantic.dev/docs/ai/models/openai-codex/).

### OpenAICodexModel

**Bases:** `OpenAIResponsesModel`

A model that uses the OpenAI Codex backend under a ChatGPT/Codex subscription.

This model mirrors the official Codex client's prompt-cache affinity by sending the `session-id`, `thread-id`, and `x-client-request-id` headers and the `prompt_cache_key` field, all derived from the `conversation_id` of the message history. Explicit `extra_headers` and `openai_prompt_cache_key` settings win.

Apart from `__init__`, all methods are private or match those of the base class.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: OpenAIModelName,
    *,
    provider: Literal['openai-codex'] | Provider[AsyncOpenAI] = 'openai-codex',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize an OpenAI Codex model.

###### Parameters

**`model_name`** : `OpenAIModelName`

The name of the OpenAI model to use.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['openai-codex'\] | `Provider`\[`AsyncOpenAI`\] _Default:_ `'openai-codex'`

The provider to use. Defaults to `'openai-codex'`.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Default model settings for this model instance.

---
