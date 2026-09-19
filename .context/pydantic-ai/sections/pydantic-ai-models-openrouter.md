# [pydantic_ai.models.openrouter](https://pydantic.dev/docs/ai/api/models/openrouter/)

# pydantic\_ai.models.openrouter

## Setup

For details on how to set up authentication with this model, see [model configuration for OpenRouter](https://pydantic.dev/docs/ai/models/openrouter/).

### OpenRouterProviderConfig

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Represents the 'Provider' object from the OpenRouter API.

#### Attributes

##### order

List of provider slugs to try in order (e.g. \["anthropic", "openai"\]). [See details](https://openrouter.ai/docs/features/provider-routing#ordering-specific-providers)

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`OpenRouterProviderName`\]

##### allow\_fallbacks

Whether to allow backup providers when the primary is unavailable. [See details](https://openrouter.ai/docs/features/provider-routing#disabling-fallbacks)

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### require\_parameters

Only use providers that support all parameters in your request.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### data\_collection

Control whether to use providers that may store data. [See details](https://openrouter.ai/docs/features/provider-routing#requiring-providers-to-comply-with-data-policies)

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['allow', 'deny'\]

##### zdr

Restrict routing to only ZDR (Zero Data Retention) endpoints. [See details](https://openrouter.ai/docs/features/provider-routing#zero-data-retention-enforcement)

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### only

List of provider slugs to allow for this request. [See details](https://openrouter.ai/docs/features/provider-routing#allowing-only-specific-providers)

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`OpenRouterProviderName`\]

##### ignore

List of provider slugs to skip for this request. [See details](https://openrouter.ai/docs/features/provider-routing#ignoring-providers)

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### quantizations

List of quantization levels to filter by (e.g. \["int4", "int8"\]). [See details](https://openrouter.ai/docs/features/provider-routing#quantization)

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['int4', 'int8', 'fp4', 'fp6', 'fp8', 'fp16', 'bf16', 'fp32', 'unknown'\]\]

##### sort

Sort providers by price or throughput. (e.g. "price" or "throughput"). [See details](https://openrouter.ai/docs/features/provider-routing#provider-sorting)

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['price', 'throughput', 'latency'\]

##### max\_price

The maximum pricing you want to pay for this request. [See details](https://openrouter.ai/docs/features/provider-routing#max-price)

**Type:** `_OpenRouterMaxPrice`

### OpenRouterReasoning

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Configuration for reasoning tokens in OpenRouter requests.

Reasoning tokens allow models to show their step-by-step thinking process. You can configure this using either OpenAI-style effort levels or Anthropic-style token limits, but not both simultaneously.

#### Attributes

##### effort

OpenAI-style reasoning effort level. Cannot be used with max\_tokens.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['xhigh', 'high', 'medium', 'low', 'minimal', 'none'\]

##### max\_tokens

Anthropic-style specific token limit for reasoning. Cannot be used with effort.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### exclude

Whether to exclude reasoning tokens from the response. Default is False. All models support this.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### enabled

Whether to enable reasoning with default parameters. Default is inferred from effort or max\_tokens.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### OpenRouterUsageConfig

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Configuration for OpenRouter usage.

### OpenRouterModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings used for an OpenRouter model request.

#### Attributes

##### openrouter\_models

A list of fallback models.

These models will be tried, in order, if the main model returns an error. [See details](https://openrouter.ai/docs/features/model-routing#the-models-parameter)

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### openrouter\_provider

OpenRouter routes requests to the best available providers for your model. By default, requests are load balanced across the top providers to maximize uptime.

You can customize how your requests are routed using the provider object. [See more](https://openrouter.ai/docs/features/provider-routing)

**Type:** `OpenRouterProviderConfig`

##### openrouter\_preset

Presets allow you to separate your LLM configuration from your code.

Create and manage presets through the OpenRouter web application to control provider routing, model selection, system prompts, and other parameters, then reference them in OpenRouter API requests. [See more](https://openrouter.ai/docs/features/presets)

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### openrouter\_transforms

To help with prompts that exceed the maximum context size of a model.

Transforms work by removing or truncating messages from the middle of the prompt, until the prompt fits within the model's context window. [See more](https://openrouter.ai/docs/features/message-transforms)

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`OpenRouterTransforms`\]

##### openrouter\_reasoning

To control the reasoning tokens in the request.

The reasoning config object consolidates settings for controlling reasoning strength across different models. [See more](https://openrouter.ai/docs/use-cases/reasoning-tokens)

**Type:** `OpenRouterReasoning`

##### openrouter\_usage

To control the usage of the model.

The usage config object consolidates settings for enabling detailed usage information. [See more](https://openrouter.ai/docs/use-cases/usage-accounting)

**Type:** `OpenRouterUsageConfig`

##### openrouter\_cache\_instructions

Whether to add `cache_control` to stable system instructions.

When enabled, supported downstream providers (Anthropic, Gemini) can cache stable system instructions and reduce costs. If dynamic instructions are present, the cache point is placed before them, matching Anthropic's static-prefix caching behavior. For Gemini models, this setting is ignored when dynamic instructions are present because OpenRouter normalizes system/developer messages into a single immutable `systemInstruction`. Ignored for other downstream providers. If `True`, uses TTL='5m'. You can also specify '5m' or '1h' directly. TTL is only included for Anthropic models; Gemini does not support explicit TTL.

See [https://openrouter.ai/docs/guides/best-practices/prompt-caching](https://openrouter.ai/docs/guides/best-practices/prompt-caching) for more information.

**Type:** `OpenRouterCacheTTL`

##### openrouter\_cache\_messages

Convenience setting to enable caching for the last message in the conversation.

When enabled, this automatically adds `cache_control` to the last content block in the final message (regardless of role), which is useful for Anthropic's prefix-based caching in multi-turn conversations. In tool-use flows, this may target a tool result message rather than a user message, which is correct for prefix caching. Ignored for downstream providers that do not support explicit cache control. If `True`, uses TTL='5m'. You can also specify '5m' or '1h' directly. TTL is only included for Anthropic models; Gemini does not support explicit TTL.

Note: OpenRouter uses only the last breakpoint across normal message content for Gemini caching. Use this when caching the final message boundary is intentional; use `openrouter_cache_instructions` for stable system context. Anthropic supports prefix-based caching across multi-turn conversations with this setting.

See [https://openrouter.ai/docs/guides/best-practices/prompt-caching](https://openrouter.ai/docs/guides/best-practices/prompt-caching) for more information.

**Type:** `OpenRouterCacheTTL`

##### openrouter\_cache\_tool\_definitions

Whether to add `cache_control` to the last tool definition.

When enabled, the last tool in the `tools` array will have `cache_control` set, allowing supported downstream providers to cache tool definitions and reduce costs. Ignored for downstream providers that do not support explicit tool definition caching. If `True`, uses TTL='5m'. You can also specify '5m' or '1h' directly. TTL is only included for Anthropic models.

Currently only effective for Anthropic models via OpenRouter, as tool definition caching is not documented for other providers.

See [https://openrouter.ai/docs/guides/best-practices/prompt-caching](https://openrouter.ai/docs/guides/best-practices/prompt-caching) for more information.

**Type:** `OpenRouterCacheTTL`

### OpenRouterModel

**Bases:** `OpenAIChatModel`

Extends OpenAIChatModel to capture extra metadata for Openrouter.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: str,
    *,
    provider: Literal['openrouter'] | Provider[AsyncOpenAI] = 'openrouter',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize an OpenRouter model.

###### Parameters

**`model_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The name of the model to use.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['openrouter'\] | `Provider`\[`AsyncOpenAI`\] _Default:_ `'openrouter'`

The provider to use for authentication and API access. If not provided, a new provider will be created with the default settings.

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

Resolve the longest explicit retention accepted by OpenRouter's downstream model.

###### Returns

`timedelta` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### supported\_native\_tools

`@classmethod`

```python
def supported_native_tools(cls) -> frozenset[type[AbstractNativeTool]]
```

Return the set of builtin tool types this model can handle.

OpenRouter supports web search through its server-tool API.

###### Returns

[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

### OpenRouterStreamedResponse

**Bases:** `OpenAIStreamedResponse`

Implementation of `StreamedResponse` for OpenRouter models.

### KnownOpenRouterProviders

Known providers in the OpenRouter marketplace

**Default:** `Literal['z-ai', 'cerebras', 'venice', 'moonshotai', 'morph', 'stealth', 'wandb', 'klusterai', 'openai', 'sambanova', 'amazon-bedrock', 'mistral', 'nextbit', 'atoma', 'ai21', 'minimax', 'baseten', 'anthropic', 'featherless', 'groq', 'lambda', 'azure', 'ncompass', 'deepseek', 'hyperbolic', 'crusoe', 'cohere', 'mancer', 'avian', 'perplexity', 'novita', 'siliconflow', 'switchpoint', 'xai', 'inflection', 'fireworks', 'deepinfra', 'inference-net', 'inception', 'atlas-cloud', 'nvidia', 'alibaba', 'friendli', 'infermatic', 'targon', 'ubicloud', 'aion-labs', 'liquid', 'nineteen', 'cloudflare', 'nebius', 'chutes', 'enfer', 'crofai', 'open-inference', 'phala', 'gmicloud', 'meta', 'relace', 'parasail', 'together', 'google-ai-studio', 'google-vertex']`

### OpenRouterProviderName

Possible OpenRouter provider names.

Since OpenRouter is constantly updating their list of providers, we explicitly list some known providers but allow any name in the type hints. See [the OpenRouter API](https://openrouter.ai/docs/api-reference/list-available-providers) for a full list.

**Default:** `str | KnownOpenRouterProviders`

### OpenRouterTransforms

Available messages transforms for OpenRouter models with limited token windows.

Currently only supports 'middle-out', but is expected to grow in the future.

**Default:** `Literal['middle-out']`

### OpenRouterCacheTTL

Cache breakpoint time-to-live for OpenRouter prompt caching.

`True` selects the default TTL ('5m'); '5m' or '1h' may be given explicitly. The TTL is only forwarded to downstream providers that support it (Anthropic); it is omitted for Gemini.

**Default:** `bool | Literal['5m', '1h']`

---
