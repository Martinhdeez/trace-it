# [pydantic_ai.models.bedrock](https://pydantic.dev/docs/ai/api/models/bedrock/)

# pydantic\_ai.models.bedrock

## Setup

For details on how to set up authentication with this model, see [model configuration for Bedrock](https://pydantic.dev/docs/ai/models/bedrock/).

### BedrockModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings for Bedrock models.

See [the Bedrock Converse API docs](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html#API_runtime_Converse_RequestSyntax) for a full list. See [the boto3 implementation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse.html) of the Bedrock Converse API.

`extra_headers` are injected before the request is signed, so under SigV4 authentication they are covered by the signature (except the few headers botocore never signs, e.g. `X-Amzn-Trace-Id`). Headers the AWS SDK computes itself (e.g. `Authorization`, `User-Agent`, `X-Amz-Date`) are overwritten by botocore afterwards.

#### Attributes

##### bedrock\_guardrail\_config

Content moderation and safety settings for Bedrock API requests.

See more about it on [https://docs.aws.amazon.com/bedrock/latest/APIReference/API\_runtime\_GuardrailConfiguration.html](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_GuardrailConfiguration.html).

**Type:** `GuardrailConfigurationTypeDef`

##### bedrock\_performance\_configuration

Performance optimization settings for model inference.

See more about it on [https://docs.aws.amazon.com/bedrock/latest/APIReference/API\_runtime\_PerformanceConfiguration.html](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_PerformanceConfiguration.html).

**Type:** `PerformanceConfigurationTypeDef`

##### bedrock\_request\_metadata

Additional metadata to attach to Bedrock API requests.

See more about it on [https://docs.aws.amazon.com/bedrock/latest/APIReference/API\_runtime\_Converse.html#API\_runtime\_Converse\_RequestSyntax](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html#API_runtime_Converse_RequestSyntax).

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### bedrock\_additional\_model\_response\_fields\_paths

JSON paths to extract additional fields from model responses.

See more about it on [https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters.html](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters.html).

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### bedrock\_prompt\_variables

Variables for substitution into prompt templates.

See more about it on [https://docs.aws.amazon.com/bedrock/latest/APIReference/API\_runtime\_PromptVariableValues.html](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_PromptVariableValues.html).

**Type:** [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `PromptVariableValuesTypeDef`\]

##### bedrock\_additional\_model\_requests\_fields

Additional model-specific parameters to include in requests.

See more about it on [https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters.html](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters.html).

**Type:** [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### bedrock\_cache\_tool\_definitions

Whether to add a cache point after the last tool definition.

When enabled, the last tool in the `tools` array will include a `cachePoint`, allowing Bedrock to cache tool definitions and reduce costs for compatible models.

Set to `True` or `'5m'` for a 5-minute TTL (the default), or `'1h'` for a 1-hour TTL. See [https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html) for more information.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['5m', '1h'\]

##### bedrock\_cache\_instructions

Whether to add a cache point after the system prompt blocks.

When enabled, an extra `cachePoint` is appended to the system prompt so Bedrock can cache system instructions.

Set to `True` or `'5m'` for a 5-minute TTL (the default), or `'1h'` for a 1-hour TTL. See [https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html) for more information.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['5m', '1h'\]

##### bedrock\_cache\_messages

Convenience setting to enable caching for the last user message.

When enabled, this automatically adds a cache point to the last content block in the final user message, which is useful for caching conversation history or context in multi-turn conversations.

Set to `True` or `'5m'` for a 5-minute TTL (the default), or `'1h'` for a 1-hour TTL.

Note: Uses 1 of Bedrock's 4 available cache points per request. Any additional CachePoint markers in messages will be automatically limited to respect the 4-cache-point maximum. See [https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html) for more information.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['5m', '1h'\]

##### bedrock\_service\_tier

Setting for optimizing performance and cost.

Accepts `{'type': 'default' | 'flex' | 'priority' | 'reserved'}`. Takes precedence over the top-level [`service_tier`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings.service_tier), and is the only way to request `'reserved'` (which requires a pre-purchased capacity reservation).

See more about it on [https://docs.aws.amazon.com/bedrock/latest/userguide/service-tiers-inference.html](https://docs.aws.amazon.com/bedrock/latest/userguide/service-tiers-inference.html).

**Type:** `ServiceTierTypeDef`

##### bedrock\_inference\_profile

An [inference profile](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles.html) ARN to use as the `modelId` in API requests.

When set, this value is used as the `modelId` in `converse` and `converse_stream` API calls instead of the base `model_name`. This allows you to pass the base model name (e.g. `'anthropic.claude-sonnet-4-5-20250929-v1:0'`) as `model_name` for detecting model capabilities and token counting, while routing requests through an inference profile for cost tracking or cross-region inference.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### BedrockConverseModel

**Bases:** `Model[BaseClient]`

A model that uses the Bedrock Converse API.

#### Attributes

##### client

The boto3 client used to make requests to the Bedrock Converse API.

Defaults to the client from the [`Provider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.Provider). It can be reassigned, e.g. to rotate short-lived credentials in a long-running service, but prefer assigning to [`BedrockProvider.client`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.bedrock.BedrockProvider.client) so all models sharing the provider pick up the new client. Once you've assigned a client here, you're responsible for keeping it valid; the provider's client is no longer consulted.

**Type:** `BedrockRuntimeClient`

##### model\_name

The model name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: BedrockModelName,
    *,
    provider: Literal['bedrock', 'gateway'] | Provider[BaseClient] = 'bedrock',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize a Bedrock model.

###### Parameters

**`model_name`** : `BedrockModelName`

The name of the model to use.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['bedrock', 'gateway'\] | `Provider`\[`BaseClient`\] _Default:_ `'bedrock'`

The provider to use for authentication and API access. Can be either the string 'bedrock' or an instance of `Provider[BaseClient]`. If not provided, a new provider will be created using the other parameters.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

##### resolve\_prompt\_cache\_retention

```python
def resolve_prompt_cache_retention(
    model_settings: ModelSettings | None,
) -> timedelta | None
```

Resolve the longest retention requested by supported Bedrock cache settings.

###### Returns

`timedelta` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### supported\_native\_tools

`@classmethod`

```python
def supported_native_tools(cls) -> frozenset[type[AbstractNativeTool]]
```

The set of builtin tool types this model can handle.

###### Returns

[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

##### count\_tokens

`@async`

```python
def count_tokens(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> usage.RequestUsage
```

Count the number of tokens, works with limited models.

Check the actual supported models on [https://docs.aws.amazon.com/bedrock/latest/userguide/count-tokens.html](https://docs.aws.amazon.com/bedrock/latest/userguide/count-tokens.html)

###### Returns

[`usage.RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage)

### BedrockStreamedResponse

**Bases:** `StreamedResponse`

Implementation of `StreamedResponse` for Bedrock models.

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

### LatestBedrockModelNames

Latest Bedrock models.

**Default:** `Literal['amazon.titan-tg1-large', 'amazon.titan-text-lite-v1', 'amazon.titan-text-express-v1', 'us.amazon.nova-2-lite-v1:0', 'us.amazon.nova-pro-v1:0', 'us.amazon.nova-lite-v1:0', 'us.amazon.nova-micro-v1:0', 'anthropic.claude-3-5-sonnet-20241022-v2:0', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0', 'anthropic.claude-3-5-haiku-20241022-v1:0', 'us.anthropic.claude-3-5-haiku-20241022-v1:0', 'anthropic.claude-instant-v1', 'anthropic.claude-v2:1', 'anthropic.claude-v2', 'anthropic.claude-3-sonnet-20240229-v1:0', 'us.anthropic.claude-3-sonnet-20240229-v1:0', 'anthropic.claude-3-haiku-20240307-v1:0', 'us.anthropic.claude-3-haiku-20240307-v1:0', 'anthropic.claude-3-opus-20240229-v1:0', 'us.anthropic.claude-3-opus-20240229-v1:0', 'anthropic.claude-3-5-sonnet-20240620-v1:0', 'us.anthropic.claude-3-5-sonnet-20240620-v1:0', 'anthropic.claude-3-7-sonnet-20250219-v1:0', 'us.anthropic.claude-3-7-sonnet-20250219-v1:0', 'anthropic.claude-opus-4-20250514-v1:0', 'us.anthropic.claude-opus-4-20250514-v1:0', 'global.anthropic.claude-opus-4-5-20251101-v1:0', 'anthropic.claude-sonnet-4-20250514-v1:0', 'us.anthropic.claude-sonnet-4-20250514-v1:0', 'eu.anthropic.claude-sonnet-4-20250514-v1:0', 'anthropic.claude-sonnet-4-5-20250929-v1:0', 'us.anthropic.claude-sonnet-4-5-20250929-v1:0', 'eu.anthropic.claude-sonnet-4-5-20250929-v1:0', 'anthropic.claude-sonnet-4-6', 'us.anthropic.claude-sonnet-4-6', 'eu.anthropic.claude-sonnet-4-6', 'anthropic.claude-haiku-4-5-20251001-v1:0', 'us.anthropic.claude-haiku-4-5-20251001-v1:0', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0', 'cohere.command-text-v14', 'cohere.command-r-v1:0', 'cohere.command-r-plus-v1:0', 'cohere.command-light-text-v14', 'meta.llama3-8b-instruct-v1:0', 'meta.llama3-70b-instruct-v1:0', 'meta.llama3-1-8b-instruct-v1:0', 'us.meta.llama3-1-8b-instruct-v1:0', 'meta.llama3-1-70b-instruct-v1:0', 'us.meta.llama3-1-70b-instruct-v1:0', 'meta.llama3-1-405b-instruct-v1:0', 'us.meta.llama3-2-11b-instruct-v1:0', 'us.meta.llama3-2-90b-instruct-v1:0', 'us.meta.llama3-2-1b-instruct-v1:0', 'us.meta.llama3-2-3b-instruct-v1:0', 'us.meta.llama3-3-70b-instruct-v1:0', 'mistral.mistral-7b-instruct-v0:2', 'mistral.mixtral-8x7b-instruct-v0:1', 'mistral.mistral-large-2402-v1:0', 'mistral.mistral-large-2407-v1:0', 'us.anthropic.claude-opus-4-1-20250805-v1:0', 'us.anthropic.claude-opus-4-5-20251101-v1:0', 'us.anthropic.claude-opus-4-6-v1', 'global.anthropic.claude-opus-4-6-v1', 'us.anthropic.claude-opus-4-7', 'global.anthropic.claude-opus-4-7', 'us.anthropic.claude-opus-4-8', 'global.anthropic.claude-opus-4-8', 'us.anthropic.claude-opus-5', 'global.anthropic.claude-opus-5', 'us.anthropic.claude-sonnet-5', 'global.anthropic.claude-sonnet-5', 'us.anthropic.claude-fable-5', 'us.anthropic.claude-fable-5-1', 'global.anthropic.claude-fable-5', 'global.anthropic.claude-fable-5-1', 'us.amazon.nova-premier-v1:0', 'global.amazon.nova-2-lite-v1:0', 'us.meta.llama4-maverick-17b-instruct-v1:0', 'us.meta.llama4-scout-17b-instruct-v1:0', 'mistral.mistral-small-2402-v1:0', 'mistral.mistral-large-3-675b-instruct', 'mistral.ministral-3-3b-instruct', 'mistral.ministral-3-8b-instruct', 'mistral.ministral-3-14b-instruct', 'mistral.magistral-small-2509', 'mistral.devstral-2-123b', 'mistral.pixtral-large-2502-v1:0', 'us.mistral.pixtral-large-2502-v1:0', 'deepseek.r1-v1:0', 'deepseek.v3.2', 'qwen.qwen3-32b-v1:0', 'qwen.qwen3-coder-30b-a3b-v1:0', 'qwen.qwen3-coder-next', 'qwen.qwen3-next-80b-a3b', 'qwen.qwen3-vl-235b-a22b', 'google.gemma-3-4b-it', 'google.gemma-3-12b-it', 'google.gemma-3-27b-it', 'minimax.minimax-m2', 'minimax.minimax-m2.1', 'minimax.minimax-m2.5', 'nvidia.nemotron-nano-9b-v2', 'nvidia.nemotron-nano-12b-v2', 'nvidia.nemotron-nano-3-30b', 'nvidia.nemotron-super-3-120b', 'us.writer.palmyra-x4-v1:0', 'us.writer.palmyra-x5-v1:0', 'zai.glm-4.7', 'zai.glm-4.7-flash', 'zai.glm-5', 'moonshot.kimi-k2-thinking', 'moonshotai.kimi-k2.5']`

### BedrockModelName

Possible Bedrock model names.

Since Bedrock supports a variety of date-stamped models, we explicitly list the latest models but allow any name in the type hints. See [the Bedrock docs](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html) for a full list.

**Default:** `str | LatestBedrockModelNames`

---
