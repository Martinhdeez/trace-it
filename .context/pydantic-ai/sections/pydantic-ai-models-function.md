# [pydantic_ai.models.function](https://pydantic.dev/docs/ai/api/models/function/)

# pydantic\_ai.models.function

A model controlled by a local function.

[`FunctionModel`](https://pydantic.dev/docs/ai/api/models/function/#pydantic_ai.models.function.FunctionModel) is similar to [`TestModel`](https://pydantic.dev/docs/ai/api/models/test/), but allows greater control over the model's behavior.

Its primary use case is for more advanced unit testing than is possible with `TestModel`.

Here's a minimal example:

function\_model\_usage.py

```python
from pydantic_ai import Agent
from pydantic_ai import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel, AgentInfo

my_agent = Agent('openai:gpt-5.2')


async def model_function(
    messages: list[ModelMessage], info: AgentInfo
) -> ModelResponse:
    print(messages)
    """
    [
        ModelRequest(
            parts=[
                UserPromptPart(
                    content='Testing my agent...',
                    timestamp=datetime.datetime(...),
                )
            ],
            timestamp=datetime.datetime(...),
            run_id='...',
            conversation_id='...',
        )
    ]
    """
    print(info)
    """
    AgentInfo(
        function_tools=[],
        allow_text_output=True,
        output_tools=[],
        model_settings=None,
        model_request_parameters=ModelRequestParameters(
            function_tools=[], native_tools=[], tool_visibility={}, output_tools=[]
        ),
        instructions=None,
    )
    """
    return ModelResponse(parts=[TextPart('hello world')])


async def test_my_agent():
    """Unit test for my_agent, to be run by pytest."""
    with my_agent.override(model=FunctionModel(model_function)):
        result = await my_agent.run('Testing my agent...')
        assert result.output == 'hello world'
```

The function can be any callable with the right signature, not just a plain function. An instance whose `__call__` is `async def` is awaited directly like an `async def` function, and can carry state or configuration between requests:

function\_model\_callable\_instance.py

```py
from pydantic_ai import Agent, ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel


class CannedResponses:
    def __init__(self, *responses: str):
        self.responses = list(responses)

    async def __call__(
        self, messages: list[ModelMessage], info: AgentInfo
    ) -> ModelResponse:
        return ModelResponse(parts=[TextPart(self.responses.pop(0))])


model = FunctionModel(CannedResponses('hello', 'world'))
agent = Agent(model)

print(agent.run_sync('First').output)
#> hello
print(agent.run_sync('Second').output)
#> world
print(model.model_name)  # (1)
#> function:CannedResponses:
```

A callable instance has no `__name__`, so the generated model name uses its class name instead.

_(This example is complete, it can be run "as is")_

See [Unit testing with `FunctionModel`](https://pydantic.dev/docs/ai/guides/testing/#unit-testing-with-functionmodel) for detailed documentation.

### FunctionModel

**Bases:** `Model`

A model controlled by a local function.

Apart from `__init__`, all methods are private or match those of the base class.

#### Attributes

##### model\_name

The model name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The system / model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    function: FunctionDef,
    *,
    model_name: str | None = None,
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
) -> None
def __init__(
    *,
    stream_function: StreamFunctionDef,
    model_name: str | None = None,
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
) -> None
def __init__(
    function: FunctionDef,
    *,
    stream_function: StreamFunctionDef,
    model_name: str | None = None,
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
) -> None
```

Initialize a `FunctionModel`.

Either `function` or `stream_function` must be provided, providing both is allowed.

###### Parameters

**`function`** : `FunctionDef` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The function to call for non-streamed requests.

**`stream_function`** : `StreamFunctionDef` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The function to call for streamed requests.

**`model_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The name of the model. If not provided, a name is generated from the function names, falling back to the class name for a callable that has no `__name__`.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

##### supported\_native\_tools

`@classmethod`

```python
def supported_native_tools(cls) -> frozenset[type[AbstractNativeTool]]
```

FunctionModel supports all builtin tools for testing flexibility.

###### Returns

[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

### AgentInfo

Information about an agent.

This is passed as the second to functions used within [`FunctionModel`](https://pydantic.dev/docs/ai/api/models/function/#pydantic_ai.models.function.FunctionModel).

#### Attributes

##### function\_tools

The function tools available on this agent.

These are the tools registered via the [`tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.tool) and [`tool_plain`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.tool_plain) decorators.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition)\]

##### allow\_text\_output

Whether a plain text output is allowed.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### output\_tools

The tools that can called to produce the final output of the run.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ToolDefinition`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition)\]

##### model\_settings

The model settings passed to the run call.

**Type:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### model\_request\_parameters

The model request parameters passed to the run call.

**Type:** `ModelRequestParameters`

##### instructions

The instructions passed to model.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### DeltaToolCall

Incremental change to a tool call.

Used to describe a chunk when streaming structured responses.

#### Attributes

##### name

Incremental change to the name of the tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### json\_args

Incremental change to the arguments as JSON

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_call\_id

Incremental change to the tool call ID.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### DeltaThinkingPart

Incremental change to a thinking part.

Used to describe a chunk when streaming thinking responses.

#### Attributes

##### content

Incremental change to the thinking content.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### signature

Incremental change to the thinking signature.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### FunctionStreamedResponse

**Bases:** `StreamedResponse`

Implementation of `StreamedResponse` for [FunctionModel](https://pydantic.dev/docs/ai/api/models/function/#pydantic_ai.models.function.FunctionModel).

#### Attributes

##### model\_name

Get the model name of the response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_name

Get the provider name.

**Type:** [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### provider\_url

Get the provider base URL.

**Type:** [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

### DeltaToolCalls

A mapping of tool call IDs to incremental changes.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `dict[int, DeltaToolCall]`

### DeltaThinkingCalls

A mapping of thinking call IDs to incremental changes.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `dict[int, DeltaThinkingPart]`

### FunctionDef

A function used to generate a non-streamed response.

Any callable with this signature works: a plain `def`, an `async def`, or an instance with a `__call__` method of either kind. An async callable is awaited directly; a sync one is run in a worker thread.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[list[ModelMessage], AgentInfo], ModelResponse | Awaitable[ModelResponse]]`

### StreamFunctionDef

A function used to generate a streamed response.

Any callable with this signature works: an async generator function, a plain `def` returning an async iterator, or an instance with a `__call__` of either kind. What matters is the value returned, not the callable -- an `async def __call__` that _returns_ an async iterator instead of yielding does not match, and its coroutine is never awaited.

While this is defined as having return type of `AsyncIterator[str | DeltaToolCalls | DeltaThinkingCalls | BuiltinTools]`, it should really be considered as `AsyncIterator[str] | AsyncIterator[DeltaToolCalls] | AsyncIterator[DeltaThinkingCalls]`,

E.g. you need to yield all text, all `DeltaToolCalls`, all `DeltaThinkingCalls`, or all `BuiltinToolCallsReturns`, not mix them.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Callable[[list[ModelMessage], AgentInfo], AsyncIterator[str | DeltaToolCalls | DeltaThinkingCalls | BuiltinToolCallsReturns]]`

---
