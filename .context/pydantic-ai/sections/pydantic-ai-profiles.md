# [pydantic_ai.profiles](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/)

# pydantic\_ai.profiles

### ModelProfile

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Describes how requests to and responses from specific models or families of models need to be constructed and processed to get the best results, independent of the model and provider classes used.

All fields are optional; absent keys mean "use the documented default" (defaults are documented per field below and applied at access sites).

Subclasses (`OpenAIModelProfile`, `AnthropicModelProfile`, ...) add provider-specific keys; cross-class merging via dict-spread is supported.

#### Attributes

##### supports\_tools

Whether the model supports tools. Default: `True`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_tool\_return\_schema

Whether the model natively supports tool return schemas. Default: `False`.

When True, the model's API accepts a structured return schema alongside each tool definition. When False, return schemas are injected as JSON text into tool descriptions as a fallback.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_json\_schema\_output

Whether the model supports JSON schema output. Default: `False`.

This is also referred to as 'native' support for structured output. Relates to the `NativeOutput` output type.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_json\_object\_output

Whether the model supports a dedicated mode to enforce JSON output, without necessarily sending a schema. Default: `False`.

E.g. [OpenAI's JSON mode](https://platform.openai.com/docs/guides/structured-outputs#json-mode) Relates to the `PromptedOutput` output type.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_image\_output

Whether the model supports image output. Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_audio\_input

Whether the model supports audio in user messages. Default: `False`.

Used when converting `SpeechPart`s from realtime session history in `Model.prepare_messages`: if `True`, retained audio is sent to the model as `BinaryContent`; otherwise the transcript text is used.

No shipping profile sets this to `True` yet, so retained realtime audio is currently always forwarded as transcript text on handoff; enabling it needs per-model-family verification that the provider accepts audio in user messages.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_inline\_system\_prompts

Whether the provider's API accepts `SystemPromptPart`s inline at any position. Default: `False`.

When `False`, non-leading `SystemPromptPart`s are wrapped as `UserPromptPart`s with `<system>...</system>` content in `Model.prepare_messages`. Leading ones still hoist to the provider's top-level system parameter.

APIs that only accept an inline system prompt in certain positions (e.g. Anthropic requires it to follow a user turn) still set this to `True`; it's on their model adapters to make the positions the API rejects legal. Preserving the part's authority is worth more than preserving the exact position it was authored at -- an instruction only governs the generation that follows it, and that's the same generation either way -- so prefer adjusting placement over falling back to the `<system>...</system>` rendering, which the model reads as user-authored. Anthropic slides the entry past intervening user turns and gives it a minimal user turn to follow when nothing legal precedes it.

`Provider.model_profile` is resolved from the model name alone, so when support also turns on something it can't see -- which SDK client the provider was built with, say -- the adapter narrows this in its own `Model.profile` override, as Anthropic does for Microsoft Foundry. Narrowing the flag rather than special-casing the adapter's own rendering keeps `Model.prepare_messages` the only place that knows the `<system>...</system>` fallback.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### default\_structured\_output\_mode

The default structured output mode to use for the model. Default: `'tool'`.

**Type:** `StructuredOutputMode`

##### prompted\_output\_template

The instructions template to use for prompted structured output. The `{schema}` placeholder will be replaced with the JSON schema for the output. Default: `DEFAULT_PROMPTED_OUTPUT_TEMPLATE`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### native\_output\_requires\_schema\_in\_instructions

Whether to add prompted output template in native structured output mode. Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### json\_schema\_transformer

The transformer to use to make JSON schemas for tools and structured output compatible with the model. Default: `None`.

**Type:** [`type`](https://docs.python.org/3/glossary.html#term-type)\[[`JsonSchemaTransformer`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.JsonSchemaTransformer)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### supports\_thinking

Whether the model supports thinking/reasoning configuration. Default: `False`.

When False, the unified `thinking` setting in `ModelSettings` is silently ignored.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### thinking\_always\_enabled

Whether the model always uses thinking/reasoning (e.g., OpenAI o-series, DeepSeek R1). Default: `False`.

When True, `thinking=False` is silently ignored since the model cannot disable thinking. Implies `supports_thinking=True`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### thinking\_tags

The tags used to indicate thinking parts in the model's output. Default: [`DEFAULT_THINKING_TAGS`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.DEFAULT_THINKING_TAGS).

**Type:** [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### ignore\_streamed\_leading\_whitespace

Whether to ignore leading whitespace when streaming a response. Default: `False`.

This is a workaround for models that emit \`<think> </think>

`or an empty text part ahead of tool calls (e.g. Ollama + Qwen3), which we don't want to end up treating as a final result when using`run\_stream`with`str`a valid`output\_type\`.

This is currently only used by `OpenAIChatModel`, `HuggingFaceModel`, `GroqModel`, and `BedrockConverseModel`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supported\_native\_tools

The set of native tool types that this model/profile supports. Default: `SUPPORTED_NATIVE_TOOLS` (all).

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

##### context\_window

The maximum number of tokens the model can handle in a single request, input and output combined. Default: `None` (unknown).

When no profile layer sets this, `Model.profile` fills it in from [genai-prices](https://github.com/pydantic/genai-prices) data if the model is known there. Set it explicitly for custom or local models, e.g. `profile={'context_window': 128_000}`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### tool\_deferral\_mode

When the provider permits a `tools` entry whose schema is withheld. Default: `None`.

`'standalone'` permits the deferral flag on its own. `'with_tool_search'` permits it only when a tool-search tool is present in the same request. `None` means hidden tools can only be withheld from the wire. Unsupported deferral is handled on a best-effort basis by withholding the tool.

**Type:** `ToolDeferralMode` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### tool\_addition\_mode

How the model natively expresses tools added mid-conversation. Default: `None`.

`'by_reference'` reveals a tool already declared in the request's tool definitions (Anthropic `tool_addition` blocks referencing a `defer_loading` entry); `'with_definitions'` carries the full newly available definitions in the reveal (OpenAI Responses `additional_tools` items). `None` means no native channel: `Model.prepare_messages` projects the change into messages. Additions only -- tool removal (#6985) is not modeled yet and will get its own field.

**Type:** `ToolAdditionMode` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### tool\_additions

Deprecated: use `tool_addition_mode` instead.

Translated (with a deprecation warning) whenever profiles are merged; an explicit `tool_addition_mode` in the same profile wins.

**Type:** `ToolAdditionMode` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### deferred\_tools\_require\_tool\_search

Deprecated: use `tool_deferral_mode` instead.

`True` translates to `tool_deferral_mode='with_tool_search'` (with a deprecation warning) whenever profiles are merged. `False` carried no signal on its own -- deferral capability came from native tool-search support -- so it is dropped; an explicit `tool_deferral_mode` in the same profile wins.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### JsonSchemaTransformer

**Bases:** `ABC`

Walks a JSON schema, applying transformations to it at each level.

The transformer is called during a model's prepare\_request() step to build the JSON schema before it is sent to the model provider.

Note: We may eventually want to rework tools to build the JSON schema from the type directly, using a subclass of pydantic.json\_schema.GenerateJsonSchema, rather than making use of this machinery.

#### Attributes

##### strict

The `strict` parameter forces the conversion of the original JSON schema (`self.schema`) of a `ToolDefinition` or `OutputObjectDefinition` to a format supported by the model provider.

The "strict mode" offered by model providers ensures that the model's output adheres closely to the defined schema. However, not all model providers offer it, and their support for various schema features may differ. For example, a model provider's required schema may not support certain validation constraints like `minLength` or `pattern`.

**Default:** `strict`

##### is\_strict\_compatible

Whether the schema is compatible with strict mode.

This value is used to set `ToolDefinition.strict` or `OutputObjectDefinition.strict` when their values are `None`.

**Default:** `True`

#### Methods

##### transform

`@abstractmethod`

```python
def transform(schema: JsonSchema) -> JsonSchema
```

Make changes to the schema.

###### Returns

`JsonSchema`

### InlineDefsJsonSchemaTransformer

**Bases:** [`JsonSchemaTransformer`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.JsonSchemaTransformer)

Transforms the JSON Schema to inline $defs.

### merge\_profile

```python
def merge_profile(
    base: ModelProfile | None,
    *overrides: ModelProfile | None,
) -> ModelProfile
```

Merge profiles via dict-spread. Later arguments override earlier ones; `None` is treated as empty.

This is the canonical way to layer profiles in providers and tests; replaces the old `ModelProfile.update()` method. Deprecated key spellings are translated per input before spreading, so a legacy key in an override still overrides the base.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

### ModelProfileSpec

Acceptable shapes for the `profile=` argument on a `Model`.

-   A `ModelProfile` dict -- a partial profile, merged on top of the provider's resolved default.
-   A `Callable[[ModelProfile], ModelProfile]` -- receives the provider's resolved default (with `DEFAULT_PROFILE` already merged in) and returns the final profile (full control: replace, derive, ignore the default).

Provider classes still expose `Provider.model_profile(model_name)` (`Callable[[str], ModelProfile | None]`) -- that's a separate concept used internally by `Model.profile` to resolve the provider's default for a given model name.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `ModelProfile | Callable[['ModelProfile'], 'ModelProfile']`

### DEFAULT\_PROFILE

Fully populated default `ModelProfile`. Used as the base layer when resolving a model's effective profile.

**Type:** [`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) **Default:** `{'supports_tools': True, 'supports_tool_return_schema': False, 'supports_json_schema_output': False, 'supports_json_object_output': False, 'supports_image_output': False, 'supports_audio_input': False, 'default_structured_output_mode': 'tool', 'prompted_output_template': DEFAULT_PROMPTED_OUTPUT_TEMPLATE, 'native_output_requires_schema_in_instructions': False, 'json_schema_transformer': None, 'supports_thinking': False, 'thinking_always_enabled': False, 'thinking_tags': DEFAULT_THINKING_TAGS, 'ignore_streamed_leading_whitespace': False, 'supported_native_tools': SUPPORTED_NATIVE_TOOLS, 'context_window': None, 'tool_deferral_mode': None, 'tool_addition_mode': None}`

### DEFAULT\_PROMPTED\_OUTPUT\_TEMPLATE

Default instructions template for prompted structured output. The `{schema}` placeholder is replaced with the JSON schema for the output.

**Default:** `dedent("\n Always respond with a JSON object that's compatible with this schema:\n\n {schema}\n\n Don't include any text or Markdown fencing before or after.\n ")`

### DEFAULT\_THINKING\_TAGS

Default `(start_tag, end_tag)` pair for parsing thinking content out of text responses.

**Type:** [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `('<think>', '</think>')`

### OpenAIModelProfile

**Bases:** [`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

Profile for models used with `OpenAIChatModel`.

ALL FIELDS MUST BE `openai_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

#### Attributes

##### openai\_chat\_thinking\_field

Non-standard field name used by some providers for model thinking content in Chat Completions API responses. Default: `None`.

Plenty of providers use custom field names for thinking content. Ollama and newer versions of vLLM use `reasoning`, while DeepSeek, older vLLM and some others use `reasoning_content`.

Notice that the thinking field configured here is currently limited to `str` type content.

If `openai_chat_send_back_thinking_parts` is set to `'field'`, this field must be set to a non-None value.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### openai\_chat\_send\_back\_thinking\_parts

Whether the model includes thinking content in requests. Default: `'auto'`.

This can be:

-   `'auto'` (default): Automatically detects how to send thinking content. If thinking was received in a custom field (tracked via `ThinkingPart.id` and `ThinkingPart.provider_name`), it's sent back in that same field. Otherwise, it's sent using tags. Only the `reasoning` and `reasoning_content` fields are checked by default when receiving responses. If your provider uses a different field name, you must explicitly set `openai_chat_thinking_field` to that field name.
-   `'tags'`: The thinking content is included in the main `content` field, enclosed within thinking tags as specified in `thinking_tags` profile option.
-   `'field'`: The thinking content is included in a separate field specified by `openai_chat_thinking_field`.
-   `False`: No thinking content is sent in the request.

Defaults to `'auto'` to ensure thinking is sent back in the format expected by the model/provider.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['auto', 'tags', 'field', [`False`](https://docs.python.org/3/builtins/constants.html#False)\]

##### openai\_supports\_strict\_tool\_definition

This can be set by a provider or user if the OpenAI-"compatible" API doesn't support strict tool definitions. Default: `True`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_unsupported\_model\_settings

A list of model settings that are not supported by this model. Default: `()`.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### openai\_supports\_tool\_choice\_required

Whether the provider accepts the value `tool_choice='required'` in the request payload. Default: `True`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_supports\_forced\_tool\_choice\_with\_thinking

Whether the provider accepts a forced `tool_choice` while thinking is enabled for this request. Default: `True`.

Unlike `openai_supports_tool_choice_required`, which is a fixed property of the model, this is evaluated per request against the effective thinking state. DeepSeek's V4 models accept `tool_choice='required'` and named-function forcing only while thinking is off, rejecting them otherwise with `Thinking mode does not support this tool_choice`. When this is `False` and thinking is active, a resolved `required` tool choice falls back to `auto`, and an explicit `tool_choice='required'` (or an explicit list of tools) raises a `UserError`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_system\_prompt\_role

The role to use for the system prompt message. If not provided, defaults to `'system'`.

**Type:** `OpenAISystemPromptRole` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### openai\_chat\_supports\_multiple\_system\_messages

Whether the Chat Completions API accepts more than one system-role message at the start of the conversation. Default: `True`.

OpenAI itself and most compatible providers accept multiple system messages, so this defaults to `True`. Set to `False` for strict OpenAI-compatible backends (e.g. some LiteLLM/vLLM deployments) that require exactly one initial system message; consecutive system messages at the start will be merged into one (joined with two newlines) before being sent.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_chat\_streaming\_requires\_finish\_reason

Whether a streamed Chat Completions response must include a non-null `finish_reason`. Default: `False`.

When enabled, reaching clean EOF before any chunk supplies a `finish_reason` raises [`ModelAPIError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelAPIError). This defaults to `False` because OpenAI-compatible APIs do not consistently guarantee the field.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_chat\_supports\_web\_search

Whether the model supports web search in Chat Completions API. Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_chat\_audio\_input\_encoding

The encoding to use for audio input in Chat Completions requests. Default: `'base64'`.

-   `'base64'`: Raw base64 encoded string. (Default, used by OpenAI)
-   `'uri'`: Data URI (e.g. `data:audio/wav;base64,...`).

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['base64', 'uri'\]

##### openai\_chat\_supports\_file\_urls

Whether the Chat API supports file URLs directly in the `file_data` field. Default: `False`.

OpenAI's native Chat API only supports base64-encoded data, but some providers like OpenRouter support passing URLs directly.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_supports\_encrypted\_reasoning\_content

Whether the model supports including encrypted reasoning content in the response. Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_supports\_reasoning

Whether the model supports reasoning (o-series, GPT-5+). Default: `False`.

When True, sampling parameters may need to be dropped depending on reasoning\_effort setting.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_reasoning\_enabled\_by\_default

Whether the model reasons by default when `reasoning_effort` is omitted. Default: `False`.

True for models whose default effort is active (e.g. 'medium'), such as the o-series, the original GPT-5, and GPT-5.5+, and False for the GPT-5.1..5.4 mainline models which default to `reasoning_effort='none'`. This decides whether sampling parameters must be dropped when no effort is set, and is independent of whether reasoning can be turned off (`openai_supports_reasoning_effort_none`).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_supports\_reasoning\_effort\_none

Whether the model accepts `reasoning_effort='none'` and allows sampling parameters (temperature, top\_p, etc.) while reasoning is off. Default: `False`.

The GPT-5.1+ mainline models support turning reasoning off via `effort='none'`, and sampling params are accepted in that mode. When reasoning is enabled (low/medium/high/xhigh), sampling params are not supported. Whether the model reasons by default is tracked separately by `openai_reasoning_enabled_by_default`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_supports\_minimal\_reasoning\_effort

Whether the model accepts `reasoning_effort='minimal'`. Default: `True`.

Disabled for GPT-5.6 models, whose documented reasoning efforts exclude `minimal`. When disabled, unified `thinking='minimal'` falls back to `reasoning_effort='low'`. See [https://developers.openai.com/api/docs/guides/latest-model](https://developers.openai.com/api/docs/guides/latest-model). Explicit `openai_reasoning_effort='minimal'` settings are still passed through unchanged.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_responses\_supports\_reasoning\_mode

Whether the Responses API supports `reasoning.mode` (`'standard' | 'pro'`) for this model. Default: `False`.

Currently only supported by the GPT-5.6 family.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_responses\_supports\_reasoning\_context

Whether the Responses API accepts `reasoning.context='all_turns'` for this model. Default: `False`.

`auto` and `current_turn` are accepted by every reasoning model, so they are gated on `openai_supports_reasoning` instead; only `all_turns` requires this flag.

Currently supported by the GPT-5.4, GPT-5.5, and GPT-5.6 families.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_responses\_requires\_function\_call\_status\_none

Whether the Responses API requires the `status` field on function tool calls to be `None`. Default: `False`.

This is required by vLLM Responses API versions before [https://github.com/vllm-project/vllm/pull/26706](https://github.com/vllm-project/vllm/pull/26706). See [https://github.com/pydantic/pydantic-ai/issues/3245](https://github.com/pydantic/pydantic-ai/issues/3245) for more details.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_responses\_supports\_json\_schema\_output

Whether the Responses API accepts `text.format` of type `json_schema` for this model. Default: `False`.

Only needed when the Responses API is more capable than Chat Completions for the same model, as with DeepSeek, whose Chat Completions endpoint rejects `response_format` of type `json_schema` with `This response_format type is unavailable now` while its Responses endpoint honors the schema. When set, `OpenAIResponsesModel` enables `supports_json_schema_output` on its resolved profile, so [`NativeOutput`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.NativeOutput) becomes available on the Responses API alone.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_responses\_tool\_call\_ids\_are\_response\_scoped

Whether Responses API tool call IDs are only unique within one response. Default: `False`.

When enabled, response IDs are incorporated into tool call IDs as responses are ingested so normalized message history keeps the history-wide uniqueness required by Pydantic AI. The qualified `response_id:tool_call_id` form is restored to the original provider tool call ID when history is replayed.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_responses\_supports\_interleaved\_function\_calls

Whether the Responses API accepts function calls interleaved with other assistant items in one assistant turn. Default: `True`.

[DeepSeek's Responses endpoint](https://api-docs.deepseek.com/guides/responses_api) merges each function call into the assistant message next to it, so an assistant item between two calls splits them into separate messages that each carry an unanswered call ([#7430](https://github.com/pydantic/pydantic-ai/issues/7430)). When this is `False`, such a turn has its calls moved to the end before the request goes out; the message history you hold is unchanged.

Reordering is best-effort: a turn carrying a native or compaction item, or a call still waiting on its result, is sent in its original order.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_supports\_phase

Whether the Responses API supports the `phase` field on assistant messages. Default: `False`.

`phase` labels an assistant message as intermediate `commentary` or the `final_answer`. When the model supports it, OpenAI recommends preserving and sending it back unchanged on every assistant message in follow-up requests; dropping it can cause preambles to be interpreted as final answers and degrade behavior in long-running or tool-heavy flows.

Supported by `gpt-5.3-codex`, `gpt-5.4` and later mainline models. The official OpenAI Responses API silently ignores the field on older models, but defaults to `False` so we don't risk sending an unrecognized field to OpenAI-compatible APIs (vLLM, Bifrost, ...) that haven't been verified to accept it.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_chat\_supports\_document\_input

Whether the Chat Completions API supports document content parts (`type='file'`). Default: `True`.

Some OpenAI-compatible providers (e.g. Azure) do not support document input via the Chat Completions API.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_chat\_supports\_max\_completion\_tokens

Whether the Chat Completions API accepts the `max_completion_tokens` field for the `max_tokens` setting. Default: `True`.

OpenAI itself (including the o-series reasoning models) uses `max_completion_tokens`, the field that caps visible output plus reasoning tokens, so this defaults to `True`. Many OpenAI-compatible providers (e.g. OpenRouter) only accept the older `max_tokens` field; set this to `False` for those so the `max_tokens` setting is sent as `max_tokens` instead.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_supports\_prompt\_cache\_breakpoints

Whether the model supports OpenAI explicit prompt cache breakpoints. Default: False.

When enabled, [`CachePoint`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CachePoint) markers are translated into `prompt_cache_breakpoint` fields on the preceding content block, on both the Chat Completions and Responses APIs. When disabled, `CachePoint` markers are filtered out.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_responses\_requires\_streaming

Whether the Responses endpoint serves streaming responses only. Default: `False`.

When `True`, nominally non-streaming requests are sent with `stream=True` and aggregated from the terminal `response.completed` event, so callers see an ordinary non-streaming [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse). Set for subscription-auth endpoints (e.g. OpenAI Codex) that reject `stream=False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_responses\_requires\_store\_false

Whether the Responses endpoint requires `store=false` on every request. Default: `False`.

When `True`, `store=false` is sent even when no `openai_store` setting is given (the field cannot be omitted), and an explicit `openai_store=True` setting is silently overridden, consistent with how other backend-rejected settings are dropped.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### openai\_supports\_input\_token\_counting

Whether the provider exposes server-side input-token counting (`responses/input_tokens`). Default: `True`.

When `False`, `count_tokens()` raises a `UserError` instead of calling a missing endpoint.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### OpenAIJsonSchemaTransformer

**Bases:** [`JsonSchemaTransformer`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.JsonSchemaTransformer)

Recursively handle the schema to make it compatible with OpenAI strict mode.

See [https://platform.openai.com/docs/guides/function-calling?api-mode=responses#strict-mode](https://platform.openai.com/docs/guides/function-calling?api-mode=responses#strict-mode) for more details, but this basically just requires:

-   `additionalProperties` must be set to false for each object in the parameters
-   all fields in properties must be marked as required

### validate\_openai\_profile

```python
def validate_openai_profile(profile: ModelProfile) -> None
```

Validate an OpenAI-compatible profile after resolution. Called from `OpenAIChatModel.__init__`.

#### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### openai\_model\_profile

```python
def openai_model_profile(model_name: str) -> ModelProfile
```

Get the model profile for an OpenAI model.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

### openai\_realtime\_model\_profile

```python
def openai_realtime_model_profile(model_name: str) -> RealtimeModelProfile
```

Get the realtime model profile for an OpenAI realtime model.

#### Returns

`RealtimeModelProfile`

### OPENAI\_REASONING\_EFFORT\_MAP

Maps unified thinking values to OpenAI reasoning\_effort strings.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[`ThinkingLevel`, [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `{True: 'medium', False: 'none', 'minimal': 'minimal', 'low': 'low', 'medium': 'medium', 'high': 'high', 'xhigh': 'xhigh'}`

### SAMPLING\_PARAMS

Sampling parameter names that are incompatible with reasoning.

These parameters are not supported when reasoning is enabled (reasoning\_effort != 'none'). See [https://platform.openai.com/docs/guides/reasoning](https://platform.openai.com/docs/guides/reasoning) for details.

**Default:** `('temperature', 'top_p', 'presence_penalty', 'frequency_penalty', 'logit_bias', 'openai_logprobs', 'openai_top_logprobs')`

### openai\_codex\_model\_profile

```python
def openai_codex_model_profile(model_name: str) -> ModelProfile
```

Get the model profile for OpenAI Codex subscription-auth models.

The Codex backend speaks the Responses API with a narrower dialect than the standard OpenAI endpoint: it serves streaming responses only, requires `store=false`, rejects sampling/tuning request fields (verified live on PR [#6433](https://github.com/pydantic/pydantic-ai/pull/6433)), and does not expose server-side input-token counting.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

### AnthropicModelProfile

**Bases:** [`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

Profile for models used with `AnthropicModel`.

ALL FIELDS MUST BE `anthropic_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

#### Attributes

##### anthropic\_supports\_fast\_speed

Whether the model supports fast inference speed (`anthropic_speed='fast'`). Default: `False`.

Currently Claude Opus 4.6, 4.7, 4.8, and 5 support fast mode. See the Anthropic docs for the latest list.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### anthropic\_supports\_adaptive\_thinking

Whether the model supports adaptive thinking (Sonnet 4.6+, Opus 4.6+). Default: `False`.

When True, unified `thinking` translates to `{'type': 'adaptive'}`. When False, it translates to `{'type': 'enabled', 'budget_tokens': N}`.

Because adaptive thinking -- unlike extended thinking -- is compatible with a forced `tool_choice`, this also decides whether unified `thinking` blocks tool forcing and switches Tool Output to Native or Prompted Output.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### anthropic\_supports\_effort

Whether the model supports the `effort` parameter in `output_config` (Opus 4.5+, Sonnet 4.6+). Default: `False`.

When True and the unified thinking level is a string (e.g. 'high'), it is also mapped to `output_config.effort`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### anthropic\_supports\_dynamic\_filtering

Whether the model supports Anthropic-managed dynamic filtering for web search/fetch. Default: `False`.

When enabled, Pydantic AI selects the `web_search_20260209` / `web_fetch_20260209` tool versions, which let Claude filter web results via code execution before they enter context.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### anthropic\_supports\_xhigh\_effort

Whether the model supports the `xhigh` effort value in `output_config`. Default: `False`.

Claude Opus 4.7, 4.8, and 5 accept `xhigh`; older Anthropic models should use `max` instead.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### anthropic\_disallows\_budget\_thinking

Whether the model rejects budget-based thinking settings. Default: `False`.

Claude Opus 4.7, 4.8, and 5 require adaptive thinking and return a 400 for `{'type': 'enabled', 'budget_tokens': ...}`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### anthropic\_disallows\_sampling\_settings

Whether the model rejects sampling settings like `temperature` and `top_p`. Default: `False`.

Claude Opus 4.7, 4.8, and 5 require these settings to be omitted from request payloads.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### anthropic\_disallows\_top\_effort\_when\_thinking\_disabled

Whether the model rejects `xhigh`/`max` effort while thinking is explicitly disabled. Default: `False`.

Claude Opus 5 caps effort at `high` when `anthropic_thinking={'type': 'disabled'}` and returns a 400 for `xhigh` or `max`; Claude Opus 4.8 accepts the same combination.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### anthropic\_default\_code\_execution\_tool\_version

The Anthropic code execution tool version used when `anthropic_code_execution_tool_version='auto'`. Default: `'20250825'`.

**Type:** `AnthropicCodeExecutionToolVersion`

##### anthropic\_supported\_code\_execution\_tool\_versions

The Anthropic code execution tool versions supported by the model. Default: `('20250825',)`.

**Type:** [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[`AnthropicCodeExecutionToolVersion`, ...\]

##### anthropic\_supports\_task\_budgets

Whether the model supports `output_config.task_budget`. Default: `False`.

Anthropic currently documents task budgets as a Claude Opus 4.7 / 4.8 / 5 beta feature.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### anthropic\_supports\_forced\_tool\_choice

Whether the model accepts a forced `tool_choice` (`{'type': 'any'}` or `{'type': 'tool'}`).

Most Anthropic models only reject forcing alongside extended thinking; Claude Fable 5.1 and Claude Mythos 5.1 reject it unconditionally with a 400. When False, a resolved `required` tool choice falls back to `auto` (filtering tools to the requested set), and an explicit `tool_choice='required'` (or an explicit list of tools) raises a `UserError`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### anthropic\_binds\_thinking\_blocks

Whether the model binds each thinking block to the conversation prefix that produced it. Default: `False`.

Claude Fable 5.1 rejects a replayed thinking block once the `system` prompt text changes or a non-deferred tool joins the `tools` array -- both of which Pydantic AI causes by design, through dynamic `@agent.instructions` and conditional toolsets. When True, Pydantic AI preserves the account's default behavior on the first request; if Anthropic rejects a stale block, it retries once with `thinking.block_binding.prefix_mismatch_behavior='drop_block'` and warns after the retry succeeds.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### resolve\_anthropic\_effort

```python
def resolve_anthropic_effort(
    level: ThinkingEffort,
    *,
    supports_xhigh: bool,
) -> AnthropicEffort
```

Resolve a unified thinking effort level to the Anthropic `output_config.effort` value.

Shared between the direct Anthropic path and any provider that translates to the Anthropic `output_config` wire shape (e.g. Bedrock Converse for Anthropic models). Keeps `ANTHROPIC_THINKING_EFFORT_MAP` as the single source of truth for the base mapping, while letting the `xhigh` passthrough decision live in one place.

#### Returns

`AnthropicEffort`

### anthropic\_model\_profile

```python
def anthropic_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for an Anthropic model.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### ANTHROPIC\_SAMPLING\_PARAMS

The unified sampling settings gated by `anthropic_disallows_sampling_settings`.

Models whose profile sets that flag reject these settings outright with a 400, so every provider serving them has to drop and warn rather than forward. It lives here rather than beside either model because `models/bedrock.py` cannot import from `models/anthropic.py` without pulling the `anthropic` SDK into the `bedrock` extra.

**Default:** `('temperature', 'top_p', 'top_k')`

### AnthropicCodeExecutionToolVersion

Concrete Anthropic code execution tool version to send for `CodeExecutionTool`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['20250825', '20260120']`

### ANTHROPIC\_THINKING\_BUDGET\_MAP

Maps unified thinking values to Anthropic budget\_tokens for non-adaptive models.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[`ThinkingLevel`, [`int`](https://docs.python.org/3/builtins/functions.html#int)\] **Default:** `{True: 10000, 'minimal': 1024, 'low': 2048, 'medium': 10000, 'high': 16384, 'xhigh': 32768}`

### AnthropicEffort

Effort values Anthropic accepts at `output_config.effort`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['low', 'medium', 'high', 'xhigh', 'max']`

### ANTHROPIC\_THINKING\_EFFORT\_MAP

Maps unified thinking effort levels to Anthropic `output_config.effort`.

`xhigh` maps to `'max'` by default; callers that target a model with `anthropic_supports_xhigh_effort` should pass `supports_xhigh=True` to [`resolve_anthropic_effort`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.anthropic.resolve_anthropic_effort) to preserve `xhigh` instead of downshifting.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[`ThinkingEffort`, `AnthropicEffort`\] **Default:** `{'minimal': 'low', 'low': 'low', 'medium': 'medium', 'high': 'high', 'xhigh': 'max'}`

### GoogleModelProfile

**Bases:** [`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

Profile for models used with `GoogleModel`.

ALL FIELDS MUST BE `google_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

#### Attributes

##### google\_supports\_tool\_combination

Whether the model supports combining function declarations with native tools and response\_schema. Default: `False`.

Gemini 3+ supports all tool combinations:

-   function\_declarations + native\_tools
-   output\_tools (function declarations) + native\_tools
-   response\_schema (NativeOutput) + function\_declarations See [https://ai.google.dev/gemini-api/docs/tool-combination](https://ai.google.dev/gemini-api/docs/tool-combination)

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### google\_supports\_server\_side\_tool\_invocations

Whether the model accepts the `include_server_side_tool_invocations` tool-config field. Default: `False`.

When enabled, Gemini emits explicit `tool_call`/`tool_response` parts for server-side native tools (Google Search, URL Context, File Search) that we round-trip through [`NativeToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolCallPart) / [`NativeToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolReturnPart). Pre-Gemini-3 models reject the field with `'Tool call context circulation is not enabled'`.

This is a Gemini Developer API (ML Dev) only parameter: the google-genai SDK's Vertex converter raises `ValueError` when the field is set, so `GoogleModel` skips it for Google Cloud (Vertex) even on Gemini 3+ models.

Distinct from [`google_supports_tool_combination`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.google.GoogleModelProfile.google_supports_tool_combination) even though both currently flip on for Gemini 3+ -- the former gates the SDK request field, the latter gates which combinations of native / function / output tools are allowed in the same request.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### google\_supported\_mime\_types\_in\_tool\_returns

MIME types supported in native FunctionResponseDict.parts. Default: `()`. See [https://ai.google.dev/gemini-api/docs/function-calling#multimodal-function-responses](https://ai.google.dev/gemini-api/docs/function-calling#multimodal-function-responses)

**Type:** [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), ...\]

##### google\_supports\_thinking\_level

Whether the model uses `thinking_level` (enum: LOW/MEDIUM/HIGH) instead of `thinking_budget` (int). Default: `False`.

Gemini 3+ models use `thinking_level`; Gemini 2.5 uses `thinking_budget`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### google\_supports\_minimal\_thinking\_level

Whether the model accepts `thinking_level='MINIMAL'`. Default: `True`.

Derived from [`google_thinking_levels`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.google.GoogleModelProfile.google_thinking_levels) when that is set. Sparse profiles without the level set fall back to this flag: when disabled, unified `thinking='minimal'` and `thinking=False` resolve to `thinking_level='LOW'`. See [https://ai.google.dev/gemini-api/docs/thinking](https://ai.google.dev/gemini-api/docs/thinking).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### google\_thinking\_levels

Thinking levels the model supports, from Google's per-model thinking table. Default: unset.

Unset means the full [`GOOGLE_THINKING_LEVELS`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.google.GOOGLE_THINKING_LEVELS) scale is assumed. Unified thinking efforts snap to the nearest supported level. See [https://ai.google.dev/gemini-api/docs/thinking](https://ai.google.dev/gemini-api/docs/thinking).

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[`GoogleThinkingLevel`\]

##### google\_supports\_strict\_tool\_definition

Whether the model supports Gemini's `VALIDATED` function-calling mode. Default: `False`.

`VALIDATED` is Gemini's equivalent of the cross-provider `strict` tool flag (like OpenAI/Anthropic strict tool calling): it behaves like `AUTO` but the API enforces that the model adheres to the declared function schema. Issue reports also observe that it mitigates the function-name hallucination some Gemini models exhibit (an observed effect, not a documented guarantee). When the flag is set, `GoogleModel` upgrades `AUTO` to `VALIDATED` by default (every schema is VALIDATED-compatible -- no rewrites), and a caller opts out per tool with `ToolDefinition.strict=False`. Because Gemini's mode is request-wide, any function or output tool with `strict=False` keeps the whole request on `AUTO`.

See [https://ai.google.dev/gemini-api/docs/function-calling#function\_calling\_config](https://ai.google.dev/gemini-api/docs/function-calling#function_calling_config).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### GoogleJsonSchemaTransformer

**Bases:** [`JsonSchemaTransformer`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.JsonSchemaTransformer)

Transforms the JSON Schema from Pydantic to be suitable for Gemini.

Gemini supports [a subset of OpenAPI v3.0.3](https://ai.google.dev/gemini-api/docs/function-calling#function_declarations).

### GoogleOpenAPISchemaTransformer

**Bases:** `GoogleJsonSchemaTransformer`

Transforms the JSON Schema from Pydantic into the OpenAPI v3.0.3 subset Gemini's `Schema` accepts.

A function declaration carries its parameters as _either_ `parametersJsonSchema` (full JSON Schema, which [`GoogleModel`](https://pydantic.dev/docs/ai/api/models/google/#pydantic_ai.models.google.GoogleModel) sends) _or_ `parameters` (an [OpenAPI v3.0.3 subset](https://ai.google.dev/gemini-api/docs/function-calling#function_declarations)) -- the two are mutually exclusive. The Live API only implements `parameters`, so [`GoogleRealtimeModel`](https://pydantic.dev/docs/ai/api/realtime/google/#pydantic_ai.realtime.google.GoogleRealtimeModel) needs this narrower form, where a union is `anyOf`, an enum is a list of strings, and there are no `$ref`s to resolve.

### google\_model\_profile

```python
def google_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Google model.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### google\_realtime\_model\_profile

```python
def google_realtime_model_profile(model_name: str) -> RealtimeModelProfile
```

Get the realtime model profile for a Gemini Live model.

#### Returns

`RealtimeModelProfile`

### GoogleThinkingLevel

Native Gemini `thinking_level` values.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['MINIMAL', 'LOW', 'MEDIUM', 'HIGH']`

### GOOGLE\_THINKING\_LEVEL\_SCALE

The full thinking-level scale, cheapest first. The resolver's order map derives from this.

**Type:** [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[`GoogleThinkingLevel`, ...\] **Default:** `('MINIMAL', 'LOW', 'MEDIUM', 'HIGH')`

### GOOGLE\_THINKING\_LEVELS

The full thinking-level scale as a set.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[`GoogleThinkingLevel`\] **Default:** `frozenset(GOOGLE_THINKING_LEVEL_SCALE)`

### meta\_model\_profile

```python
def meta_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Meta model.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### amazon\_model\_profile

```python
def amazon_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for an Amazon model.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### deepseek\_model\_profile

```python
def deepseek_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a DeepSeek model.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### GrokModelProfile

**Bases:** [`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

Profile for Grok models (used with XaiProvider and various OpenAI-compatible providers).

ALL FIELDS MUST BE `grok_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

#### Attributes

##### grok\_supports\_builtin\_tools

Whether the model supports builtin tools (web\_search, x\_search, code\_execution, mcp). Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### grok\_supports\_tool\_choice\_required

Whether the provider accepts the value `tool_choice='required'` in the request payload. Default: `True`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### grok\_reasoning\_efforts

Native `reasoning_effort` values supported by the Grok model. Default: empty (`frozenset()`).

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[`GrokReasoningEffort`\]

### grok\_model\_profile

```python
def grok_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Grok model.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### grok\_realtime\_model\_profile

```python
def grok_realtime_model_profile(model_name: str) -> RealtimeModelProfile
```

Get the realtime model profile for an xAI Grok Voice model.

#### Returns

`RealtimeModelProfile`

### GrokReasoningEffort

Native xAI `reasoning_effort` values.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['none', 'low', 'medium', 'high']`

### mistral\_model\_profile

```python
def mistral_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Mistral model.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### qwen\_model\_profile

```python
def qwen_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Qwen model.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### GroqModelProfile

**Bases:** [`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

Profile for models used with GroqModel.

ALL FIELDS MUST BE `groq_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

#### Attributes

##### groq\_always\_has\_web\_search\_builtin\_tool

Whether the model always has the web search built-in tool available. Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### groq\_supports\_reasoning\_disable

Whether `thinking=False` truly disables reasoning via `reasoning_effort='none'`. Default: `False`.

Only the qwen3 family supports this; other Groq reasoning models can at most suppress reasoning _output_ via `reasoning_format='hidden'` while still reasoning internally.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### groq\_supports\_graded\_reasoning\_effort

Whether the model accepts graded `reasoning_effort` values (`low`/`medium`/`high`). Default: `False`.

Only the gpt-oss family supports this; unified `thinking` levels map to those values via [`GROQ_GPT_OSS_REASONING_EFFORT_MAP`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.groq.GROQ_GPT_OSS_REASONING_EFFORT_MAP). The qwen3 family instead only accepts `none`/`default` (see `groq_supports_reasoning_disable`).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### groq\_model\_profile

```python
def groq_model_profile(model_name: str) -> ModelProfile
```

Get the model profile for a Groq model.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

### GROQ\_GPT\_OSS\_REASONING\_EFFORT\_MAP

Maps unified thinking effort levels to the graded `reasoning_effort` values the gpt-oss family accepts.

gpt-oss only accepts `low`/`medium`/`high` (not `none`/`default`), so `minimal` folds into `low` and `xhigh` into `high`. `thinking=True` (bare enable) maps to `medium` in `GroqModel`, mirroring the neutral default other providers use. See [the Groq docs](https://console.groq.com/docs/reasoning#reasoning-effort).

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[`ThinkingEffort`, [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['low', 'medium', 'high'\]\] **Default:** `{'minimal': 'low', 'low': 'low', 'medium': 'medium', 'high': 'high', 'xhigh': 'high'}`

### ZaiModelProfile

**Bases:** [`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

Profile for Z.AI (Zhipu AI) GLM models.

#### Attributes

##### zai\_supports\_reasoning\_effort

Whether the model accepts a per-request `reasoning_effort` level (GLM-5.2 and GLM-5.3).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### zai\_reasoning\_effort\_mapping

Substitutions applied to the unified thinking effort level before it is sent as `reasoning_effort`.

Levels not in the mapping are forwarded unchanged. GLM-5.2 accepts all unified levels, so it needs no mapping; GLM-5.3 only accepts `low`/`high`/`max` (per the Z.AI docs and the error message returned when disabling thinking on it), so its other unified levels are mapped.

**Type:** [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

### zai\_model\_profile

```python
def zai_model_profile(model_name: str) -> ModelProfile | None
```

The model profile for ZAI (Zhipu AI) GLM models, matched by Z.AI's native `glm-*` ids.

Marks thinking-capable models (`glm-5`, `glm-4.7`, `glm-4.6`, `glm-4.5`) via `supports_thinking=True`. This includes the `glm-4.6v` and `glm-4.5v` vision models, which also support thinking mode per the Z.AI docs. GLM-5.2 and GLM-5.3 additionally accept a per-request reasoning effort level, flagged via `zai_supports_reasoning_effort=True`. GLM-5.3 always reasons and cannot disable thinking, flagged via `thinking_always_enabled=True`.

The provider-specific request/response shape (e.g. the `reasoning_content` field used by Z.AI's API) is configured in `ZaiProvider.model_profile()` rather than here. Providers that serve GLM models under a different id scheme (e.g. Cerebras's `zai-glm-*`, which doesn't match the `glm-*` prefixes above) configure thinking support in their own `model_profile()`.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

---
