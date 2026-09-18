# [pydantic_ai.native_tools](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/)

# pydantic\_ai.native\_tools

### AbstractNativeTool

**Bases:** `ABC`

A native tool that can be used by an agent.

This class is abstract and cannot be instantiated directly.

The native tools are passed to the model as part of the `ModelRequestParameters`.

#### Attributes

##### kind

Native tool identifier, this should be available on all native tools as a discriminator.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'unknown_native_tool'`

##### optional

Whether this instance is a best-effort upgrade rather than a hard requirement.

When `True`, the instance is silently dropped from the request on a model that doesn't support it natively, instead of raising when no local fallback is provided. Use for native tools where a fallback path exists (e.g. a local function tool that takes over when the native one isn't available). When `False` (the default), the request errors on models that can't honor the native tool -- the user explicitly asked for it, so fail loudly rather than silently substituting different behavior.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### unique\_id

A unique identifier for the native tool.

If multiple instances of the same native tool can be passed to the model, subclasses should override this property to allow them to be distinguished.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### label

Human-readable label for UI display.

Subclasses should override this to provide a meaningful label.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### WebSearchTool

**Bases:** `AbstractNativeTool`

A native tool that allows your agent to search the web for information.

The parameters that PydanticAI passes depend on the model, as some parameters may not be supported by certain models. OpenRouter uses its Beta web-search server tool, which lets the model decide whether to search and how often. It accepts the portable settings below, though their effect depends on OpenRouter's selected search engine and downstream provider.

Supported by:

-   Anthropic
-   OpenAI Responses
-   Groq
-   Google
-   xAI
-   OpenRouter

#### Attributes

##### search\_context\_size

The `search_context_size` parameter controls how much context is retrieved from the web to help the tool formulate a response.

Supported by:

-   OpenAI Responses
-   OpenRouter

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['low', 'medium', 'high'\] **Default:** `'medium'`

##### user\_location

The `user_location` parameter allows you to localize search results based on a user's location.

Supported by:

-   Anthropic
-   OpenAI Responses
-   xAI, see [https://docs.x.ai/docs/guides/tools/search-tools#web-search-parameters](https://docs.x.ai/docs/guides/tools/search-tools#web-search-parameters)
-   OpenRouter, see [https://openrouter.ai/docs/guides/features/server-tools/web-search#configuration](https://openrouter.ai/docs/guides/features/server-tools/web-search#configuration)

**Type:** [`WebSearchUserLocation`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.WebSearchUserLocation) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### blocked\_domains

If provided, these domains will never appear in results.

With Anthropic, you can only use one of `blocked_domains` or `allowed_domains`, not both.

Supported by:

-   Anthropic, see [https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool#domain-filtering](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool#domain-filtering)
-   Groq, see [https://console.groq.com/docs/agentic-tooling#search-settings](https://console.groq.com/docs/agentic-tooling#search-settings)
-   xAI, see [https://docs.x.ai/docs/guides/tools/search-tools#web-search-parameters](https://docs.x.ai/docs/guides/tools/search-tools#web-search-parameters)
-   OpenRouter, see [https://openrouter.ai/docs/guides/features/server-tools/web-search#configuration](https://openrouter.ai/docs/guides/features/server-tools/web-search#configuration)

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### allowed\_domains

If provided, only these domains will be included in results.

With Anthropic, you can only use one of `blocked_domains` or `allowed_domains`, not both.

Supported by:

-   Anthropic, see [https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool#domain-filtering](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/web-search-tool#domain-filtering)
-   Groq, see [https://console.groq.com/docs/agentic-tooling#search-settings](https://console.groq.com/docs/agentic-tooling#search-settings)
-   OpenAI Responses, see [https://platform.openai.com/docs/guides/tools-web-search](https://platform.openai.com/docs/guides/tools-web-search)
-   xAI, see [https://docs.x.ai/docs/guides/tools/search-tools#web-search-parameters](https://docs.x.ai/docs/guides/tools/search-tools#web-search-parameters)
-   OpenRouter, see [https://openrouter.ai/docs/guides/features/server-tools/web-search#configuration](https://openrouter.ai/docs/guides/features/server-tools/web-search#configuration)

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_uses

If provided, the tool will stop searching the web after the given number of uses.

For OpenRouter, this limit is enforced with a non-native search engine or Anthropic's native search. Other native providers ignore it.

Supported by:

-   Anthropic
-   OpenRouter

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### external\_web\_access

Whether the hosted web search tool may fetch live web content.

If `False`, the tool uses only cached or indexed results. If `None`, the parameter is omitted and the provider default is used. OpenAI currently defaults to `True`.

Supported by:

-   OpenAI Responses `web_search` tool, see [https://developers.openai.com/api/docs/guides/tools-web-search#live-internet-access](https://developers.openai.com/api/docs/guides/tools-web-search#live-internet-access)

OpenAI's legacy `web_search_preview` tool ignores this parameter.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### kind

The kind of tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'web_search'`

### WebSearchUserLocation

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Allows you to localize search results based on a user's location.

Supported by:

-   Anthropic
-   OpenAI Responses
-   xAI
-   OpenRouter

#### Attributes

##### city

The city where the user is located.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### country

The country where the user is located.

For OpenAI and xAI, this must be a 2-letter ISO 3166-1 alpha-2 country code (e.g., 'US', 'GB').

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### region

The region or state where the user is located.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timezone

The timezone of the user's location.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### XSearchTool

**Bases:** `AbstractNativeTool`

A native tool that allows your agent to search X/Twitter for posts and content.

See [https://docs.x.ai/developers/tools/x-search](https://docs.x.ai/developers/tools/x-search) for more details.

When used via the [`XSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.XSearch) capability with a `fallback_subagent_model` set, this tool also works with non-xAI models by delegating to a subagent running the specified xAI model.

Supported by:

-   xAI

#### Attributes

##### allowed\_x\_handles

If provided, only posts from these X handles will be included (max 20).

Supported by:

-   xAI, see [https://docs.x.ai/developers/tools/x-search](https://docs.x.ai/developers/tools/x-search)

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### excluded\_x\_handles

If provided, posts from these X handles will be excluded (max 20).

Supported by:

-   xAI, see [https://docs.x.ai/developers/tools/x-search](https://docs.x.ai/developers/tools/x-search)

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### from\_date

If provided, only posts created on or after this datetime will be included.

Naive datetimes are interpreted as UTC by the xAI API.

Supported by:

-   xAI, see [https://docs.x.ai/developers/tools/x-search](https://docs.x.ai/developers/tools/x-search)

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### to\_date

If provided, only posts created on or before this datetime will be included.

Naive datetimes are interpreted as UTC by the xAI API.

Supported by:

-   xAI, see [https://docs.x.ai/developers/tools/x-search](https://docs.x.ai/developers/tools/x-search)

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### enable\_image\_understanding

Enable image analysis from X posts.

Supported by:

-   xAI, see [https://docs.x.ai/developers/tools/x-search](https://docs.x.ai/developers/tools/x-search)

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### enable\_video\_understanding

Enable video analysis from X content.

Supported by:

-   xAI, see [https://docs.x.ai/developers/tools/x-search](https://docs.x.ai/developers/tools/x-search)

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### include\_output

Include raw X search results in the response as [`NativeToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolReturnPart).

Without this, the model uses the search results internally but only returns its text summary. Enabling it gives programmatic access to searched posts, sources, and metadata.

Can also be set via [`XaiModelSettings.xai_include_x_search_output`](https://pydantic.dev/docs/ai/api/models/xai/#pydantic_ai.models.xai.XaiModelSettings.xai_include_x_search_output).

Supported by:

-   xAI, see [https://docs.x.ai/developers/tools/x-search](https://docs.x.ai/developers/tools/x-search)

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### kind

The kind of tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'x_search'`

### CodeExecutionTool

**Bases:** `AbstractNativeTool`

A native tool that allows your agent to execute code.

Supported by:

-   Anthropic
-   OpenAI Responses
-   Google
-   Bedrock (Nova2.0)
-   xAI

#### Attributes

##### files

Uploaded files to make available in the code execution environment.

Only files matching the model provider are used; files from other providers are ignored.

Supported by:

-   Anthropic
-   OpenAI Responses

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`UploadedFile`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UploadedFile)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### kind

The kind of tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'code_execution'`

### WebFetchTool

**Bases:** `AbstractNativeTool`

Allows your agent to access contents from URLs.

The parameters that PydanticAI passes depend on the model, as some parameters may not be supported by certain models.

Supported by:

-   Anthropic
-   Google

#### Attributes

##### max\_uses

If provided, the tool will stop fetching URLs after the given number of uses.

Supported by:

-   Anthropic

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### allowed\_domains

If provided, only these domains will be fetched.

With Anthropic, you can only use one of `blocked_domains` or `allowed_domains`, not both.

Supported by:

-   Anthropic, see [https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-fetch-tool#domain-filtering](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-fetch-tool#domain-filtering)

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### blocked\_domains

If provided, these domains will never be fetched.

With Anthropic, you can only use one of `blocked_domains` or `allowed_domains`, not both.

Supported by:

-   Anthropic, see [https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-fetch-tool#domain-filtering](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-fetch-tool#domain-filtering)

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### enable\_citations

If True, enables citations for fetched content.

Supported by:

-   Anthropic

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### max\_content\_tokens

Maximum content length in tokens for fetched content.

Supported by:

-   Anthropic

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### kind

The kind of tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'web_fetch'`

### ImageGenerationTool

**Bases:** `AbstractNativeTool`

A native tool that allows your agent to generate images.

Supported by:

-   OpenAI Responses
-   Google

#### Attributes

##### action

Whether to generate a new image or edit an existing image.

Supported by:

-   OpenAI Responses. Default: 'auto'.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['generate', 'edit', 'auto'\] **Default:** `'auto'`

##### background

Background type for the generated image.

Supported by:

-   OpenAI Responses. 'transparent' is only supported for 'png' and 'webp' output formats.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['transparent', 'opaque', 'auto'\] **Default:** `'auto'`

##### input\_fidelity

Control how much effort the model will exert to match the style and features, especially facial features, of input images.

Supported by:

-   OpenAI Responses. Default: 'low'.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['high', 'low'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### moderation

Moderation level for the generated image.

Supported by:

-   OpenAI Responses

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['auto', 'low'\] **Default:** `'auto'`

##### model

The image generation model to use.

Supported by:

-   OpenAI Responses. Defaults to the provider's image generation model selection. Known image generation models include `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1`, and `gpt-image-1-mini`.

This selects the underlying image generation model used by the tool; it does not change the agent's conversational model.

**Type:** `ImageGenerationModelName` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### output\_compression

Compression level for the output image.

Supported by:

-   OpenAI Responses. Only supported for 'jpeg' and 'webp' output formats. Default: 100.
-   Google (Vertex AI only). Only supported for 'jpeg' output format. Default: 75. Setting this will default `output_format` to 'jpeg' if not specified.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### output\_format

The output format of the generated image.

Supported by:

-   OpenAI Responses. Default: 'png'.
-   Google (Vertex AI only). Default: 'png', or 'jpeg' if `output_compression` is set.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['png', 'webp', 'jpeg'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### partial\_images

Number of partial images to generate in streaming mode.

Supported by:

-   OpenAI Responses. Supports 0 to 3.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### quality

The quality of the generated image.

Supported by:

-   OpenAI Responses

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['low', 'medium', 'high', 'auto'\] **Default:** `'auto'`

##### size

The size of the generated image.

-   OpenAI Responses: 'auto' (default: model selects the size based on the prompt), '1024x1024', '1024x1536', '1536x1024'
-   Google (Gemini 3 Pro Image and later): '512' (Gemini 3.1 Flash Image only), '1K' (default), '2K', '4K'

**Type:** `ImageSize` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### aspect\_ratio

The aspect ratio to use for generated images.

Supported by:

-   Google image-generation models (Gemini)
-   OpenAI Responses (maps '1:1', '2:3', and '3:2' to supported sizes)

**Type:** `ImageAspectRatio` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### kind

The kind of tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'image_generation'`

### MemoryTool

**Bases:** `AbstractNativeTool`

A native tool that allows your agent to use memory.

Supported by:

-   Anthropic

#### Attributes

##### kind

The kind of tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'memory'`

### MCPServerTool

**Bases:** `AbstractNativeTool`

A native tool that allows your agent to use MCP servers.

Supported by:

-   OpenAI Responses
-   Anthropic
-   xAI

#### Attributes

##### id

A unique identifier for the MCP server.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### url

The URL of the MCP server to use.

For OpenAI Responses, it is possible to use `connector_id` by providing it as `x-openai-connector:<connector_id>`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### authorization\_token

Authorization header to use when making requests to the MCP server.

Supported by:

-   OpenAI Responses
-   Anthropic
-   xAI

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### description

A description of the MCP server.

Supported by:

-   OpenAI Responses
-   xAI

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### allowed\_tools

A list of tools that the MCP server can use.

Supported by:

-   OpenAI Responses
-   Anthropic
-   xAI

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### headers

Optional HTTP headers to send to the MCP server.

Use for authentication or other purposes.

Supported by:

-   OpenAI Responses
-   xAI

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### FileSearchTool

**Bases:** `AbstractNativeTool`

A native tool that allows your agent to search through uploaded files using vector search.

This tool provides a fully managed Retrieval-Augmented Generation (RAG) system that handles file storage, chunking, embedding generation, and context injection into prompts.

Supported by:

-   OpenAI Responses
-   Google (Gemini)
-   xAI (mapped to collections search)

#### Attributes

##### file\_store\_ids

The file store IDs to search through.

For OpenAI, these are the IDs of vector stores created via the OpenAI API. For Google, these are file search store names that have been uploaded and processed via the Gemini Files API. For xAI, these are collection IDs for the xAI collections search tool.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### max\_num\_results

The maximum number of results to return.

Supported by:

-   xAI (mapped to collections search `limit`, defaults to 10 server-side)

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### instructions

Optional instructions that guide how the collections search results are interpreted and ranked.

Supported by:

-   xAI

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### retrieval\_mode

The retrieval strategy for the search.

Supported by:

-   xAI (defaults to `hybrid` server-side)

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['hybrid', 'semantic', 'keyword'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### kind

The kind of tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'file_search'`

### AdvisorTool

**Bases:** `AbstractNativeTool`

A native tool that lets a faster executor model consult a stronger advisor model mid-generation.

The fields map 1:1 to the parameters of Anthropic's advisor tool definition. OpenRouter exposes the advisor as a gateway server tool that honors a subset (`model`, `max_tokens`) and ignores the unsupported fields; see the per-field docstrings for which provider supports each.

Supported by:

-   Anthropic
-   OpenRouter

#### Attributes

##### model

The advisor model to consult, i.e. the `model` field of the provider's advisor tool definition.

The executor/advisor pairing is validated by the provider's API, not here. The accepted namespace depends on the executing provider: Anthropic model IDs (e.g. `claude-opus-4-8`) on Anthropic, OpenRouter catalog slugs (e.g. `anthropic/claude-opus-4.8`) on OpenRouter.

Supported by:

-   Anthropic
-   OpenRouter

**Type:** `AdvisorModelName`

##### max\_uses

If provided, the advisor can be consulted at most this many times per request. Maps to `max_uses`.

This is a per-request cap, not a per-run budget: a run that spans multiple requests resets the count each request. Enforce a conversation-wide ceiling yourself if you need one.

Supported by:

-   Anthropic

OpenRouter caps advisor consultations per request with a fixed gateway limit and ignores `max_uses`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_tokens

If provided, caps the advisor's output tokens (minimum 1024). Maps to `max_tokens` on Anthropic and `max_completion_tokens` on OpenRouter.

When set, the Anthropic advisor result carries a `stop_reason`.

Supported by:

-   Anthropic
-   OpenRouter

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### caching

If provided, caches the advisor context ephemerally with the given TTL. Maps to `caching={'type': 'ephemeral', 'ttl': ...}`.

Supported by:

-   Anthropic

OpenRouter's advisor tool has no equivalent knob and ignores `caching`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['5m', '1h'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### kind

The kind of tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'advisor'`

### NATIVE\_TOOL\_TYPES

Registry of all native tool types, keyed by their kind string.

This dict is populated automatically via `__init_subclass__` when tool classes are defined.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\] **Default:** `{}`

### ImageAspectRatio

Supported aspect ratios for image generation tools.

The direct image API takes the wider [`ImageGenerationAspectRatio`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationAspectRatio), of which these ten are a subset.

**Default:** `Literal['21:9', '16:9', '4:3', '3:2', '1:1', '9:16', '3:4', '2:3', '5:4', '4:5']`

### ImageSize

Supported sizes for image generation tools.

**Default:** `Literal['auto', '1024x1024', '1024x1536', '1536x1024', '512', '1K', '2K', '4K']`

### ImageGenerationModelName

Known OpenAI image generation model names, or another OpenAI image model ID.

**Default:** `Literal['gpt-image-2', 'gpt-image-1.5', 'gpt-image-1', 'gpt-image-1-mini'] | str`

### AdvisorModelName

Known Anthropic advisor model names, or any other model ID string.

These are the models Anthropic currently accepts as the _advisor_ -- the stronger model an executor consults mid-generation. The executor/advisor pairing is validated by the API, not here. The literals are Anthropic model IDs; on OpenRouter, pass a catalog slug string instead (e.g. `anthropic/claude-opus-4.8` or the `~anthropic/claude-opus-latest` alias).

**Default:** `Literal['claude-fable-5-1', 'claude-fable-5', 'claude-mythos-5-1', 'claude-mythos-5', 'claude-opus-5', 'claude-opus-4-8', 'claude-opus-4-7', 'claude-opus-4-6', 'claude-sonnet-4-6'] | str`

### SUPPORTED\_NATIVE\_TOOLS

Set of all native tool types.

**Default:** `frozenset(NATIVE_TOOL_TYPES.values())`

---
