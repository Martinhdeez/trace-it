# [MCP](https://pydantic.dev/docs/ai/capabilities/mcp/)

# MCP

[`MCP`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.MCP) is a [provider-adaptive capability](https://pydantic.dev/docs/ai/capabilities/overview/#provider-adaptive-tools) and the primary entry point for [MCP](https://pydantic.dev/docs/ai/mcp/overview/) in Pydantic AI. It runs the MCP server locally by default -- keeping credentials, hooks, and tracing under your control -- and supports both URL-based servers and direct client / toolset / transport inputs.

Backed by [`MCPServerTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.MCPServerTool) on the native side (see [MCP Server Tool](https://pydantic.dev/docs/ai/tools-toolsets/native-tools/#mcp-server-tool) for provider support and configuration) -- pass `native=MCPServerTool(...)` directly when you need full control (e.g. a different `id`, `authorization_token`, or `description` than the capability would derive). On the local side, `local=` accepts any [`MCPToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset) input (URL, `fastmcp.Client`, transport, in-process `FastMCP` server, script path, ...) -- non-toolset inputs are wrapped in `MCPToolset` automatically.

mcp.py

```python
from pydantic_ai.capabilities import MCP
from pydantic_ai.native_tools import MCPServerTool

# URL-based MCP server, running locally (requires `pydantic-ai-slim[mcp]`)
MCP('https://mcp.example.com/api')

# Local client without a URL -- pass any `MCPToolset` input
# (URL, `fastmcp.Client`, transport, in-process `FastMCP` server, script path, etc.)
MCP(local=my_fastmcp_client)

# Native preferred; URL-based local fallback
MCP('https://mcp.example.com/api', native=True)

# Strict native-only (no local -- does not require the `mcp` extra)
MCP('https://mcp.example.com/api', native=True, local=False)

# Explicit native + explicit local -- independent configuration on each side
# (e.g. provider-relay URL for native, direct connection for local)
MCP(
    native=MCPServerTool(
        id='public-mcp',
        url='https://relay.example.com/mcp',
        authorization_token='relay-token',
    ),
    local=my_fastmcp_client,
)
```

For lower-level access -- managing the [`MCPToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset) lifecycle directly, advanced transport / client configuration, or using MCP servers without going through a capability -- see the [MCP documentation](https://pydantic.dev/docs/ai/mcp/overview/).

---
