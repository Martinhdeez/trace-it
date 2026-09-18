# [Installation](https://pydantic.dev/docs/ai/overview/install/)

# Installation

Pydantic AI is available on PyPI as [`pydantic-ai`](https://pypi.org/project/pydantic-ai/) so installation is as simple as:

-   [pip](#tab-panel-241)
-   [uv](#tab-panel-242)

Terminal

```bash
pip install pydantic-ai
```

Terminal

```bash
uv add pydantic-ai
```

(Requires Python 3.10+)

This installs the `pydantic_ai` package, core dependencies, and libraries required to use the OpenAI, Anthropic, and Google models, plus the [CLI](https://pydantic.dev/docs/ai/integrations/cli/), [MCP](https://pydantic.dev/docs/ai/mcp/client/), [Evals](https://pydantic.dev/docs/ai/evals/evals/), [Web UI](https://pydantic.dev/docs/ai/integrations/ui/overview/), and [Logfire](https://pydantic.dev/docs/ai/integrations/logfire/) integrations. To use any other models or integrations, add the relevant extras to your install command, e.g. `pydantic-ai[bedrock,temporal]`. Alternatively, you can install the [`pydantic-ai-slim`](#slim-install) package with only the extras you need.

## TLS certificates

Pydantic AI's own HTTP requests, and those of providers migrated to [`httpx2`](https://httpx2.pydantic.dev/), verify TLS certificates against the operating system trust store rather than shipping a `certifi` bundle. Minimal container images and corporate proxies that rely on a private CA therefore need those certificates installed in the image (for example the `ca-certificates` package, plus your proxy's root CA). Alternatively, pass such a provider an `httpx2.AsyncClient` you configured yourself through its `http_client` argument -- see the [provider docs](https://pydantic.dev/docs/ai/models/overview/) for the client each one accepts. Providers whose SDKs still use legacy `httpx` (such as Groq and Cohere) keep its `certifi`\-based verification and take a legacy `httpx.AsyncClient` instead.

## Use with Pydantic Logfire

Pydantic AI has an excellent (but completely optional) integration with [Pydantic Logfire](https://pydantic.dev/logfire) to help you view and understand agent runs.

Logfire comes included with `pydantic-ai` (but not the ["slim" version](#slim-install)), so you can typically start using it immediately by following the [Logfire setup docs](https://pydantic.dev/docs/ai/integrations/logfire/#using-logfire).

## Running Examples

We distribute the [`pydantic_ai_examples`](https://github.com/pydantic/pydantic-ai/tree/main/examples/pydantic_ai_examples) directory as a separate PyPI package ([`pydantic-ai-examples`](https://pypi.org/project/pydantic-ai-examples/)) to make examples extremely easy to customize and run.

To install examples, use the `examples` optional group:

-   [pip](#tab-panel-243)
-   [uv](#tab-panel-244)

Terminal

```bash
pip install "pydantic-ai[examples]"
```

Terminal

```bash
uv add "pydantic-ai[examples]"
```

To run the examples, follow instructions in the [examples docs](https://pydantic.dev/docs/ai/examples/setup/).

## Slim Install

If you know which model you're going to use and want to avoid installing superfluous packages, you can use the [`pydantic-ai-slim`](https://pypi.org/project/pydantic-ai-slim/) package. For example, if you're using just [`OpenAIChatModel`](https://pydantic.dev/docs/ai/api/models/openai/#pydantic_ai.models.openai.OpenAIChatModel), you would run:

-   [pip](#tab-panel-245)
-   [uv](#tab-panel-246)

Terminal

```bash
pip install "pydantic-ai-slim[openai]"
```

Terminal

```bash
uv add "pydantic-ai-slim[openai]"
```

`pydantic-ai-slim` has the following optional groups:

-   `logfire` -- installs [Pydantic Logfire](https://pydantic.dev/docs/ai/integrations/logfire/) dependency `logfire` [PyPI ↗](https://pypi.org/project/logfire)
-   `evals` -- installs [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/) dependency `pydantic-evals` [PyPI ↗](https://pypi.org/project/pydantic-evals)
-   `openai` -- installs [OpenAI Model](https://pydantic.dev/docs/ai/models/openai/) dependency `openai` [PyPI ↗](https://pypi.org/project/openai)
-   `google` -- installs [Google Model](https://pydantic.dev/docs/ai/models/google/) dependency `google-genai` [PyPI ↗](https://pypi.org/project/google-genai)
-   `anthropic` -- installs [Anthropic Model](https://pydantic.dev/docs/ai/models/anthropic/) dependency `anthropic` [PyPI ↗](https://pypi.org/project/anthropic)
-   `groq` -- installs [Groq Model](https://pydantic.dev/docs/ai/models/groq/) dependency `groq` [PyPI ↗](https://pypi.org/project/groq)
-   `mistral` -- installs [Mistral Model](https://pydantic.dev/docs/ai/models/mistral/) dependency `mistralai` [PyPI ↗](https://pypi.org/project/mistralai)
-   `cohere` - installs [Cohere Model](https://pydantic.dev/docs/ai/models/cohere/) dependency `cohere` [PyPI ↗](https://pypi.org/project/cohere)
-   `bedrock` - installs [Bedrock Model](https://pydantic.dev/docs/ai/models/bedrock/) dependency `boto3` [PyPI ↗](https://pypi.org/project/boto3)
-   `bedrock-mantle` - installs [Bedrock Mantle Model](https://pydantic.dev/docs/ai/models/bedrock/#bedrock-mantle) dependencies `openai` [PyPI ↗](https://pypi.org/project/openai) and `botocore` [PyPI ↗](https://pypi.org/project/botocore)
-   `xai` - installs [xAI Model](https://pydantic.dev/docs/ai/models/xai/) dependency `xai-sdk` [PyPI ↗](https://pypi.org/project/xai-sdk)
-   `openrouter` - installs the [OpenRouter](https://pydantic.dev/docs/ai/models/openrouter/) dependency `openai` [PyPI ↗](https://pypi.org/project/openai)
-   `zai` - installs the [Z.AI](https://pydantic.dev/docs/ai/models/zai/) dependency `openai` [PyPI ↗](https://pypi.org/project/openai)
-   `snowflake` - installs the [Snowflake Cortex](https://pydantic.dev/docs/ai/models/snowflake/) dependency `openai` [PyPI ↗](https://pypi.org/project/openai)
-   `crusoe` - installs the [Crusoe](https://pydantic.dev/docs/ai/models/crusoe/) dependency `openai` [PyPI ↗](https://pypi.org/project/openai)
-   `cerebras` - installs the [Cerebras](https://pydantic.dev/docs/ai/models/cerebras/) dependency `openai` [PyPI ↗](https://pypi.org/project/openai)
-   `huggingface` - installs [Hugging Face Model](https://pydantic.dev/docs/ai/models/huggingface/) dependency `huggingface-hub` [PyPI ↗](https://pypi.org/project/huggingface-hub)
-   `sentence-transformers` - installs [Sentence Transformers Embedding Model](https://pydantic.dev/docs/ai/guides/embeddings/#sentence-transformers-local) dependency `sentence-transformers` [PyPI ↗](https://pypi.org/project/sentence-transformers)
-   `voyageai` - installs [VoyageAI Embedding Model](https://pydantic.dev/docs/ai/guides/embeddings/#voyageai) dependency `voyageai` [PyPI ↗](https://pypi.org/project/voyageai)
-   `duckduckgo` - installs [DuckDuckGo Search Tool](https://pydantic.dev/docs/ai/tools-toolsets/common-tools/#duckduckgo-search-tool) dependency `ddgs` [PyPI ↗](https://pypi.org/project/ddgs)
-   `tavily` - installs [Tavily Search Tool](https://pydantic.dev/docs/ai/tools-toolsets/common-tools/#tavily-search-tool) dependency `tavily-python` [PyPI ↗](https://pypi.org/project/tavily-python)
-   `exa` - installs [Exa Search Tool](https://pydantic.dev/docs/ai/tools-toolsets/common-tools/#exa-search-tool) dependency `exa-py` [PyPI ↗](https://pypi.org/project/exa-py)
-   `web-fetch` - installs [Web Fetch Tool](https://pydantic.dev/docs/ai/tools-toolsets/common-tools/#web-fetch-tool) dependency `markdownify` [PyPI ↗](https://pypi.org/project/markdownify)
-   `cli` - installs [CLI](https://pydantic.dev/docs/ai/integrations/cli/) dependencies `rich` [PyPI ↗](https://pypi.org/project/rich), `prompt-toolkit` [PyPI ↗](https://pypi.org/project/prompt-toolkit), and `argcomplete` [PyPI ↗](https://pypi.org/project/argcomplete)
-   `mcp` - installs [MCP](https://pydantic.dev/docs/ai/mcp/client/) dependency `fastmcp-slim[client]` [PyPI ↗](https://pypi.org/project/fastmcp-slim)
-   `mcp-tasks` - installs the [MCP](https://pydantic.dev/docs/ai/mcp/client/) FastMCP 4 tasks extension (`use_task=True`) dependency `fastmcp-tasks` [PyPI ↗](https://pypi.org/project/fastmcp-tasks)
-   `ui` - installs [UI Event Streams](https://pydantic.dev/docs/ai/integrations/ui/overview/) dependency `starlette` [PyPI ↗](https://pypi.org/project/starlette)
-   `web` - installs [Web UI](https://pydantic.dev/docs/ai/integrations/ui/overview/) dependencies `starlette` [PyPI ↗](https://pypi.org/project/starlette) and `uvicorn` [PyPI ↗](https://pypi.org/project/uvicorn)
-   `ag-ui` - installs [AG-UI Event Stream Protocol](https://pydantic.dev/docs/ai/integrations/ui/ag-ui/) dependencies `ag-ui-protocol` [PyPI ↗](https://pypi.org/project/ag-ui-protocol) and `starlette` [PyPI ↗](https://pypi.org/project/starlette)
-   `retries` - installs [transport retries](https://pydantic.dev/docs/ai/core-concepts/retries/#transport-retries) dependency `tenacity` [PyPI ↗](https://pypi.org/project/tenacity), plus legacy `httpx` [PyPI ↗](https://pypi.org/project/httpx) support until Pydantic AI v3
-   `temporal` - installs [Temporal Durable Execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/temporal/) dependency `temporalio` [PyPI ↗](https://pypi.org/project/temporalio)
-   `dbos` - installs [DBOS Durable Execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/) dependency `dbos` [PyPI ↗](https://pypi.org/project/dbos)
-   `prefect` - installs [Prefect Durable Execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/prefect/) dependency `prefect` [PyPI ↗](https://pypi.org/project/prefect)
-   `spec` - installs [AgentSpec](https://pydantic.dev/docs/ai/core-concepts/agent-spec/) dependencies `pyyaml` [PyPI ↗](https://pypi.org/project/PyYAML) and `pydantic-handlebars` [PyPI ↗](https://pypi.org/project/pydantic-handlebars)

You can also install dependencies for multiple models and use cases, for example:

-   [pip](#tab-panel-247)
-   [uv](#tab-panel-248)

Terminal

```bash
pip install "pydantic-ai-slim[openai,google,logfire]"
```

Terminal

```bash
uv add "pydantic-ai-slim[openai,google,logfire]"
```

---
