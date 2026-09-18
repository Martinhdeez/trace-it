# [pydantic_ai.models.bedrock_mantle](https://pydantic.dev/docs/ai/api/models/bedrock_mantle/)

# pydantic\_ai.models.bedrock\_mantle

## Setup

For details on how to set up authentication with these models, see [model configuration for Bedrock Mantle](https://pydantic.dev/docs/ai/models/bedrock/#bedrock-mantle).

### BedrockMantleResponsesModel

**Bases:** `OpenAIResponsesModel`

An OpenAI Responses model served by Amazon Bedrock Mantle.

Serves GPT-5.4+ (on the `/openai/v1` endpoint) and GPT-OSS (on the `/v1` endpoint); the endpoint is chosen from the model profile.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: BedrockMantleModelName,
    *,
    provider: Literal['bedrock-mantle'] | BedrockMantleProvider = 'bedrock-mantle',
    profile: ModelProfileSpec | None = None,
    settings: OpenAIResponsesModelSettings | None = None,
) -> None
```

Initialize a Bedrock Mantle Responses model.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`model_name`** : `BedrockMantleModelName`

The name of the model, e.g. `openai.gpt-5.6-luna`.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['bedrock-mantle'\] | `BedrockMantleProvider` _Default:_ `'bedrock-mantle'`

The provider to use. Defaults to the `bedrock-mantle` provider.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`settings`** : `OpenAIResponsesModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model settings to use. Defaults to `None`.

### BedrockMantleChatModel

**Bases:** `OpenAIChatModel`

An OpenAI Chat Completions model served by Amazon Bedrock Mantle (GPT-OSS Safeguard).

The response-scoped tool-call-ID normalization added for #6536 is Responses-only: Mantle's Chat Completions API returns globally-unique `chatcmpl-tool-*` IDs across separate responses (verified live), unlike the `/openai/v1/responses` endpoint's per-response `call_0` counter, so the Chat path needs no normalization.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: BedrockMantleModelName,
    *,
    provider: Literal['bedrock-mantle'] | BedrockMantleProvider = 'bedrock-mantle',
    profile: ModelProfileSpec | None = None,
    settings: OpenAIChatModelSettings | None = None,
) -> None
```

Initialize a Bedrock Mantle Chat Completions model.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`model_name`** : `BedrockMantleModelName`

The name of the model, e.g. `openai.gpt-oss-safeguard-20b`.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['bedrock-mantle'\] | `BedrockMantleProvider` _Default:_ `'bedrock-mantle'`

The provider to use. Defaults to the `bedrock-mantle` provider.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`settings`** : `OpenAIChatModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model settings to use. Defaults to `None`.

### LatestBedrockMantleModelNames

Latest OpenAI models served through Amazon Bedrock Mantle.

**Default:** `Literal['openai.gpt-5.4', 'openai.gpt-5.4-2026-03-05', 'openai.gpt-5.5', 'openai.gpt-5.5-2026-04-23', 'openai.gpt-5.6-luna', 'openai.gpt-5.6-sol', 'openai.gpt-5.6-terra', 'openai.gpt-oss-20b', 'openai.gpt-oss-120b', 'openai.gpt-oss-safeguard-20b', 'openai.gpt-oss-safeguard-120b']`

### BedrockMantleModelName

Possible Amazon Bedrock Mantle model names.

Since Bedrock Mantle supports a variety of OpenAI models and the list changes frequently, we explicitly list the latest models but allow any name in the type hints.

**Default:** `str | LatestBedrockMantleModelNames`

---
