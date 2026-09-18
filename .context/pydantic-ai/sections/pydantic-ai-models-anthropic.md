# [pydantic_ai.models.anthropic](https://pydantic.dev/docs/ai/api/models/anthropic/)

# pydantic\_ai.models.anthropic

## Setup

For details on how to set up authentication with this model, see [model configuration for Anthropic](https://pydantic.dev/docs/ai/models/anthropic/).

### AnthropicStaleThinkingBlockWarning

**Bases:** [`Warning`](https://docs.python.org/3/builtins/exceptions.html#Warning)

Warning raised when Anthropic rejected a replayed thinking block and Pydantic AI retried without it.

Claude Fable 5.1 binds each thinking block to the conversation prefix that produced it and rejects a replay once that prefix changes -- which a dynamic [instructions](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.instructions) function and a [filtered toolset](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#filtering-tools) both do by design. Anthropic enforces the check for accounts created on or after 2026-08-31; for older accounts it records the mismatch and acts on it only if the request asks it to.

Pydantic AI therefore asks for nothing by default, so an older account keeps replaying its reasoning untouched. Where the check is enforced, the rejected request is retried once with `thinking.block_binding.prefix_mismatch_behavior='drop_block'`: the stale block is dropped, the run continues, and later requests carrying that response history keep asking for the drop as Anthropic requires. The drop is recorded on [`ModelResponse.provider_details`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse.provider_details) and as an `anthropic.input_transformations` span event.

### AnthropicModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings used for an Anthropic model request.

#### Attributes

##### anthropic\_metadata

An object describing metadata about the request.

Contains `user_id`, an external identifier for the user who is associated with the request.

**Type:** `BetaMetadataParam`

##### anthropic\_thinking

Determine whether the model should generate a thinking block.

See [the Anthropic docs](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) for more information.

**Type:** `BetaThinkingConfigParam`

##### anthropic\_cache\_tool\_definitions

Whether to add `cache_control` to the last tool definition.

When enabled, the last tool in the `tools` array will have `cache_control` set, allowing Anthropic to cache tool definitions and reduce costs. If `True`, uses TTL='5m'. You can also specify '5m' or '1h' directly. See [https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) for more information.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['5m', '1h'\]

##### anthropic\_service\_tier

The service tier to use for the model request.

See [https://docs.anthropic.com/en/docs/build-with-claude/latency-and-throughput](https://docs.anthropic.com/en/docs/build-with-claude/latency-and-throughput) for more information.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['auto', 'standard\_only'\]

##### anthropic\_cache\_instructions

Whether to add `cache_control` to the last system prompt block.

When enabled, the last system prompt will have `cache_control` set, allowing Anthropic to cache system instructions and reduce costs. If `True`, uses TTL='5m'. You can also specify '5m' or '1h' directly. See [https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) for more information.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['5m', '1h'\]

##### anthropic\_cache\_messages

Whether to add `cache_control` to the last message content block.

This is an alternative to `anthropic_cache` for Anthropic-compatible gateways and proxies that accept the Anthropic message format but don't support the top-level automatic caching parameter.

If `True`, uses TTL='5m'. You can also specify '5m' or '1h' directly. Cannot be combined with `anthropic_cache`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['5m', '1h'\]

##### anthropic\_cache

Enable prompt caching for multi-turn conversations.

Passes a top-level `cache_control` parameter so the server automatically applies a cache breakpoint to the last cacheable block and moves it forward as conversations grow.

On Bedrock and Vertex, automatic caching is not yet supported, so this falls back to per-block caching on the last user message. If the last content block already has `cache_control` from an explicit `CachePoint`, it is preserved.

If `True`, uses TTL='5m'. You can also specify '5m' or '1h' directly.

This can be combined with explicit cache breakpoints (`anthropic_cache_instructions`, `anthropic_cache_tool_definitions`, `CachePoint`). The automatic breakpoint counts as 1 of Anthropic's 4 cache point slots; we automatically trim excess explicit breakpoints. See [https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching#automatic-caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching#automatic-caching) for more information.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['5m', '1h'\]

##### anthropic\_effort

The effort level for the model to use when generating a response.

See [the Anthropic docs](https://docs.anthropic.com/en/docs/build-with-claude/effort) for more information.

**Type:** `AnthropicEffort` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### anthropic\_task\_budget

Task budget configuration for Anthropic beta requests.

Maps to `output_config.task_budget`. Supported models are gated by the [`anthropic_supports_task_budgets`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.anthropic.AnthropicModelProfile.anthropic_supports_task_budgets) profile flag, and Pydantic AI automatically enables Anthropic's required task-budget beta when this setting is present.

Omit `remaining` unless you are intentionally carrying a budget across compaction or other rewritten context.

**Type:** `AnthropicTaskBudget`

##### anthropic\_container

Container configuration for multi-turn conversations.

By default, if previous messages contain a container\_id (from a prior response), it will be reused automatically. An id recovered that way is the only container Pydantic AI may replace on its own: if a request carrying both that id and `CodeExecutionTool` uploads comes back `500`, the id is dropped and the request is sent once more so the upload lands in a fresh container. Nothing else is replaced -- not a container you set here, and not the id used to reconnect a paused turn -- so a request pinning a container the API will not accept raises instead.

Set to `False` to force a fresh container (ignore any `container_id` from history). Set to a container id string (e.g. `'container_xxx'`) to explicitly reuse a container, or to a `BetaContainerParams` dict (e.g. `{'skills': [...]}` or `{'id': 'container_xxx', 'skills': [...]}`) when passing Skills to the Anthropic Skills beta.

**Type:** `BetaContainerParams` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\[[`False`](https://docs.python.org/3/builtins/constants.html#False)\]

##### anthropic\_code\_execution\_tool\_version

Which Anthropic code execution tool version to send for `CodeExecutionTool`.

Defaults to `'auto'`, which uses the default version from the model profile: `'20260120'` for Sonnet 4.5+ and Opus 4.5+, otherwise `'20250825'`. Set a concrete version to force that tool version; a `UserError` is raised if the selected model profile does not support that version.

**Type:** `AnthropicCodeExecutionToolVersion` | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['auto'\]

##### anthropic\_eager\_input\_streaming

Whether to enable eager input streaming on tool definitions.

When enabled, all tool definitions will have `eager_input_streaming` set to `True`, allowing Anthropic to stream tool call arguments incrementally instead of buffering the entire JSON before streaming. This reduces latency for tool calls with large inputs. See [https://platform.claude.com/docs/en/agents-and-tools/tool-use/fine-grained-tool-streaming](https://platform.claude.com/docs/en/agents-and-tools/tool-use/fine-grained-tool-streaming) for more information.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### anthropic\_betas

List of Anthropic beta features to enable for API requests.

Each item can be a known beta name (e.g. 'interleaved-thinking-2025-05-14') or a custom string. Merged with auto-added betas (e.g. builtin tools) and any betas from extra\_headers\['anthropic-beta'\]. See the Anthropic docs for available beta features.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`AnthropicBetaParam`\]

##### anthropic\_speed

The inference speed mode for this request.

`'fast'` enables high output-tokens-per-second inference for supported models (currently Claude Opus 4.6, 4.7, 4.8, and 5). On unsupported models or clients, `anthropic_speed='fast'` is ignored with a `UserWarning`. Fast mode is a research preview and only available on the direct Anthropic API (not Bedrock, Vertex, or Foundry); see [the Anthropic docs](https://platform.claude.com/docs/en/build-with-claude/fast-mode) for details. Note: switching between `'fast'` and `'standard'` invalidates the prompt cache.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['standard', 'fast'\]

##### anthropic\_context\_management

Context management configuration for automatic compaction.

When configured, Anthropic will automatically compact older context when the input token count exceeds the configured threshold. The compaction produces a summary that replaces the compacted messages.

See [the Anthropic docs](https://docs.anthropic.com/en/docs/build-with-claude/compaction) for more details.

**Type:** `BetaContextManagementConfigParam`

### AnthropicModel

**Bases:** `Model[AsyncAnthropicClient]`

A model that uses the Anthropic API.

Internally, this uses the [Anthropic Python client](https://github.com/anthropics/anthropic-sdk-python) to interact with the API.

Apart from `__init__`, all methods are private or match those of the base class.

#### Attributes

##### model\_name

The model name.

**Type:** `AnthropicModelName`

##### system

The model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### profile

The model profile.

Anthropic web-tool availability depends on both model support and the client/platform, so the profile's `supported_native_tools` and `anthropic_supports_dynamic_filtering` are narrowed here for clients that don't support them (e.g. Bedrock, Vertex). `supports_inline_system_prompts` is narrowed the same way, and for the same reason: serving a `{'role': 'system'}` entry is a fact about the transport as much as about the model. Thinking-block binding is likewise narrowed, but by client class rather than by base URL: its beta and drop-block retry are verified against Anthropic's Messages API, which a proxied or gateway `AsyncAnthropic` still reaches.

**Type:** `AnthropicModelProfile`

##### tool\_addition\_mode

The effective addition mode, narrowed for transports without inline system messages.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['by\_reference'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: AnthropicModelName,
    *,
    provider: Literal['anthropic', 'gateway'] | Provider[AsyncAnthropicClient] = 'anthropic',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize an Anthropic model.

###### Parameters

**`model_name`** : `AnthropicModelName`

The name of the Anthropic model to use. List of model names available [here](https://docs.anthropic.com/en/docs/about-claude/models).

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['anthropic', 'gateway'\] | `Provider`\[`AsyncAnthropicClient`\] _Default:_ `'anthropic'`

The provider to use for the Anthropic API. Can be either the string 'anthropic' or an instance of `Provider[AsyncAnthropicClient]`. Defaults to 'anthropic'.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name. The default 'anthropic' provider will use the default `..profiles.anthropic.anthropic_model_profile`.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Default model settings for this model instance.

##### resolve\_prompt\_cache\_retention

```python
def resolve_prompt_cache_retention(
    model_settings: ModelSettings | None,
) -> timedelta | None
```

Resolve the longest retention requested by active Anthropic cache settings.

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

### AnthropicCompaction

**Bases:** `AbstractCapability[AgentDepsT]`

Compaction capability for Anthropic models.

Configures automatic context management via Anthropic's `context_management` API parameter. Compaction triggers server-side when input tokens exceed the configured threshold.

Example usage:

```python
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicCompaction

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[AnthropicCompaction(token_threshold=100_000)],
)
```

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    token_threshold: int = 150000,
    instructions: str | None = None,
    pause_after_compaction: bool = False,
) -> None
```

Initialize the Anthropic compaction capability.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`token_threshold`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) _Default:_ `150000`

Compact when input tokens exceed this threshold. Minimum 50,000.

**`instructions`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom instructions for the compaction summarization.

**`pause_after_compaction`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

If `True`, the response will stop after the compaction block with `stop_reason='compaction'`, allowing explicit handling.

### AnthropicStreamedResponse

**Bases:** `StreamedResponse`

Implementation of `StreamedResponse` for Anthropic models.

#### Attributes

##### model\_name

Get the model name of the response.

**Type:** `AnthropicModelName`

##### provider\_name

Get the provider name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_url

Get the provider base URL.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

### LatestAnthropicModelNames

Anthropic model names from the installed SDK.

**Default:** `ModelParam`

### AnthropicModelName

Possible Anthropic model names.

The installed Anthropic SDK exposes the current literal set and still allows arbitrary string model names. See [the Anthropic docs](https://docs.anthropic.com/en/docs/about-claude/models) for a full list.

**Default:** `LatestAnthropicModelNames`

### DEPRECATED\_ANTHROPIC\_MODELS

Models that have been retired by Anthropic but are still present in the SDK's type definitions.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `frozenset({'claude-3-haiku-20240307', 'claude-opus-4-0', 'claude-opus-4-20250514', 'claude-sonnet-4-0', 'claude-sonnet-4-20250514'})`

### AnthropicTaskBudget

Anthropic task budget payload for `output_config.task_budget`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `BetaTokenTaskBudgetParam`

---
