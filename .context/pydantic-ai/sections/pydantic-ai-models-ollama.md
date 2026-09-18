# [pydantic_ai.models.ollama](https://pydantic.dev/docs/ai/api/models/ollama/)

# pydantic\_ai.models.ollama

## Setup

For details on how to set up authentication with this model, see [model configuration for Ollama](https://pydantic.dev/docs/ai/models/ollama/).

Ollama model implementation using OpenAI-compatible API.

### OllamaModel

**Bases:** `OpenAIChatModel`

A model that uses Ollama's OpenAI-compatible Chat Completions API.

Self-hosted Ollama (v0.5.0+) honors `response_format` with `json_schema` via `llama.cpp`'s grammar-constrained decoder, so `NativeOutput` produces schema-valid output at generation time.

Ollama Cloud currently accepts `response_format` with `json_schema` without error but does not enforce the schema upstream (see [pydantic-ai#4917](https://github.com/pydantic/pydantic-ai/issues/4917) and [ollama/ollama#12362](https://github.com/ollama/ollama/issues/12362)). When this model detects a Cloud path -- either a `base_url` on `ollama.com` or a model name ending in `-cloud` -- it disables `supports_json_schema_output` on the resolved profile. With that flag off, [`NativeOutput`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.NativeOutput) raises a clear [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) so users pick a mode that actually works on Cloud ([`ToolOutput`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.ToolOutput) -- the default -- and [`PromptedOutput`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.PromptedOutput) are both verified to work).

Apart from `__init__`, all methods are inherited from the base class.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: str,
    *,
    provider: Literal['ollama'] | Provider[AsyncOpenAI] = 'ollama',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize an Ollama model.

###### Parameters

**`model_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The name of the Ollama model to use (e.g. `'qwen3'`, `'llama3.2'`).

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['ollama'\] | `Provider`\[`AsyncOpenAI`\] _Default:_ `'ollama'`

The provider to use. Defaults to `'ollama'`.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name, adjusted to disable `supports_json_schema_output` when the request routes through Ollama Cloud.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

---
