# [pydantic_ai.output](https://pydantic.dev/docs/ai/api/pydantic-ai/output/)

# pydantic\_ai.output

### ToolOutput

**Bases:** `Generic[OutputDataT]`

Marker class to use a tool for output and optionally customize the tool.

Example:

tool\_output.py

```python
from pydantic import BaseModel

from pydantic_ai import Agent, ToolOutput


class Fruit(BaseModel):
    name: str
    color: str


class Vehicle(BaseModel):
    name: str
    wheels: int


agent = Agent(
    'openai:gpt-5.2',
    output_type=[
        ToolOutput(Fruit, name='return_fruit'),
        ToolOutput(Vehicle, name='return_vehicle'),
    ],
)
result = agent.run_sync('What is a banana?')
print(repr(result.output))
#> Fruit(name='banana', color='yellow')
```

#### Attributes

##### output

An output type or function.

**Type:** `OutputTypeOrFunction`\[`OutputDataT`\] **Default:** `type_`

##### name

The name of the tool that will be passed to the model. If not specified and only one output is provided, `final_result` will be used. If multiple outputs are provided, the name of the output type or function will be added to the tool name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `name`

##### description

The description of the tool that will be passed to the model. If not specified, the docstring of the output type or function will be used.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `description`

##### max\_retries

Per-tool retry limit for this output tool.

Overrides the output side of the agent's retry budget, which itself acts as the per-tool default for output tools that do not specify their own limit. If not set, the agent-level value is used.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `max_retries`

##### strict

Whether to use strict mode for the tool.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `strict`

##### sequential

Whether this output tool must run as a barrier, not overlapping with other tool calls.

Only meaningful under `end_strategy='exhaustive'`, where tools otherwise run in parallel: a `sequential=True` output tool runs alone, so function tools the model emitted before it complete first. Under `'early'`/`'graceful'` output tools already run sequentially, so this has no effect.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `sequential`

### NativeOutput

**Bases:** `Generic[OutputDataT]`

Marker class to use the model's native structured outputs functionality for outputs and optionally customize the name and description.

Example:

native\_output.py

```python
from pydantic_ai import Agent, NativeOutput

from tool_output import Fruit, Vehicle

agent = Agent(
    'openai:gpt-5.2',
    output_type=NativeOutput(
        [Fruit, Vehicle],
        name='Fruit or vehicle',
        description='Return a fruit or vehicle.'
    ),
)
result = agent.run_sync('What is a Ford Explorer?')
print(repr(result.output))
#> Vehicle(name='Ford Explorer', wheels=4)
```

#### Attributes

##### outputs

The output types or functions.

**Type:** `OutputTypeOrFunction`\[`OutputDataT`\] | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`OutputTypeOrFunction`\[`OutputDataT`\]\] **Default:** `outputs`

##### name

The name of the structured output that will be passed to the model. If not specified and only one output is provided, the name of the output type or function will be used.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `name`

##### description

The description of the structured output that will be passed to the model. If not specified and only one output is provided, the docstring of the output type or function will be used.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `description`

##### strict

Whether to use strict mode for the output, if the model supports it.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `strict`

##### template

Template for the prompt passed to the model. The '{schema}' placeholder will be replaced with the output JSON schema. If no template is specified but the model's profile indicates that it requires the schema to be sent as a prompt, the default template specified on the profile will be used. Set to `False` to disable the schema prompt entirely.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\[[`False`](https://docs.python.org/3/builtins/constants.html#False)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `template`

### PromptedOutput

**Bases:** `Generic[OutputDataT]`

Marker class to use a prompt to tell the model what to output and optionally customize the prompt.

Example:

prompted\_output.py

```python
from pydantic import BaseModel

from pydantic_ai import Agent, PromptedOutput

from tool_output import Vehicle


class Device(BaseModel):
    name: str
    kind: str


agent = Agent(
    'openai:gpt-5.2',
    output_type=PromptedOutput(
        [Vehicle, Device],
        name='Vehicle or device',
        description='Return a vehicle or device.'
    ),
)
result = agent.run_sync('What is a MacBook?')
print(repr(result.output))
#> Device(name='MacBook', kind='laptop')

agent = Agent(
    'openai:gpt-5.2',
    output_type=PromptedOutput(
        [Vehicle, Device],
        template='Gimme some JSON: {schema}'
    ),
)
result = agent.run_sync('What is a Ford Explorer?')
print(repr(result.output))
#> Vehicle(name='Ford Explorer', wheels=4)
```

#### Attributes

##### outputs

The output types or functions.

**Type:** `OutputTypeOrFunction`\[`OutputDataT`\] | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`OutputTypeOrFunction`\[`OutputDataT`\]\] **Default:** `outputs`

##### name

The name of the structured output that will be passed to the model. If not specified and only one output is provided, the name of the output type or function will be used.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `name`

##### description

The description that will be passed to the model. If not specified and only one output is provided, the docstring of the output type or function will be used.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `description`

##### template

Template for the prompt passed to the model. The '{schema}' placeholder will be replaced with the output JSON schema. If not specified, the default template specified on the model's profile will be used. Set to `False` to disable the schema prompt entirely.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\[[`False`](https://docs.python.org/3/builtins/constants.html#False)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `template`

### TextOutput

**Bases:** `Generic[OutputDataT]`

Marker class to use text output for an output function taking a string argument.

Example:

```python
from pydantic_ai import Agent, TextOutput


def split_into_words(text: str) -> list[str]:
    return text.split()


agent = Agent(
    'openai:gpt-5.2',
    output_type=TextOutput(split_into_words),
)
result = agent.run_sync('Who was Albert Einstein?')
print(result.output)
#> ['Albert', 'Einstein', 'was', 'a', 'German-born', 'theoretical', 'physicist.']
```

Note

When streaming, [`stream_text()`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.stream_text) does not apply the wrapped function. Use [`stream_output()`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.stream_output) to stream the value it produces.

#### Attributes

##### output\_function

The function that will be called to process the model's plain text output. The function must take a single string argument.

**Type:** `TextOutputFunc`\[`OutputDataT`\]

### OutputObjectDefinition

Definition of an output object used for structured output generation.

### StructuredDict

```python
def StructuredDict(
    json_schema: JsonSchemaValue,
    name: str | None = None,
    description: str | None = None,
) -> type[JsonSchemaValue]
```

Returns a `dict[str, Any]` subclass with a JSON schema attached that will be used for structured output.

Example:

structured\_dict.py

```python
from pydantic_ai import Agent, StructuredDict

schema = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'age': {'type': 'integer'}
    },
    'required': ['name', 'age']
}

agent = Agent('openai:gpt-5.2', output_type=StructuredDict(schema))
result = agent.run_sync('Create a person')
print(result.output)
#> {'name': 'John Doe', 'age': 30}
```

#### Returns

[`type`](https://docs.python.org/3/glossary.html#term-type)\[`JsonSchemaValue`\]

#### Parameters

**`json_schema`** : `JsonSchemaValue`

A JSON schema of type `object` defining the structure of the dictionary content.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional name of the structured output. If not provided, the `title` field of the JSON schema will be used if it's present.

**`description`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional description of the structured output. If not provided, the `description` field of the JSON schema will be used if it's present.

### OutputDataT

Covariant type variable for the output data type of a run.

**Default:** `TypeVar('OutputDataT', default=str, covariant=True)`

---
