# [pydantic_ai.models.snowflake](https://pydantic.dev/docs/ai/api/models/snowflake/)

# pydantic\_ai.models.snowflake

## Setup

For details on how to set up authentication with this model, see [model configuration for Snowflake Cortex](https://pydantic.dev/docs/ai/models/snowflake/).

Snowflake Cortex model implementation using Snowflake's OpenAI-compatible Chat Completions API.

### SnowflakeReasoning

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Configuration for reasoning tokens in Snowflake Cortex requests to Claude models.

See [https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-rest-api](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-rest-api) for details.

#### Attributes

##### effort

Reasoning effort level. Converted to a reasoning token budget by Cortex. Cannot be used with `max_tokens`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['high', 'medium', 'low'\]

##### max\_tokens

Specific token limit for reasoning. Cannot be used with `effort`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

### SnowflakeModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings used for a Snowflake Cortex model request.

ALL FIELDS MUST BE `snowflake_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

#### Attributes

##### snowflake\_reasoning

Configure reasoning tokens for Claude models.

Defaults to an effort level based on the unified `thinking` setting.

**Type:** `SnowflakeReasoning`

### SnowflakeModel

**Bases:** `OpenAIChatModel`

A model that uses Snowflake Cortex's OpenAI-compatible Chat Completions API.

Snowflake Cortex serves Claude, GPT, Llama, Mistral, DeepSeek, and Snowflake's own models, with all inference running inside the customer's Snowflake account.

Apart from `__init__`, all methods are private or match those of the base class.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: SnowflakeModelName,
    *,
    provider: Literal['snowflake'] | Provider[AsyncOpenAI] = 'snowflake',
    profile: ModelProfileSpec | None = None,
    settings: SnowflakeModelSettings | None = None,
)
```

Initialize a Snowflake Cortex model.

###### Parameters

**`model_name`** : `SnowflakeModelName`

The name of the Snowflake Cortex model to use.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['snowflake'\] | `Provider`\[`AsyncOpenAI`\] _Default:_ `'snowflake'`

The provider to use. Defaults to 'snowflake'.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile based on the model name.

**`settings`** : `SnowflakeModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

### SnowflakeStreamedResponse

**Bases:** `OpenAIStreamedResponse`

Implementation of `StreamedResponse` for Snowflake Cortex models.

### SnowflakeModelName

Possible Snowflake Cortex model names.

Since Snowflake Cortex serves a variety of models and the list changes frequently, we explicitly list known models but allow any name in the type hints. Fine-tuned models can be referenced as `database.schema.model`.

See [https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-rest-api](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-rest-api) for an up to date list of models.

**Default:** `str | LatestSnowflakeModelNames`

---
