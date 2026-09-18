# [pydantic_ai.mcp](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/)

# pydantic\_ai.mcp

### MCPError

**Bases:** [`RuntimeError`](https://docs.python.org/3/builtins/exceptions.html#RuntimeError)

Raised when an MCP server returns an error response.

This exception wraps error responses from MCP servers, following the ErrorData schema from the MCP specification.

#### Attributes

##### message

The error message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

##### code

The error code returned by the server.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `code`

##### data

Additional information about the error, if provided by the server.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `data`

#### Methods

##### from\_mcp\_sdk

`@classmethod`

```python
def from_mcp_sdk(cls, error: McpError) -> MCPError
```

Create an MCPError from an MCP SDK McpError.

###### Returns

`MCPError`

###### Parameters

**`error`** : `McpError`

An McpError from the MCP SDK.

### ResourceAnnotations

Additional properties describing MCP entities.

See the [resource annotations in the MCP specification](https://modelcontextprotocol.io/specification/2025-11-25/server/resources#annotations).

#### Attributes

##### audience

Intended audience for this entity.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`mcp_types.Role`](https://modelcontextprotocol.github.io/python-sdk/api/mcp_types/#mcp_types.Role)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### priority

Priority level for this entity, ranging from 0.0 to 1.0.

**Type:** [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated)\[[`float`](https://docs.python.org/3/builtins/functions.html#float), `Field`(`ge`\=0.0, `le`\=1.0)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### last\_modified

ISO 8601 timestamp of the last modification.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### from\_mcp\_sdk

`@classmethod`

```python
def from_mcp_sdk(cls, mcp_annotations: mcp_types.Annotations) -> ResourceAnnotations
```

Convert from MCP SDK Annotations to ResourceAnnotations.

###### Returns

`ResourceAnnotations`

###### Parameters

**`mcp_annotations`** : [`mcp_types.Annotations`](https://modelcontextprotocol.github.io/python-sdk/api/mcp_types/#mcp_types.Annotations)

The MCP SDK annotations object.

### Icon

An icon for display in user interfaces.

#### Attributes

##### src

URL or data URI for the icon.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### mime\_type

Optional MIME type for the icon.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### sizes

Optional list of strings specifying icon dimensions (e.g., \["48x48", "96x96"\]).

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### BaseResource

**Bases:** `ABC`

Base class for MCP resources.

#### Attributes

##### name

The programmatic name of the resource.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### title

Human-readable title for UI contexts.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### description

A description of what this resource represents.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### mime\_type

The MIME type of the resource, if known.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### annotations

Optional annotations for the resource.

**Type:** `ResourceAnnotations` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### icons

Optional icons for the resource.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`Icon`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### metadata

Optional metadata for the resource.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### Resource

**Bases:** `BaseResource`

A resource that can be read from an MCP server.

See the [resources in the MCP specification](https://modelcontextprotocol.io/specification/2025-11-25/server/resources).

#### Attributes

##### uri

The URI of the resource.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### size

The size of the raw resource content in bytes (before base64 encoding), if known.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### from\_mcp\_sdk

`@classmethod`

```python
def from_mcp_sdk(cls, mcp_resource: mcp_types.Resource) -> Resource
```

Convert from MCP SDK Resource to PydanticAI Resource.

###### Returns

`Resource`

###### Parameters

**`mcp_resource`** : [`mcp_types.Resource`](https://modelcontextprotocol.github.io/python-sdk/api/mcp_types/#mcp_types.Resource)

The MCP SDK Resource object.

### ResourceTemplate

**Bases:** `BaseResource`

A template for parameterized resources on an MCP server.

See the [resource templates in the MCP specification](https://modelcontextprotocol.io/specification/2025-11-25/server/resources#resource-templates).

#### Attributes

##### uri\_template

URI template (RFC 6570) for constructing resource URIs.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### from\_mcp\_sdk

`@classmethod`

```python
def from_mcp_sdk(cls, mcp_template: mcp_types.ResourceTemplate) -> ResourceTemplate
```

Convert from MCP SDK ResourceTemplate to PydanticAI ResourceTemplate.

###### Returns

`ResourceTemplate`

###### Parameters

**`mcp_template`** : [`mcp_types.ResourceTemplate`](https://modelcontextprotocol.github.io/python-sdk/api/mcp_types/#mcp_types.ResourceTemplate)

The MCP SDK ResourceTemplate object.

### ResourceLink

A resource link referenced in a prompt or tool call result.

Unlike [`EmbeddedResource`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.EmbeddedResource), this does not include the resource content directly -- it is a reference to a resource that the server can read.

Note: resource links returned by tools are not guaranteed to appear in the results of `resources/list` requests.

See the [MCP specification](https://modelcontextprotocol.io/specification/2025-11-25/server/resources).

#### Attributes

##### uri

The URI of the linked resource.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### name

The programmatic name of the linked resource.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### title

Human-readable title for UI contexts.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### description

A description of what this linked resource represents.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### mime\_type

The MIME type of the linked resource, if known.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### size

The size of the raw resource content in bytes (before base64 encoding), if known.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### annotations

Optional annotations for the linked resource.

**Type:** `ResourceAnnotations` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### icons

Optional icons for the linked resource.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`Icon`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### metadata

Optional metadata for the linked resource.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### type

Discriminator for resource link content.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['resource\_link'\] **Default:** `'resource_link'`

#### Methods

##### from\_mcp\_sdk

`@classmethod`

```python
def from_mcp_sdk(cls, mcp_resource_link: mcp_types.ResourceLink) -> ResourceLink
```

Convert from MCP SDK ResourceLink to PydanticAI ResourceLink.

###### Returns

`ResourceLink`

### PromptArgument

An argument for a prompt template.

#### Attributes

##### name

The name of the argument.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### title

Human-readable title for the argument.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### description

A human-readable description of the argument.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### required

Whether the argument is required or optional. If not specified, the server may determine this based on context.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### Prompt

A prompt or prompt template that the server offers.

#### Attributes

##### name

The programmatic name of the prompt.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### title

Human-readable title for prompt.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### description

An optional description of what this prompt provides.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### arguments

A list of arguments to use for templating the prompt.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`PromptArgument`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### icons

An optional list of icons for this prompt.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`Icon`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### metadata

See [MCP specification](https://modelcontextprotocol.io/specification/2025-11-25/basic#_meta) for notes on \_meta usage.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### from\_mcp\_sdk

`@classmethod`

```python
def from_mcp_sdk(cls, mcp_prompt: mcp_types.Prompt) -> Prompt
```

Convert from MCP SDK Prompt to PydanticAI Prompt.

###### Returns

`Prompt`

###### Parameters

**`mcp_prompt`** : [`mcp_types.Prompt`](https://modelcontextprotocol.github.io/python-sdk/api/mcp_types/#mcp_types.Prompt)

The MCP SDK Prompt object.

### EmbeddedResource

A resource embedded into a prompt or tool call result.

Contains the actual resource content alongside its metadata, unlike [`ResourceLink`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.ResourceLink) which is only a reference.

See the [MCP specification](https://modelcontextprotocol.io/specification/2025-11-25/server/resources).

#### Attributes

##### uri

The URI of the embedded resource.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### content

The content of the embedded resource.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`messages.BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent)

##### type

Discriminator for embedded resource content.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['resource'\] **Default:** `'resource'`

##### mime\_type

The MIME type of the resource, if known.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### annotations

Optional annotations for the resource.

**Type:** `ResourceAnnotations` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### metadata

See [MCP specification](https://modelcontextprotocol.io/specification/2025-11-25/basic#_meta) for notes on \_meta usage.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### resource\_metadata

`_meta` carried on the nested resource contents (separate from the embedding's own `_meta`).

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### from\_mcp\_sdk

`@classmethod`

```python
def from_mcp_sdk(
    cls,
    part: mcp_types.EmbeddedResource,
    content: str | messages.BinaryContent,
) -> EmbeddedResource
```

Convert from MCP SDK EmbeddedResource to PydanticAI EmbeddedResource.

###### Returns

`EmbeddedResource`

### PromptMessage

A message returned as part of a prompt result.

#### Attributes

##### role

The role of the message sender.

**Type:** `PromptRole`

##### content

The content of the message.

**Type:** `ContentBlock`

### PromptResult

The result of a [`get_prompt`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset.get_prompt) request.

#### Attributes

##### messages

The prompt messages.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`PromptMessage`\]

##### description

An optional description for the prompt.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### metadata

See [MCP specification](https://modelcontextprotocol.io/specification/2025-11-25/basic#_meta) for notes on \_meta usage.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### ServerCapabilities

Capabilities that an MCP server supports.

#### Attributes

##### experimental

Experimental, non-standard capabilities that the server supports.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### logging

Whether the server supports sending log messages to the client.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### prompts

Whether the server offers any prompt templates.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### prompts\_list\_changed

Whether the server will emit notifications when the list of prompts changes.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### resources

Whether the server offers any resources to read.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### resources\_list\_changed

Whether the server will emit notifications when the list of resources changes.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### tools

Whether the server offers any tools to call.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### tools\_list\_changed

Whether the server will emit notifications when the list of tools changes.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### completions

Whether the server offers autocompletion suggestions for prompts and resources.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

#### Methods

##### from\_mcp\_sdk

`@classmethod`

```python
def from_mcp_sdk(
    cls,
    mcp_capabilities: mcp_types.ServerCapabilities,
) -> ServerCapabilities
```

Convert from MCP SDK ServerCapabilities to PydanticAI ServerCapabilities.

###### Returns

`ServerCapabilities`

###### Parameters

**`mcp_capabilities`** : [`mcp_types.ServerCapabilities`](https://modelcontextprotocol.github.io/python-sdk/api/mcp_types/#mcp_types.ServerCapabilities)

The MCP SDK ServerCapabilities object.

### CallToolFunc

**Bases:** [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

A callable that invokes an MCP tool -- typically `MCPToolset.direct_call_tool` or its legacy equivalent.

Passed to user-defined [`ProcessToolCallback`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.ProcessToolCallback) functions as the underlying call hook. `metadata` is keyword-only -- pass it as `await call_tool(name, args, metadata=...)`.

### MCPToolset

**Bases:** `AbstractToolset[AgentDepsT]`

A toolset for connecting to an MCP server.

`MCPToolset` is the recommended way to use [Model Context Protocol](https://modelcontextprotocol.io/) servers in Pydantic AI. It is built on the [FastMCP](https://gofastmcp.com/) `Client`, which supports the full MCP protocol -- tools, resources, sampling, elicitation, OAuth -- and a wide range of transports (HTTP, SSE, stdio, in-process FastMCP servers, multi-server configs).

Pass any input that FastMCP can build a transport from -- a URL, a script path, a `FastMCP` server instance for in-process testing -- or a pre-built `fastmcp.Client` for full control over its configuration. For multi-server JSON config files, use [`load_mcp_toolsets`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.load_mcp_toolsets) instead.

Example -- connect to a streamable-HTTP MCP server:

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset

toolset = MCPToolset('http://localhost:8000/mcp')
agent = Agent('openai:gpt-5', toolsets=[toolset])
```

Example -- connect to a local stdio MCP server:

```python
from pydantic_ai.mcp import MCPToolset

toolset = MCPToolset('my_mcp_server.py')
```

Example -- pass a pre-built FastMCP Client for full configuration control:

```python
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport

from pydantic_ai.mcp import MCPToolset

client = Client(StreamableHttpTransport('http://localhost:8000/mcp'), auth='oauth')
toolset = MCPToolset(client)
```

#### Attributes

##### client

The underlying FastMCP `Client`. Always normalized to a `fastmcp.Client` regardless of how the toolset was constructed.

**Type:** `FastMCPClient`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### max\_retries

Maximum number of times a tool call may be retried after a `ModelRetry`.

`None` (default) inherits the agent's retry count at runtime. Set explicitly to override.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `max_retries`

##### tool\_error\_behavior

How to handle tool errors raised by the server.

`'retry'` (default) raises [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) so the model can self-correct; `'error'` propagates the underlying `fastmcp.exceptions.ToolError` to the caller. `'failed'` raises [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed) so the model can see the error.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['retry', 'error', 'failed'\] **Default:** `tool_error_behavior`

##### process\_tool\_call

Hook to wrap tool calls -- useful for adding request-level metadata, custom retry policies, or telemetry. See [`ProcessToolCallback`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.ProcessToolCallback).

**Type:** `ProcessToolCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `process_tool_call`

##### prefer\_tasks

Whether to prefer task-augmented execution (SEP-1686) for tools that support it optionally.

Defaults to `True`. Tools that require task-augmented execution always use it, while tools that forbid it never do. This client-side routing is a FastMCP 3 concept: FastMCP 4 servers direct task creation themselves (SEP-2663), so this preference has no effect there.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `prefer_tasks`

##### cache\_tools

Whether to cache the list of tools across `get_tools()` calls.

When enabled (default), tools are fetched once and cached until either:

-   The server sends a `notifications/tools/list_changed` notification
-   The toolset is fully exited (last `__aexit__` matches the first `__aenter__`)

Set to `False` for servers that change tools dynamically without sending notifications, or when passing a pre-built FastMCP Client (the cache-invalidation message handler isn't installed in that case, so caches are only invalidated by session close).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `cache_tools`

##### cache\_resources

Whether to cache the list of resources across `list_resources()` calls.

Same semantics as [`cache_tools`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset.cache_tools) but for `notifications/resources/list_changed` notifications.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `cache_resources`

##### cache\_prompts

Whether to cache the list of prompts across `list_prompts()` calls.

Same semantics as [`cache_tools`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset.cache_tools) but for `notifications/prompts/list_changed` notifications.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `cache_prompts`

##### include\_instructions

Whether to include the server's `initialize` instructions string in the agent's instruction set.

Defaults to `False` for backward compatibility. When `True`, the instructions returned by the server during initialization are added to the agent's instructions.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `include_instructions`

##### include\_return\_schema

Whether to include each tool's `outputSchema` in the schema sent to the model.

When `None` (the default), defaults to `False` unless the [`IncludeToolReturnSchemas`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.IncludeToolReturnSchemas) capability is used.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `include_return_schema`

##### sampling\_model

A Pydantic AI model that the server may sample from via the MCP `sampling/createMessage` flow.

When set (and no explicit `sampling_handler` is passed), Pydantic AI builds a sampling handler that delegates to this model with the request's `maxTokens`/`temperature`/`stopSequences` settings applied. If both `sampling_model` and `sampling_handler` are passed, an error is raised.

**Type:** [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `sampling_model`

##### log\_level

Log level requested from the server via `logging/setLevel` after initialization.

This is supported by FastMCP 3, and by FastMCP 4 on legacy protocol sessions; a modern session warns and leaves it unapplied. `None` (default) leaves the server's default log level alone. Combine with `log_handler` to receive log messages.

**Type:** [`mcp_types.LoggingLevel`](https://modelcontextprotocol.github.io/python-sdk/api/mcp_types/#mcp_types.LoggingLevel) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `log_level`

##### server\_info

The server's implementation info, when the server provided it.

Raises [`AttributeError`](https://docs.python.org/3/builtins/exceptions.html#AttributeError) when accessed before the toolset has been entered, or when a modern MCP session's server omitted the optional `serverInfo` stamp.

**Type:** [`mcp_types.Implementation`](https://modelcontextprotocol.github.io/python-sdk/api/mcp_types/#mcp_types.Implementation)

##### capabilities

The capabilities advertised by the server during initialization.

Raises [`AttributeError`](https://docs.python.org/3/builtins/exceptions.html#AttributeError) when accessed before the toolset has been entered.

**Type:** `ServerCapabilities`

##### instructions

The instructions sent by the server during initialization.

Raises [`AttributeError`](https://docs.python.org/3/builtins/exceptions.html#AttributeError) when accessed before the toolset has been entered.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### is\_running

Whether the toolset is currently entered (the FastMCP session is open).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    client: MCPToolsetClient,
    *,
    id: str | None = None,
    max_retries: int | None = None,
    tool_error_behavior: Literal['retry', 'error', 'failed'] = 'retry',
    process_tool_call: ProcessToolCallback | None = None,
    prefer_tasks: bool = True,
    cache_tools: bool = True,
    cache_resources: bool = True,
    cache_prompts: bool = True,
    include_instructions: bool = False,
    include_return_schema: bool | None = None,
    sampling_model: models.Model | None = None,
    sampling_handler: SamplingHandler[Any, Any] | None = None,
    elicitation_handler: ElicitationHandler[Any, Any] | None = None,
    log_handler: LogHandler | None = None,
    log_level: mcp_types.LoggingLevel | None = None,
    progress_handler: ProgressHandler | None = None,
    message_handler: MessageHandlerT | None = None,
    client_info: mcp_types.Implementation | None = None,
    init_timeout: float | None = _UNSET,
    read_timeout: float | None = _UNSET,
    roots: RootsList | RootsHandler[Any] | None = None,
    auth: httpx.Auth | Literal['oauth'] | str | None = None,
    verify: ssl.SSLContext | bool | str | None = None,
    headers: dict[str, str] | None = None,
    http_client: httpx.AsyncClient | None = None,
)
```

Build a new `MCPToolset`.

###### Parameters

**`client`** : `MCPToolsetClient`

How to connect to the MCP server. See the class docstring for accepted shapes.

**`id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An optional unique identifier for this toolset. Required for use in durable execution environments like Temporal or DBOS, where it identifies the toolset's activities/steps within a workflow.

**`max_retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Maximum number of times a tool call may be retried after a `ModelRetry`. `None` inherits the agent's retry count at runtime.

**`tool_error_behavior`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['retry', 'error', 'failed'\] _Default:_ `'retry'`

`'retry'` (default) raises [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) on tool errors so the model can self-correct; `'error'` propagates the underlying exception; `'failed'` raises [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed) so the model can see the error.

**`process_tool_call`** : `ProcessToolCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Hook to wrap tool calls. See [`ProcessToolCallback`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.ProcessToolCallback).

**`prefer_tasks`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to prefer task-augmented execution (SEP-1686) for tools that support it optionally. Tools that require task-augmented execution always use it, while tools that forbid it never do.

**`cache_tools`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to cache the list of tools. See [`MCPToolset.cache_tools`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset.cache_tools).

**`cache_resources`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to cache the list of resources. See [`MCPToolset.cache_resources`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset.cache_resources).

**`cache_prompts`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to cache the list of prompts. See [`MCPToolset.cache_prompts`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset.cache_prompts).

**`include_instructions`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether to include the server's instructions in the agent's instructions. See [`MCPToolset.include_instructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset.include_instructions).

**`include_return_schema`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to include return schemas in tool definitions. See [`MCPToolset.include_return_schema`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset.include_return_schema).

**`sampling_model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A Pydantic AI model the server may sample from. Mutually exclusive with `sampling_handler`.

**`sampling_handler`** : `SamplingHandler`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A FastMCP-shaped sampling handler. Use for full control over the sampling response.

**`elicitation_handler`** : `ElicitationHandler`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A FastMCP-shaped elicitation handler that receives MCP `elicitation/create` requests from the server.

**`log_handler`** : `LogHandler` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A FastMCP-shaped log handler that receives log messages from the server.

**`log_level`** : [`mcp_types.LoggingLevel`](https://modelcontextprotocol.github.io/python-sdk/api/mcp_types/#mcp_types.LoggingLevel) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Log level requested via `logging/setLevel` after initialization. A modern MCP session warns and skips it because the method is handshake-era only, and expects the client to filter in `log_handler`; legacy sessions remain supported despite the upstream deprecation.

**`progress_handler`** : `ProgressHandler` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A FastMCP-shaped progress handler.

**`message_handler`** : `MessageHandlerT` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A FastMCP-shaped message handler called for every server-sent message. Pydantic AI installs its own message handler internally to invalidate caches on `list_changed` notifications; if you provide one, both run (yours after ours).

**`client_info`** : [`mcp_types.Implementation`](https://modelcontextprotocol.github.io/python-sdk/api/mcp_types/#mcp_types.Implementation) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Information describing the MCP client implementation, sent to the server during initialization.

**`init_timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `_UNSET`

Timeout in seconds for the initial connection and `initialize` handshake.

**`read_timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `_UNSET`

Maximum time in seconds to wait for new messages on the long-lived connection. Defaults to 5 minutes.

**`roots`** : `RootsList` | `RootsHandler`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Filesystem roots advertised to the server.

**`auth`** : `httpx.Auth` | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['oauth'\] | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

HTTP authentication for HTTP transports -- an `httpx.Auth`, the literal string `'oauth'` to enable FastMCP's OAuth flow, or a bearer-token string.

**`verify`** : [`ssl.SSLContext`](https://docs.python.org/3/library/ssl.html#ssl.SSLContext) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

SSL verification mode for HTTP transports -- an `ssl.SSLContext`, a CA bundle path string, or a bool.

**`headers`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Extra HTTP headers for HTTP transports. Mutually exclusive with `http_client`.

**`http_client`** : `httpx.AsyncClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A pre-configured `httpx.AsyncClient` to use for HTTP transports -- useful for self-signed certificates or custom connection pooling. Mutually exclusive with `headers`.

###### Raises

-   `ValueError` -- If a pre-built `fastmcp.Client` is passed alongside any of the kwargs that would otherwise build a default Client (sampling, elicitation, headers, etc.), or if `sampling_model` and `sampling_handler` are both passed, or if `headers` and `http_client` are both passed.

##### set\_sampling\_model

```python
def set_sampling_model(model: models.Model) -> None
```

Set the [`sampling_model`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset.sampling_model) on an already-constructed toolset.

Swaps both the public attribute and the underlying FastMCP client's sampling callback. Takes effect on the next session opened by the client; calls already in flight on an existing session continue using the previously configured handler.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_instructions

`@async`

```python
def get_instructions(ctx: RunContext[AgentDepsT]) -> messages.InstructionPart | None
```

Return the server's instructions if `include_instructions` is enabled.

###### Returns

[`messages.InstructionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### list\_tools

`@async`

```python
def list_tools() -> list[mcp_types.Tool]
```

Retrieve the tools currently exposed by the server.

When [`cache_tools`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset.cache_tools) is enabled (default), results are cached and invalidated by `notifications/tools/list_changed` or the toolset's last `__aexit__`.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`mcp_types.Tool`](https://modelcontextprotocol.github.io/python-sdk/api/mcp_types/#mcp_types.Tool)\]

##### tool\_for\_tool\_def

```python
def tool_for_tool_def(
    tool_def: ToolDefinition,
    *,
    ctx: RunContext[AgentDepsT],
) -> ToolsetTool[AgentDepsT]
```

Build the tool to call for a tool definition that was already prepared elsewhere.

###### Returns

[`ToolsetTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.ToolsetTool)\[`AgentDepsT`\]

###### Parameters

**`tool_def`** : [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition)

The prepared tool definition to build the tool from.

**`ctx`** : [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]

The run context used to resolve the tool's retry budget.

##### direct\_call\_tool

`@async`

```python
def direct_call_tool(
    name: str,
    args: dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
    use_task: bool = False,
) -> Any
```

Call a tool on the server directly.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The name of the tool to call.

**`args`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

The arguments to pass to the tool.

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional request-level `_meta` payload sent alongside the call.

**`use_task`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

When `True`, ask the server to run the call as a durable, cancelable, pollable task. FastMCP 3 uses the MCP SEP-1686 `task=True` call path, while FastMCP 4 uses its tasks extension (SEP-2663). Only valid for tools that support task execution. Both paths wait for and return the completed tool result; on FastMCP 4, `use_task=True` explicitly selects the tasks extension even though an ordinary call can also drive a task-only tool to completion.

###### Raises

-   `ModelRetry` -- If a completed tool error occurs with `tool_error_behavior='retry'` (the default), or if a protocol-level `McpError` occurs and `tool_error_behavior` is not `'error'`.
-   `fastmcp.exceptions.ToolError or the MCP SDK's McpError` -- If an error occurs and `tool_error_behavior='error'`.
-   `ToolFailed` -- If a completed tool error occurs and `tool_error_behavior='failed'`.
-   `UserError` -- If `use_task=True` and the FastMCP 4 client negotiated a legacy protocol session, which has no task path.
-   `ImportError` -- If `use_task=True` on FastMCP 4 and `fastmcp-tasks` is not installed.

##### list\_prompts

`@async`

```python
def list_prompts() -> list[Prompt]
```

Retrieve the prompts currently exposed by the server.

When [`cache_prompts`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset.cache_prompts) is enabled (default), results are cached and invalidated by `notifications/prompts/list_changed` or the toolset's last `__aexit__`.

Returns an empty list if the server does not advertise the `prompts` capability.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`Prompt`\]

###### Raises

-   `MCPError` -- If the server returns an error.

##### get\_prompt

`@async`

```python
def get_prompt(name: str, arguments: dict[str, str] | None = None) -> PromptResult
```

Retrieve a specific prompt from the server, optionally parameterized.

###### Returns

`PromptResult`

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The name of the prompt to retrieve.

**`arguments`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Arguments to parameterize the prompt, if applicable.

###### Raises

-   `MCPError` -- If the server doesn't advertise the `prompts` capability, or if it returns an error response.

##### list\_resources

`@async`

```python
def list_resources() -> list[Resource]
```

Retrieve the resources currently exposed by the server.

When [`cache_resources`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset.cache_resources) is enabled (default), results are cached and invalidated by `notifications/resources/list_changed` or the toolset's last `__aexit__`.

Returns an empty list if the server does not advertise the `resources` capability.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`Resource`\]

###### Raises

-   `MCPError` -- If the server returns an error.

##### list\_resource\_templates

`@async`

```python
def list_resource_templates() -> list[ResourceTemplate]
```

Retrieve the resource templates currently exposed by the server.

Returns an empty list if the server does not advertise the `resources` capability.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`ResourceTemplate`\]

###### Raises

-   `MCPError` -- If the server returns an error.

##### read\_resource

`@async`

```python
def read_resource(
    uri: str,
) -> str | messages.BinaryContent | list[str | messages.BinaryContent]
def read_resource(
    uri: Resource,
) -> str | messages.BinaryContent | list[str | messages.BinaryContent]
```

Read the contents of a specific resource by URI.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`messages.BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) | [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`messages.BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent)\] -- The resource contents -- a single value if the resource has one content item, or a list [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`messages.BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) | [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`messages.BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent)\] -- otherwise. Text content is returned as `str`, binary content as [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`messages.BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) | [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`messages.BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent)\] -- [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent).

###### Parameters

**`uri`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `Resource`

The URI of the resource to read, or a [`Resource`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.Resource) object.

###### Raises

-   `MCPError` -- If the server returns an error.

### load\_mcp\_toolsets

```python
def load_mcp_toolsets(config_path: str | Path) -> list[AbstractToolset[Any]]
```

Load `MCPToolset`s from a configuration file.

The configuration file uses the same `mcpServers` JSON shape as Claude Desktop, Claude Code, and Cursor. Each server entry produces one [`MCPToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset), wrapped in a [`PrefixedToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.PrefixedToolset) using the server's name as prefix to disambiguate tools across multiple servers.

Environment variables can be referenced in the configuration file using:

-   `${VAR_NAME}` syntax -- expands to the value of `VAR_NAME`, raises if not defined
-   `${VAR_NAME:-default}` syntax -- expands to `VAR_NAME` if set, otherwise the default

#### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- A list of toolsets, one per server in the config file, each prefixed with the server name.

#### Parameters

**`config_path`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `Path`

Path to the JSON configuration file.

#### Raises

-   `OSError` -- If the configuration file does not exist (`FileNotFoundError`), or exists but cannot be read -- a directory, or a file without read permission.
-   `ValidationError` -- If the configuration does not match the `mcpServers` shape above. This is a `ValueError` subclass, so catching `ValueError` covers it too.
-   `ValueError` -- If the file is not valid JSON, a server entry has neither `command` nor `url`, or an environment variable referenced in the configuration is not defined and no default is provided.

### ContentBlock

A content block that can be used in prompts and tool results.

**Default:** `messages.TextContent | messages.BinaryContent | ResourceLink | EmbeddedResource`

### ToolResult

The result type of an MCP tool call.

**Default:** `str | messages.BinaryContent | dict[str, Any] | list[Any] | Sequence[str | messages.BinaryContent | dict[str, Any] | list[Any]]`

### ProcessToolCallback

A process tool callback.

It accepts a run context, the original tool call function, a tool name, and arguments.

Allows wrapping an MCP server tool call to customize it, including adding extra request metadata.

**Default:** `Callable[[RunContext[Any], CallToolFunc, str, dict[str, Any]], Awaitable[ToolResult]]`

### MCPToolsetClient

Anything `MCPToolset` accepts as its `client` argument -- a pre-built `fastmcp.Client`, a FastMCP `ClientTransport`, an in-process `FastMCP` server, an `AnyUrl`/URL string, a script `Path`, or a URL/path/script string.

For multi-server JSON config files, use [`load_mcp_toolsets`](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.load_mcp_toolsets) instead -- it expands env vars and constructs one `MCPToolset` per server entry.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `FastMCPClient[Any] | ClientTransport | FastMCP | FastMCP1Server | AnyUrl | Path | str`

---
