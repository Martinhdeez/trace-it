# [pydantic_ai.agent](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/)

# pydantic\_ai.agent

### Agent

**Bases:** `AbstractAgent[AgentDepsT, OutputDataT]`

Class for defining "agents" - a way to have a specific type of "conversation" with an LLM.

Agents are generic in the dependency type they take [`AgentDepsT`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.AgentDepsT) and the output type they return, [`OutputDataT`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.OutputDataT).

By default, if neither generic parameter is customised, agents have type `Agent[object, str]`.

Minimal usage example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')
result = agent.run_sync('What is the capital of France?')
print(result.output)
#> The capital of France is Paris.
```

#### Attributes

##### end\_strategy

The strategy for handling function tool calls the model requests alongside a result that ends the run.

That result usually comes from an output tool call, but with `NativeOutput`, `PromptedOutput`, or image output it comes from the structured text or image the model returns in the same response. Plain, unstructured text (`str` or `TextOutput`) is not treated as such a result: since the model isn't told its text is final, `end_strategy` never skips tools on its account, even under `'early'`.

Defaults to `'graceful'`. See [`EndStrategy`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.EndStrategy) for the behavior of each strategy.

**Type:** [`EndStrategy`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.EndStrategy) **Default:** `end_strategy`

##### model\_settings

Optional model request settings to use for this agent's runs, by default.

Can be a static `ModelSettings` dict or a callable that takes a [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) and returns `ModelSettings`. Callables are called before each model request, allowing dynamic per-step settings.

Note, if `model_settings` is also provided at run time, those settings will be merged on top of the agent-level settings, with the run-level argument taking priority.

**Type:** [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `model_settings`

##### instrument

Instrumentation settings applied to this agent.

**Type:** [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### model

The default model configured for this agent.

**Type:** [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### name

The name of the agent, used for logging.

If `None`, we try to infer the agent name from the call frame when the agent is first run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### description

A human-readable description of the agent.

If the description is a TemplateStr, returns the raw template source. The rendered description is available at runtime via OTel span attributes.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### deps\_type

The type of dependencies used by the agent.

**Type:** [`type`](https://docs.python.org/3/glossary.html#term-type)

##### output\_type

The type of data output by agent runs, used to validate the data returned by the model, defaults to `str`.

**Type:** `OutputSpec`\[`OutputDataT`\]

##### event\_stream\_handler

Optional handler for events from the model's streaming response and the agent's execution of tools.

**Type:** `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### validation\_context

The Pydantic validation context used to validate tool arguments and outputs.

Set this when validators need values from [`ValidationInfo.context`](https://docs.pydantic.dev/latest/api/pydantic-core/pydantic_core_schema/#pydantic_core.core_schema.ValidationInfo.context). A callable can build the context from the current [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext).

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]\], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### root\_capability

The root capability of the agent, containing all registered capabilities.

**Type:** `CombinedCapability`\[`AgentDepsT`\]

##### toolsets

All toolsets registered on the agent, including a function toolset holding tools that were registered on the agent directly.

Output tools are not included.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\]

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model: models.Model | models.KnownModelName | str | None = None,
    *,
    output_type: OutputSpec[OutputDataT] = str,
    instructions: AgentInstructions[AgentDepsT] = None,
    system_prompt: str | Sequence[str] = (),
    deps_type: type[AgentDepsT] = object,
    name: str | None = None,
    description: TemplateStr[AgentDepsT] | str | None = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    validation_context: Any | Callable[[RunContext[AgentDepsT]], Any] = None,
    tools: Sequence[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]] = (),
    toolsets: Sequence[AgentToolset[AgentDepsT]] | None = None,
    defer_model_check: bool = False,
    end_strategy: EndStrategy = 'graceful',
    metadata: AgentMetadata[AgentDepsT] | None = None,
    tool_timeout: float | None = None,
    max_concurrency: _concurrency.AnyConcurrencyLimit = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
) -> None
def __init__(
    model: models.Model | models.KnownModelName | str | None = None,
    *,
    output_type: OutputSpec[OutputDataT] = str,
    instructions: AgentInstructions[AgentDepsT] = None,
    system_prompt: str | Sequence[str] = (),
    deps_type: type[AgentDepsT] = object,
    name: str | None = None,
    description: TemplateStr[AgentDepsT] | str | None = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    validation_context: Any | Callable[[RunContext[AgentDepsT]], Any] = None,
    tools: Sequence[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]] = (),
    toolsets: Sequence[AgentToolset[AgentDepsT]] | None = None,
    defer_model_check: bool = False,
    end_strategy: EndStrategy = 'graceful',
    metadata: AgentMetadata[AgentDepsT] | None = None,
    tool_timeout: float | None = None,
    max_concurrency: _concurrency.AnyConcurrencyLimit = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
) -> None
```

Create an agent.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The default model to use for this agent, if not provided, you must provide the model when calling it. We allow `str` here since the actual list of allowed models changes frequently.

**`output_type`** : `OutputSpec`\[`OutputDataT`\] _Default:_ `str`

The type of the output data, used to validate the data returned by the model, defaults to `str`.

**`instructions`** : `AgentInstructions`\[`AgentDepsT`\] _Default:_ `None`

Instructions to use for this agent, you can also register instructions via a function with [`instructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.instructions) or pass additional, temporary, instructions when executing a run.

**`system_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] _Default:_ `()`

Static system prompts to use for this agent, you can also register system prompts via a function with [`system_prompt`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.system_prompt).

**`deps_type`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`AgentDepsT`\] _Default:_ `object`

The type used for dependency injection, this parameter exists solely to allow you to fully parameterize the agent, and therefore get the best out of static type checking. If you're not using deps, but want type checking to pass, you can set `deps=None` to satisfy Pyright or add a type hint `: Agent[object, <return type>]`.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The name of the agent, used for logging. If `None`, we try to infer the agent name from the call frame when the agent is first run.

**`description`** : [`TemplateStr`](https://pydantic.dev/docs/ai/api/pydantic-ai/template/#pydantic_ai.template.TemplateStr)\[`AgentDepsT`\] | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A human-readable description of the agent, attached to the agent run span as `gen_ai.agent.description` when instrumentation is enabled.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model request settings to use for this agent's runs, by default. Can be a static `ModelSettings` dict or a callable that takes a [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) and returns `ModelSettings`. Callables are called before each model request, allowing dynamic per-step settings.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Per-category retry budgets for tools and output validation. Pass an `int` to set the same budget for both, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to set them individually (e.g. `retries={'tools': 3, 'output': 1}`). Defaults to 1 for both. On the text path, `output` is a global budget shared across all output-validation retries in a run; on the tool path it is the default per-tool `max_retries` for each output tool, overridable via [`ToolOutput(max_retries=...)`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.ToolOutput.max_retries). Both budgets can be overridden per run via `agent.run(retries=...)` (and friends), passing an `AgentRetries` dict (e.g. `retries={'tools': 3}`) for per-category control. For model request retries, see the [transport retries](https://pydantic.dev/docs/ai/core-concepts/retries/#transport-retries) documentation.

**`validation_context`** : [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]\], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] _Default:_ `None`

Pydantic [validation context](https://docs.pydantic.dev/latest/concepts/validators/#validation-context) used to validate tool arguments and outputs.

**`tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\] | `ToolFuncEither`\[`AgentDepsT`, ...\]\] _Default:_ `()`

Tools to register with the agent, you can also register tools via the decorators [`@agent.tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.tool) and [`@agent.tool_plain`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.tool_plain).

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AgentToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Toolsets to register with the agent, including MCP servers and functions which take a run context and return a toolset. See [`ToolsetFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.ToolsetFunc) for more information.

**`defer_model_check`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

by default, if you provide a [named](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) model, it's evaluated to create a [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) instance immediately, which checks for the necessary environment variables. Set this to `True` to defer the evaluation until the first run. Useful if you want to [override the model](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.override) for testing.

**`end_strategy`** : [`EndStrategy`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.EndStrategy) _Default:_ `'graceful'`

Strategy for handling tool calls that are requested alongside a final result. See [`EndStrategy`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.EndStrategy) for more information.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to store with each run. Provide a dictionary of primitives, or a callable returning one computed from the [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) on each run. Metadata is resolved when a run starts and recomputed after a successful run finishes so it can reflect the final state. Resolved metadata can be read after the run completes via [`AgentRun.metadata`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun), [`AgentRunResult.metadata`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult), and [`StreamedRunResult.metadata`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult), and is attached to the agent run span when instrumentation is enabled.

**`tool_timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Default timeout in seconds for tool execution. If a tool takes longer than this, the tool is considered to have failed and a retry prompt is returned to the model (counting towards the retry limit). Individual tools can override this with their own timeout. Defaults to None (no timeout).

**`max_concurrency`** : `_concurrency.AnyConcurrencyLimit` _Default:_ `None`

Optional limit on concurrent agent runs. Can be an integer for simple limiting, a [`ConcurrencyLimit`](https://pydantic.dev/docs/ai/api/pydantic-ai/concurrency/#pydantic_ai.ConcurrencyLimit) for advanced configuration with backpressure, a [`ConcurrencyLimiter`](https://pydantic.dev/docs/ai/api/pydantic-ai/concurrency/#pydantic_ai.ConcurrencyLimiter) for sharing limits across multiple agents, or None (default) for no limiting. When the limit is reached, additional calls to `run()` or `iter()` will wait until a slot becomes available.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional list of [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) to configure the agent with, including functions which take a run context and return a capability. See [`CapabilityFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.CapabilityFunc) for more information. Custom capabilities can be created by subclassing [`AbstractCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability).

##### from\_spec

`@classmethod`

```python
def from_spec(
    cls,
    spec: dict[str, Any] | AgentSpec,
    *,
    custom_capability_types: Sequence[type[AbstractCapability[Any]]] = (),
    model: models.Model | models.KnownModelName | str | None = None,
    output_type: OutputSpec[Any] = str,
    instructions: AgentInstructions[Any] = None,
    system_prompt: str | Sequence[str] = (),
    name: str | None = None,
    description: TemplateStr[Any] | str | None = None,
    model_settings: ModelSettings | None = None,
    retries: int | AgentRetries | None = None,
    validation_context: Any = None,
    tools: Sequence[Tool[Any] | ToolFuncEither[Any, ...]] = (),
    toolsets: Sequence[AgentToolset[Any]] | None = None,
    defer_model_check: bool = False,
    end_strategy: EndStrategy | None = None,
    metadata: AgentMetadata[Any] | None = None,
    tool_timeout: float | None = None,
    max_concurrency: _concurrency.AnyConcurrencyLimit = None,
    capabilities: Sequence[AgentCapability[Any]] | None = None,
) -> Agent[object, str]
def from_spec(
    cls,
    spec: dict[str, Any] | AgentSpec,
    *,
    deps_type: type[T],
    custom_capability_types: Sequence[type[AbstractCapability[Any]]] = (),
    model: models.Model | models.KnownModelName | str | None = None,
    output_type: OutputSpec[Any] = str,
    instructions: AgentInstructions[Any] = None,
    system_prompt: str | Sequence[str] = (),
    name: str | None = None,
    description: TemplateStr[Any] | str | None = None,
    model_settings: ModelSettings | None = None,
    retries: int | AgentRetries | None = None,
    validation_context: Any = None,
    tools: Sequence[Tool[Any] | ToolFuncEither[Any, ...]] = (),
    toolsets: Sequence[AgentToolset[Any]] | None = None,
    defer_model_check: bool = False,
    end_strategy: EndStrategy | None = None,
    metadata: AgentMetadata[Any] | None = None,
    tool_timeout: float | None = None,
    max_concurrency: _concurrency.AnyConcurrencyLimit = None,
    capabilities: Sequence[AgentCapability[Any]] | None = None,
) -> Agent[T, str]
```

Construct an Agent from a spec dict or `AgentSpec`.

This allows defining agents declaratively in YAML/JSON/dict form. Keyword arguments supplement the spec: scalar spec fields (like `name`, `retries`) are used as defaults that explicit arguments override, while `capabilities` from both sources are merged.

###### Returns

[`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- A new Agent instance.

###### Parameters

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec)

The agent specification, either a dict or an `AgentSpec` instance.

**`deps_type`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] _Default:_ `type(None)`

The type of the dependencies for the agent. When provided, template strings in capabilities (e.g. `"Hello {{name}}"`) are compiled and validated against this type.

**`custom_capability_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractCapability`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]\] _Default:_ `()`

Additional capability classes to make available beyond the built-in defaults.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the model from the spec.

**`output_type`** : `OutputSpec`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] _Default:_ `str`

The type of the output data, defaults to `str`.

**`instructions`** : `AgentInstructions`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] _Default:_ `None`

Instructions for the agent.

**`system_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] _Default:_ `()`

Static system prompts.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The agent name, overrides spec `name` if provided.

**`description`** : [`TemplateStr`](https://pydantic.dev/docs/ai/api/pydantic-ai/template/#pydantic_ai.template.TemplateStr)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The agent description, overrides spec `description` if provided.

**`model_settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model request settings.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Retry budgets for tools and output validation. Pass an `int` to set the same budget for both, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to set them individually. Overrides spec `retries` if provided.

**`validation_context`** : [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) _Default:_ `None`

Pydantic validation context for tool arguments and outputs.

**`tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | `ToolFuncEither`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any), ...\]\] _Default:_ `()`

Tools to register with the agent.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AgentToolset)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Toolsets to register with the agent.

**`defer_model_check`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Defer model evaluation until first run.

**`end_strategy`** : [`EndStrategy`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.EndStrategy) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Strategy for tool calls alongside a final result, overrides spec `end_strategy` if provided.

**`metadata`** : `AgentMetadata`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Metadata to store with each run, overrides spec `metadata` if provided.

**`tool_timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Default timeout for tool execution, overrides spec `tool_timeout` if provided.

**`max_concurrency`** : `_concurrency.AnyConcurrencyLimit` _Default:_ `None`

Limit on concurrent agent runs.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Additional capabilities merged with those from the spec.

##### from\_file

`@classmethod`

```python
def from_file(
    cls,
    path: Path | str,
    *,
    fmt: Literal['yaml', 'json'] | None = None,
    custom_capability_types: Sequence[type[AbstractCapability[Any]]] = (),
    model: models.Model | models.KnownModelName | str | None = None,
    output_type: OutputSpec[Any] = str,
    instructions: AgentInstructions[Any] = None,
    system_prompt: str | Sequence[str] = (),
    name: str | None = None,
    description: TemplateStr[Any] | str | None = None,
    model_settings: ModelSettings | None = None,
    retries: int | AgentRetries | None = None,
    validation_context: Any = None,
    tools: Sequence[Tool[Any] | ToolFuncEither[Any, ...]] = (),
    toolsets: Sequence[AgentToolset[Any]] | None = None,
    defer_model_check: bool = False,
    end_strategy: EndStrategy | None = None,
    metadata: AgentMetadata[Any] | None = None,
    tool_timeout: float | None = None,
    max_concurrency: _concurrency.AnyConcurrencyLimit = None,
    capabilities: Sequence[AgentCapability[Any]] | None = None,
) -> Agent[object, str]
def from_file(
    cls,
    path: Path | str,
    *,
    fmt: Literal['yaml', 'json'] | None = None,
    deps_type: type[T],
    custom_capability_types: Sequence[type[AbstractCapability[Any]]] = (),
    model: models.Model | models.KnownModelName | str | None = None,
    output_type: OutputSpec[Any] = str,
    instructions: AgentInstructions[Any] = None,
    system_prompt: str | Sequence[str] = (),
    name: str | None = None,
    description: TemplateStr[Any] | str | None = None,
    model_settings: ModelSettings | None = None,
    retries: int | AgentRetries | None = None,
    validation_context: Any = None,
    tools: Sequence[Tool[Any] | ToolFuncEither[Any, ...]] = (),
    toolsets: Sequence[AgentToolset[Any]] | None = None,
    defer_model_check: bool = False,
    end_strategy: EndStrategy | None = None,
    metadata: AgentMetadata[Any] | None = None,
    tool_timeout: float | None = None,
    max_concurrency: _concurrency.AnyConcurrencyLimit = None,
    capabilities: Sequence[AgentCapability[Any]] | None = None,
) -> Agent[T, str]
```

Construct an Agent from a YAML or JSON spec file.

This is a convenience method equivalent to `Agent.from_spec(AgentSpec.from_file(path), ...)`.

The file format is inferred from the extension (`.yaml`/`.yml` or `.json`) unless overridden with the `fmt` argument.

All other arguments are forwarded to [`from_spec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.from_spec).

###### Returns

[`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### instrument\_all

`@staticmethod`

```python
def instrument_all(instrument: InstrumentationSettings | bool = True) -> None
```

Set the instrumentation options for all agents that don't explicitly add an `Instrumentation` capability.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### render\_description

```python
def render_description(deps: AgentDepsT = None) -> str | None
```

Return the agent description, rendering any TemplateStr with the given deps.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### iter

`@async`

```python
def iter(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRun[AgentDepsT, OutputDataT]]
def iter(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRun[AgentDepsT, RunOutputDataT]]
```

A contextmanager which can be used to iterate over the agent graph's nodes as they are executed.

This method builds an internal agent graph (using system prompts, tools and output schemas) and then returns an `AgentRun` object. The `AgentRun` can be used to async-iterate over the nodes of the graph as they are executed. This is the API to use if you want to consume the outputs coming from each LLM model response, or the stream of events coming from the execution of tools.

The `AgentRun` also provides methods to access the full message history, new messages, and usage statistics, and the final result of the run once it has completed.

For more details, see the documentation of `AgentRun`.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    nodes = []
    async with agent.iter('What is the capital of France?') as agent_run:
        async for node in agent_run:
            nodes.append(node)
    print(nodes)
    '''
    [
        UserPromptNode(
            user_prompt='What is the capital of France?',
            instructions_functions=[],
            system_prompts=(),
            system_prompt_functions=[],
            system_prompt_dynamic_functions={},
        ),
        ModelRequestNode(
            request=ModelRequest(
                parts=[
                    UserPromptPart(
                        content='What is the capital of France?',
                        timestamp=datetime.datetime(...),
                    )
                ],
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        CallToolsNode(
            model_response=ModelResponse(
                parts=[TextPart(content='The capital of France is Paris.')],
                usage=RequestUsage(
                    cost=Decimal('0.000196'), input_tokens=56, output_tokens=7
                ),
                model_name='gpt-5.2',
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        End(data=FinalResult(output='The capital of France is Paris.')),
    ]
    '''
    print(agent_run.result.output)
    #> The capital of France is Paris.
```

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[[`AgentRun`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun)\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : `AgentInstructions`\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request, or a callable that receives [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) and returns settings. Callables are called before each model request, allowing dynamic per-step settings.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Token used to cancel this run from another task or thread. Single-use: mint a fresh token per run, as a reused (already-cancelled) token prevents the run from starting.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run. At run time, spec values are additive.

##### override

```python
def override(
    *,
    name: str | _utils.Unset = _utils.UNSET,
    deps: AgentDepsT | _utils.Unset = _utils.UNSET,
    model: models.Model | models.KnownModelName | str | _utils.Unset = _utils.UNSET,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | _utils.Unset = _utils.UNSET,
    tools: Sequence[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]] | _utils.Unset = _utils.UNSET,
    native_tools: Sequence[AgentNativeTool[AgentDepsT]] | _utils.Unset = _utils.UNSET,
    instructions: AgentInstructions[AgentDepsT] | _utils.Unset = _utils.UNSET,
    metadata: AgentMetadata[AgentDepsT] | _utils.Unset = _utils.UNSET,
    model_settings: AgentModelSettings[AgentDepsT] | _utils.Unset = _utils.UNSET,
    retries: int | AgentRetries | _utils.Unset = _utils.UNSET,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> Generator[None]
```

Context manager to temporarily override agent configuration.

This is particularly useful when testing. You can find an example of this [here](https://pydantic.dev/docs/ai/guides/testing/#overriding-model-via-pytest-fixtures).

###### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The name to use instead of the name passed to the agent constructor and agent run.

**`deps`** : `AgentDepsT` | `_utils.Unset` _Default:_ `_utils.UNSET`

The dependencies to use instead of the dependencies passed to the agent run.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The model to use instead of the model passed to the agent run.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The toolsets to use instead of the toolsets passed to the agent constructor and agent run.

**`tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\] | `ToolFuncEither`\[`AgentDepsT`, ...\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The tools to use instead of the tools registered with the agent.

**`native_tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentNativeTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.AgentNativeTool)\[`AgentDepsT`\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The native tools to use instead of the agent's configured native tools.

**`instructions`** : `AgentInstructions`\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The instructions to use instead of the instructions registered with the agent. Note: this also replaces capability-contributed instructions (e.g. from [`get_instructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.get_instructions)).

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The metadata to use instead of the metadata passed to the agent constructor. When set, any per-run `metadata` argument is ignored.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The model settings to use instead of the model settings passed to the agent constructor. When set, any per-run `model_settings` argument is ignored.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | `_utils.Unset` _Default:_ `_utils.UNSET`

The retry budgets to use instead of the agent-level configuration. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). When set, any per-run `retries` argument is ignored.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec providing defaults for override. Explicit params take precedence over spec values. When the spec includes `capabilities`, they replace (not merge with) the agent's existing capabilities. To add capabilities without replacing, pass `spec` to `run()` or `iter()` instead.

##### instructions

```python
def instructions(
    func: Callable[[RunContext[AgentDepsT]], str | None],
    /,
) -> Callable[[RunContext[AgentDepsT]], str | None]
def instructions(
    func: Callable[[RunContext[AgentDepsT]], Awaitable[str | None]],
    /,
) -> Callable[[RunContext[AgentDepsT]], Awaitable[str | None]]
def instructions(func: Callable[[], str | None], /) -> Callable[[], str | None]
def instructions(
    func: Callable[[], Awaitable[str | None]],
    /,
) -> Callable[[], Awaitable[str | None]]
def instructions(
    *,
    name: str | None = None,
) -> Callable[[SystemPromptFunc[AgentDepsT]], SystemPromptFunc[AgentDepsT]]
```

Decorator to register an instructions function.

Optionally takes [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) as its only argument. Can decorate a sync or async functions.

The decorator can be used bare (`agent.instructions`).

Overloads for every possible signature of `instructions` are included so the decorator doesn't obscure the type of the function.

Example:

```python
from pydantic_ai import Agent, RunContext

agent = Agent('test', deps_type=str)

@agent.instructions
def simple_instructions() -> str:
    return 'foobar'

@agent.instructions
async def async_instructions(ctx: RunContext[str]) -> str:
    return f'{ctx.deps} is the best'
```

###### Returns

[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`SystemPromptFunc`\[`AgentDepsT`\]\], `SystemPromptFunc`\[`AgentDepsT`\]\] | `SystemPromptFunc`\[`AgentDepsT`\]

###### Parameters

**`func`** : `SystemPromptFunc`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The instructions function to register.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An optional name for the instruction part this function produces, keyed as `'agent:<name>'` on [`InstructionPart.id`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart.id) so an application can address this part specifically, where the bare `'agent'` key addresses the agent's literal instructions. See [instruction parts](https://pydantic.dev/docs/ai/core-concepts/agent/#instruction-parts).

##### system\_prompt\_parts

`@async`

```python
def system_prompt_parts(
    *,
    deps: AgentDepsT = None,
    model: models.Model | models.KnownModelName | str | None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    prompt: str | Sequence[_messages.UserContent] | None = None,
    usage: _usage.RunUsage | None = None,
    model_settings: ModelSettings | None = None,
) -> list[_messages.SystemPromptPart]
```

Resolve the agent's configured system prompts into `SystemPromptPart`s.

See [`AbstractAgent.system_prompt_parts`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.system_prompt_parts).

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.SystemPromptPart`\]

##### system\_prompt

```python
def system_prompt(
    func: Callable[[RunContext[AgentDepsT]], str | None],
    /,
) -> Callable[[RunContext[AgentDepsT]], str | None]
def system_prompt(
    func: Callable[[RunContext[AgentDepsT]], Awaitable[str | None]],
    /,
) -> Callable[[RunContext[AgentDepsT]], Awaitable[str | None]]
def system_prompt(func: Callable[[], str | None], /) -> Callable[[], str | None]
def system_prompt(
    func: Callable[[], Awaitable[str | None]],
    /,
) -> Callable[[], Awaitable[str | None]]
def system_prompt(
    *,
    dynamic: bool = False,
) -> Callable[[SystemPromptFunc[AgentDepsT]], SystemPromptFunc[AgentDepsT]]
```

Decorator to register a system prompt function.

Optionally takes [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) as its only argument. Can decorate a sync or async functions.

The decorator can be used either bare (`agent.system_prompt`) or as a function call (`agent.system_prompt(...)`), see the examples below.

Overloads for every possible signature of `system_prompt` are included so the decorator doesn't obscure the type of the function, see `tests/typed_agent.py` for tests.

Example:

```python
from pydantic_ai import Agent, RunContext

agent = Agent('test', deps_type=str)

@agent.system_prompt
def simple_system_prompt() -> str:
    return 'foobar'

@agent.system_prompt(dynamic=True)
async def async_system_prompt(ctx: RunContext[str]) -> str:
    return f'{ctx.deps} is the best'
```

###### Returns

[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`SystemPromptFunc`\[`AgentDepsT`\]\], `SystemPromptFunc`\[`AgentDepsT`\]\] | `SystemPromptFunc`\[`AgentDepsT`\]

###### Parameters

**`func`** : `SystemPromptFunc`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The function to decorate

**`dynamic`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

If True, the system prompt will be reevaluated even when `messages_history` is provided, see [`SystemPromptPart.dynamic_ref`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SystemPromptPart.dynamic_ref)

##### output\_validator

```python
def output_validator(
    func: Callable[[RunContext[AgentDepsT], OutputDataT], OutputDataT],
    /,
) -> Callable[[RunContext[AgentDepsT], OutputDataT], OutputDataT]
def output_validator(
    func: Callable[[RunContext[AgentDepsT], OutputDataT], Awaitable[OutputDataT]],
    /,
) -> Callable[[RunContext[AgentDepsT], OutputDataT], Awaitable[OutputDataT]]
def output_validator(
    func: Callable[[OutputDataT], OutputDataT],
    /,
) -> Callable[[OutputDataT], OutputDataT]
def output_validator(
    func: Callable[[OutputDataT], Awaitable[OutputDataT]],
    /,
) -> Callable[[OutputDataT], Awaitable[OutputDataT]]
```

Decorator to register an output validator function.

Optionally takes [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) as its first argument. Can decorate a sync or async functions.

Overloads for every possible signature of `output_validator` are included so the decorator doesn't obscure the type of the function, see `tests/typed_agent.py` for tests.

Example:

```python
from pydantic_ai import Agent, ModelRetry, RunContext

agent = Agent('test', deps_type=str)

@agent.output_validator
def output_validator_simple(data: str) -> str:
    if 'wrong' in data:
        raise ModelRetry('wrong response')
    return data

@agent.output_validator
async def output_validator_deps(ctx: RunContext[str], data: str) -> str:
    if ctx.deps in data:
        raise ModelRetry('wrong response')
    return data

result = agent.run_sync('foobar', deps='spam')
print(result.output)
#> success (no tool calls)
```

###### Returns

`_output.OutputValidatorFunc`\[`AgentDepsT`, `OutputDataT`\]

##### on\_event

```python
def on_event(
    func: OnEventHookFunc[_messages.AgentStreamEvent],
    /,
) -> OnEventHookFunc[_messages.AgentStreamEvent]
def on_event(
    *event_types: type[EventT],
    timeout: float | None = None,
) -> Callable[[OnEventHookFunc[EventT]], OnEventHookFunc[EventT]]
```

Decorator to register a listener for events on this agent's run event stream.

Every event on the stream can be listened for: the framework's own model and tool events, the application's [`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent)s, and the [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent)s published by the agent's capabilities. Naming event classes narrows the `event` argument to their union and lets dispatch skip the agent's listeners for anything else; a bare `@agent.on_event` sees every [`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent).

This is the application-level counterpart to [`@on_event`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.on_event) on a capability, and it dispatches at the same point. These listeners join after the agent's own capabilities, so they see the events those emitted, and they survive an overridden root capability. Capability ordering still applies: one asking for `position='innermost'` keeps that position and its listeners run after these.

Dispatch happens _upstream_ of [`wrap_run_event_stream()`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.wrap_run_event_stream), so a listener sees each event as it was emitted, not as it is finally delivered. A capability that rewrites, replaces or drops events in its stream wrapper does so after every listener has already run, which means a listener can see an event that no stream consumer ever receives. To act on the delivered stream instead, wrap it yourself with `wrap_run_event_stream` on a [`Hooks`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Hooks) capability, or consume [`run_stream_events()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run_stream_events).

Being application code, a listener may emit a `CustomEvent` of its own. That is how a capability's internal event reaches a frontend: capability events are deliberately not forwarded by the [AG-UI](https://pydantic.dev/docs/ai/integrations/ui/ag-ui/) and [Vercel AI](https://pydantic.dev/docs/ai/integrations/ui/vercel-ai/) adapters, so you republish the part of one that is public.

For hook families other than events, pass a [`Hooks`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Hooks) capability to `capabilities=`, where its position among the other capabilities -- which decides where it sits in each wrap chain -- is yours to choose.

Example:

```python
from dataclasses import dataclass

from pydantic_ai import Agent, CapabilityEvent, CustomEvent, RunContext

agent = Agent('test')


@dataclass(kw_only=True)
class IndexRebuiltEvent(CapabilityEvent, namespace='indexer'):
    documents: int


@dataclass(kw_only=True)
class SearchReadyEvent(CustomEvent):
    documents: int


@agent.on_event(IndexRebuiltEvent)
async def republish(ctx: RunContext[None], event: IndexRebuiltEvent) -> None:
    await ctx.emit(SearchReadyEvent(documents=event.documents))
```

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

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
    docstring_format: DocstringFormat = 'auto',
    require_parameter_descriptions: bool = False,
    schema_generator: type[GenerateJsonSchema] = GenerateToolJsonSchema,
    strict: bool | None = None,
    sequential: bool = False,
    requires_approval: bool = False,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
    defer_loading: bool = False,
    include_return_schema: bool | None = None,
) -> Callable[[ToolFuncContext[AgentDepsT, ToolParams]], ToolFuncContext[AgentDepsT, ToolParams]]
```

Decorator to register a tool function which takes [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) as its first argument.

Can decorate a sync or async functions.

The docstring is inspected to extract both the tool description and description of each parameter, [learn more](https://pydantic.dev/docs/ai/tools-toolsets/tools/#function-tools-and-schema).

We can't add overloads for every possible signature of tool, since the return type is a recursive union so the signature of functions decorated with `@agent.tool` is obscured.

Example:

```python
from pydantic_ai import Agent, RunContext

agent = Agent('test', deps_type=int)

@agent.tool
def foobar(ctx: RunContext[int], x: int) -> int:
    return ctx.deps + x

@agent.tool(retries=2)
async def spam(ctx: RunContext[str], y: float) -> float:
    return ctx.deps + y

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

The description of the tool, defaults to the function docstring.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The number of retries to allow for this tool, defaults to the agent's default retries, which defaults to 1.

**`prepare`** : `ToolPrepareFunc`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to prepare the tool definition for each step, return `None` to omit this tool from a given step. This is useful if you want to customise a tool at call time, or omit it completely from a step. See [`ToolPrepareFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolPrepareFunc).

**`args_validator`** : `ArgsValidatorFunc`\[`AgentDepsT`, `ToolParams`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to validate tool arguments after schema validation has passed, before execution. The validator receives the already-validated and type-converted parameters, with `RunContext` as the first argument. Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to ask the model to correct the arguments and try again, or [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed) to report a terminal failure the model should adapt to instead of retrying. Return `None` on success. See [`ArgsValidatorFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ArgsValidatorFunc).

**`docstring_format`** : `DocstringFormat` _Default:_ `'auto'`

The format of the docstring, see [`DocstringFormat`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DocstringFormat). Defaults to `'auto'`, such that the format is inferred from the structure of the docstring.

**`require_parameter_descriptions`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

If True, raise an error if a parameter description is missing. Defaults to False.

**`schema_generator`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`GenerateJsonSchema`\] _Default:_ `GenerateToolJsonSchema`

The JSON schema generator class to use for this tool. Defaults to `GenerateToolJsonSchema`.

**`strict`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to enforce (vendor-specific) strict schema adherence for tool calls (supported by OpenAI, Anthropic, Google, and Bedrock). See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info.

**`sequential`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether this tool acts as a barrier that runs alone, not overlapping with other tool calls. See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info. Defaults to False.

**`requires_approval`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether this tool requires human-in-the-loop approval. Defaults to False. See the [tools documentation](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval) for more info.

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization.

**`timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model. Overrides the agent-level `tool_timeout` if set. Defaults to None (no timeout).

**`defer_loading`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether to hide this tool until it's revealed by tool search, `load_capability`, or another tool's `ToolReturn.tools`. Defaults to False. See [Tool Search](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#tool-search) for more info.

**`include_return_schema`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to include the return schema in the tool definition sent to the model. If `None`, defaults to `False` unless the [`IncludeToolReturnSchemas`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.IncludeToolReturnSchemas) capability is used.

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
    docstring_format: DocstringFormat = 'auto',
    require_parameter_descriptions: bool = False,
    schema_generator: type[GenerateJsonSchema] = GenerateToolJsonSchema,
    strict: bool | None = None,
    sequential: bool = False,
    requires_approval: bool = False,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None,
    defer_loading: bool = False,
    include_return_schema: bool | None = None,
) -> Callable[[ToolFuncPlain[ToolParams]], ToolFuncPlain[ToolParams]]
```

Decorator to register a tool function which DOES NOT take `RunContext` as an argument.

Can decorate a sync or async functions.

The docstring is inspected to extract both the tool description and description of each parameter, [learn more](https://pydantic.dev/docs/ai/tools-toolsets/tools/#function-tools-and-schema).

We can't add overloads for every possible signature of tool, since the return type is a recursive union so the signature of functions decorated with `@agent.tool` is obscured.

Example:

```python
from pydantic_ai import Agent, RunContext

agent = Agent('test')

@agent.tool
def foobar(ctx: RunContext[int]) -> int:
    return 123

@agent.tool(retries=2)
async def spam(ctx: RunContext[str]) -> float:
    return 3.14

result = agent.run_sync('foobar', deps=1)
print(result.output)
#> {"foobar":123,"spam":3.14}
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

The number of retries to allow for this tool, defaults to the agent's default retries, which defaults to 1.

**`prepare`** : `ToolPrepareFunc`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to prepare the tool definition for each step, return `None` to omit this tool from a given step. This is useful if you want to customise a tool at call time, or omit it completely from a step. See [`ToolPrepareFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolPrepareFunc).

**`args_validator`** : `ArgsValidatorFunc`\[`AgentDepsT`, `ToolParams`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

custom method to validate tool arguments after schema validation has passed, before execution. The validator receives the already-validated and type-converted parameters, with [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) as the first argument -- even though the tool function itself does not take `RunContext` when using `tool_plain`. Raise [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) to ask the model to correct the arguments and try again, or [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed) to report a terminal failure the model should adapt to instead of retrying. Return `None` on success. See [`ArgsValidatorFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ArgsValidatorFunc).

**`docstring_format`** : `DocstringFormat` _Default:_ `'auto'`

The format of the docstring, see [`DocstringFormat`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DocstringFormat). Defaults to `'auto'`, such that the format is inferred from the structure of the docstring.

**`require_parameter_descriptions`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

If True, raise an error if a parameter description is missing. Defaults to False.

**`schema_generator`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`GenerateJsonSchema`\] _Default:_ `GenerateToolJsonSchema`

The JSON schema generator class to use for this tool. Defaults to `GenerateToolJsonSchema`.

**`strict`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to enforce (vendor-specific) strict schema adherence for tool calls (supported by OpenAI, Anthropic, Google, and Bedrock). See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info.

**`sequential`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether this tool acts as a barrier that runs alone, not overlapping with other tool calls. See [`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition) for more info. Defaults to False.

**`requires_approval`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether this tool requires human-in-the-loop approval. Defaults to False. See the [tools documentation](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval) for more info.

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata for the tool. This is not sent to the model but can be used for filtering and tool behavior customization.

**`timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Timeout in seconds for tool execution. If the tool takes longer, a retry prompt is returned to the model. Overrides the agent-level `tool_timeout` if set. Defaults to None (no timeout).

**`defer_loading`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether to hide this tool until it's revealed by tool search, `load_capability`, or another tool's `ToolReturn.tools`. Defaults to False. See [Tool Search](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#tool-search) for more info.

**`include_return_schema`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to include the return schema in the tool definition sent to the model. If `None`, defaults to `False` unless the [`IncludeToolReturnSchemas`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.IncludeToolReturnSchemas) capability is used.

##### toolset

```python
def toolset(func: ToolsetFunc[AgentDepsT], /) -> ToolsetFunc[AgentDepsT]
def toolset(
    *,
    per_run_step: bool = True,
    id: str | None = None,
) -> Callable[[ToolsetFunc[AgentDepsT]], ToolsetFunc[AgentDepsT]]
```

Decorator to register a toolset function which takes [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) as its only argument.

Can decorate a sync or async functions.

The decorator can be used bare (`agent.toolset`).

Example:

```python
from pydantic_ai import AbstractToolset, Agent, FunctionToolset, RunContext

agent = Agent('test', deps_type=str)

@agent.toolset
async def simple_toolset(ctx: RunContext[str]) -> AbstractToolset[str]:
    return FunctionToolset()
```

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

###### Parameters

**`func`** : [`ToolsetFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.ToolsetFunc)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The toolset function to register.

**`per_run_step`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to re-evaluate the toolset for each run step. Defaults to True.

**`id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An optional unique ID for the dynamic toolset. Under durable execution, construct a [`DynamicToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.DynamicToolset) with this ID and pass it to `Agent(toolsets=[...])` instead; decorator registrations cannot be used inside a workflow or flow because they happen after durable units are created.

##### \_\_aenter\_\_

`@async`

```python
def __aenter__() -> Self
```

Enter the agent context.

This will start all [`MCPToolset`s](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset) registered as `toolsets` so they are ready to be used, and enter the model so the provider's HTTP client will be closed cleanly on exit.

This is a no-op if the agent has already been entered.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self)

##### set\_mcp\_sampling\_model

```python
def set_mcp_sampling_model(
    model: models.Model | models.KnownModelName | str | None = None,
) -> None
```

Set the sampling model on all [`MCPToolset`s](https://pydantic.dev/docs/ai/api/pydantic-ai/mcp/#pydantic_ai.mcp.MCPToolset) registered with the agent.

If no sampling model is provided, the agent's model will be used.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### to\_web

```python
def to_web(
    *,
    models: ModelsParam = None,
    deps: AgentDepsT = None,
    model_settings: ModelSettings | None = None,
    instructions: str | None = None,
    html_source: str | Path | None = None,
    allowed_hosts: Sequence[str] | None = None,
) -> Starlette
```

Create a Starlette app that serves a web chat UI for this agent.

This method returns a pre-configured Starlette application that provides a web-based chat interface for interacting with the agent. By default, the UI is fetched from a CDN and cached on first use.

The returned Starlette application can be mounted into a FastAPI app or run directly with any ASGI server (uvicorn, hypercorn, etc.).

Note that the `deps` and `model_settings` will be the same for each request. To provide different `deps` for each request use the lower-level adapters directly.

The agent's configured native tools (registered via `capabilities=[NativeTool(...)]` or higher-level capabilities like `WebSearch()`) are automatically exposed as options in the UI.

###### Returns

`Starlette` -- A configured Starlette application ready to be served (e.g., with uvicorn)

###### Parameters

**`models`** : `ModelsParam` _Default:_ `None`

Additional models to make available in the UI. Can be:

-   A sequence of model names/instances (e.g., `['openai:gpt-5', 'anthropic:claude-sonnet-4-6']`)
-   A dict mapping display labels to model names/instances (e.g., `{'GPT 5': 'openai:gpt-5', 'Claude': 'anthropic:claude-sonnet-4-6'}`) The agent's model is always included. Native tool support is automatically determined from each model's profile.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for all requests.

**`model_settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for all model requests.

**`instructions`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional extra instructions to pass to each agent run.

**`html_source`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `Path` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Path or URL for the chat UI HTML. Can be:

-   None (default): Fetches from CDN and caches locally
-   A Path instance: Reads from the local file
-   A URL string (http:// or https://): Fetches from the URL
-   A file path string: Reads from the local file

**`allowed_hosts`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Additional hostnames to answer to, e.g. `['ui.example.com']` or `['*.example.com']` (subdomains only, so list the apex separately if you serve it). IP addresses and `localhost` are always allowed; any other `Host` header is refused with a `421`, so that a website cannot reach the UI on your machine by pointing a hostname it controls at you (DNS rebinding). Pass `['*']` to answer to any host, only if something in front of the app already authenticates requests.

### AbstractAgent

**Bases:** `Generic[AgentDepsT, OutputDataT]`, `ABC`

Abstract superclass for [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent), [`WrapperAgent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.WrapperAgent), and your own custom agent implementations.

#### Attributes

##### model

The default model configured for this agent.

**Type:** [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### name

The name of the agent, used for logging.

If `None`, we try to infer the agent name from the call frame when the agent is first run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### description

A human-readable description of the agent.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### deps\_type

The type of dependencies used by the agent.

**Type:** [`type`](https://docs.python.org/3/glossary.html#term-type)

##### output\_type

The type of data output by agent runs, used to validate the data returned by the model, defaults to `str`.

**Type:** `OutputSpec`\[`OutputDataT`\]

##### event\_stream\_handler

Optional handler for events from the model's streaming response and the agent's execution of tools.

**Type:** `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### root\_capability

The root capability of the agent, containing all registered capabilities.

**Type:** `CombinedCapability`\[`AgentDepsT`\]

##### toolsets

All toolsets registered on the agent.

Output tools are not included.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\]

#### Methods

##### system\_prompt\_parts

`@async`

```python
def system_prompt_parts(
    *,
    deps: AgentDepsT = None,
    model: models.Model | models.KnownModelName | str | None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    prompt: str | Sequence[_messages.UserContent] | None = None,
    usage: _usage.RunUsage | None = None,
    model_settings: ModelSettings | None = None,
) -> list[_messages.SystemPromptPart]
```

Resolve the agent's configured system prompts into `SystemPromptPart`s.

Returns a list suitable for prepending to a `ModelRequest`. Static strings and runners decorated with [`@agent.system_prompt`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.system_prompt) are evaluated using a minimal `RunContext` built from the provided kwargs -- useful when reconstructing a `message_history` that should carry the agent's configured system prompt (e.g. in UI adapters or after history compaction).

Dynamic runners produce parts with `dynamic_ref` set so they can continue to be re-evaluated by the standard agent graph path on subsequent turns.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.SystemPromptPart`\]

###### Parameters

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies for dynamic system prompt functions.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for `RunContext.model`. Falls back to the agent's configured model; required only if the agent has no model set.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional message history to expose as `RunContext.messages`.

**`prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional user prompt to expose as `RunContext.prompt`.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to expose as `RunContext.usage`.

**`model_settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to expose as `RunContext.model_settings`.

##### output\_json\_schema

```python
def output_json_schema(
    output_type: OutputSpec[OutputDataT | RunOutputDataT] | None = None,
) -> JsonSchema
```

The output return JSON schema.

###### Returns

`JsonSchema`

##### run

`@async`

```python
def run(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[OutputDataT]
def run(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[RunOutputDataT]
```

Run the agent with a user prompt in async mode.

This method builds an internal agent graph (using system prompts, tools and output schemas) and then runs the graph to completion. The result of the run is returned.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    agent_run = await agent.run('What is the capital of France?')
    print(agent_run.output)
    #> The capital of France is Paris.
```

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request, or a callable that receives [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) and returns settings. Callables are called before each model request, allowing dynamic per-step settings.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Token used to cancel this run from another task or thread. Single-use: mint a fresh token per run, as a reused (already-cancelled) token prevents the run from starting.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional handler for events from the model's streaming response and the agent's execution of tools to use for this run. Under a durability capability, this per-run handler runs workflow-side; model events are replayed after each model request completes. For handler I/O inside the durable boundary, pass `event_stream_handler=` to the durability capability.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run. At run time, spec values are additive.

##### run\_sync

```python
def run_sync(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[OutputDataT]
def run_sync(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AgentRunResult[RunOutputDataT]
```

Synchronously run the agent with a user prompt.

This is a convenience method that wraps [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) with `loop.run_until_complete(...)`. You therefore can't use this method inside async code or if there's an active event loop.

This method cannot be used inside a synchronous tool, output function, or other function called during an agent run. To delegate to another agent, make the function `async def` and `await` [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) instead. See [Agent delegation](https://pydantic.dev/docs/ai/guides/multi-agent-applications/#agent-delegation).

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

result_sync = agent.run_sync('What is the capital of Italy?')
print(result_sync.output)
#> The capital of Italy is Rome.
```

###### Returns

[`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request, or a callable that receives [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) and returns settings. Callables are called before each model request, allowing dynamic per-step settings.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Token used to cancel this run from another task or thread. Single-use: mint a fresh token per run, as a reused (already-cancelled) token prevents the run from starting.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional handler for events from the model's streaming response and the agent's execution of tools to use for this run. Under a durability capability, this per-run handler runs workflow-side; model events are replayed after each model request completes. For handler I/O inside the durable boundary, pass `event_stream_handler=` to the durability capability.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run. At run time, spec values are additive.

##### run\_stream

`@async`

```python
def run_stream(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[result.StreamedRunResult[AgentDepsT, OutputDataT]]
def run_stream(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[result.StreamedRunResult[AgentDepsT, RunOutputDataT]]
```

Run the agent with a user prompt in async streaming mode.

This method builds an internal agent graph (using system prompts, tools and output schemas) and then runs the graph until the model produces output matching the `output_type`, for example text or structured data. At this point, a streaming run result object is yielded from which you can stream the output as it comes in, and -- once this output has completed streaming -- get the complete output, message history, and usage.

As this method will consider the first output matching the `output_type` to be the final output, it will stop running the agent graph and will not execute any tool calls made by the model after this "final" output. If you want to always run the agent graph to completion and stream events and output at the same time, use [`agent.run()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) with an `event_stream_handler` or [`agent.iter()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.iter) instead.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    async with agent.run_stream('What is the capital of the UK?') as response:
        print(await response.get_output())
        #> The capital of the UK is London.
```

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[[`result.StreamedRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult)\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request, or a callable that receives [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) and returns settings. Callables are called before each model request, allowing dynamic per-step settings.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Token used to cancel this run from another task or thread. Single-use: mint a fresh token per run, as a reused (already-cancelled) token prevents the run from starting.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional handler for events from the model's streaming response and the agent's execution of tools to use for this run. Under a durability capability, this per-run handler runs workflow-side; model events are replayed after each model request completes. For handler I/O inside the durable boundary, pass `event_stream_handler=` to the durability capability. It will receive all the events up until the final result is found, which you can then read or stream from inside the context manager. Note that it does _not_ receive any events after the final result is found.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run. At run time, spec values are additive.

##### run\_stream\_sync

```python
def run_stream_sync(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> result.StreamedRunResultSync[AgentDepsT, OutputDataT]
def run_stream_sync(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    event_stream_handler: EventStreamHandler[AgentDepsT] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> result.StreamedRunResultSync[AgentDepsT, RunOutputDataT]
```

Run the agent with a user prompt in sync streaming mode.

This is a convenience method that wraps [`run_stream()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run_stream), running all of the agent's async work on the caller's event loop while keeping context-manager and iterator lifecycles in stable tasks. You therefore can't use this method inside async code or if there's an active event loop.

Like [`run_sync()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run_sync), this method cannot be used inside a synchronous tool, output function, or other function called during an agent run. See [Agent delegation](https://pydantic.dev/docs/ai/guides/multi-agent-applications/#agent-delegation).

The returned [`StreamedRunResultSync`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResultSync) is a synchronous context manager and should be used and closed on the thread where it was created. Use a `with` block so the stream is cleaned up when you're done.

This method builds an internal agent graph (using system prompts, tools and output schemas) and then runs the graph until the model produces output matching the `output_type`, for example text or structured data. At this point, a streaming run result object is yielded from which you can stream the output as it comes in, and -- once this output has completed streaming -- get the complete output, message history, and usage.

As this method will consider the first output matching the `output_type` to be the final output, it will stop running the agent graph and will not execute any tool calls made by the model after this "final" output. If you want to always run the agent graph to completion and stream events and output at the same time, use [`agent.run()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) with an `event_stream_handler` or [`agent.iter()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.iter) instead.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

def main():
    with agent.run_stream_sync('What is the capital of the UK?') as response:
        print(response.get_output())
        #> The capital of the UK is London.
```

###### Returns

[`result.StreamedRunResultSync`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResultSync)\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request, or a callable that receives [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) and returns settings. Callables are called before each model request, allowing dynamic per-step settings.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Token used to cancel this run from another task or thread. Single-use: mint a fresh token per run, as a reused (already-cancelled) token prevents the run from starting.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`event_stream_handler`** : `EventStreamHandler`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional handler for events from the model's streaming response and the agent's execution of tools to use for this run. Under a durability capability, this per-run handler runs workflow-side; model events are replayed after each model request completes. For handler I/O inside the durable boundary, pass `event_stream_handler=` to the durability capability. It will receive all the events up until the final result is found, which you can then read or stream from inside the context manager. Note that it does _not_ receive any events after the final result is found.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run. At run time, spec values are additive.

##### run\_stream\_events

```python
def run_stream_events(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRunEvents[OutputDataT]]
def run_stream_events(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRunEvents[RunOutputDataT]]
```

Run the agent with a user prompt in async mode and stream events from the run.

This is a convenience method that wraps [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) and uses the `event_stream_handler` kwarg to get a stream of events from the run.

The background run starts on the first iteration of the event handle, not on entering the context manager, so entering and exiting without iterating never calls the model.

The handle can cancel the whole run and access its messages, usage, and completed result.

Must be used as an async context manager so the background run task is deterministically cleaned up when the consumer stops iterating early.

Example:

```python
from pydantic_ai import Agent, AgentRunResultEvent, AgentStreamEvent

agent = Agent('openai:gpt-5.2')

async def main():
    collected: list[AgentStreamEvent | AgentRunResultEvent] = []
    async with agent.run_stream_events('What is the capital of France?') as events:
        async for event in events:
            collected.append(event)
    print(collected)
    '''
    [
        PartStartEvent(index=0, part=TextPart(content='The capital of ')),
        FinalResultEvent(tool_name=None, tool_call_id=None),
        PartDeltaEvent(index=0, delta=TextPartDelta(content_delta='France is Paris. ')),
        PartEndEvent(
            index=0, part=TextPart(content='The capital of France is Paris. ')
        ),
        AgentRunResultEvent(
            result=AgentRunResult(output='The capital of France is Paris. ')
        ),
    ]
    '''
```

Arguments are the same as for [`self.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run), except that `event_stream_handler` is now allowed.

###### Returns

`AbstractAsyncContextManager`\[[`AgentRunEvents`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRunEvents)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- An async context manager that yields an [`AgentRunEvents`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRunEvents) `AbstractAsyncContextManager`\[[`AgentRunEvents`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRunEvents)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- handle over `AgentStreamEvent`s ending with a final `AgentRunResultEvent` carrying the run result.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request, or a callable that receives [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) and returns settings. Callables are called before each model request, allowing dynamic per-step settings.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Token used to cancel this run from another task or thread. Single-use: mint a fresh token per run, as a reused (already-cancelled) token prevents the run from starting.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run. At run time, spec values are additive.

##### iter

`@abstractmethod`

`@async`

```python
def iter(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRun[AgentDepsT, OutputDataT]]
def iter(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRun[AgentDepsT, RunOutputDataT]]
```

A contextmanager which can be used to iterate over the agent graph's nodes as they are executed.

This method builds an internal agent graph (using system prompts, tools and output schemas) and then returns an `AgentRun` object. The `AgentRun` can be used to async-iterate over the nodes of the graph as they are executed. This is the API to use if you want to consume the outputs coming from each LLM model response, or the stream of events coming from the execution of tools.

The `AgentRun` also provides methods to access the full message history, new messages, and usage statistics, and the final result of the run once it has completed.

For more details, see the documentation of `AgentRun`.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    nodes = []
    async with agent.iter('What is the capital of France?') as agent_run:
        async for node in agent_run:
            nodes.append(node)
    print(nodes)
    '''
    [
        UserPromptNode(
            user_prompt='What is the capital of France?',
            instructions_functions=[],
            system_prompts=(),
            system_prompt_functions=[],
            system_prompt_dynamic_functions={},
        ),
        ModelRequestNode(
            request=ModelRequest(
                parts=[
                    UserPromptPart(
                        content='What is the capital of France?',
                        timestamp=datetime.datetime(...),
                    )
                ],
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        CallToolsNode(
            model_response=ModelResponse(
                parts=[TextPart(content='The capital of France is Paris.')],
                usage=RequestUsage(
                    cost=Decimal('0.000196'), input_tokens=56, output_tokens=7
                ),
                model_name='gpt-5.2',
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        End(data=FinalResult(output='The capital of France is Paris.')),
    ]
    '''
    print(agent_run.result.output)
    #> The capital of France is Paris.
```

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[[`AgentRun`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun)\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request, or a callable that receives [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) and returns settings. Callables are called before each model request, allowing dynamic per-step settings.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Token used to cancel this run from another task or thread. Single-use: mint a fresh token per run, as a reused (already-cancelled) token prevents the run from starting.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run. At run time, spec values are additive.

##### override

`@abstractmethod`

```python
def override(
    *,
    name: str | _utils.Unset = _utils.UNSET,
    deps: AgentDepsT | _utils.Unset = _utils.UNSET,
    model: models.Model | models.KnownModelName | str | _utils.Unset = _utils.UNSET,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | _utils.Unset = _utils.UNSET,
    tools: Sequence[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]] | _utils.Unset = _utils.UNSET,
    native_tools: Sequence[AgentNativeTool[AgentDepsT]] | _utils.Unset = _utils.UNSET,
    instructions: _instructions.AgentInstructions[AgentDepsT] | _utils.Unset = _utils.UNSET,
    metadata: AgentMetadata[AgentDepsT] | _utils.Unset = _utils.UNSET,
    model_settings: AgentModelSettings[AgentDepsT] | _utils.Unset = _utils.UNSET,
    retries: int | AgentRetries | _utils.Unset = _utils.UNSET,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> Generator[None]
```

Context manager to temporarily override agent configuration.

This is particularly useful when testing. You can find an example of this [here](https://pydantic.dev/docs/ai/guides/testing/#overriding-model-via-pytest-fixtures).

###### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The name to use instead of the name passed to the agent constructor and agent run.

**`deps`** : `AgentDepsT` | `_utils.Unset` _Default:_ `_utils.UNSET`

The dependencies to use instead of the dependencies passed to the agent run.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The model to use instead of the model passed to the agent run.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The toolsets to use instead of the toolsets passed to the agent constructor and agent run.

**`tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\] | `ToolFuncEither`\[`AgentDepsT`, ...\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The tools to use instead of the tools registered with the agent.

**`native_tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentNativeTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.AgentNativeTool)\[`AgentDepsT`\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The native tools to use instead of the agent's configured native tools.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The instructions to use instead of the instructions registered with the agent.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The metadata to use instead of the metadata passed to the agent constructor. When set, any per-run `metadata` argument is ignored.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The model settings to use instead of the model settings passed to the agent constructor. When set, any per-run `model_settings` argument is ignored.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | `_utils.Unset` _Default:_ `_utils.UNSET`

The retry budgets to use instead of the agent-level configuration. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). When set, any per-run `retries` argument is ignored.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec providing defaults for override.

##### realtime

```python
def realtime(
    model: RealtimeModel | KnownRealtimeModelName | str,
    *,
    deps: AgentDepsT = None,
    model_settings: RealtimeModelSettings | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    usage: _usage.RunUsage | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
) -> AgentRealtime[AgentDepsT]
```

Bind this agent's configuration to a realtime `model`, returning an accessor for realtime operations.

The returned [`AgentRealtime`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime) carries the agent's realtime configuration so that opening a session with [`session()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.session) reuses the same instructions, tools, capabilities, and run context without re-passing them.

These parameters mirror [`iter`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.iter). Parameters specific to the request-response graph -- `output_type`, `retries`, `event_stream_handler`, `deferred_tool_results` -- do not apply; structured output should be delegated to a normal [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent) (see the realtime docs). Capabilities run `for_run` once when the session connects; their instructions, toolsets, and native tools are applied. Tool hooks (`prepare_tools` and `before`/`after`/`wrap`/ `on_error` for `tool_validate` and `tool_execute`) run for each tool call. Run hooks (`before_run`, `after_run`, `wrap_run`, `on_run_error`) run once around the session and event-stream hooks wrap the session iterator; graph, model-request, and output-stage hooks do not run.

```python
from pydantic_ai import Agent
from pydantic_ai.realtime.openai import OpenAIRealtimeModel

agent = Agent(instructions='You are a helpful voice assistant.')

@agent.tool_plain
def get_weather(city: str) -> str:
    return f'Sunny in {city}'

async def main():
    model = OpenAIRealtimeModel('gpt-realtime')
    async with agent.realtime(model).session() as session:
        await session.send_audio(b'...')
        async for _event in session:
            pass
```

###### Returns

`AgentRealtime`\[`AgentDepsT`\]

###### Parameters

**`model`** : `RealtimeModel` | `KnownRealtimeModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The realtime model to connect to.

**`deps`** : `AgentDepsT` _Default:_ `None`

Dependencies passed to tool functions.

**`model_settings`** : `RealtimeModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional realtime settings overriding the model's defaults for the session.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Additional instructions for the session, combined with the agent's instructions. Dynamic instruction functions (`@agent.instructions`) are evaluated once at connect time (there is no per-request rebuild in a realtime session).

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for the session, on top of the agent's.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional capabilities for the session. Their `for_run`, setup contributions, and tool-lifecycle hooks apply; run hooks fire once around the session and event-stream hooks wrap the iterator; model-request, graph, and output hooks are not invoked.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage) to accumulate token usage into; exposed as `session.usage`. A fresh one is used when omitted.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional [`UsageLimits`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.UsageLimits). Request, token, and tool-call limits are enforced as usage accrues; a breach raises [`UsageLimitExceeded`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UsageLimitExceeded) from the session's event iterator, matching how `run` / `iter` surface a usage limit.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata set on the [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) available to tools and capabilities, and on the realtime session telemetry span.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional conversation id, set on the run context and the telemetry span so a realtime session can be correlated with other runs. Session-built messages are stamped with it as well, allowing a later standard run to resume the same conversation; seeded messages are left unchanged.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this realtime session, which is one long-lived run covering every exchange. Never inherited from `message_history`; passing an empty or previously used ID raises `UserError`. If omitted, a fresh UUID7 is generated and stamped on session-built messages, while seeded messages are left unchanged.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Prior conversation to seed the session with. Replayable text, transcripts, thinking, tool rounds, images, and supported retained user audio are projected to the provider's initial conversation items; unrepresentable content raises `UserError`. The history is included in [`session.all_messages()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.all_messages) (but not `new_messages()`). Hand off from a prior session or a standard [`Agent.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) by passing its messages here.

##### parallel\_tool\_call\_execution\_mode

`@staticmethod`

```python
def parallel_tool_call_execution_mode(
    mode: tool_manager.ParallelExecutionMode = 'parallel',
) -> Generator[None]
```

Set the parallel execution mode during the context.

###### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

###### Parameters

**`mode`** : [`tool_manager.ParallelExecutionMode`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tool_manager.ParallelExecutionMode) _Default:_ `'parallel'`

The execution mode for tool calls:

-   'parallel': Run tool calls in parallel, yielding events as they complete (default).
-   'sequential': Run tool calls one at a time in order.
-   'parallel\_ordered\_events': Run tool calls in parallel, but events are emitted in order, after all calls complete.

##### using\_thread\_executor

`@staticmethod`

```python
def using_thread_executor(executor: Executor) -> Generator[None]
```

Use a custom executor for running sync functions in threads during the context.

By default, sync tool functions and other sync callbacks are run in threads using `anyio.to_thread.run_sync`, which creates ephemeral threads. In long-running servers (e.g. FastAPI), this can lead to thread accumulation under sustained load.

This context manager lets you provide a bounded [`ThreadPoolExecutor`](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor) (or any [`Executor`](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Executor)) to control thread lifecycle:

```python
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from pydantic_ai import Agent

@asynccontextmanager
async def lifespan(app):
    executor = ThreadPoolExecutor(max_workers=16)
    with Agent.using_thread_executor(executor):
        yield
    executor.shutdown(wait=True)
```

For per-agent configuration, use the [`UseThreadExecutor`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.UseThreadExecutor) capability instead.

###### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

###### Parameters

**`executor`** : `Executor`

The executor to use for running sync functions.

##### using\_sleep

`@staticmethod`

```python
def using_sleep(sleep_func: _agent_graph.AgentGraphSleepFunc) -> Generator[None]
```

Use a custom async sleep function for agent-graph delays during the context.

By default the agent graph uses `asyncio.sleep` when it needs to wait during a run (e.g. between polls of a suspended/background model response). Durable execution frameworks (Temporal, Prefect, DBOS, ...) register their own durable sleep here so delays survive workflow replays and don't waste activity time.

###### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

##### is\_model\_request\_node

`@staticmethod`

```python
def is_model_request_node(
    node: _agent_graph.AgentNode[T, S] | End[result.FinalResult[S]],
) -> TypeIs[_agent_graph.ModelRequestNode[T, S]]
```

Check if the node is a `ModelRequestNode`, narrowing the type if it is.

This method preserves the generic parameters while narrowing the type, unlike a direct call to `isinstance`.

###### Returns

[`TypeIs`](https://docs.python.org/3/library/typing.html#typing.TypeIs)\[[`_agent_graph.ModelRequestNode`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.ModelRequestNode)\[`T`, `S`\]\]

##### is\_call\_tools\_node

`@staticmethod`

```python
def is_call_tools_node(
    node: _agent_graph.AgentNode[T, S] | End[result.FinalResult[S]],
) -> TypeIs[_agent_graph.CallToolsNode[T, S]]
```

Check if the node is a `CallToolsNode`, narrowing the type if it is.

This method preserves the generic parameters while narrowing the type, unlike a direct call to `isinstance`.

###### Returns

[`TypeIs`](https://docs.python.org/3/library/typing.html#typing.TypeIs)\[[`_agent_graph.CallToolsNode`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.CallToolsNode)\[`T`, `S`\]\]

##### is\_user\_prompt\_node

`@staticmethod`

```python
def is_user_prompt_node(
    node: _agent_graph.AgentNode[T, S] | End[result.FinalResult[S]],
) -> TypeIs[_agent_graph.UserPromptNode[T, S]]
```

Check if the node is a `UserPromptNode`, narrowing the type if it is.

This method preserves the generic parameters while narrowing the type, unlike a direct call to `isinstance`.

###### Returns

[`TypeIs`](https://docs.python.org/3/library/typing.html#typing.TypeIs)\[[`_agent_graph.UserPromptNode`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.UserPromptNode)\[`T`, `S`\]\]

##### is\_end\_node

`@staticmethod`

```python
def is_end_node(
    node: _agent_graph.AgentNode[T, S] | End[result.FinalResult[S]],
) -> TypeIs[End[result.FinalResult[S]]]
```

Check if the node is a `End`, narrowing the type if it is.

This method preserves the generic parameters while narrowing the type, unlike a direct call to `isinstance`.

###### Returns

[`TypeIs`](https://docs.python.org/3/library/typing.html#typing.TypeIs)\[`End`\[`result.FinalResult`\[`S`\]\]\]

##### to\_cli

`@async`

```python
def to_cli(
    deps: AgentDepsT = None,
    prog_name: str = 'pydantic-ai',
    message_history: Sequence[_messages.ModelMessage] | None = None,
    model_settings: ModelSettings | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
) -> None
```

Run the agent in a CLI chat interface.

Example:

agent\_to\_cli.py

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2', instructions='You always respond in Italian.')

async def main():
    await agent.to_cli()
```

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`deps`** : `AgentDepsT` _Default:_ `None`

The dependencies to pass to the agent.

**`prog_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'pydantic-ai'`

The name of the program to use for the CLI. Defaults to 'pydantic-ai'.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`model_settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for the agent run.

##### to\_cli\_sync

```python
def to_cli_sync(
    deps: AgentDepsT = None,
    prog_name: str = 'pydantic-ai',
    message_history: Sequence[_messages.ModelMessage] | None = None,
    model_settings: ModelSettings | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
) -> None
```

Run the agent in a CLI chat interface with the non-async interface.

agent\_to\_cli\_sync.py

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2', instructions='You always respond in Italian.')
agent.to_cli_sync()
agent.to_cli_sync(prog_name='assistant')
```

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`deps`** : `AgentDepsT` _Default:_ `None`

The dependencies to pass to the agent.

**`prog_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'pydantic-ai'`

The name of the program to use for the CLI. Defaults to 'pydantic-ai'.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`model_settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for the agent run.

### WrapperAgent

**Bases:** `AbstractAgent[AgentDepsT, OutputDataT]`

Agent which wraps another agent.

Does nothing on its own, used as a base class.

#### Attributes

##### validation\_context

The Pydantic validation context used to validate tool arguments and outputs.

Set this when validators need values from [`ValidationInfo.context`](https://docs.pydantic.dev/latest/api/pydantic-core/pydantic_core_schema/#pydantic_core.core_schema.ValidationInfo.context). A callable can build the context from the current [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext).

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]\], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

#### Methods

##### iter

`@async`

```python
def iter(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: None = None,
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRun[AgentDepsT, OutputDataT]]
def iter(
    user_prompt: str | Sequence[_messages.UserContent] | None = None,
    *,
    output_type: OutputSpec[RunOutputDataT],
    message_history: Sequence[_messages.ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: AgentModelSettings[AgentDepsT] | None = None,
    usage_limits: _usage.UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: _usage.RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    retries: int | AgentRetries | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AgentCapability[AgentDepsT]] | None = None,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> AbstractAsyncContextManager[AgentRun[AgentDepsT, RunOutputDataT]]
```

A contextmanager which can be used to iterate over the agent graph's nodes as they are executed.

This method builds an internal agent graph (using system prompts, tools and output schemas) and then returns an `AgentRun` object. The `AgentRun` can be used to async-iterate over the nodes of the graph as they are executed. This is the API to use if you want to consume the outputs coming from each LLM model response, or the stream of events coming from the execution of tools.

The `AgentRun` also provides methods to access the full message history, new messages, and usage statistics, and the final result of the run once it has completed.

For more details, see the documentation of `AgentRun`.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    nodes = []
    async with agent.iter('What is the capital of France?') as agent_run:
        async for node in agent_run:
            nodes.append(node)
    print(nodes)
    '''
    [
        UserPromptNode(
            user_prompt='What is the capital of France?',
            instructions_functions=[],
            system_prompts=(),
            system_prompt_functions=[],
            system_prompt_dynamic_functions={},
        ),
        ModelRequestNode(
            request=ModelRequest(
                parts=[
                    UserPromptPart(
                        content='What is the capital of France?',
                        timestamp=datetime.datetime(...),
                    )
                ],
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        CallToolsNode(
            model_response=ModelResponse(
                parts=[TextPart(content='The capital of France is Paris.')],
                usage=RequestUsage(
                    cost=Decimal('0.000196'), input_tokens=56, output_tokens=7
                ),
                model_name='gpt-5.2',
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        End(data=FinalResult(output='The capital of France is Paris.')),
    ]
    '''
    print(agent_run.result.output)
    #> The capital of France is Paris.
```

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[[`AgentRun`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun)\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] -- The result of the run.

###### Parameters

**`user_prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

User input to start/continue the conversation.

**`output_type`** : `OutputSpec`\[`RunOutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.ModelMessage`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : `_usage.UsageLimits` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Token used to cancel this run from another task or thread.

**`usage`** : `_usage.RunUsage` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override the agent-level retry budgets for this run. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). See [`Agent.__init__`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.__init__) for semantics of the two enforcement paths.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AgentCapability)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply for this run.

##### override

```python
def override(
    *,
    name: str | _utils.Unset = _utils.UNSET,
    deps: AgentDepsT | _utils.Unset = _utils.UNSET,
    model: models.Model | models.KnownModelName | str | _utils.Unset = _utils.UNSET,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | _utils.Unset = _utils.UNSET,
    tools: Sequence[Tool[AgentDepsT] | ToolFuncEither[AgentDepsT, ...]] | _utils.Unset = _utils.UNSET,
    native_tools: Sequence[AgentNativeTool[AgentDepsT]] | _utils.Unset = _utils.UNSET,
    instructions: _instructions.AgentInstructions[AgentDepsT] | _utils.Unset = _utils.UNSET,
    metadata: AgentMetadata[AgentDepsT] | _utils.Unset = _utils.UNSET,
    model_settings: AgentModelSettings[AgentDepsT] | _utils.Unset = _utils.UNSET,
    retries: int | AgentRetries | _utils.Unset = _utils.UNSET,
    spec: dict[str, Any] | AgentSpec | None = None,
) -> Generator[None]
```

Context manager to temporarily override agent configuration.

This is particularly useful when testing. You can find an example of this [here](https://pydantic.dev/docs/ai/guides/testing/#overriding-model-via-pytest-fixtures).

###### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The name to use instead of the name passed to the agent constructor and agent run.

**`deps`** : `AgentDepsT` | `_utils.Unset` _Default:_ `_utils.UNSET`

The dependencies to use instead of the dependencies passed to the agent run.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The model to use instead of the model passed to the agent run.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The toolsets to use instead of the toolsets passed to the agent constructor and agent run.

**`tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool)\[`AgentDepsT`\] | `ToolFuncEither`\[`AgentDepsT`, ...\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The tools to use instead of the tools registered with the agent.

**`native_tools`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AgentNativeTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.AgentNativeTool)\[`AgentDepsT`\]\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The native tools to use instead of the agent's configured native tools.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The instructions to use instead of the instructions registered with the agent.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The metadata to use instead of the metadata passed to the agent constructor. When set, any per-run `metadata` argument is ignored.

**`model_settings`** : [`AgentModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentModelSettings)\[`AgentDepsT`\] | `_utils.Unset` _Default:_ `_utils.UNSET`

The model settings to use instead of the model settings passed to the agent constructor. When set, any per-run `model_settings` argument is ignored.

**`retries`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) | `_utils.Unset` _Default:_ `_utils.UNSET`

The retry budgets to use instead of the agent-level configuration. Pass an `int` to override both the tool-retry and output budgets, or an [`AgentRetries`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRetries) dict to override just one (e.g. `retries={'tools': 3}`). When set, any per-run `retries` argument is ignored.

**`spec`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional agent spec to apply as overrides.

### AgentRetries

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Per-category retry budgets for an [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent).

Pass to `Agent(retries=...)` as a dict to set different budgets per category.

A bare `int` is shorthand for setting both `tools` and `output` to that value -- the same at every call site (`Agent(retries=N)`, `run()`, `iter()`, `override()`, and a run-time `spec`). To set only one budget, pass a dict, e.g. `retries={'tools': ...}` or `retries={'output': ...}`.

### AgentRealtime

**Bases:** `Generic[AgentDepsT]`

An agent bound to a realtime model, returned by [`AbstractAgent.realtime`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.realtime).

Carries the agent's realtime configuration (mirroring the parameters of [`iter`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.iter)) so that opening a session reuses the same instructions, tools, capabilities, and run context without re-passing them. Construct it via [`agent.realtime(model, ...)`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.realtime), then open a session with [`session()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.session).

#### Methods

##### answer\_webrtc\_offer

`@async`

```python
def answer_webrtc_offer(sdp_offer: str) -> WebRTCAnswer
```

Resolve this agent's realtime configuration and relay a browser WebRTC SDP offer.

The resolved instructions and tool definitions are baked into the call, so the provider session is fully configured before (or without) a server sideband attaching. If a sideband later attaches with [`session(provider_session=...)`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.session), it resolves and pushes the same configuration over the control channel again.

Resolution uses the same machinery as opening a session: dynamic `@agent.instructions` functions and capability `for_run` hooks run, and toolsets are set up (including starting MCP servers) to list their tools, then torn down. Bound `message_history` is not baked into the offer; a sideband session seeds it when it attaches.

This delegates to [`answer_webrtc_offer`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.answer_webrtc_offer), which is implemented by the OpenAI and Azure OpenAI realtime models. Other models raise [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError); branch on [`supports_webrtc`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile.supports_webrtc) to check up front.

###### Returns

`WebRTCAnswer`

##### create\_client\_secret

`@async`

```python
def create_client_secret(
    *,
    expires_after_seconds: int | None = None,
) -> RealtimeClientSecret
```

Resolve this agent's realtime configuration and mint a browser client secret.

The resolved instructions and tool definitions are baked into the secret, so the provider session is fully configured before (or without) a server sideband attaching. If a sideband later attaches with [`session(provider_session=...)`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.session), it resolves and pushes the same configuration over the control channel again.

Resolution uses the same machinery as opening a session: dynamic `@agent.instructions` functions and capability `for_run` hooks run, and toolsets are set up (including starting MCP servers) to list their tools, then torn down. Bound `message_history` is not baked into the secret; a sideband session seeds it when it attaches.

This delegates to [`create_client_secret`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.create_client_secret), which is implemented by the OpenAI and Azure OpenAI realtime models. Other models raise [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError); branch on [`supports_webrtc`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile.supports_webrtc) to check up front.

###### Returns

`RealtimeClientSecret`

###### Parameters

**`expires_after_seconds`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Requested lifetime of the client secret in seconds. The provider may constrain the accepted value.

##### session

`@async`

```python
def session(
    *,
    audio_retention: AudioRetention = 'transcript_only',
    handle_barge_in: bool = False,
    retain_images_every_n: int = 1,
    retain_images_max: int | None = 100,
    provider_session: RealtimeProviderSession | None = None,
) -> AsyncGenerator[RealtimeSession]
```

Open a realtime speech-to-speech session backed by the agent's tools.

The session connects to the bound realtime model and automatically executes tool calls using the agent's registered tools, sending the results back to the model. See `Agent.realtime` for how `run`/`iter` features map to a duplex session.

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[`RealtimeSession`\]

###### Parameters

**`audio_retention`** : `AudioRetention` _Default:_ `'transcript_only'`

How much spoken audio the session retains in its history, on top of transcripts. Defaults to `'transcript_only'` (drop audio bytes); see [`AudioRetention`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.AudioRetention).

**`handle_barge_in`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Let the session handle the local half of barge-in itself. When the user starts speaking over the model, the session discards the buffered audio the user will never hear, truncates the provider's transcript to what was actually played, and cancels the response -- normalizing what each provider signals and supports, and doing nothing when the previous reply was heard in full. Requires playback to drain the session's single [`stream_audio()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_audio) iterator chunk by chunk at device pace (the setup behind [`played_audio_bytes`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.played_audio_bytes)); any other playback topology should leave this off and call [`interrupt()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.interrupt) itself. Defaults to `False`.

**`retain_images_every_n`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) _Default:_ `1`

Keep one of every `N` images sent during the session in message history. Defaults to `1` (keep every image); increase for high-rate camera/screen streams.

**`retain_images_max`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `100`

Bound on how many images stay in message history; once exceeded, the oldest retained image is evicted. Defaults to `100` so a long-running frame stream can't grow memory without limit; `0` retains no images, `None` removes the bound.

**`provider_session`** : `RealtimeProviderSession` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A [`RealtimeProviderSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeProviderSession) to attach a **sideband** control session to, from [`answer_webrtc_offer`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.answer_webrtc_offer). When set, the browser exchanges audio with the provider directly over WebRTC and this session runs only the control plane (instructions, tools, transcripts, history) -- the audio methods (`send_audio`/`commit_audio`/`clear_audio`) are unavailable and `audio_retention` must be left at `'transcript_only'`. See the realtime docs for the full browser/WebRTC flow.

### AgentRun

**Bases:** `Generic[AgentDepsT, OutputDataT]`

A stateful, async-iterable run of an [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent).

You generally obtain an `AgentRun` instance by calling `async with my_agent.iter(...) as agent_run:`.

Once you have an instance, you can use it to iterate through the run's nodes as they execute. When an [`End`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.End) is reached, the run finishes and [`result`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.result) becomes available.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    nodes = []
    # Iterate through the run, recording each node along the way:
    async with agent.iter('What is the capital of France?') as agent_run:
        async for node in agent_run:
            nodes.append(node)
    print(nodes)
    '''
    [
        UserPromptNode(
            user_prompt='What is the capital of France?',
            instructions_functions=[],
            system_prompts=(),
            system_prompt_functions=[],
            system_prompt_dynamic_functions={},
        ),
        ModelRequestNode(
            request=ModelRequest(
                parts=[
                    UserPromptPart(
                        content='What is the capital of France?',
                        timestamp=datetime.datetime(...),
                    )
                ],
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        CallToolsNode(
            model_response=ModelResponse(
                parts=[TextPart(content='The capital of France is Paris.')],
                usage=RequestUsage(
                    cost=Decimal('0.000196'), input_tokens=56, output_tokens=7
                ),
                model_name='gpt-5.2',
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        End(data=FinalResult(output='The capital of France is Paris.')),
    ]
    '''
    print(agent_run.result.output)
    #> The capital of France is Paris.
```

You can also manually drive the iteration using the [`next`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.next) method for more granular control.

#### Attributes

##### ctx

The current context of the agent run.

**Type:** `GraphRunContext`\[`_agent_graph.GraphAgentState`, `_agent_graph.GraphAgentDeps`\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]

##### next\_node

The next node that will be run in the agent graph.

This is the next node that will be used during async iteration, or if a node is not passed to `self.next(...)`.

**Type:** `_agent_graph.AgentNode`\[`AgentDepsT`, `OutputDataT`\] | `End`\[`FinalResult`\[`OutputDataT`\]\]

##### result

The final result of the run if it has ended, otherwise `None`.

Once the run returns an [`End`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.End) node, `result` is populated with an [`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult).

**Type:** [`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[`OutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### usage

Get usage statistics for the run so far, including token usage, model requests, and so on.

**Type:** `_usage.RunUsage`

##### metadata

Metadata associated with this agent run, if configured.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### run\_id

The unique identifier for the agent run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### conversation\_id

The unique identifier for the conversation this run belongs to.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### pending\_messages

Internal: live view of the queue mutated by `enqueue` and drained by the internal `PendingMessageDrainCapability`.

Exposed for inspection / debugging; use [`enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.enqueue) to add messages.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`PendingMessage`\]

#### Methods

##### all\_messages

```python
def all_messages() -> list[_messages.ModelMessage]
```

Return all messages for the run so far.

Messages from older runs are included.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\]

##### all\_messages\_json

```python
def all_messages_json(*, output_tool_return_content: str | None = None) -> bytes
```

Return all messages from [`all_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.all_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the messages.

##### new\_messages

```python
def new_messages() -> list[_messages.ModelMessage]
```

Return the messages produced during this run so far.

Messages provided via `message_history` and messages from older runs are excluded.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\]

##### new\_messages\_json

```python
def new_messages_json() -> bytes
```

Return new messages from [`new_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.new_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the new messages.

##### \_\_aiter\_\_

```python
def __aiter__(

) -> AsyncIterator[_agent_graph.AgentNode[AgentDepsT, OutputDataT] | End[FinalResult[OutputDataT]]]
```

Provide async-iteration over the nodes in the agent run.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`_agent_graph.AgentNode`\[`AgentDepsT`, `OutputDataT`\] | `End`\[`FinalResult`\[`OutputDataT`\]\]\]

##### \_\_anext\_\_

`@async`

```python
def __anext__(

) -> _agent_graph.AgentNode[AgentDepsT, OutputDataT] | End[FinalResult[OutputDataT]]
```

Advance to the next node automatically based on the last returned node.

Yields each node before it runs, ending with the [`End`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.End) node. Advancing goes through [`next()`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.next), so capability hooks fire exactly as they do for [`agent.run()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run).

###### Returns

`_agent_graph.AgentNode`\[`AgentDepsT`, `OutputDataT`\] | `End`\[`FinalResult`\[`OutputDataT`\]\]

##### next

`@async`

```python
def next(
    node: _agent_graph.AgentNode[AgentDepsT, OutputDataT],
) -> _agent_graph.AgentNode[AgentDepsT, OutputDataT] | End[FinalResult[OutputDataT]]
```

Manually drive the agent run by passing in the node you want to run next.

This lets you inspect or mutate the node before continuing execution, or skip certain nodes under dynamic conditions. The agent run should be stopped when you return an [`End`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.End) node.

Example:

```python
from pydantic_ai import Agent
from pydantic_graph import End

agent = Agent('openai:gpt-5.2')

async def main():
    async with agent.iter('What is the capital of France?') as agent_run:
        next_node = agent_run.next_node  # start with the first node
        nodes = [next_node]
        while not isinstance(next_node, End):
            next_node = await agent_run.next(next_node)
            nodes.append(next_node)
        # Once `next_node` is an End, we've finished:
        print(nodes)
        '''
        [
            UserPromptNode(
                user_prompt='What is the capital of France?',
                instructions_functions=[],
                system_prompts=(),
                system_prompt_functions=[],
                system_prompt_dynamic_functions={},
            ),
            ModelRequestNode(
                request=ModelRequest(
                    parts=[
                        UserPromptPart(
                            content='What is the capital of France?',
                            timestamp=datetime.datetime(...),
                        )
                    ],
                    timestamp=datetime.datetime(...),
                    run_id='...',
                    conversation_id='...',
                )
            ),
            CallToolsNode(
                model_response=ModelResponse(
                    parts=[TextPart(content='The capital of France is Paris.')],
                    usage=RequestUsage(
                        cost=Decimal('0.000196'), input_tokens=56, output_tokens=7
                    ),
                    model_name='gpt-5.2',
                    timestamp=datetime.datetime(...),
                    run_id='...',
                    conversation_id='...',
                )
            ),
            End(data=FinalResult(output='The capital of France is Paris.')),
        ]
        '''
        print('Final result:', agent_run.result.output)
        #> Final result: The capital of France is Paris.
```

###### Returns

`_agent_graph.AgentNode`\[`AgentDepsT`, `OutputDataT`\] | `End`\[`FinalResult`\[`OutputDataT`\]\] -- The next node returned by the graph logic, or an [`End`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.End) node if `_agent_graph.AgentNode`\[`AgentDepsT`, `OutputDataT`\] | `End`\[`FinalResult`\[`OutputDataT`\]\] -- the run has completed.

###### Parameters

**`node`** : `_agent_graph.AgentNode`\[`AgentDepsT`, `OutputDataT`\]

The node to run next in the graph.

##### emit

`@async`

```python
def emit(event: CustomEventT, /) -> CustomEventT
```

Emit a [`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent) into this run's event stream.

Lets code driving [`Agent.iter`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.iter) inject application-defined events (e.g. from an external harness or event bus) into the stream, alongside events emitted from tools via [`RunContext.emit`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.emit). The event surfaces on the next pull from the run's node stream.

Designed to be called from the same event loop driving `agent.iter()`. If you're forwarding events from a different thread, submit the coroutine to the agent's loop (e.g. `asyncio.run_coroutine_threadsafe(agent_run.emit(event), loop)`).

###### Returns

`CustomEventT` -- The event as emitted.

###### Parameters

**`event`** : `CustomEventT`

The [`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent) to emit.

###### Raises

-   `UserError` -- If the run has already ended (no stream remains to deliver the event), or if passed a [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent): those belong to capabilities, and code driving the run is application code.

##### enqueue

```python
def enqueue(
    *content: EnqueueContent,
    priority: PendingMessagePriority = 'asap',
) -> str | None
```

Enqueue content to be injected into the conversation.

Designed to be called from the same event loop driving `agent.iter()`. If you're forwarding events from a different thread (e.g. a webhook handler running on its own loop or thread), marshal the call back onto the agent's loop first (e.g. `loop.call_soon_threadsafe(agent_run.enqueue, msg)`). The drain's `queue[:] = remaining` pattern in `_drain_by_priority` isn't atomic against concurrent appends from a different thread.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- The `enqueue_id` of the queued message, echoed on the [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- [`EnqueuedMessagesEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.EnqueuedMessagesEvent) emitted when it's [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- delivered, or `None` when there was nothing to enqueue (an empty call).

###### Parameters

**`*content`** : `EnqueueContent` _Default:_ `()`

One or more [`EnqueueContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.EnqueueContent) items. Adjacent [`UserContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserContent) (a `str` or multi-modal content like an [`ImageUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ImageUrl)) is gathered into one [`UserPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserPromptPart), and each [`ModelRequestPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequestPart) (e.g. a [`SystemPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SystemPromptPart)) is coalesced with adjacent part-style items into one [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest); a complete [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest) or [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse) is kept as its own message. The assembled sequence must end in a request. Calling with no positional args is a no-op.

**`priority`** : `PendingMessagePriority` _Default:_ `'asap'`

When to deliver: `'asap'` (default) -- at the earliest opportunity (next model request, or a redirect if the agent would otherwise end). `'when_idle'` -- only when the agent would otherwise end, after `'asap'` messages.

##### cancel

```python
def cancel() -> None
```

Cancel the whole agent run.

The run stops what it is doing -- the in-flight model request is torn down, in-flight tool tasks are cancelled and drained, a suspended server-side job is best-effort cancelled -- and the code driving the run sees `asyncio.CancelledError`. When the `agent.iter()` context exits, this becomes [`RunCancelled`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled) (including for `agent.run()`, which wraps `iter()`). Everything that completed before the cancellation took effect is preserved in message history. [`RunCancelled.all_messages()`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled.all_messages) returns a complete snapshot that can be passed to a new run as `message_history` to resume the conversation.

Cancellation is terminal: capability hooks (`wrap_run`, `wrap_node_run`, `on_run_error`) may observe it and clean up, but cannot recover the run into a successful result.

Unlike [`StreamedRunResult.cancel()`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.cancel), which only stops the current model response and lets the run continue, this ends the run itself.

Safe to call from another task or thread (e.g. a TUI's key handler while the run is awaited elsewhere). Idempotent; a no-op once the run has finished -- where "finished" means the `agent.iter()`/`agent.run()` context has exited. A `cancel()` issued inside the context after the run has already produced its result (e.g. after iterating to `End`) is still honored and surfaces as `RunCancelled` on exit, so that a hook running at context exit (like `after_run`) can still cancel the run; only after the context has exited is `cancel()` a true no-op. Externally cancelling the task running the agent (`asyncio.Task.cancel()`) remains supported and keeps raising `asyncio.CancelledError` instead; when both happen, the external cancellation wins.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### AgentRunEvents

**Bases:** `Generic[OutputDataT]`, `AgentStreamEvent | AgentRunResultEvent[OutputDataT]]`

The event iterator returned by [`run_stream_events()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run_stream_events).

Lazily starts a background `run()` task on the first `__anext__()` and forwards its events over a memory object stream, ending with a single trailing `AgentRunResultEvent` that carries the run's result. Entering the context manager without iterating therefore never starts a run ([https://github.com/pydantic/pydantic-ai/issues/6162](https://github.com/pydantic/pydantic-ai/issues/6162)).

This is a hand-written iterator class rather than an `async def` generator on purpose: generator cleanup runs by throwing `GeneratorExit` into the suspended frame during finalization, which on Python 3.10/3.11 can resume the frame under a different `Context` and raise the `pydantic_ai.current_run_context` token error ([https://github.com/pydantic/pydantic-ai/issues/5132](https://github.com/pydantic/pydantic-ai/issues/5132)). Driving cleanup explicitly through `aclose()` keeps teardown in the caller's task and context.

The handle can cancel the whole run and exposes its live messages and usage after iteration has started. After successful completion, `result` contains the final run result.

`cancel()` and the state accessors (`all_messages()`, `new_messages()`, `usage`) require the run to be driven through the standard [`Agent.iter()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.iter) path, which binds the run to this handle. The built-in `Agent` and the durable wrapper agents do this; a custom [`AbstractAgent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent) subclass whose `run()`/`iter()` chain doesn't consume that binding gets a `cancel()` that silently no-ops and state accessors that raise `UserError`, even after iteration has started.

#### Attributes

##### usage

Return the run's current usage.

Raises `UserError` if accessed before the first iteration has started the run.

**Type:** `_usage.RunUsage`

##### result

Return the successful run result once complete, otherwise `None`.

**Type:** [`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[`OutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### cancel

```python
def cancel() -> None
```

Request cancellation of the whole run.

This method is idempotent, is a no-op after completion, and is safe to call from another task (e.g. a TUI's key handler) or thread -- the underlying controller marshals onto the run's event loop, just like [`CancellationToken.cancel()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken.cancel). It does not affect external cancellation of the consumer task. If iteration continues, cancellation surfaces as [`RunCancelled`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled); leaving the context instead performs quiet teardown. Cancelling before the first iteration prevents the run from starting at all; iterating afterwards raises `RunCancelled` with empty `messages`.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### all\_messages

```python
def all_messages() -> list[_messages.ModelMessage]
```

Return all messages from the run, including messages supplied as history.

Raises `UserError` if accessed before the first iteration has started the run.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\]

##### new\_messages

```python
def new_messages() -> list[_messages.ModelMessage]
```

Return only messages created by the run.

Raises `UserError` if accessed before the first iteration has started the run.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\]

##### aclose

`@async`

```python
def aclose() -> None
```

Cancel the background run (if started) and close the receive stream, idempotently.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### AgentRunResult

**Bases:** `Generic[OutputDataT]`

The final result of an agent run.

#### Attributes

##### output

The output data from the agent run.

**Type:** `OutputDataT`

##### response

Return the last response from the message history.

**Type:** `_messages.ModelResponse`

##### usage

Return the usage of the whole run.

**Type:** `_usage.RunUsage`

##### timestamp

Return the timestamp of last response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

##### metadata

Metadata associated with this agent run, if configured.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### run\_id

The unique identifier for the agent run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### conversation\_id

The unique identifier for the conversation this run belongs to.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### all\_messages

```python
def all_messages(
    *,
    output_tool_return_content: str | None = None,
) -> list[_messages.ModelMessage]
```

Return the history of \_messages.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\] -- List of messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### all\_messages\_json

```python
def all_messages_json(*, output_tool_return_content: str | None = None) -> bytes
```

Return all messages from [`all_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult.all_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### new\_messages

```python
def new_messages(
    *,
    output_tool_return_content: str | None = None,
) -> list[_messages.ModelMessage]
```

Return the messages produced during this run.

Messages provided via `message_history` and messages from older runs are excluded.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\] -- List of new messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### new\_messages\_json

```python
def new_messages_json(*, output_tool_return_content: str | None = None) -> bytes
```

Return new messages from [`new_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult.new_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the new messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

### InstrumentationSettings

Options for instrumenting models and agents with OpenTelemetry.

Used in:

-   [`Instrumentation`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Instrumentation) capability
-   [`Agent.instrument`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.instrument) / [`Agent.instrument_all()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.instrument_all)
-   [`InstrumentedModel`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentedModel)

See the [Debugging and Monitoring guide](https://pydantic.dev/docs/ai/integrations/logfire/) for more info.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    tracer_provider: TracerProvider | None = None,
    meter_provider: MeterProvider | None = None,
    include_binary_content: bool = True,
    include_content: bool = True,
    include_model_request_parameters: bool = True,
    version: Literal[2, 3, 4, 5, 6] = DEFAULT_INSTRUMENTATION_VERSION,
    use_aggregated_usage_attribute_names: bool = True,
)
```

Create instrumentation options.

###### Parameters

**`tracer_provider`** : `TracerProvider` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The OpenTelemetry tracer provider to use. If not provided, the global tracer provider is used. Calling `logfire.configure()` sets the global tracer provider, so most users don't need this.

**`meter_provider`** : `MeterProvider` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The OpenTelemetry meter provider to use. If not provided, the global meter provider is used. Calling `logfire.configure()` sets the global meter provider, so most users don't need this.

**`include_binary_content`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to include binary file data in the instrumentation events: user prompts and model responses, tool returns, the agent's output and the arguments its output function receives, and run and tool deferral metadata. The media type is recorded either way. Binary content is found inside dictionaries, lists and `ToolReturn`s, but not inside your own types: a `BinaryContent` held as a field of a model or dataclass you define is still recorded in full.

**`include_content`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to include prompts, completions, and tool call arguments and responses in the instrumentation events.

**`include_model_request_parameters`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to emit the `model_request_parameters` span attribute on model request spans. This serializes the full `ModelRequestParameters` (output configuration and every tool definition, including fields that are not sent to the model such as tool `metadata` and, when not requested, `return_schema`). Defaults to `True`. Set to `False` to omit it entirely, which is useful when large tool output schemas make the attribute big enough to strain span export. The OpenTelemetry `gen_ai.tool.definitions` attribute (tool name, description, and parameters) is always emitted regardless of this setting.

**`version`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\[2, 3, 4, 5, 6\] _Default:_ `DEFAULT_INSTRUMENTATION_VERSION`

Version of the data format. This is unrelated to the Pydantic AI package version. Defaults to version 5. Versions 2, 3, and 4 are deprecated compatibility formats and emit a `PydanticAIDeprecationWarning` when used. Version 2 uses the newer OpenTelemetry GenAI spec and stores messages in the following attributes:

-   `gen_ai.system_instructions` for instructions passed to the agent.
-   `gen_ai.input.messages` and `gen_ai.output.messages` on model request spans.
-   `pydantic_ai.all_messages` on agent run spans. Version 3 is the same as version 2, with additional support for thinking tokens. Version 4 is the same as version 3, with GenAI semantic conventions for multimodal content: URL-based media uses type='uri' with uri and mime\_type fields (and modality for image/audio/video). Inline binary content uses type='blob' with mime\_type and content fields (and modality for image/audio/video). [https://opentelemetry.io/docs/specs/semconv/gen-ai/non-normative/examples-llm-calls/#multimodal-inputs-example](https://opentelemetry.io/docs/specs/semconv/gen-ai/non-normative/examples-llm-calls/#multimodal-inputs-example) Version 5 is the same as version 4, but CallDeferred and ApprovalRequired exceptions no longer record an exception event or set the span status to ERROR -- the span is left as UNSET, since deferrals are control flow, not errors. Version 6 is the same as version 5, but tool results are emitted in a message with `role='tool'` rather than `role='user'`, which is the role the GenAI semantic conventions pair with the `tool_call_response` parts they carry. Opt in to it when your telemetry consumer keys on the message role; it is not the default.

**`use_aggregated_usage_attribute_names`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to use `gen_ai.aggregated_usage.*` attribute names for token usage on agent run spans instead of the standard `gen_ai.usage.*` names. Defaults to True to prevent double-counting in observability backends that aggregate span attributes across parent and child spans. Note: `gen_ai.aggregated_usage.*` is a custom namespace, not part of the OpenTelemetry Semantic Conventions. It may be updated if OTel introduces an official convention.

##### aggregated\_usage\_attributes

```python
def aggregated_usage_attributes(usage: UsageBase) -> dict[str, int]
```

Cumulative-usage OpenTelemetry attributes for a run/session span.

Remaps `gen_ai.usage.*` to `gen_ai.aggregated_usage.*` when `use_aggregated_usage_attribute_names` is set, so a backend that sums span attributes doesn't double-count the run's cumulative usage against the per-request `chat` spans' `gen_ai.usage.*`. Shared by the classic agent-run span (the `Instrumentation` capability) and the realtime session span so the two can't drift.

###### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`int`](https://docs.python.org/3/builtins/functions.html#int)\]

### AgentSpec

**Bases:** `BaseModel`

Specification for constructing an Agent from a dict/YAML/JSON.

#### Methods

##### from\_file

`@classmethod`

```python
def from_file(
    cls,
    path: Path | str,
    fmt: Literal['yaml', 'json'] | None = None,
) -> AgentSpec
```

Load an agent spec from a YAML or JSON file.

###### Returns

[`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) -- A new AgentSpec instance.

###### Parameters

**`path`** : `Path` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Path to the file to load.

**`fmt`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['yaml', 'json'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Format of the file. If None, inferred from file extension.

##### from\_text

`@classmethod`

```python
def from_text(cls, text: str, fmt: Literal['yaml', 'json'] = 'yaml') -> AgentSpec
```

Parse YAML or JSON text into an AgentSpec.

###### Returns

[`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) -- A new AgentSpec instance.

###### Parameters

**`text`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The string content to parse.

**`fmt`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['yaml', 'json'\] _Default:_ `'yaml'`

Format of the content. Must be either 'yaml' or 'json'.

##### from\_dict

`@classmethod`

```python
def from_dict(cls, data: dict[str, Any]) -> AgentSpec
```

Validate a dictionary into an AgentSpec.

###### Returns

[`AgentSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentSpec) -- A new AgentSpec instance.

###### Parameters

**`data`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

Dictionary representation of the agent spec.

##### to\_file

```python
def to_file(
    path: Path | str,
    fmt: Literal['yaml', 'json'] | None = None,
    schema_path: Path | str | None = DEFAULT_SCHEMA_PATH_TEMPLATE,
    custom_capability_types: Sequence[type[AbstractCapability[Any]]] = (),
) -> None
```

Save the agent spec to a YAML or JSON file.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`path`** : `Path` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Path to save the spec to.

**`fmt`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['yaml', 'json'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Format to use. If None, inferred from file extension.

**`schema_path`** : `Path` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `DEFAULT_SCHEMA_PATH_TEMPLATE`

Path to save the JSON schema to. If None, no schema will be saved. Can be a string template with {stem} which will be replaced with the spec filename stem.

**`custom_capability_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractCapability`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]\] _Default:_ `()`

Custom capability classes to include in the schema.

##### model\_json\_schema\_with\_capabilities

`@classmethod`

```python
def model_json_schema_with_capabilities(
    cls,
    custom_capability_types: Sequence[type[AbstractCapability[Any]]] = (),
) -> dict[str, Any]
```

Generate a JSON schema for this agent spec type, including capability details.

This is useful for generating a schema that can be used to validate YAML-format agent spec files.

###### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- A dictionary representing the JSON schema.

###### Parameters

**`custom_capability_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractCapability`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]\] _Default:_ `()`

Custom capability classes to include in the schema.

### UserPromptNode

**Bases:** `AgentNode[DepsT, NodeRunEndT]`

The node that handles the user prompt and instructions.

### ModelRequestNode

**Bases:** `AgentNode[DepsT, NodeRunEndT]`

The node that makes a request to the model using the last message in state.message\_history.

### CallToolsNode

**Bases:** `AgentNode[DepsT, NodeRunEndT]`

The node that processes a model response, and decides whether to end the run or make a new request.

#### Attributes

##### tool\_call\_metadata

Metadata for deferred tool calls, keyed by `tool_call_id`.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### user\_prompt

Optional user prompt to include alongside tool call results.

This prompt is only sent to the model when the `model_response` contains tool calls. If the `model_response` has final output instead, this user prompt is ignored. The user prompt will be appended after all tool return parts in the next model request.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`_messages.UserContent`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### stream

`@async`

```python
def stream(
    ctx: GraphRunContext[GraphAgentState, GraphAgentDeps[DepsT, NodeRunEndT]],
) -> AsyncGenerator[AsyncIterator[_messages.AgentStreamEvent]]
```

Process the model response and yield events for the start and end of each function tool call.

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`_messages.AgentStreamEvent`\]\]

### PydanticAIDeprecationWarning

**Bases:** [`UserWarning`](https://docs.python.org/3/builtins/exceptions.html#UserWarning)

Warning emitted when a deprecated Pydantic AI API is used.

Inherits from `UserWarning` instead of `DeprecationWarning` so that deprecations are visible by default at runtime, following the approach described in [https://sethmlarson.dev/deprecations-via-warnings-dont-work-for-python-libraries](https://sethmlarson.dev/deprecations-via-warnings-dont-work-for-python-libraries).

### capture\_run\_messages

```python
def capture_run_messages() -> Generator[list[_messages.ModelMessage]]
```

Context manager to access the messages used in a [`run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run), [`run_sync`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run_sync), or [`run_stream`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run_stream) call.

Useful when a run may raise an exception, see [model errors](https://pydantic.dev/docs/ai/core-concepts/agent/#model-errors) for more information.

Examples:

```python
from pydantic_ai import Agent, capture_run_messages

agent = Agent('test')

with capture_run_messages() as messages:
    try:
        result = agent.run_sync('foobar')
    except Exception:
        print(messages)
        raise
```

Note

If you call `run`, `run_sync`, or `run_stream` more than once within a single `capture_run_messages` context, `messages` will represent the messages exchanged during the first call only.

Contexts can be nested: each `capture_run_messages` context captures the runs for which it is the innermost active context. A run started inside a nested context is captured by that nested context, not by any enclosing one, so wrapping a nested agent run (e.g. inside a tool) in its own `capture_run_messages` lets you inspect that inner run's messages independently.

If a run is interrupted by an exception or cancellation while streaming a response or executing tool calls, the partial [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse) or [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest) is still captured here with `state='interrupted'`, so consumers can detect and inspect partial state.

#### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\]\]

### EndStrategy

How to handle function tool calls a model requests alongside a result that ends the run.

The final result usually comes from an output tool call, but with [`NativeOutput`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.NativeOutput), [`PromptedOutput`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.PromptedOutput), or image output it comes from the text or image the model returns in the same response.

-   `'early'`: Output tools run in the order the model emitted them and the run ends at the first one that succeeds; function tools are not executed. If every output tool fails, function tools run so the model can correct on the next round. Likewise, if the response contains a valid structured output (`NativeOutput`/`PromptedOutput` text, or an image) alongside function tool calls, that output ends the run and the function tools are skipped. Plain, unstructured text output (`str` or `TextOutput`) does _not_ skip tools this way -- the model isn't told its text is final, so its preamble shouldn't silently cancel a tool call; the function tools run and the run continues.
-   `'graceful'` (default): Tools run in the order the model emitted them -- function tools that precede an output tool complete before it. Output tools run in order and the first success wins; subsequent output tools are skipped (their side effects don't run). If a function tool raises [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry), the output result is suppressed and the retry is surfaced to the model instead.
-   `'exhaustive'`: Every tool runs (in parallel by default); the first valid output by emission order becomes the final result. As with `'graceful'`, a function tool's [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) suppresses the output result. Use `sequential=True` on a tool (including via [`ToolOutput`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.ToolOutput)) to make it a barrier that doesn't overlap with others.

Under `'graceful'` and `'exhaustive'`, a structured output (`NativeOutput`/`PromptedOutput` text, or an image) returned alongside function tool calls does _not_ end the run early: the function tools run and the run continues, so their results can inform the model's eventual output. Only `'early'` skips them.

The default changed from `'early'` to `'graceful'` in v2. Set `end_strategy='early'` to keep the v1 behavior where the run ends the instant an output tool succeeds.

**Default:** `Literal['early', 'graceful', 'exhaustive']`

### RunOutputDataT

Type variable for the result data of a run where `output_type` was customized on the run call.

**Default:** `TypeVar('RunOutputDataT')`

### EventStreamHandler

A function that receives agent [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) and an async iterable of events from the model's streaming response and the agent's execution of tools.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[RunContext[AgentDepsT], 'AsyncIterable[_messages.AgentStreamEvent]'], Awaitable[None]]`

### AgentModelSettings

Type alias for agent model settings -- a static `ModelSettings` dict, or a callable receiving `RunContext` that returns one dynamically per request.

**Default:** `ModelSettings | Callable[[RunContext[AgentDepsT]], ModelSettings]`

### AgentInstructions

**Default:** `AgentInstruction[AgentDepsT] | Sequence[AgentInstruction[AgentDepsT]] | None`

### CancellationToken

A thread-safe handle for cancelling one or more agent runs.

A token is permanently cancelled after [`cancel`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken.cancel) is called. The same token may be passed to multiple concurrent runs, in which case all of them are cancelled.

#### Attributes

##### cancelled

Whether cancellation has been requested.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### Methods

##### cancel

```python
def cancel() -> None
```

Cancel every live run registered with this token.

This method is idempotent and may be called from any thread.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

---
