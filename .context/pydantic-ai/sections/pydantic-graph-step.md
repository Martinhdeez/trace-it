# [pydantic_graph.step](https://pydantic.dev/docs/ai/api/pydantic_graph/step/)

# pydantic\_graph.step

Step-based graph execution components.

This module provides the core abstractions for step-based graph execution, including step contexts, step functions, and step nodes that bridge between the declarative `BaseNode` API and the builder graph.

### StepContext

**Bases:** `Generic[StateT, DepsT, InputT]`

Context information passed to step functions during graph execution.

The step context provides access to the current graph state, dependencies, and input data for a step.

#### Attributes

##### inputs

The input data for this step.

This must be a property to ensure correct variance behavior

**Type:** `InputT`

### StepFunction

**Bases:** `Protocol[StateT, DepsT, InputT, OutputT]`

Protocol for step functions that can be executed in the graph.

Step functions are async callables that receive a step context and return a result.

#### Methods

##### \_\_call\_\_

```python
def __call__(ctx: StepContext[StateT, DepsT, InputT]) -> Awaitable[OutputT]
```

Execute the step function with the given context.

###### Returns

[`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[`OutputT`\] -- An awaitable that resolves to the step's output

###### Parameters

**`ctx`** : `StepContext`\[`StateT`, `DepsT`, `InputT`\]

The step context containing state, dependencies, and inputs

### StreamFunction

**Bases:** `Protocol[StateT, DepsT, InputT, OutputT]`

Protocol for stream functions that can be executed in the graph.

Stream functions are async callables that receive a step context and return an async iterator.

#### Methods

##### \_\_call\_\_

```python
def __call__(ctx: StepContext[StateT, DepsT, InputT]) -> AsyncIterator[OutputT]
```

Execute the stream function with the given context.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`OutputT`\] -- An async iterator yielding the streamed output

###### Parameters

**`ctx`** : `StepContext`\[`StateT`, `DepsT`, `InputT`\]

The step context containing state, dependencies, and inputs

### Step

**Bases:** `Generic[StateT, DepsT, InputT, OutputT]`

A step in the graph execution that wraps a step function.

Steps represent individual units of execution in the graph, encapsulating a step function along with metadata like ID and label.

#### Attributes

##### id

Unique identifier for this step.

**Type:** `NodeID` **Default:** `id`

##### label

Optional human-readable label for this step.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `label`

##### call

The step function to execute. This needs to be a property for proper variance inference.

**Type:** `StepFunction`\[`StateT`, `DepsT`, `InputT`, `OutputT`\]

#### Methods

##### as\_node

```python
def as_node(inputs: None = None) -> StepNode[StateT, DepsT]
def as_node(inputs: InputT) -> StepNode[StateT, DepsT]
```

Create a step node with bound inputs.

###### Returns

`StepNode`\[`StateT`, `DepsT`\] -- A [`StepNode`](https://pydantic.dev/docs/ai/api/pydantic_graph/step/#pydantic_graph.step.StepNode) with this step and the bound inputs

###### Parameters

**`inputs`** : `InputT` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The input data to bind to this step, or None

### StepNode

**Bases:** `BaseNode[StateT, DepsT, Any]`

A `BaseNode` that represents a builder step with bound inputs.

`StepNode` lets a [`BaseNode`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.BaseNode) subclass hand off to a builder [`Step`](https://pydantic.dev/docs/ai/api/pydantic_graph/step/#pydantic_graph.step.Step) by wrapping the step together with the value it should receive as `inputs`. It is not meant to be run directly; returning a `StepNode` from a `BaseNode.run` method tells the graph builder which step to invoke next.

#### Attributes

##### step

The step to execute.

**Type:** `Step`\[`StateT`, `DepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### inputs

The inputs bound to this step.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

#### Methods

##### run

`@async`

```python
def run(ctx: GraphRunContext[StateT, DepsT]) -> BaseNode[StateT, DepsT, Any] | End[Any]
```

Attempt to run the step node.

###### Returns

`BaseNode`\[`StateT`, `DepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | `End`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- The result of step execution

###### Parameters

**`ctx`** : `GraphRunContext`\[`StateT`, `DepsT`\]

The graph execution context

###### Raises

-   `NotImplementedError` -- Always raised as StepNode is not meant to be run directly

### NodeStep

**Bases:** `Step[StateT, DepsT, Any, BaseNode[StateT, DepsT, Any] | End[Any]]`

A step that wraps a `BaseNode` type for execution by the builder graph.

`NodeStep` lets a [`BaseNode`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.BaseNode) subclass participate as a step in the builder graph. It validates that the input is an instance of the expected node type and runs it with the appropriate graph context.

#### Attributes

##### node\_type

The BaseNode type this step executes.

**Type:** [`type`](https://docs.python.org/3/glossary.html#term-type)\[`BaseNode`\[`StateT`, `DepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] **Default:** `get_origin(node_type) or node_type`

#### Methods

##### \_\_init\_\_

```python
def __init__(
    node_type: type[BaseNode[StateT, DepsT, Any]],
    *,
    id: NodeID | None = None,
    label: str | None = None,
)
```

Initialize a node step.

###### Parameters

**`node_type`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`BaseNode`\[`StateT`, `DepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]

The BaseNode class this step will execute

**`id`** : `NodeID` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional unique identifier, defaults to the node's get\_node\_id()

**`label`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional human-readable label for this step

### AnyStepFunction

Type alias for a step function with any type parameters.

**Default:** `StepFunction[Any, Any, Any, Any]`

---
