# [You.com](https://pydantic.dev/docs/ai/harness/youdotcom/)

> Give a Pydantic AI agent web research tools backed by the You.com APIs -- search with query-relevant excerpts or full-page markdown, page retrieval, cited one-call answers, and multi-step research including a finance-tuned mode.

# You.com

`YouSearch` and `YouResearch` give an agent web research tools backed by the [You.com](https://you.com/) APIs. `YouSearch` adds `web_search` and `get_page`, for surveying the web and reading one page in full. `YouResearch` adds `answer`, `research`, and `finance_research`, for cited answers to questions a single lookup cannot settle.

[Source](https://github.com/pydantic/pydantic-ai-harness/tree/main/pydantic_ai_harness/youdotcom/)

> While Pydantic AI Harness is on 0.x releases, the API may change between minor releases; when it does, deprecation warnings and release-note migration guidance tell you (or your agent) exactly how to upgrade. See the [version policy](https://pydantic.dev/docs/ai/harness/#version-policy).

## The problem

Some search tools return only a title and a snippet, so the agent has to fetch the page before it can judge the source. Others return the whole page, which fills the context with text the agent throws away. And some questions are not a lookup at all: answering them takes many searches, reading across the results, and writing up an answer with citations.

`YouSearch` and `YouResearch` wrap the You.com search, page, and research APIs as two [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/). Each brings its tools, a limit on how much text those tools return, and short research guidance for the system prompt.

## Usage

Install the `youdotcom` extra and set the `YDC_API_KEY` environment variable (create a key at [https://api.you.com](https://api.you.com/); the legacy `YOU_API_KEY_AUTH` is also honored). The examples below use an Anthropic model and `Agent.from_file`, so they also pull in the `anthropic` provider and the `spec` YAML support:

-   [pip](#tab-panel-158)
-   [uv](#tab-panel-159)

Terminal

```bash
pip install "pydantic-ai-harness[youdotcom,anthropic]" "pydantic-ai-slim[spec]"
```

Terminal

```bash
uv add "pydantic-ai-harness[youdotcom,anthropic]" "pydantic-ai-slim[spec]"
```

Then pass the capabilities to an `Agent` via the `capabilities` parameter:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import YouResearch, YouSearch

agent = Agent('anthropic:claude-sonnet-4-6', capabilities=[YouSearch(), YouResearch()])

result = agent.run_sync('What changed in the latest stable Python release?')
print(result.output)
```

Use `YouSearch` on its own if you only need search and page reads.

## Tools

Tool

Capability

Purpose

`web_search`

`YouSearch`

Search the web and return the top `num_results` pages, each with title, URL, and its most relevant excerpts.

`get_page`

`YouSearch`

Retrieve the markdown of one specific URL -- a promising `web_search` hit, or a URL the user provided.

`answer`

`YouResearch`

Get a synthesized answer with citations, grounded in live web results, in one call.

`research`

`YouResearch`

Run multi-step research that reads across many sources and returns a thorough, cited answer.

`finance_research`

`YouResearch`

The finance-tuned counterpart of `research`, for companies, markets, and instruments.

`web_search` returns short excerpts from each page rather than the whole page, so looking over several sources stays cheap. The agent then reads a page it picks with `get_page`. Set `extraction_mode='full_page'` to get each result's full markdown instead.

`get_page` and full-page `web_search` text are capped at `max_text_chars` characters, keeping the **head** (a page's lead carries the substance); when a page exceeds the cap the output ends with a `[... page text truncated at N characters]` marker. The number of results is limited the same way: `num_results` is sent to You.com, and applied again to the response that comes back.

A `web_search` query that matches nothing is a valid answer, not an error: the tool returns `No results found for {query!r}.`. Other failures reach the model as a [`ModelRetry`](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#tool-retries): a URL or question that comes back empty, a rate limit, a parameter You.com rejected (422), or a temporary API or network problem. The run keeps going, and the model can fix the URL, reword the question, or try again. Authentication, billing, and permission failures (401/402/403) are things you have to fix in your own setup, so they stop the run.

## Research

Use `answer` for a direct question you expect one call to settle. Use `research` when the question needs many searches and a write-up across the sources. `finance_research` is `research` tuned for financial analysis.

`research` waits for its result rather than handing back a job to poll, and deep and exhaustive research routinely take minutes, so `timeout_ms` defaults to 10 minutes. How hard it works is set by `research_effort`: `lite`, `standard`, `deep`, or `exhaustive`. You.com also has a `frontier` level, but it only runs as a background job, so this capability does not offer it. `finance_research` has its own `finance_effort`: `deep` or `exhaustive`.

```python
from pydantic_ai_harness import YouResearch

YouResearch(research_effort='deep')
```

Set `output_schema` to a JSON schema to have `research` return structured output (written out as JSON) instead of prose. You.com rejects an `output_schema` when `research_effort` is `'lite'`, so asking for both raises an error when you create the capability.

## Structured citations

Every tool returns a [`ToolReturn`](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#advanced-tool-returns). Its `return_value` is the text the model sees, with a `Sources:` block added when the tool has citations. Its `metadata['sources']` holds the same sources as `YouSource` records (`{'url': ..., 'title': ...}`). `web_search` also puts the response's `search_uuid` and `latency` in metadata, for tracing. The model does not see metadata: your application reads it from the `ToolReturnPart` in the message history, so you can show citations without parsing any text:

```python
from pydantic_ai.messages import ModelRequest, ToolReturnPart

for message in result.all_messages():
    if isinstance(message, ModelRequest):
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and part.metadata is not None:
                for source in part.metadata.get('sources', []):
                    print(source['url'], source['title'])
```

## Instructions

`YouSearch` adds short research guidance to the system prompt: search wide with `web_search` first, read the most promising pages in full with `get_page` before drawing conclusions, prefer primary sources, and cite the URLs you used. `YouResearch` adds guidance on when to use `answer`, `research`, and `finance_research`. Both tell the model to treat the web content it fetches as untrusted data, not as instructions to follow. On either capability, set `guidance` to your own text to replace the default, or to `''` to add nothing.

## Configuration

Every field of `YouSearch` with its default:

```python
from pydantic_ai_harness import YouSearch

YouSearch(
    num_results=10,              # results per web_search call (1 to 20)
    extraction_mode='highlights',  # 'highlights' excerpts, or 'full_page' markdown
    max_text_chars=10_000,       # get_page / full-page text cap, in characters
    include_domains=[],          # only return results from these domains (allowlist)
    exclude_domains=[],          # never return results from these domains (denylist)
    boost_domains=[],            # re-rank these domains higher without excluding others
    freshness=None,              # 'day' | 'week' | 'month' | 'year' | 'YYYY-MM-DDtoYYYY-MM-DD'
    country=None,                # two-letter country code to focus results
    guidance=None,               # None = default instructions, '' = none, str = custom
    timeout_ms=60_000,           # per-request timeout for the default client
    client=None,                 # YouClient -- None builds youdotcom.You from YDC_API_KEY
)
```

Every field of `YouResearch` with its default:

```python
from pydantic_ai_harness import YouResearch

YouResearch(
    research_effort='standard',  # 'lite' | 'standard' | 'deep' | 'exhaustive'
    finance_effort='deep',       # 'deep' | 'exhaustive'
    include_domains=[],          # only draw from these domains (allowlist)
    exclude_domains=[],          # never draw from these domains (denylist)
    boost_domains=[],            # re-rank these domains higher
    freshness=None,              # 'day' | 'week' | 'month' | 'year' | 'YYYY-MM-DDtoYYYY-MM-DD'
    country=None,                # two-letter country code to focus results
    output_schema=None,          # JSON schema for research structured output
    guidance=None,               # None = default instructions, '' = none, str = custom
    timeout_ms=600_000,          # per-request timeout for the default client
    client=None,                 # YouClient -- None builds youdotcom.You from YDC_API_KEY
)
```

`include_domains` is an allowlist, and cannot be combined with `exclude_domains` or `boost_domains`. Combining them raises an error when you create the capability, as do out-of-range limits and an invalid `freshness`. The domain, `freshness`, and `country` settings apply to `web_search`, `answer` and `research`. `finance_research` takes only its input and `finance_effort`.

## Multiple instances

Two instances of the same capability register the same tool names, which is an error. To run more than one setup in a single agent -- say one `YouSearch` over the open web and one limited to a few domains -- wrap the extra ones in core's `PrefixTools` capability. It puts a prefix in front of their tool names:

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import PrefixTools

from pydantic_ai_harness import YouSearch

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[
        YouSearch(),  # web_search, get_page
        PrefixTools(
            wrapped=YouSearch(include_domains=['sec.gov'], guidance=''),
            prefix='sec',
        ),  # sec_web_search, sec_get_page
    ],
)
```

Set `guidance=''` on the wrapped instance (or replace it with text that tells the model when to use the prefixed tools), since each instance otherwise contributes the same default research guidance.

## Custom client

The default client is `youdotcom.You`, built from the `YDC_API_KEY` environment variable. When that variable is not set, creating the capability fails with a message telling you how to fix it. To set the API key yourself, point at a different host, or use a fake in tests, pass any object with the methods listed in the `YouClient` protocol:

```python
from youdotcom import You

from pydantic_ai_harness import YouSearch

YouSearch(client=You(api_key_auth='...'))
```

## YouSearch vs core WebSearch

Core ships a [`WebSearch`](https://pydantic.dev/docs/ai/capabilities/overview/#provider-adaptive-tools) capability that adapts to the model: it uses the provider's own search where the model has one, and a local DuckDuckGo tool everywhere else. Use it when you want search that follows whichever model you run. Use `YouSearch` when you want the same search on every model: one vendor, excerpts with every result, page reads you ask for, domain filters, and freshness controls.

Give an agent one web search capability: core `WebSearch`, harness `ExaSearch`, or `YouSearch`. They all name their tools the same way -- `web_search`, plus `get_page` for the two harness ones -- and an agent cannot have two tools with the same name, so it fails when you create it. If you want two of them anyway, wrap one in `PrefixTools` to rename its tools, as shown in [Multiple instances](#multiple-instances). There is one extra case: on Anthropic models the built-in search is also called `web_search`, so `WebSearch` clashes there even though the search runs on Anthropic's side. Pass `WebSearch(native=False)` to switch it to the DuckDuckGo tool, which is called `duckduckgo_search` and does not clash.

## Agent spec (YAML/JSON)

`YouSearch` and `YouResearch` work with Pydantic AI's [agent spec](https://pydantic.dev/docs/ai/core-concepts/agent-spec/), so you can declare them in a config file instead of Python:

```yaml
# agent.yaml
model: anthropic:claude-sonnet-4-6
capabilities:
  - YouSearch:
      num_results: 5
      freshness: month
  - YouResearch:
      research_effort: deep
```

```python
from pydantic_ai import Agent
from pydantic_ai_harness import YouResearch, YouSearch

agent = Agent.from_file('agent.yaml', custom_capability_types=[YouSearch, YouResearch])
```

Pass `custom_capability_types` so the spec loader knows how to instantiate the capabilities. The `client` field is not spec-serializable; spec-loaded instances always build the default client from `YDC_API_KEY`. In specs, `output_schema` takes the JSON-schema dict form.

## Further reading

-   [Pydantic AI capabilities](https://pydantic.dev/docs/ai/capabilities/overview/)
-   [Toolsets](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/)
-   [You.com API documentation](https://documentation.you.com/)

## API reference

### YouSearch

**Bases:** `AbstractCapability[AgentDepsT]`

Web research for agents, backed by the [You.com](https://you.com/) search API.

Adds two tools: `web_search`, which returns search results with query-relevant excerpts (or full page markdown, with `extraction_mode='full_page'`), and `get_page`, which retrieves the markdown of a specific URL.

```python
from pydantic_ai import Agent
from pydantic_ai_harness.youdotcom import YouSearch

agent = Agent('anthropic:claude-sonnet-4-6', capabilities=[YouSearch()])
```

Authentication comes from the `YDC_API_KEY` environment variable by default; pass `client` to configure it explicitly.

#### Attributes

##### num\_results

Number of results `web_search` returns per query (1 to 20).

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `10`

##### extraction\_mode

How `web_search` attaches page content.

`'highlights'` (the default) returns query-relevant excerpts per result, which keeps surveying several sources cheap. `'full_page'` returns each result's full markdown, capped at `max_text_chars`.

**Type:** `ExtractionModeName` **Default:** `'highlights'`

##### max\_text\_chars

Maximum characters of page text `get_page` and full-page `web_search` return.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `10000`

##### include\_domains

If non-empty, results only come from these domains (allowlist).

Mutually exclusive with `exclude_domains` and `boost_domains`; the You.com API rejects combining an allowlist with either.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(list[str]))`

##### exclude\_domains

Results never come from these domains (denylist).

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(list[str]))`

##### boost\_domains

Results from these domains are re-ranked higher without excluding others.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(list[str]))`

##### freshness

Restrict results by recency: `day`, `week`, `month`, `year`, or a `YYYY-MM-DDtoYYYY-MM-DD` range.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### country

Two-letter country code that focuses results geographically.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### guidance

Custom research guidance for the system prompt.

Leave as `None` for the default guidance, or set `''` to contribute no instructions at all.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### timeout\_ms

Per-request timeout for the default client, in milliseconds. Ignored when `client` is set.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `DEFAULT_SEARCH_TIMEOUT_MS`

##### client

You.com client to use; when `None`, a `youdotcom.You` is built from `YDC_API_KEY`.

Any object satisfying the `YouClient` protocol works: use it to pass an API key explicitly, point at a different host, or substitute a fake in tests.

**Type:** `YouClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### \_\_post\_init\_\_

```python
def __post_init__() -> None
```

Validate configuration against the You.com API's documented bounds.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_instructions

```python
def get_instructions() -> AgentInstructions[AgentDepsT] | None
```

Static research guidance: search wide, read the promising pages in full, cite URLs.

A non-`None` `guidance` replaces the default; `''` disables instructions entirely.

###### Returns

`AgentInstructions`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_toolset

```python
def get_toolset() -> YouSearchToolset[AgentDepsT]
```

Build the toolset providing `web_search` and `get_page`.

###### Returns

`YouSearchToolset`\[`AgentDepsT`\]

##### from\_spec

`@classmethod`

```python
def from_spec(
    cls,
    *,
    num_results: int = 10,
    extraction_mode: ExtractionModeName = 'highlights',
    max_text_chars: int = 10000,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    boost_domains: list[str] | None = None,
    freshness: str | None = None,
    country: str | None = None,
    guidance: str | None = None,
    timeout_ms: int = DEFAULT_SEARCH_TIMEOUT_MS,
) -> YouSearch[AgentDepsT]
```

Construct the capability from serializable spec options.

The `client` field is not spec-serializable, so spec-loaded instances always build the default `youdotcom.You` from `YDC_API_KEY`.

###### Returns

`YouSearch`\[`AgentDepsT`\]

### YouResearch

**Bases:** `AbstractCapability[AgentDepsT]`

Cited answers and multi-step research, backed by the [You.com](https://you.com/) APIs.

Adds three tools: `answer` (a synthesized answer with citations in one call), `research` (multi-step research that reads across many sources), and `finance_research` (the finance-tuned counterpart).

```python
from pydantic_ai import Agent
from pydantic_ai_harness.youdotcom import YouResearch

agent = Agent('anthropic:claude-sonnet-4-6', capabilities=[YouResearch()])
```

Authentication comes from the `YDC_API_KEY` environment variable by default; pass `client` to configure it explicitly.

#### Attributes

##### research\_effort

How hard `research` works: `lite`, `standard`, `deep`, or `exhaustive`.

Higher levels run more searches and take longer. `frontier`, which the API only runs in background mode, is not supported by this capability.

**Type:** `ResearchEffortName` **Default:** `'standard'`

##### finance\_effort

How hard `finance_research` works: `deep` or `exhaustive`.

**Type:** `FinanceEffortName` **Default:** `'deep'`

##### include\_domains

If non-empty, `answer` and `research` only draw from these domains (allowlist).

Mutually exclusive with `exclude_domains` and `boost_domains`.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(list[str]))`

##### exclude\_domains

`answer` and `research` never draw from these domains (denylist).

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(list[str]))`

##### boost\_domains

Results from these domains are re-ranked higher for `answer` and `research`.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(list[str]))`

##### freshness

Restrict `answer` and `research` by recency: `day`, `week`, `month`, `year`, or a range.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### country

Two-letter country code that focuses `answer` and `research` geographically.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### output\_schema

JSON schema for `research` structured output. `None` returns prose.

The You.com API rejects an `output_schema` with `research_effort='lite'`, so that combination raises at construction.

**Type:** [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`object`](https://docs.python.org/3/glossary.html#term-object)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### guidance

Custom guidance for the system prompt. `None` uses the default; `''` contributes none.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### timeout\_ms

Per-request timeout for the default client, in milliseconds. Ignored when `client` is set.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `DEFAULT_RESEARCH_TIMEOUT_MS`

##### client

You.com client to use; when `None`, a `youdotcom.You` is built from `YDC_API_KEY`.

**Type:** `YouClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### \_\_post\_init\_\_

```python
def __post_init__() -> None
```

Validate configuration against the You.com API's documented constraints.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_instructions

```python
def get_instructions() -> AgentInstructions[AgentDepsT] | None
```

Static guidance on when to reach for `answer`, `research`, and `finance_research`.

###### Returns

`AgentInstructions`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_toolset

```python
def get_toolset() -> YouResearchToolset[AgentDepsT]
```

Build the toolset providing `answer`, `research`, and `finance_research`.

###### Returns

`YouResearchToolset`\[`AgentDepsT`\]

##### from\_spec

`@classmethod`

```python
def from_spec(
    cls,
    *,
    research_effort: ResearchEffortName = 'standard',
    finance_effort: FinanceEffortName = 'deep',
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    boost_domains: list[str] | None = None,
    freshness: str | None = None,
    country: str | None = None,
    output_schema: Mapping[str, object] | None = None,
    guidance: str | None = None,
    timeout_ms: int = DEFAULT_RESEARCH_TIMEOUT_MS,
) -> YouResearch[AgentDepsT]
```

Construct the capability from serializable spec options.

The `client` field is not spec-serializable, so spec-loaded instances always build the default `youdotcom.You` from `YDC_API_KEY`.

###### Returns

`YouResearch`\[`AgentDepsT`\]

### YouSearchToolset

**Bases:** `FunctionToolset[AgentDepsT]`

Gives an agent web research tools backed by the You.com Search and Contents APIs.

`web_search` surveys the web and returns results with query-relevant excerpts (or full page markdown, with `extraction_mode='full_page'`), and `get_page` retrieves the markdown of one specific URL.

Each tool returns a `ToolReturn` whose `return_value` is the text the model sees and whose `metadata['sources']` lists the result URLs and titles (`YouSource` dicts), so applications can render citations from `ToolReturnPart.metadata` without parsing the text. `web_search` also carries the response `search_uuid` and `latency` in metadata for tracing.

`get_page` and full-page `web_search` text are capped at `max_text_chars` characters. Bounds are validated by `YouSearch` at construction.

#### Methods

##### web\_search

`@async`

```python
def web_search(query: str) -> ToolReturn[str]
```

Search the web and return matching pages, each with its most relevant excerpts.

###### Returns

[`ToolReturn`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturn)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] -- The matching pages, each with title, URL, and excerpts.

###### Parameters

**`query`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The search query. Natural-language questions and keyword queries both work.

##### get\_page

`@async`

```python
def get_page(url: str) -> ToolReturn[str]
```

Retrieve the markdown of a specific URL.

Use it to read a promising URL from `web_search` results in full, or a URL the user provided.

###### Returns

[`ToolReturn`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturn)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] -- The page's title, URL, and markdown content.

###### Parameters

**`url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The URL of the page to read.

### YouResearchToolset

**Bases:** `FunctionToolset[AgentDepsT]`

Provides `answer`, `research`, and `finance_research` backed by the You.com APIs.

Each tool returns a `ToolReturn` whose `return_value` is the synthesized, cited answer the model sees, with a `Sources:` block appended, and whose `metadata['sources']` lists the sources as `YouSource` dicts.

`research` runs as a blocking call bounded by `timeout_ms`. It supports the `lite`, `standard`, `deep`, and `exhaustive` effort levels; `frontier`, which the API only runs in background mode, is not supported here.

#### Methods

##### answer

`@async`

```python
def answer(query: str) -> ToolReturn[str]
```

Get a synthesized answer with citations, grounded in live web results.

###### Returns

[`ToolReturn`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturn)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] -- A cited answer, followed by the sources it drew on.

###### Parameters

**`query`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The question to answer.

##### research

`@async`

```python
def research(input: str) -> ToolReturn[str]
```

Run multi-step research and return a thorough, cited answer.

Suited to questions too complex for a single lookup: it runs many searches, reads the sources, and synthesizes a verifiable answer.

###### Returns

[`ToolReturn`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturn)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] -- The synthesized answer, followed by the sources it drew on.

###### Parameters

**`input`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The research question or complex query.

##### finance\_research

`@async`

```python
def finance_research(input: str) -> ToolReturn[str]
```

Run finance-tuned research on companies, markets, and instruments.

###### Returns

[`ToolReturn`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturn)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] -- The synthesized analysis, followed by the sources it drew on.

###### Parameters

**`input`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The finance research question.

### YouSource

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

One source behind a tool result, carried in `ToolReturn.metadata['sources']`.

---
