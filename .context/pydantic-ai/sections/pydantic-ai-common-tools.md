# [pydantic_ai.common_tools](https://pydantic.dev/docs/ai/api/pydantic-ai/common_tools/)

# pydantic\_ai.common\_tools

### DuckDuckGoResult

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

A DuckDuckGo search result.

#### Attributes

##### title

The title of the search result.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### href

The URL of the search result.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### body

The body of the search result.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### DuckDuckGoSearchTool

The DuckDuckGo search tool.

#### Attributes

##### client

The DuckDuckGo search client.

**Type:** `DDGS`

##### max\_results

The maximum number of results. If None, returns results only from the first response.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_call\_\_

`@async`

```python
def __call__(query: str) -> list[DuckDuckGoResult]
```

Searches DuckDuckGo for the given query and returns the results.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`DuckDuckGoResult`\] -- The search results.

###### Parameters

**`query`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The query to search for.

### duckduckgo\_search\_tool

```python
def duckduckgo_search_tool(
    duckduckgo_client: DDGS | None = None,
    max_results: int | None = None,
)
```

Creates a DuckDuckGo search tool.

#### Parameters

**`duckduckgo_client`** : `DDGS` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The DuckDuckGo search client.

**`max_results`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The maximum number of results. If None, returns results only from the first response.

Exa tools for Pydantic AI agents.

Provides web search, content retrieval, and AI-powered answer capabilities using the Exa API, a neural search engine that finds high-quality, relevant results across billions of web pages.

These tools are deprecated and will be removed in v3. Use the `ExaSearch` capability from the [Pydantic AI Harness](https://pydantic.dev/docs/ai/harness/exa-search/) instead.

### ExaSearchResult

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

An Exa search result with content.

See [Exa Search API documentation](https://docs.exa.ai/reference/search) for more information.

#### Attributes

##### title

The title of the search result.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### url

The URL of the search result.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### published\_date

The published date of the content, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### author

The author of the content, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### text

The text content of the search result.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### ExaAnswerResult

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

An Exa answer result with citations.

See [Exa Answer API documentation](https://docs.exa.ai/reference/answer) for more information.

#### Attributes

##### answer

The AI-generated answer to the query.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### citations

Citations supporting the answer.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]

### ExaContentResult

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Content retrieved from a URL.

See [Exa Contents API documentation](https://docs.exa.ai/reference/get-contents) for more information.

#### Attributes

##### url

The URL of the content.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### title

The title of the page.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### text

The text content of the page.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### author

The author of the content, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### published\_date

The published date of the content, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### ExaSearchTool

The Exa search tool.

#### Attributes

##### client

The Exa async client.

**Type:** `AsyncExa`

##### num\_results

The number of results to return.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### max\_characters

Maximum characters of text content per result, or None for no limit.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_call\_\_

`@async`

```python
def __call__(
    query: str,
    search_type: Literal['auto', 'keyword', 'neural', 'fast', 'deep'] = 'auto',
) -> list[ExaSearchResult]
```

Searches Exa for the given query and returns the results with content.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`ExaSearchResult`\] -- The search results with text content.

###### Parameters

**`query`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The search query to execute with Exa.

**`search_type`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['auto', 'keyword', 'neural', 'fast', 'deep'\] _Default:_ `'auto'`

The type of search to perform. 'auto' automatically chooses the best search type, 'keyword' for exact matches, 'neural' for semantic search, 'fast' for speed-optimized search, 'deep' for comprehensive multi-query search.

### ExaFindSimilarTool

The Exa find similar tool.

#### Attributes

##### client

The Exa async client.

**Type:** `AsyncExa`

##### num\_results

The number of results to return.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

#### Methods

##### \_\_call\_\_

`@async`

```python
def __call__(url: str, exclude_source_domain: bool = True) -> list[ExaSearchResult]
```

Finds pages similar to the given URL and returns them with content.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`ExaSearchResult`\] -- Similar pages with text content.

###### Parameters

**`url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The URL to find similar pages for.

**`exclude_source_domain`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to exclude results from the same domain as the input URL. Defaults to True.

### ExaGetContentsTool

The Exa get contents tool.

#### Attributes

##### client

The Exa async client.

**Type:** `AsyncExa`

#### Methods

##### \_\_call\_\_

`@async`

```python
def __call__(urls: list[str]) -> list[ExaContentResult]
```

Gets the content of the specified URLs.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`ExaContentResult`\] -- The content of each URL.

###### Parameters

**`urls`** : [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

A list of URLs to get content for.

### ExaAnswerTool

The Exa answer tool.

#### Attributes

##### client

The Exa async client.

**Type:** `AsyncExa`

#### Methods

##### \_\_call\_\_

`@async`

```python
def __call__(query: str) -> ExaAnswerResult
```

Generates an AI-powered answer to the query with citations.

###### Returns

`ExaAnswerResult` -- An answer with supporting citations from web sources.

###### Parameters

**`query`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The question to answer.

### ExaToolset

**Bases:** [`FunctionToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.FunctionToolset)

A toolset that provides Exa search tools with a shared client.

Deprecated in favor of the [`ExaSearch`](https://pydantic.dev/docs/ai/harness/exa-search/) capability in the Pydantic AI Harness:

```python
from pydantic_ai_harness.exa import ExaSearch

from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2', capabilities=[ExaSearch()])
```

#### Methods

##### \_\_init\_\_

```python
def __init__(
    api_key: str,
    *,
    num_results: int = 5,
    max_characters: int | None = None,
    include_search: bool = True,
    include_find_similar: bool = True,
    include_get_contents: bool = True,
    include_answer: bool = True,
    id: str | None = None,
)
```

Creates an Exa toolset with a shared client.

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The Exa API key.

You can get one by signing up at [https://dashboard.exa.ai](https://dashboard.exa.ai/).

**`num_results`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) _Default:_ `5`

The number of results to return for search and find\_similar. Defaults to 5.

**`max_characters`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Maximum characters of text content per result. Use this to limit token usage. Defaults to None (no limit).

**`include_search`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to include the search tool. Defaults to True.

**`include_find_similar`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to include the find\_similar tool. Defaults to True.

**`include_get_contents`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to include the get\_contents tool. Defaults to True.

**`include_answer`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to include the answer tool. Defaults to True.

**`id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for the toolset, used for durable execution environments.

### exa\_search\_tool

`@deprecated`

```python
def exa_search_tool(
    api_key: str,
    *,
    num_results: int = 5,
    max_characters: int | None = None,
) -> Tool[Any]
def exa_search_tool(
    *,
    client: AsyncExa,
    num_results: int = 5,
    max_characters: int | None = None,
) -> Tool[Any]
```

Creates an Exa search tool.

#### Returns

[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

#### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Exa API key. Required if `client` is not provided.

You can get one by signing up at [https://dashboard.exa.ai](https://dashboard.exa.ai/).

**`client`** : `AsyncExa` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing AsyncExa client. If provided, `api_key` is ignored. This is useful for sharing a client across multiple tools.

**`num_results`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) _Default:_ `5`

The number of results to return. Defaults to 5.

**`max_characters`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Maximum characters of text content per result. Use this to limit token usage. Defaults to None (no limit).

### exa\_find\_similar\_tool

`@deprecated`

```python
def exa_find_similar_tool(api_key: str, *, num_results: int = 5) -> Tool[Any]
def exa_find_similar_tool(*, client: AsyncExa, num_results: int = 5) -> Tool[Any]
```

Creates an Exa find similar tool.

#### Returns

[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

#### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Exa API key. Required if `client` is not provided.

You can get one by signing up at [https://dashboard.exa.ai](https://dashboard.exa.ai/).

**`client`** : `AsyncExa` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing AsyncExa client. If provided, `api_key` is ignored. This is useful for sharing a client across multiple tools.

**`num_results`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) _Default:_ `5`

The number of similar results to return. Defaults to 5.

### exa\_get\_contents\_tool

`@deprecated`

```python
def exa_get_contents_tool(api_key: str) -> Tool[Any]
def exa_get_contents_tool(*, client: AsyncExa) -> Tool[Any]
```

Creates an Exa get contents tool.

#### Returns

[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

#### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Exa API key. Required if `client` is not provided.

You can get one by signing up at [https://dashboard.exa.ai](https://dashboard.exa.ai/).

**`client`** : `AsyncExa` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing AsyncExa client. If provided, `api_key` is ignored. This is useful for sharing a client across multiple tools.

### exa\_answer\_tool

`@deprecated`

```python
def exa_answer_tool(api_key: str) -> Tool[Any]
def exa_answer_tool(*, client: AsyncExa) -> Tool[Any]
```

Creates an Exa answer tool.

#### Returns

[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

#### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Exa API key. Required if `client` is not provided.

You can get one by signing up at [https://dashboard.exa.ai](https://dashboard.exa.ai/).

**`client`** : `AsyncExa` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing AsyncExa client. If provided, `api_key` is ignored. This is useful for sharing a client across multiple tools.

### ImageGenerationSubagentTool

Local image generation tool that delegates to a subagent.

Uses a subagent with the specified model and native tool configuration to generate images when the outer agent's model doesn't support image generation natively.

#### Attributes

##### model

The model to use for image generation, or a callable that returns one.

**Type:** `Model` | `KnownModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `ImageGenerationFallbackModelFunc`

##### native\_tool

The image generation configuration or outer-run factory to pass to the subagent.

**Type:** `ImageGenerationNativeTool`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### instructions

Instructions for the subagent that generates the image.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'Generate an image based on the user prompt. Do not ask clarifying questions.'`

#### Methods

##### \_\_call\_\_

`@async`

```python
def __call__(ctx: RunContext[Any], prompt: str) -> BinaryImage
```

Generate an image using a subagent.

###### Returns

[`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage)

###### Parameters

**`ctx`** : [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

The run context from the outer agent.

**`prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

A description of the image to generate.

### image\_generation\_tool

```python
def image_generation_tool(
    model: Model | KnownModelName | str | ImageGenerationFallbackModelFunc,
    native_tool: ImageGenerationNativeTool[Any],
    *,
    instructions: str = 'Generate an image based on the user prompt. Do not ask clarifying questions.',
) -> Tool[Any]
```

Creates an image generation tool backed by a subagent.

#### Returns

[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

#### Parameters

**`model`** : `Model` | `KnownModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `ImageGenerationFallbackModelFunc`

The model to use for image generation (e.g. `'openai-responses:gpt-5.4'`), or a callable taking `RunContext` that returns a model.

**`native_tool`** : `ImageGenerationNativeTool`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

The image generation configuration, or a callable that resolves it from the outer run context.

**`instructions`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'Generate an image based on the user prompt. Do not ask clarifying questions.'`

Instructions for the subagent that generates the image.

### ImageGenerationFallbackModelFunc

Callable that resolves the subagent's model dynamically per-run.

May return a `Model` instance or a model name string (e.g. `'openai-responses:gpt-5.4'`); strings are resolved to a model at call time.

**Default:** `Callable[[RunContext[Any]], Awaitable[Model | KnownModelName | str] | Model | KnownModelName | str]`

### ImageGenerationFallbackModel

Type of [`ImageGeneration.fallback_subagent_model`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ImageGeneration.fallback_subagent_model): a model, model name, factory callable, or None.

**Default:** `Model | KnownModelName | str | ImageGenerationFallbackModelFunc | None`

### ImageGenerationNativeTool

Type for the native tool: an `ImageGenerationTool` instance, or a callable resolving one from the run context.

The callable resolves once per fallback subagent invocation, from that tool call's [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext). It belongs to the same run and carries the same `deps` as the resolution on the native path, but it is not the same context: `tool_call_id` and `tool_name` name the fallback tool call rather than being `None`, and `messages` holds the run so far. Read `ctx.deps` for configuration that has to match across both.

Unlike the capability-level `native=` parameter, this callable may not return `None`: omitting the tool is meaningless once the subagent has been invoked, so returning `None` anyway raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) rather than enabling a default `ImageGenerationTool`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `ImageGenerationTool | Callable[[RunContext[AgentDepsT]], Awaitable[ImageGenerationTool] | ImageGenerationTool]`

### TavilySearchResult

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

A Tavily search result.

See [Tavily Search Endpoint documentation](https://docs.tavily.com/api-reference/endpoint/search) for more information.

#### Attributes

##### title

The title of the search result.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### url

The URL of the search result..

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### content

A short description of the search result.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### score

The relevance score of the search result.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

### TavilySearchTool

The Tavily search tool.

#### Attributes

##### client

The Tavily search client.

**Type:** `AsyncTavilyClient`

##### max\_results

The maximum number of results. If None, the Tavily default is used.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### \_\_call\_\_

`@async`

```python
def __call__(
    query: str,
    search_depth: Literal['basic', 'advanced', 'fast', 'ultra-fast'] = 'basic',
    topic: Literal['general', 'news', 'finance'] = 'general',
    time_range: Literal['day', 'week', 'month', 'year'] | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> list[TavilySearchResult]
```

Searches Tavily for the given query and returns the results.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`TavilySearchResult`\] -- A list of search results from Tavily.

###### Parameters

**`query`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The search query to execute with Tavily.

**`search_depth`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['basic', 'advanced', 'fast', 'ultra-fast'\] _Default:_ `'basic'`

The depth of the search.

**`topic`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['general', 'news', 'finance'\] _Default:_ `'general'`

The category of the search.

**`time_range`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['day', 'week', 'month', 'year'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The time range back from the current date to filter results.

**`include_domains`** : [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

List of domains to specifically include in the search results.

**`exclude_domains`** : [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

List of domains to specifically exclude from the search results.

### tavily\_search\_tool

```python
def tavily_search_tool(
    api_key: str,
    *,
    max_results: int | None = None,
    search_depth: Literal['basic', 'advanced', 'fast', 'ultra-fast'] = _UNSET,
    topic: Literal['general', 'news', 'finance'] = _UNSET,
    time_range: Literal['day', 'week', 'month', 'year'] | None = _UNSET,
    include_domains: list[str] | None = _UNSET,
    exclude_domains: list[str] | None = _UNSET,
) -> Tool[Any]
def tavily_search_tool(
    *,
    client: AsyncTavilyClient,
    max_results: int | None = None,
    search_depth: Literal['basic', 'advanced', 'fast', 'ultra-fast'] = _UNSET,
    topic: Literal['general', 'news', 'finance'] = _UNSET,
    time_range: Literal['day', 'week', 'month', 'year'] | None = _UNSET,
    include_domains: list[str] | None = _UNSET,
    exclude_domains: list[str] | None = _UNSET,
) -> Tool[Any]
```

Creates a Tavily search tool.

`max_results` is always developer-controlled and does not appear in the LLM tool schema. Other parameters, when provided, are fixed for all searches and hidden from the LLM's tool schema. Parameters left unset remain available for the LLM to set per-call.

#### Returns

[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

#### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Tavily API key. Required if `client` is not provided.

You can get one by signing up at [https://app.tavily.com/home](https://app.tavily.com/home).

**`client`** : `AsyncTavilyClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing AsyncTavilyClient. If provided, `api_key` is ignored. This is useful for sharing a client across multiple tool instances.

**`max_results`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The maximum number of results. If None, the Tavily default is used.

**`search_depth`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['basic', 'advanced', 'fast', 'ultra-fast'\] _Default:_ `_UNSET`

The depth of the search.

**`topic`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['general', 'news', 'finance'\] _Default:_ `_UNSET`

The category of the search.

**`time_range`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['day', 'week', 'month', 'year'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `_UNSET`

The time range back from the current date to filter results.

**`include_domains`** : [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `_UNSET`

List of domains to specifically include in the search results.

**`exclude_domains`** : [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `_UNSET`

List of domains to specifically exclude from the search results.

Web fetch tool for Pydantic AI agents.

Fetches web pages and converts their content to markdown using SSRF-protected HTTP requests and the `markdownify` library for HTML-to-markdown conversion.

### WebFetchResult

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Result of fetching a web page.

#### Attributes

##### url

The URL that was fetched.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### title

The page title, or empty string if not found.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### content

The page content converted to markdown.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### WebFetchLocalTool

Fetches a URL and converts the response to markdown.

#### Attributes

##### max\_content\_length

Maximum character length of returned content. None for no limit.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### allow\_local\_urls

Whether to allow fetching from private/local IP addresses.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### timeout

Request timeout in seconds.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### max\_download\_bytes

Maximum size in bytes of the response body to download. None for no limit.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=_MAX_DOWNLOAD_BYTES)`

##### allowed\_domains

Only fetch from these domains (exact hostname match). Raises `ModelRetry` on violation.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None)`

##### blocked\_domains

Never fetch from these domains (exact hostname match). Raises `ModelRetry` on violation.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None)`

##### headers

Additional HTTP headers to include in the request.

The model controls the URL, so use `allowed_domains` when these include credentials.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None)`

#### Methods

##### \_\_call\_\_

`@async`

```python
def __call__(url: str) -> WebFetchResult | BinaryContent
```

Fetches the content of a web page at the given URL and returns it as markdown.

For textual content (HTML, JSON, plain text), returns a [`WebFetchResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/common_tools/#pydantic_ai.common_tools.web_fetch.WebFetchResult). For binary content (PDF, images, etc.), returns a [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) so the model can process it natively.

###### Returns

`WebFetchResult` | [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) -- The fetched page content.

###### Parameters

**`url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The URL to fetch.

### web\_fetch\_tool

```python
def web_fetch_tool(
    *,
    max_content_length: int | None = 50000,
    allow_local_urls: bool = False,
    timeout: int = 30,
    max_download_bytes: int | None = _MAX_DOWNLOAD_BYTES,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
    headers: dict[str, str] | None = None,
) -> Tool[Any]
```

Creates a web fetch tool that fetches URLs and converts content to markdown.

This tool uses SSRF protection via `pydantic_ai._ssrf.safe_download`.

By default, sends `Accept: text/markdown` to request markdown directly from servers that support it (e.g. Cloudflare, Vercel, Mintlify). This reduces token usage and improves content quality. Falls back to HTML-to-markdown conversion when the server doesn't support markdown responses.

#### Returns

[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

#### Parameters

**`max_content_length`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `50000`

Maximum character length of returned content. Defaults to 50,000 (~12,500 tokens). Use `None` for no limit.

**`allow_local_urls`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether to allow fetching from private/local IP addresses. Defaults to `False`.

**`timeout`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) _Default:_ `30`

Request timeout in seconds. Defaults to 30.

**`max_download_bytes`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `_MAX_DOWNLOAD_BYTES`

Maximum size in bytes of the response body to download, applied before the body is buffered. Defaults to 50 MiB. Use `None` for no limit, which lets a response of any size be read into memory.

**`allowed_domains`** : [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Only fetch from these domains (exact hostname match). Raises `ModelRetry` on violation.

**`blocked_domains`** : [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Never fetch from these domains (exact hostname match). Raises `ModelRetry` on violation.

**`headers`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Additional HTTP headers to include in requests. Overrides the default `Accept: text/markdown` header if `Accept` is provided. The URL is controlled by the model, so a credential configured here (e.g. `Authorization`) can be sent to any URL the model requests that passes the domain filters, which match the hostname only, not scheme or port. On redirects, configured sensitive headers (`Authorization`, `Cookie`, `Proxy-Authorization`) are only forwarded to the same origin (scheme, host, and port) or a same-host http→https upgrade on the default ports.

### XSearchSubagentTool

Local X search tool that delegates to a subagent.

Uses a subagent with the specified xAI model and `XSearchTool` native tool to search X/Twitter when the outer agent's model doesn't support X search natively.

#### Attributes

##### model

The model to use for X search, or a callable that returns one.

**Type:** `Model` | `KnownModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `XSearchFallbackModelFunc`

##### native\_tool

The X search tool configuration or outer-run factory to pass to the subagent.

**Type:** `XSearchNativeTool`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### instructions

Instructions for the subagent that performs the X search.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'Search X/Twitter based on the user query. Return a comprehensive summary of the results.'`

#### Methods

##### \_\_call\_\_

`@async`

```python
def __call__(ctx: RunContext[Any], query: str) -> str
```

Search X/Twitter using a subagent.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

###### Parameters

**`ctx`** : [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

The run context from the outer agent.

**`query`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The search query to run on X/Twitter.

### x\_search\_tool

```python
def x_search_tool(
    model: Model | KnownModelName | str | XSearchFallbackModelFunc,
    native_tool: XSearchNativeTool[Any],
    *,
    instructions: str = 'Search X/Twitter based on the user query. Return a comprehensive summary of the results.',
) -> Tool[Any]
```

Creates an X search tool backed by a subagent.

#### Returns

[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

#### Parameters

**`model`** : `Model` | `KnownModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `XSearchFallbackModelFunc`

The model to use for X search. Must be an xAI model that natively supports the `XSearchTool` native tool, e.g. `'xai:grok-4.3'`. Can also be a callable taking `RunContext` that returns such a model.

**`native_tool`** : `XSearchNativeTool`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

The X search tool configuration, or a callable that resolves it from the outer run context.

**`instructions`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'Search X/Twitter based on the user query. Return a comprehensive summary of the results.'`

Instructions for the subagent that performs the X search.

### XSearchFallbackModelFunc

Callable that resolves the subagent's model dynamically per-run.

May return a `Model` instance or a model name string (e.g. `'xai:grok-4-1-fast-non-reasoning'`); strings are resolved to a model at call time.

**Default:** `Callable[[RunContext[Any]], Awaitable[Model | KnownModelName | str] | Model | KnownModelName | str]`

### XSearchFallbackModel

Type of [`XSearch.fallback_subagent_model`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.XSearch.fallback_subagent_model): a model, model name, factory callable, or None.

**Default:** `Model | KnownModelName | str | XSearchFallbackModelFunc | None`

### XSearchNativeTool

Type for the native tool: an `XSearchTool` instance, or a callable resolving one from the run context.

The callable resolves once per fallback subagent invocation, from that tool call's [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext). It belongs to the same run and carries the same `deps` as the resolution on the native path, but it is not the same context: `tool_call_id` and `tool_name` name the fallback tool call rather than being `None`, and `messages` holds the run so far. Read `ctx.deps` for configuration that has to match across both.

Unlike the capability-level `native=` parameter, this callable may not return `None`: omitting the tool is meaningless once the subagent has been invoked, so returning `None` anyway raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) rather than enabling a default `XSearchTool`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `XSearchTool | Callable[[RunContext[AgentDepsT]], Awaitable[XSearchTool] | XSearchTool]`

---
