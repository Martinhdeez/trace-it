# [pydantic_ai.models.test](https://pydantic.dev/docs/ai/api/models/test/)

# pydantic\_ai.models.test

Utility model for quickly testing apps built with Pydantic AI.

Here's a minimal example:

test\_model\_usage.py

```python
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

my_agent = Agent('openai:gpt-5.2', instructions='...')


async def test_my_agent():
    """Unit test for my_agent, to be run by pytest."""
    m = TestModel()
    with my_agent.override(model=m):
        result = await my_agent.run('Testing my agent...')
        assert result.output == 'success (no tool calls)'
    assert m.last_model_request_parameters.function_tools == []
```

See [Unit testing with `TestModel`](https://pydantic.dev/docs/ai/guides/testing/#unit-testing-with-testmodel) for detailed documentation.

### TestModel

**Bases:** `Model`

A model specifically for testing purposes.

This will (by default) call all tools in the agent, then return a tool response if possible, otherwise a plain response.

How useful this model is will vary significantly.

Apart from `__init__` derived by the `dataclass` decorator, all methods are private or match those of the base class.

#### Attributes

##### call\_tools

List of tools to call. If `'all'`, all tools will be called.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['all'\] **Default:** `call_tools`

##### custom\_output\_text

If set, this text is returned as the final output.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `custom_output_text`

##### custom\_output\_args

If set, these args will be passed to the output tool.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `custom_output_args`

##### seed

Seed for generating random data.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `seed`

##### last\_model\_request\_parameters

The last ModelRequestParameters passed to the model in a request.

The ModelRequestParameters contains information about the function and output tools available during request handling.

This is set when a request is made, so will reflect the function tools from the last step of the last run.

**Type:** `ModelRequestParameters` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### model\_name

The model name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    call_tools: list[str] | Literal['all'] = 'all',
    custom_output_text: str | None = None,
    custom_output_args: Any | None = None,
    seed: int = 0,
    model_name: str = 'test',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize TestModel with optional settings and profile.

##### supported\_native\_tools

`@classmethod`

```python
def supported_native_tools(cls) -> frozenset[type[AbstractNativeTool]]
```

TestModel supports all native tools for testing flexibility.

`ToolSearchTool` is excluded because TestModel can't emulate provider-native tool search. Auto-injected `ToolSearch` capabilities work transparently thanks to the local `search_tools` fallback.

###### Returns

[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

### TestStreamedResponse

**Bases:** `StreamedResponse`

A structured response that streams test data.

#### Attributes

##### model\_name

Get the model name of the response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_name

Get the provider name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_url

Get the provider base URL.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

---
