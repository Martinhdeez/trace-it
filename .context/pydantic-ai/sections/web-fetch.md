# [Web Fetch](https://pydantic.dev/docs/ai/capabilities/web-fetch/)

# Web Fetch

The [`WebFetch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebFetch) [capability](https://pydantic.dev/docs/ai/capabilities/overview/) lets your agent fetch the contents of URLs. Like all [provider-adaptive tools](https://pydantic.dev/docs/ai/capabilities/overview/#provider-adaptive-tools), it prefers the provider's native web fetch tool and can fall back to a local implementation on other models.

[`WebFetch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebFetch) defaults to native-only. Backed by [`WebFetchTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.WebFetchTool) on the native side (see [Web Fetch Tool](https://pydantic.dev/docs/ai/tools-toolsets/native-tools/#web-fetch-tool) for provider support and configuration) -- pass `native=WebFetchTool(...)` directly for full control.

For the local side, pass `local=True` for the bundled [markdownify-based fetch tool](https://pydantic.dev/docs/ai/tools-toolsets/common-tools/#web-fetch-tool) (requires the `web-fetch` optional group), or any callable, [`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool), or [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset).

Native constraint fields: `allowed_domains`, `blocked_domains`, `max_uses`, `enable_citations`, `max_content_tokens`. Only `max_uses` requires native; domain filters are enforced locally when native isn't available.

web\_fetch.py

```python
from pydantic_ai.capabilities import WebFetch

# Native-only -- raises on models without native web fetch
WebFetch()

# Native preferred; markdownify-based fallback (needs `pydantic-ai-slim[web-fetch]`)
WebFetch(local=True)

# Domain filters enforced locally when native isn't available
WebFetch(allowed_domains=['example.com'], local=True)
```

---
