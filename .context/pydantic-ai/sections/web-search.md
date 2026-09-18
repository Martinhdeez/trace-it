# [Web Search](https://pydantic.dev/docs/ai/capabilities/web-search/)

# Web Search

The [`WebSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebSearch) [capability](https://pydantic.dev/docs/ai/capabilities/overview/) gives your agent web search. Like all [provider-adaptive tools](https://pydantic.dev/docs/ai/capabilities/overview/#provider-adaptive-tools), it uses the provider's native web search when the model supports it and can fall back to a local implementation on other models.

[`WebSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebSearch) defaults to native-only. Backed by [`WebSearchTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.WebSearchTool) on the native side (see [Web Search Tool](https://pydantic.dev/docs/ai/tools-toolsets/native-tools/#web-search-tool) for provider support and configuration) -- pass `native=WebSearchTool(...)` directly when you need full control over the native instance.

For the local side, pass `local='duckduckgo'` (or `local=True`) for a [DuckDuckGo](https://pydantic.dev/docs/ai/tools-toolsets/common-tools/#duckduckgo-search-tool) fallback (requires the `duckduckgo` optional group); for other search providers, use a [Tavily](https://pydantic.dev/docs/ai/api/pydantic-ai/common_tools/#pydantic_ai.common_tools.tavily.tavily_search_tool) wrapper from [`common_tools`](https://pydantic.dev/docs/ai/tools-toolsets/common-tools/), the [`ExaSearchToolset`](https://pydantic.dev/docs/ai/harness/exa-search/) from the Pydantic AI Harness, or any callable, [`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool), or [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset).

Native configuration fields: `search_context_size`, `user_location`, `blocked_domains`, `allowed_domains`, `max_uses`, and OpenAI Responses' `external_web_access`. The domain and `max_uses` constraints require native support. Setting `external_web_access=False` also requires native support because a local fallback cannot guarantee cached or indexed-only search.

web\_search.py

```python
from pydantic_ai.capabilities import WebSearch

# Native-only -- raises on models without native web search
WebSearch()

# Native preferred; DuckDuckGo fallback (needs `pydantic-ai-slim[duckduckgo]`)
WebSearch(local='duckduckgo')

# Native preferred; custom callable as fallback
def my_search(query: str) -> str: ...
WebSearch(local=my_search)
```

---
