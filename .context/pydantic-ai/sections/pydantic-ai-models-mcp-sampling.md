# [pydantic_ai.models.mcp_sampling](https://pydantic.dev/docs/ai/api/models/mcp-sampling/)

# pydantic\_ai.models.mcp\_sampling

### MCPSamplingModelSettings

**Bases:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings)

Settings used for an MCP Sampling model request.

#### Attributes

##### mcp\_model\_preferences

Model preferences to use for MCP Sampling.

**Type:** `ModelPreferences`

### MCPSamplingModel

**Bases:** `Model`

A model that uses MCP Sampling.

[MCP Sampling](https://modelcontextprotocol.io/docs/concepts/sampling) allows an MCP server to make requests to a model by calling back to the MCP client that connected to it.

#### Attributes

##### session

The MCP server session to use for sampling.

**Type:** `ServerSession`

##### default\_max\_tokens

Default max tokens to use if not set in [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings.max_tokens).

Max tokens is a required parameter for MCP Sampling, but optional on [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings), so this value is used as fallback.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `16384`

##### model\_name

The model name.

Since the model name isn't known until the request is made, this property always returns `'mcp-sampling'`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The system / model provider, returns `'MCP'`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

---
