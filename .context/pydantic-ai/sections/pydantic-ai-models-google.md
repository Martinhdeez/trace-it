# [pydantic_ai.models.google](https://pydantic.dev/docs/ai/api/models/google/)

# pydantic\_ai.models.google

Interface that uses the [`google-genai`](https://pypi.org/project/google-genai/) package under the hood to access Google's Gemini models via both the Gemini API and Google Cloud (formerly known as Vertex AI).

## Setup

For details on how to set up authentication with this model, see [model configuration for Google](https://pydantic.dev/docs/ai/models/google/).

### GoogleModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings used for a Gemini model request.

#### Attributes

##### google\_safety\_settings

The safety settings to use for the model.

See [https://ai.google.dev/gemini-api/docs/safety-settings](https://ai.google.dev/gemini-api/docs/safety-settings) for more information.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`SafetySettingDict`\]

##### google\_thinking\_config

The thinking configuration to use for the model.

See [https://ai.google.dev/gemini-api/docs/thinking](https://ai.google.dev/gemini-api/docs/thinking) for more information.

**Type:** `ThinkingConfigDict`

##### google\_labels

User-defined metadata to break down billed charges. Only supported by the Vertex AI API.

See the [Gemini API docs](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/add-labels-to-api-calls) for use cases and limitations.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### google\_video\_resolution

The video resolution to use for the model.

See [https://ai.google.dev/api/generate-content#MediaResolution](https://ai.google.dev/api/generate-content#MediaResolution) for more information.

**Type:** `MediaResolution`

##### google\_cached\_content

The name of the cached content to use for the model.

When set, `system_instruction`, `tools`, and `tool_config` are omitted from the outgoing request -- the cached content resource owns those fields, and both the Gemini API and Vertex AI reject requests that supply them alongside `cached_content` (`400 INVALID_ARGUMENT`: "Tool config, tools and system instruction should not be set in the request when using cached content."). Any tools registered on the agent and any system prompt are therefore ignored on requests that go through the cache; a `UserWarning` is emitted whenever stripping actually drops a field so the mismatch is discoverable.

See [https://ai.google.dev/gemini-api/docs/caching](https://ai.google.dev/gemini-api/docs/caching) for more information.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### google\_logprobs

Include log probabilities in the response.

See [https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/content-generation-parameters#log-probabilities-output-tokens](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/content-generation-parameters#log-probabilities-output-tokens) for more information.

Note: Only supported for Vertex AI and non-streaming requests.

These will be included in `ModelResponse.provider_details['logprobs']`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### google\_top\_logprobs

Include log probabilities of the top n tokens in the response.

See [https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/content-generation-parameters#log-probabilities-output-tokens](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/content-generation-parameters#log-probabilities-output-tokens) for more information.

Note: Only supported for Vertex AI and non-streaming requests.

These will be included in `ModelResponse.provider_details['logprobs']`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### google\_cloud\_service\_tier

The service tier to use for the model request when using Google Cloud.

Controls routing for Provisioned Throughput, Flex PayGo, and Priority PayGo (e.g., `'pt_only'`, `'flex_only'`, `'priority_only'`).

See [`GoogleCloudServiceTier`](https://pydantic.dev/docs/ai/api/models/google/#pydantic_ai.models.google.GoogleCloudServiceTier) for all values, headers sent, and links to Google docs.

**Type:** `GoogleCloudServiceTier`

##### google\_model\_armor\_config

Model Armor configuration for screening prompts and responses. Only supported by the Vertex AI API.

Specifies the Model Armor templates to use for sanitizing user prompts and model responses. Both fields are optional -- omit either to skip screening for that direction.

Mutually exclusive with `google_safety_settings`: Vertex AI rejects a request that sets both, since Model Armor replaces the built-in safety filters for that request.

Note: Model Armor screening -- both prompt and response -- is only applied for non-streaming requests. Google's API ignores `modelArmorConfig` for streaming requests (`streamGenerateContent`).

See the [Model Armor docs](https://cloud.google.com/security-command-center/docs/model-armor-overview) for use cases and limitations.

**Type:** `ModelArmorConfigDict`

### GoogleModel

**Bases:** `Model[Client]`

A model that uses Gemini via `generativelanguage.googleapis.com` API.

This is implemented from scratch rather than using a dedicated SDK, good API documentation is available [here](https://ai.google.dev/api).

Apart from `__init__`, all methods are private or match those of the base class.

#### Attributes

##### model\_name

The model name.

**Type:** `GoogleModelName`

##### system

The model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: GoogleModelName,
    *,
    provider: Literal['google', 'google-cloud', 'gateway'] | Provider[Client] = 'google',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize a Gemini model.

###### Parameters

**`model_name`** : `GoogleModelName`

The name of the model to use.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['google', 'google-cloud', 'gateway'\] | `Provider`\[`Client`\] _Default:_ `'google'`

The provider to use for authentication and API access. Can be either the string 'google' (Gemini API) or 'google-cloud' (Google Cloud, formerly known as Vertex AI), or an instance of `Provider[google.genai.AsyncClient]`. Defaults to 'google'.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model settings to use. Defaults to None.

##### supported\_native\_tools

`@classmethod`

```python
def supported_native_tools(cls) -> frozenset[type[AbstractNativeTool]]
```

Return the set of native tool types this model can handle.

###### Returns

[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

### GeminiStreamedResponse

**Bases:** `StreamedResponse`

Implementation of `StreamedResponse` for the Gemini model.

#### Attributes

##### model\_name

Get the model name of the response.

**Type:** `GoogleModelName`

##### provider\_name

Get the provider name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_url

Get the provider base URL.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

### LatestGoogleModelNames

Latest Gemini models.

**Default:** `Literal['gemini-flash-latest', 'gemini-flash-lite-latest', 'gemini-2.0-flash', 'gemini-2.0-flash-lite', 'gemini-2.5-flash', 'gemini-2.5-flash-preview-09-2025', 'gemini-2.5-flash-image', 'gemini-2.5-flash-lite', 'gemini-2.5-pro', 'gemini-3-flash-preview', 'gemini-3-pro-image', 'gemini-3-pro-image-preview', 'gemini-3-pro-preview', 'gemini-3.1-flash-image', 'gemini-3.1-flash-image-preview', 'gemini-3.1-flash-lite', 'gemini-3.1-pro-preview', 'gemini-3.5-flash', 'gemini-3.5-flash-lite', 'gemini-3.6-flash', 'gemini-3.7-flash', 'gemini-3.8-flash']`

### GoogleModelName

Possible Gemini model names.

Since Gemini supports a variety of date-stamped models, we explicitly list the latest models but allow any name in the type hints. See [the Gemini API docs](https://ai.google.dev/gemini-api/docs/models/gemini#model-variations) for a full list.

**Default:** `str | LatestGoogleModelNames`

### GoogleCloudServiceTier

Values for the `google_cloud_service_tier` field on [`GoogleModelSettings`](https://pydantic.dev/docs/ai/api/models/google/#pydantic_ai.models.google.GoogleModelSettings).

Controls Google Cloud HTTP headers for [Provisioned Throughput](https://cloud.google.com/vertex-ai/generative-ai/docs/provisioned-throughput/use-provisioned-throughput) (PT), [Flex PayGo](https://cloud.google.com/vertex-ai/generative-ai/docs/flex-paygo), and [Priority PayGo](https://cloud.google.com/vertex-ai/generative-ai/docs/priority-paygo).

-   `'pt_then_on_demand'` (**default**): PT when quota allows, then standard on-demand spillover. No headers sent.
-   `'pt_only'`: PT only (`X-Vertex-AI-LLM-Request-Type: dedicated`). No on-demand spillover; returns 429 when over quota.
-   `'pt_then_flex'`: PT when quota allows, then [Flex PayGo](https://cloud.google.com/vertex-ai/generative-ai/docs/flex-paygo) spillover (`X-Vertex-AI-LLM-Shared-Request-Type: flex`).
-   `'pt_then_priority'`: PT when quota allows, then [Priority PayGo](https://cloud.google.com/vertex-ai/generative-ai/docs/priority-paygo) spillover (`X-Vertex-AI-LLM-Shared-Request-Type: priority`).
-   `'on_demand'`: Standard on-demand only (`X-Vertex-AI-LLM-Request-Type: shared`). Bypasses PT for this request.
-   `'flex_only'`: [Flex PayGo](https://cloud.google.com/vertex-ai/generative-ai/docs/flex-paygo) only (`X-Vertex-AI-LLM-Request-Type: shared` and `X-Vertex-AI-LLM-Shared-Request-Type: flex`). Bypasses PT.
-   `'priority_only'`: [Priority PayGo](https://cloud.google.com/vertex-ai/generative-ai/docs/priority-paygo) only (`X-Vertex-AI-LLM-Request-Type: shared` and `X-Vertex-AI-LLM-Shared-Request-Type: priority`). Bypasses PT.

Not every model or region supports every value; see the linked Google docs.

**Default:** `Literal['pt_then_on_demand', 'pt_only', 'pt_then_flex', 'pt_then_priority', 'on_demand', 'flex_only', 'priority_only']`

---
