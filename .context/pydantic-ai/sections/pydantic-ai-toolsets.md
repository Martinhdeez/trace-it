# [pydantic_ai.toolsets](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/)

# pydantic\_ai.toolsets

### AbstractToolset

**Bases:** `ABC`, `Generic[AgentDepsT]`

A toolset is a collection of tools that can be used by an agent.

It is responsible for:

-   Listing the tools it contains
-   Validating the arguments of the tools
-   Calling the tools

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/) for more information.

#### Attributes

##### id

An ID for the toolset that is unique among all toolsets registered with the same agent.

If you're implementing a concrete implementation that users can instantiate more than once, you should let them optionally pass a custom ID to the constructor and return that here.

A toolset needs to have an ID in order to be used in a durable execution environment like Temporal, in which case the ID will be used to identify the toolset's activities within the workflow.

IDs wrapped in angle brackets (`'<agent>'` for an agent's own function toolset, `'<output>'` for its output tools) name a role the framework fills on the user's behalf rather than a registered toolset. Don't return one from your own toolset.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### label

The name of the toolset for use in error messages.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### tool\_name\_conflict\_hint

A hint for how to avoid name conflicts with other toolsets for use in error messages.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### for\_run

`@async`

```python
def for_run(ctx: RunContext[AgentDepsT]) -> AbstractToolset[AgentDepsT]
```

Return the toolset to use for this agent run.

Called once per run, before `__aenter__`. Override this to return a fresh instance for per-run state isolation. Default: return `self` (shared across runs).

###### Returns

[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]

##### for\_run\_step

`@async`

```python
def for_run_step(ctx: RunContext[AgentDepsT]) -> AbstractToolset[AgentDepsT]
```

Return the toolset to use for this run step.

Called at the start of each run step. Override this to return a modified instance for per-step state transitions. If returning a new instance, you are responsible for managing any lifecycle transitions (exiting old inner toolsets, entering new ones). Default: return `self` (no per-step changes).

###### Returns

[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]

##### \_\_aenter\_\_

`@async`

```python
def __aenter__() -> Self
```

Enter the toolset context.

This is where you can set up network connections in a concrete implementation.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self)

##### \_\_aexit\_\_

`@async`

```python
def __aexit__(*args: Any) -> bool | None
```

Exit the toolset context.

This is where you can tear down network connections in a concrete implementation.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_instructions

`@async`

```python
def get_instructions(
    ctx: RunContext[AgentDepsT],
) -> str | InstructionPart | Sequence[str | InstructionPart] | None
```

Return instructions for how to use this toolset's tools.

Override this method to provide instructions that help the agent understand how to use the tools in this toolset effectively.

Simple implementations can return a plain `str`; advanced implementations can return [`InstructionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart) objects to indicate whether each instruction part is static or dynamic for caching purposes.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`InstructionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`InstructionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- Instruction string, `InstructionPart`, list of either, or `None`. [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`InstructionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`InstructionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- Plain `str` values are treated as dynamic instructions by default.

###### Parameters

**`ctx`** : [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]

The run context for this agent run.

##### get\_tools

`@abstractmethod`

`@async`

```python
def get_tools(ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]
```

The tools that are available in this toolset.

###### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`ToolsetTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.ToolsetTool)\[`AgentDepsT`\]\]

##### call\_tool

`@abstractmethod`

`@async`

```python
def call_tool(
    name: str,
    tool_args: dict[str, Any],
    ctx: RunContext[AgentDepsT],
    tool: ToolsetTool[AgentDepsT],
) -> Any
```

Call a tool with the given arguments.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The name of the tool to call.

**`tool_args`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

The arguments to pass to the tool.

**`ctx`** : [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]

The run context.

**`tool`** : [`ToolsetTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.ToolsetTool)\[`AgentDepsT`\]

The tool definition returned by [`get_tools`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset.get_tools) that was called.

##### apply

```python
def apply(visitor: Callable[[AbstractToolset[AgentDepsT]], None]) -> None
```

Run a visitor function on all "leaf" toolsets (i.e. those that implement their own tool listing and calling).

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### visit\_and\_replace

```python
def visit_and_replace(
    visitor: Callable[[AbstractToolset[AgentDepsT]], AbstractToolset[AgentDepsT]],
) -> AbstractToolset[AgentDepsT]
```

Run a visitor function on all "leaf" toolsets (i.e. those that implement their own tool listing and calling) and replace them in the hierarchy with the result of the function.

###### Returns

[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]

##### filtered

```python
def filtered(
    filter_func: Callable[[RunContext[AgentDepsT], ToolDefinition], bool | Awaitable[bool]],
) -> FilteredToolset[AgentDepsT]
```

Returns a new toolset that filters this toolset's tools using a filter function that takes the agent context and the tool definition.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#filtering-tools) for more information.

###### Returns

[`FilteredToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.FilteredToolset)\[`AgentDepsT`\]

##### prefixed

```python
def prefixed(prefix: str) -> PrefixedToolset[AgentDepsT]
```

Returns a new toolset that prefixes the names of this toolset's tools.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#prefixing-tool-names) for more information.

###### Returns

[`PrefixedToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.PrefixedToolset)\[`AgentDepsT`\]

##### prepared

```python
def prepared(prepare_func: ToolsPrepareFunc[AgentDepsT]) -> PreparedToolset[AgentDepsT]
```

Returns a new toolset that prepares this toolset's tools using a prepare function that takes the agent context and the original tool definitions.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#preparing-tool-definitions) for more information.

###### Returns

[`PreparedToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.PreparedToolset)\[`AgentDepsT`\]

##### renamed

```python
def renamed(name_map: dict[str, str]) -> RenamedToolset[AgentDepsT]
```

Returns a new toolset that renames this toolset's tools using a dictionary mapping new names to original names.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#renaming-tools) for more information.

###### Returns

[`RenamedToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.RenamedToolset)\[`AgentDepsT`\]

##### approval\_required

```python
def approval_required(
    approval_required_func: Callable[[RunContext[AgentDepsT], ToolDefinition, dict[str, Any]], bool] = lambda ctx, tool_def, tool_args: True,
) -> ApprovalRequiredToolset[AgentDepsT]
```

Returns a new toolset that requires (some) calls to tools it contains to be approved.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#requiring-tool-approval) for more information.

###### Returns

[`ApprovalRequiredToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.ApprovalRequiredToolset)\[`AgentDepsT`\]

##### defer\_loading

```python
def defer_loading(
    tool_names: Sequence[str] | None = None,
) -> DeferredLoadingToolset[AgentDepsT]
```

Returns a new toolset that marks tools for deferred loading, hiding them until revealed.

Tool search, `load_capability` and another tool's `ToolReturn.tools` all reveal.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#deferred-loading) for more information.

###### Returns

[`DeferredLoadingToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.DeferredLoadingToolset)\[`AgentDepsT`\]

###### Parameters

**`tool_names`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional sequence of tool names to mark for deferred loading. If `None`, all tools are marked for deferred loading.

##### include\_return\_schemas

```python
def include_return_schemas() -> IncludeReturnSchemasToolset[AgentDepsT]
```

Returns a new toolset that sets `include_return_schema=True` on all tools.

This causes the model to receive return type information for the tools in this toolset. For models that natively support return schemas (e.g. Google Gemini), the schema is passed as a structured field. For other models, it is injected into the tool description as JSON text.

This is the toolset-level equivalent of the [`IncludeToolReturnSchemas`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.IncludeToolReturnSchemas) capability, which can be used to enable return schemas across all toolsets or a subset matched by a [`ToolSelector`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolSelector).

###### Returns

[`IncludeReturnSchemasToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.IncludeReturnSchemasToolset)\[`AgentDepsT`\]

##### with\_metadata

```python
def with_metadata(**metadata: Any) -> SetMetadataToolset[AgentDepsT]
```

Returns a new toolset that merges the given metadata onto all tools.

###### Returns

[`SetMetadataToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.SetMetadataToolset)\[`AgentDepsT`\]

### ToolsetTool

**Bases:** `Generic[AgentDepsT]`

Definition of a tool available on a toolset.

This is a wrapper around a plain tool definition that includes information about:

-   the toolset that provided it, for use in error messages
-   the maximum number of retries to attempt if the tool call fails
-   the validator for the tool's arguments

#### Attributes

##### toolset

The toolset that provided this tool, for use in error messages.

**Type:** [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]

##### tool\_def

The tool definition for this tool, including the name, description, and parameters.

**Type:** [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition)

##### max\_retries

The maximum number of retries to attempt if the tool call fails.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### args\_validator

The Pydantic Core validator for the tool's arguments.

For example, a [`pydantic.TypeAdapter(...).validator`](https://docs.pydantic.dev/latest/concepts/type_adapter/) or [`pydantic_core.SchemaValidator`](https://docs.pydantic.dev/latest/api/pydantic_core/#pydantic_core.SchemaValidator).

**Type:** `SchemaValidator` | `SchemaValidatorProt`

##### args\_validator\_func

Custom args validator function that runs after schema validation but before tool execution.

Called on every tool call, receiving the schema-validated arguments as keyword args. The function should have the same typed parameters as the tool function, with `RunContext` as the first argument. Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to ask the model to correct the arguments and try again, or [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed) to report a terminal failure the model should adapt to instead of retrying. Return `None` on success.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[..., [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### CombinedToolset

**Bases:** `AbstractToolset[AgentDepsT]`

A toolset that combines multiple toolsets.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#combining-toolsets) for more information.

### ExternalToolset

**Bases:** `AbstractToolset[AgentDepsT]`

A toolset that holds tools whose results will be produced outside of the Pydantic AI agent run in which they were called.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#external-toolset) for more information.

### ApprovalRequiredToolset

**Bases:** `WrapperToolset[AgentDepsT]`

A toolset that requires (some) calls to tools it contains to be approved.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#requiring-tool-approval) for more information.

### FilteredToolset

**Bases:** `WrapperToolset[AgentDepsT]`

A toolset that filters the tools it contains using a filter function that takes the agent context and the tool definition.

Both sync and async filter functions are accepted.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#filtering-tools) for more information.

### FunctionToolset

**Bases:** `AbstractToolset[AgentDepsT]`

A toolset that lets Python functions be used as tools.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#function-toolset) for more information.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    tools: Sequence[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]] = [],
    *,
    max_retries: int | None = None,
    timeout: float | None = None,
    docstring_format: DocstringFormat = 'auto',
    require_parameter_descriptions: bool = False,
    schema_generator: type[GenerateJsonSchema] = GenerateToolJsonSchema,
    strict: bool | None = None,
    sequential: bool = False,
    requires_approval: bool = False,
    metadata: dict[str, Any] | None = None,
    defer_loading: bool = False,
    include_return_schema: bool | None = None,
    id: str | None = None,
    instructions: AgentInstructions[AgentDepsT] = None,
)
```

Build a new function toolset.

###### Parameters

**`tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\] | `ToolFuncEither`\[`AgentDepsT`, ...\]\] _Default:_ `[]`

The tools to add to the toolset.

**`max_retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The maximum number of retries for each tool during a run. If `None`, inherits the agent's default retry count at runtime. Applies to all tools, unless overridden when adding a tool.

**`timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Timeout in seconds for tool execution. If a tool takes longer than this, a retry prompt is returned to the model. Individual tools can override this with their own timeout. Defaults to None (no timeout).

**`docstring_format`** : `DocstringFormat` _Default:_ `'auto'`

Format of tool docstring, see [`DocstringFormat`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DocstringFormat). Defaults to `'auto'`, such that the format is inferred from the structure of the docstring. Applies to all tools, unless overridden when adding a tool.

**`require_parameter_descriptions`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

If True, raise an error if a parameter description is missing. Defaults to False. Applies to all tools, unless overridden when adding a tool.

**`schema_generator`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`GenerateJsonSchema`\] _Default:_ `GenerateToolJsonSchema`

The JSON schema generator class to use for this tool. Defaults to `GenerateToolJsonSchema`. Applies to all tools, unless overridden when adding a tool.

**`strict`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to enforce (vendor-specific) strict schema adherence for tool calls (supported by OpenAI, Anthropic, Google, and Bedrock). See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info.

**`sequential`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether this tool acts as a barrier that runs alone, not overlapping with other tool calls. See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info. Defaults to False. Applies to all tools, unless overridden when adding a tool.

**`requires_approval`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether this tool requires human-in-the-loop approval. Defaults to False. See the [tools documentation](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval) for more info. Applies to all tools, unless overridden when adding a tool.

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization. Applies to all tools, unless overridden when adding a tool, which will be merged with the toolset's metadata.

**`defer_loading`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether to hide tools from the model until they're revealed by tool search, `load_capability`, or another tool's `ToolReturn.tools`. See [Tool Search](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#tool-search) for more info. Applies to all tools, unless overridden when adding a tool.

**`include_return_schema`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to include return schemas in tool definitions sent to the model. If `None`, defaults to `False` unless the [`IncludeToolReturnSchemas`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.IncludeToolReturnSchemas) capability is used. Applies to all tools, unless overridden when adding a tool.

**`id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An optional unique ID for the toolset. A toolset needs to have an ID in order to be used in a durable execution environment like Temporal, in which case the ID will be used to identify the toolset's activities within the workflow.

**`instructions`** : `AgentInstructions`\[`AgentDepsT`\] _Default:_ `None`

Instructions for this toolset that are automatically included in the model request. Can be a string, an [`InstructionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart) declaring the part's [`name`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart.name) and whether it is [`dynamic`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart.dynamic), a function (sync or async, with or without `RunContext`), or a sequence of these.

##### tool

```python
def tool(
    func: ToolFuncContext[AgentDepsT, ToolParams],
    /,
) -> ToolFuncContext[AgentDepsT, ToolParams]
def tool(
    *,
    name: str | None = None,
    description: str | None = None,
    retries: int | None = None,
    prepare: ToolPrepareFunc[AgentDepsT] | None = None,
    args_validator: ArgsValidatorFunc[AgentDepsT, ToolParams] | None = None,
    docstring_format: DocstringFormat | None = None,
    require_parameter_descriptions: bool | None = None,
    schema_generator: type[GenerateJsonSchema] | None = None,
    strict: bool | None = None,
    sequential: bool | None = None,
    requires_approval: bool | None = None,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
    defer_loading: bool | None = None,
    include_return_schema: bool | None = None,
) -> Callable[[ToolFuncContext[AgentDepsT, ToolParams]], ToolFuncContext[AgentDepsT, ToolParams]]
```

Decorator to register a tool function which takes [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) as its first argument.

Can decorate a sync or async functions.

The docstring is inspected to extract both the tool description and description of each parameter, [learn more](https://pydantic.dev/docs/ai/tools-toolsets/tools/#function-tools-and-schema).

We can't add overloads for every possible signature of tool, since the return type is a recursive union so the signature of functions decorated with `@toolset.tool` is obscured.

Example:

```python
from pydantic_ai import Agent, FunctionToolset, RunContext

toolset = FunctionToolset()

@toolset.tool
def foobar(ctx: RunContext[int], x: int) -> int:
    return ctx.deps + x

@toolset.tool(retries=2)
async def spam(ctx: RunContext[str], y: float) -> float:
    return ctx.deps + y

agent = Agent('test', toolsets=[toolset], deps_type=int)
result = agent.run_sync('foobar', deps=1)
print(result.output)
#> {"foobar":1,"spam":1.0}
```

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

###### Parameters

**`func`** : `ToolFuncContext`\[`AgentDepsT`, `ToolParams`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The tool function to register.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The name of the tool, defaults to the function name.

**`description`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The description of the tool,defaults to the function docstring.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The number of retries to allow for this tool, defaults to the agent's default retries, which defaults to 1.

**`prepare`** : `ToolPrepareFunc`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to prepare the tool definition for each step, return `None` to omit this tool from a given step. This is useful if you want to customise a tool at call time, or omit it completely from a step. See [`ToolPrepareFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolPrepareFunc).

**`args_validator`** : `ArgsValidatorFunc`\[`AgentDepsT`, `ToolParams`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to validate tool arguments after schema validation has passed, before execution. The validator receives the already-validated and type-converted parameters, with `RunContext` as the first argument. Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to ask the model to correct the arguments and try again, or [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed) to report a terminal failure the model should adapt to instead of retrying. Return `None` on success. See [`ArgsValidatorFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ArgsValidatorFunc).

**`docstring_format`** : `DocstringFormat` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The format of the docstring, see [`DocstringFormat`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DocstringFormat). If `None`, the default value is determined by the toolset.

**`require_parameter_descriptions`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

If True, raise an error if a parameter description is missing. If `None`, the default value is determined by the toolset.

**`schema_generator`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`GenerateJsonSchema`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The JSON schema generator class to use for this tool. If `None`, the default value is determined by the toolset.

**`strict`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to enforce (vendor-specific) strict schema adherence for tool calls (supported by OpenAI, Anthropic, Google, and Bedrock). See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info. If `None`, the default value is determined by the toolset.

**`sequential`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether this tool acts as a barrier that runs alone, not overlapping with other tool calls. See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info. Defaults to False. If `None`, the default value is determined by the toolset.

**`requires_approval`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether this tool requires human-in-the-loop approval. Defaults to False. See the [tools documentation](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval) for more info. If `None`, the default value is determined by the toolset.

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization. If `None`, the default value is determined by the toolset. If provided, it will be merged with the toolset's metadata.

**`timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model. Defaults to None (no timeout).

**`defer_loading`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to hide this tool until it's revealed by tool search, `load_capability`, or another tool's `ToolReturn.tools`. See [Tool Search](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#tool-search) for more info. If `None`, the default value is determined by the toolset.

**`include_return_schema`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to include the return schema in the tool definition sent to the model. If `None`, the default value is determined by the toolset.

##### tool\_plain

```python
def tool_plain(func: ToolFuncPlain[ToolParams], /) -> ToolFuncPlain[ToolParams]
def tool_plain(
    *,
    name: str | None = None,
    description: str | None = None,
    retries: int | None = None,
    prepare: ToolPrepareFunc[AgentDepsT] | None = None,
    args_validator: ArgsValidatorFunc[AgentDepsT, ToolParams] | None = None,
    docstring_format: DocstringFormat | None = None,
    require_parameter_descriptions: bool | None = None,
    schema_generator: type[GenerateJsonSchema] | None = None,
    strict: bool | None = None,
    sequential: bool | None = None,
    requires_approval: bool | None = None,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
    defer_loading: bool | None = None,
    include_return_schema: bool | None = None,
) -> Callable[[ToolFuncPlain[ToolParams]], ToolFuncPlain[ToolParams]]
```

Decorator to register a tool function which DOES NOT take `RunContext` as an argument.

Can decorate a sync or async functions.

The docstring is inspected to extract both the tool description and description of each parameter, [learn more](https://pydantic.dev/docs/ai/tools-toolsets/tools/#function-tools-and-schema).

We can't add overloads for every possible signature of tool, since the return type is a recursive union so the signature of functions decorated with `@toolset.tool_plain` is obscured.

Example:

```python
from pydantic_ai import Agent, FunctionToolset

toolset = FunctionToolset()

@toolset.tool_plain
def foobar(x: int) -> int:
    return x + 1

@toolset.tool_plain(retries=2)
async def spam(y: float) -> float:
    return y * 2.0

agent = Agent('test', toolsets=[toolset])
result = agent.run_sync('foobar')
print(result.output)
#> {"foobar":1,"spam":0.0}
```

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

###### Parameters

**`func`** : `ToolFuncPlain`\[`ToolParams`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The tool function to register.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The name of the tool, defaults to the function name.

**`description`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The description of the tool, defaults to the function docstring.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The number of retries to allow for this tool, defaults to the toolset's default retries, which defaults to the agent's default.

**`prepare`** : `ToolPrepareFunc`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to prepare the tool definition for each step, return `None` to omit this tool from a given step. This is useful if you want to customise a tool at call time, or omit it completely from a step. See [`ToolPrepareFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolPrepareFunc).

**`args_validator`** : `ArgsValidatorFunc`\[`AgentDepsT`, `ToolParams`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to validate tool arguments after schema validation has passed, before execution. The validator receives the already-validated and type-converted parameters, with [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) as the first argument -- even though the tool function itself does not take `RunContext` when using `tool_plain`. Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to ask the model to correct the arguments and try again, or [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed) to report a terminal failure the model should adapt to instead of retrying. Return `None` on success. See [`ArgsValidatorFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ArgsValidatorFunc).

**`docstring_format`** : `DocstringFormat` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The format of the docstring, see [`DocstringFormat`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DocstringFormat). If `None`, the default value is determined by the toolset.

**`require_parameter_descriptions`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

If True, raise an error if a parameter description is missing. If `None`, the default value is determined by the toolset.

**`schema_generator`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`GenerateJsonSchema`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The JSON schema generator class to use for this tool. If `None`, the default value is determined by the toolset.

**`strict`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to enforce (vendor-specific) strict schema adherence for tool calls (supported by OpenAI, Anthropic, Google, and Bedrock). See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info. If `None`, the default value is determined by the toolset.

**`sequential`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether this tool acts as a barrier that runs alone, not overlapping with other tool calls. See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info. Defaults to False. If `None`, the default value is determined by the toolset.

**`requires_approval`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether this tool requires human-in-the-loop approval. Defaults to False. See the [tools documentation](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval) for more info. If `None`, the default value is determined by the toolset.

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization. If `None`, the default value is determined by the toolset. If provided, it will be merged with the toolset's metadata.

**`timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model. Defaults to None (no timeout).

**`defer_loading`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to hide this tool until it's revealed by tool search, `load_capability`, or another tool's `ToolReturn.tools`. See [Tool Search](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#tool-search) for more info. If `None`, the default value is determined by the toolset.

**`include_return_schema`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to include the return schema in the tool definition sent to the model. If `None`, the default value is determined by the toolset.

##### instructions

```python
def instructions(func: SystemPromptFunc[AgentDepsT], /) -> SystemPromptFunc[AgentDepsT]
```

Decorator to register an instructions function for this toolset.

The function can be sync or async, and can optionally take a [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) as its first argument.

Example:

```python
from pydantic_ai import FunctionToolset, RunContext

toolset = FunctionToolset[int]()

@toolset.instructions
def my_instructions(ctx: RunContext[int]) -> str:
    return 'Always use the search tool when looking for information.'

@toolset.tool
def search(ctx: RunContext[int], query: str) -> str:
    return f'Results for: {query}'
```

###### Returns

`SystemPromptFunc`\[`AgentDepsT`\]

###### Parameters

**`func`** : `SystemPromptFunc`\[`AgentDepsT`\]

The instructions function to register.

##### add\_function

```python
def add_function(
    func: ToolFuncEither[AgentDepsT, ToolParams],
    takes_ctx: bool | None = None,
    name: str | None = None,
    description: str | None = None,
    retries: int | None = None,
    prepare: ToolPrepareFunc[AgentDepsT] | None = None,
    args_validator: ArgsValidatorFunc[AgentDepsT, ToolParams] | None = None,
    docstring_format: DocstringFormat | None = None,
    require_parameter_descriptions: bool | None = None,
    schema_generator: type[GenerateJsonSchema] | None = None,
    strict: bool | None = None,
    sequential: bool | None = None,
    requires_approval: bool | None = None,
    defer_loading: bool | None = None,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
    include_return_schema: bool | None = None,
) -> Tool[AgentDepsT]
```

Add a function as a tool to the toolset.

Can take a sync or async function.

The docstring is inspected to extract both the tool description and description of each parameter, [learn more](https://pydantic.dev/docs/ai/tools-toolsets/tools/#function-tools-and-schema).

###### Returns

[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\]

###### Parameters

**`func`** : `ToolFuncEither`\[`AgentDepsT`, `ToolParams`\]

The tool function to register.

**`takes_ctx`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether the function takes a [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) as its first argument. If `None`, this is inferred from the function signature.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The name of the tool, defaults to the function name.

**`description`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The description of the tool, defaults to the function docstring.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The number of retries to allow for this tool, defaults to the agent's default retries, which defaults to 1.

**`prepare`** : `ToolPrepareFunc`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to prepare the tool definition for each step, return `None` to omit this tool from a given step. This is useful if you want to customise a tool at call time, or omit it completely from a step. See [`ToolPrepareFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolPrepareFunc).

**`args_validator`** : `ArgsValidatorFunc`\[`AgentDepsT`, `ToolParams`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to validate tool arguments after schema validation has passed, before execution. The validator receives the already-validated and type-converted parameters, with `RunContext` as the first argument. Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to ask the model to correct the arguments and try again, or [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed) to report a terminal failure the model should adapt to instead of retrying. Return `None` on success. See [`ArgsValidatorFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ArgsValidatorFunc).

**`docstring_format`** : `DocstringFormat` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The format of the docstring, see [`DocstringFormat`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DocstringFormat). If `None`, the default value is determined by the toolset.

**`require_parameter_descriptions`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

If True, raise an error if a parameter description is missing. If `None`, the default value is determined by the toolset.

**`schema_generator`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`GenerateJsonSchema`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The JSON schema generator class to use for this tool. If `None`, the default value is determined by the toolset.

**`strict`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to enforce (vendor-specific) strict schema adherence for tool calls (supported by OpenAI, Anthropic, Google, and Bedrock). See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info. If `None`, the default value is determined by the toolset.

**`sequential`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether this tool acts as a barrier that runs alone, not overlapping with other tool calls. See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info. Defaults to False. If `None`, the default value is determined by the toolset.

**`requires_approval`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether this tool requires human-in-the-loop approval. Defaults to False. See the [tools documentation](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval) for more info. If `None`, the default value is determined by the toolset.

**`defer_loading`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to hide this tool until it's revealed by tool search, `load_capability`, or another tool's `ToolReturn.tools`. See [Tool Search](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#tool-search) for more info. If `None`, the default value is determined by the toolset.

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization. If `None`, the default value is determined by the toolset. If provided, it will be merged with the toolset's metadata.

**`timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model. Defaults to None (no timeout).

**`include_return_schema`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to include the return schema in the tool definition sent to the model. If `None`, the default value is determined by the toolset.

##### add\_tool

```python
def add_tool(tool: Tool[AgentDepsT]) -> None
```

Add a tool to the toolset.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`tool`** : [`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\]

The tool to add.

##### tool\_for\_tool\_def

```python
def tool_for_tool_def(
    tool_def: ToolDefinition,
    *,
    ctx: RunContext[AgentDepsT],
    original_name: str | None = None,
) -> FunctionToolsetTool[AgentDepsT]
```

Build the tool to call for a tool definition that was already prepared elsewhere.

Used by [durable execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/) to rebuild the tool inside the durable unit (e.g. a Temporal activity) from the tool definition that [`get_tools()`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset.get_tools) produced outside it, instead of running the tool's `prepare` function a second time against a different run context.

###### Returns

`FunctionToolsetTool`\[`AgentDepsT`\]

###### Parameters

**`tool_def`** : [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition)

The prepared tool definition to build the tool from.

**`ctx`** : [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]

The run context used to resolve the tool's retry budget.

**`original_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The name this toolset holds the tool under, from the built tool's `original_name`. Defaults to `tool_def.name`, which is only the same when no `prepare` function renamed the tool. This is specific to `FunctionToolset` because per-tool preparation runs inside its own `get_tools()` and can change the exposed name without changing the key in `tools`.

###### Raises

-   `KeyError` -- If the toolset holds no tool under that name.

### IncludeReturnSchemasToolset

**Bases:** `PreparedToolset[AgentDepsT]`

A toolset that sets `include_return_schema=True` on all its tools.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/) for more information.

### DeferredLoadingToolset

**Bases:** `PreparedToolset[AgentDepsT]`

A toolset that marks tools for deferred loading, hiding them from the model until revealed.

Tool search, `load_capability` and another tool's `ToolReturn.tools` all reveal.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#deferred-loading) for more information.

#### Attributes

##### tool\_names

Optional set of tool names to mark for deferred loading. If `None`, all tools are marked for deferred loading.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `tool_names`

### DynamicToolset

**Bases:** `AbstractToolset[AgentDepsT]`

A toolset that dynamically builds a toolset using a function that takes the run context.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    toolset_func: ToolsetFunc[AgentDepsT],
    *,
    per_run_step: bool = True,
    id: str | None = None,
)
```

Build a new dynamic toolset.

###### Parameters

**`toolset_func`** : [`ToolsetFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.ToolsetFunc)\[`AgentDepsT`\]

A function that takes the run context and returns a toolset or None.

**`per_run_step`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to re-evaluate the toolset for each run step.

**`id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An optional unique ID for the toolset. Required for durable execution environments like Temporal.

##### for\_run

`@async`

```python
def for_run(ctx: RunContext[AgentDepsT]) -> AbstractToolset[AgentDepsT]
```

Create a per-run copy with the factory evaluated.

For `per_run_step=False`, evaluates the factory now (only chance). For `per_run_step=True`, defers factory evaluation to `for_run_step`.

###### Returns

[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]

##### for\_run\_step

`@async`

```python
def for_run_step(ctx: RunContext[AgentDepsT]) -> AbstractToolset[AgentDepsT]
```

If per\_run\_step, re-evaluate factory and manage transitions in-place.

Handles the inner toolset lifecycle (exiting old, entering new) and returns self.

###### Returns

[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]

### PrefixedToolset

**Bases:** `WrapperToolset[AgentDepsT]`

A toolset that prefixes the names of the tools it contains.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#prefixing-tool-names) for more information.

### RenamedToolset

**Bases:** `WrapperToolset[AgentDepsT]`

A toolset that renames the tools it contains using a dictionary mapping new names to original names.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#renaming-tools) for more information.

### SetMetadataToolset

**Bases:** `PreparedToolset[AgentDepsT]`

A toolset that merges metadata key-value pairs onto all its tools.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/) for more information.

### PreparedToolset

**Bases:** `WrapperToolset[AgentDepsT]`

A toolset that prepares the tools it contains using a prepare function that takes the agent context and the original tool definitions.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#preparing-tool-definitions) for more information.

### WrapperToolset

**Bases:** `AbstractToolset[AgentDepsT]`

A toolset that wraps another toolset and delegates to it.

See [toolset docs](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#changing-tool-execution) for more information.

#### Methods

##### get\_instructions

`@async`

```python
def get_instructions(
    ctx: RunContext[AgentDepsT],
) -> str | InstructionPart | Sequence[str | InstructionPart] | None
```

Collect instructions from the wrapped authoring toolset.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`InstructionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`InstructionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### ToolsetFunc

A sync/async function which takes a run context and returns a toolset.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[RunContext[AgentDepsT]], AbstractToolset[AgentDepsT] | None | Awaitable[AbstractToolset[AgentDepsT] | None]]`

### AgentToolset

A toolset or a factory function that creates a toolset from a run context.

**Default:** `Union[AbstractToolset[AgentDepsT], ToolsetFunc[AgentDepsT]]`

---
