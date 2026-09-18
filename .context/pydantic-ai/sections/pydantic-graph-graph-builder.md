# [pydantic_graph.graph_builder](https://pydantic.dev/docs/ai/api/pydantic_graph/graph_builder/)

# pydantic\_graph.graph\_builder

Builder-based graph API: builder, graph runner, and mermaid rendering.

This module is the canonical home for the builder-based graph API: [`GraphBuilder`](https://pydantic.dev/docs/ai/api/pydantic_graph/graph_builder/#pydantic_graph.graph_builder.GraphBuilder) for declaratively constructing executable graphs, [`Graph`](https://pydantic.dev/docs/ai/api/pydantic_graph/graph_builder/#pydantic_graph.graph_builder.Graph) and [`GraphRun`](https://pydantic.dev/docs/ai/api/pydantic_graph/graph_builder/#pydantic_graph.graph_builder.GraphRun) for executing them, and the mermaid rendering helpers used by `Graph.render()`. The same public symbols are re-exported from `pydantic_graph` directly.

### EndMarker

**Bases:** `Generic[OutputT]`

A marker indicating the end of graph execution with a final value.

EndMarker is used internally to signal that the graph has completed execution and carries the final output value.

### ErrorMarker

A marker indicating that a graph node raised an exception.

Yielded by the graph iterator instead of raising immediately, allowing the caller to recover by sending new tasks via `GraphRun.next()` or `GraphRun.override_next()`. If the caller does not override, the error is re-raised on the next iteration.

#### Attributes

##### error

The exception raised by the node.

**Type:** [`BaseException`](https://docs.python.org/3/builtins/exceptions.html#BaseException)

### JoinItem

An item representing data flowing into a join operation.

JoinItem carries input data from a parallel execution path to a join node, along with metadata about which execution 'fork' it originated from.

#### Attributes

##### join\_id

The ID of the join node this item is targeting.

**Type:** `JoinID`

##### inputs

The input data for the join operation.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### fork\_stack

The stack of ForkStackItems that led to producing this join item.

**Type:** `ForkStack`

### Graph

**Bases:** `Generic[StateT, DepsT, InputT, OutputT]`

A complete graph definition ready for execution.

The Graph class represents a complete workflow graph with typed inputs, outputs, state, and dependencies. It contains all nodes, edges, and metadata needed for execution.

#### Attributes

##### name

Optional name for the graph, if not provided the name will be inferred from the calling frame on the first call to a graph method.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### state\_type

The type of the graph state.

**Type:** [`type`](https://docs.python.org/3/glossary.html#term-type)\[`StateT`\]

##### deps\_type

The type of the dependencies.

**Type:** [`type`](https://docs.python.org/3/glossary.html#term-type)\[`DepsT`\]

##### input\_type

The type of the input data.

**Type:** [`type`](https://docs.python.org/3/glossary.html#term-type)\[`InputT`\]

##### output\_type

The type of the output data.

**Type:** [`type`](https://docs.python.org/3/glossary.html#term-type)\[`OutputT`\]

##### auto\_instrument

Whether to automatically create instrumentation spans.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### nodes

All nodes in the graph indexed by their ID.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[`NodeID`, `AnyNode`\]

##### edges\_by\_source

Outgoing paths from each source node.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[`NodeID`, [`list`](https://docs.python.org/3/glossary.html#term-list)\[`Path`\]\]

##### parent\_forks

Parent fork information for each join node.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[`JoinID`, `ParentFork`\[`NodeID`\]\]

##### intermediate\_join\_nodes

For each join, the set of other joins that appear between it and its parent fork.

Used to determine which joins are "final" (have no other joins as intermediates) and which joins should preserve fork stacks when proceeding downstream.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[`JoinID`, [`set`](https://docs.python.org/3/reference/expressions.html#set)\[`JoinID`\]\]

#### Methods

##### get\_parent\_fork

```python
def get_parent_fork(join_id: JoinID) -> ParentFork[NodeID]
```

Get the parent fork information for a join node.

###### Returns

`ParentFork`\[`NodeID`\] -- The parent fork information for the join

###### Parameters

**`join_id`** : `JoinID`

The ID of the join node

###### Raises

-   `RuntimeError` -- If the join ID is not found or has no parent fork

##### is\_final\_join

```python
def is_final_join(join_id: JoinID) -> bool
```

Check if a join is 'final' (has no downstream joins with the same parent fork).

A join is non-final if it appears as an intermediate node for another join with the same parent fork.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool) -- True if the join is final, False if it's non-final

###### Parameters

**`join_id`** : `JoinID`

The ID of the join node

##### run

`@async`

```python
def run(
    *,
    state: StateT = None,
    deps: DepsT = None,
    inputs: InputT = None,
    span: AbstractContextManager[AbstractSpan] | None = None,
    infer_name: bool = True,
) -> OutputT
```

Execute the graph and return the final output.

This is the main entry point for graph execution. It runs the graph to completion and returns the final output value.

###### Returns

`OutputT` -- The final output from the graph execution

###### Parameters

**`state`** : `StateT` _Default:_ `None`

The graph state instance

**`deps`** : `DepsT` _Default:_ `None`

The dependencies instance

**`inputs`** : `InputT` _Default:_ `None`

The input data for the graph

**`span`** : `AbstractContextManager`\[`AbstractSpan`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional span for tracing/instrumentation

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to infer the graph name from the calling frame.

##### run\_sync

```python
def run_sync(
    *,
    state: StateT = None,
    deps: DepsT = None,
    inputs: InputT = None,
    span: AbstractContextManager[AbstractSpan] | None = None,
    infer_name: bool = True,
) -> OutputT
```

Synchronously execute the graph and return the final output.

This is a convenience wrapper around [`run`](https://pydantic.dev/docs/ai/api/pydantic_graph/graph_builder/#pydantic_graph.graph_builder.Graph.run) that runs the coroutine on the current event loop via `loop.run_until_complete(...)`. As such, it cannot be called from inside async code or when an event loop is already running.

###### Returns

`OutputT` -- The final output from the graph execution

###### Parameters

**`state`** : `StateT` _Default:_ `None`

The graph state instance

**`deps`** : `DepsT` _Default:_ `None`

The dependencies instance

**`inputs`** : `InputT` _Default:_ `None`

The input data for the graph

**`span`** : `AbstractContextManager`\[`AbstractSpan`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional span for tracing/instrumentation

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to infer the graph name from the calling frame.

##### iter

`@async`

```python
def iter(
    *,
    state: StateT = None,
    deps: DepsT = None,
    inputs: InputT = None,
    span: AbstractContextManager[AbstractSpan] | None = None,
    infer_name: bool = True,
) -> AsyncGenerator[GraphRun[StateT, DepsT, OutputT]]
```

Create an iterator for step-by-step graph execution.

This method allows for more fine-grained control over graph execution, enabling inspection of intermediate states and results.

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[`GraphRun`\[`StateT`, `DepsT`, `OutputT`\]\]

###### Parameters

**`state`** : `StateT` _Default:_ `None`

The graph state instance

**`deps`** : `DepsT` _Default:_ `None`

The dependencies instance

**`inputs`** : `InputT` _Default:_ `None`

The input data for the graph

**`span`** : `AbstractContextManager`\[`AbstractSpan`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional span for tracing/instrumentation

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to infer the graph name from the calling frame.

##### render

```python
def render(
    *,
    title: str | None = None,
    direction: StateDiagramDirection | None = None,
) -> str
```

Render the graph as a Mermaid diagram string.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) -- A string containing the Mermaid diagram representation

###### Parameters

**`title`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional title for the diagram

**`direction`** : `StateDiagramDirection` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional direction for the diagram layout

##### \_\_str\_\_

```python
def __str__() -> str
```

Return a Mermaid diagram representation of the graph.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) -- A string containing the Mermaid diagram of the graph

### GraphTaskRequest

A request to run a task representing the execution of a node in the graph.

GraphTaskRequest encapsulates all the information needed to execute a specific node, including its inputs and the fork context it's executing within.

#### Attributes

##### node\_id

The ID of the node to execute.

**Type:** `NodeID`

##### inputs

The input data for the node.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### fork\_stack

Stack of forks that have been entered.

Used by the GraphRun to decide when to proceed through joins.

**Type:** `ForkStack` **Default:** `field(repr=False)`

### GraphTask

**Bases:** `GraphTaskRequest`

A task representing the execution of a node in the graph.

GraphTask encapsulates all the information needed to execute a specific node, including its inputs and the fork context it's executing within, and has a unique ID to identify the task within the graph run.

#### Attributes

##### task\_id

Unique identifier for this task.

**Type:** `TaskID` **Default:** `field(repr=False)`

### GraphRun

**Bases:** `Generic[StateT, DepsT, OutputT]`

A single execution instance of a graph.

GraphRun manages the execution state for a single run of a graph, including task scheduling, fork/join coordination, and result tracking.

#### Attributes

##### graph

The graph being executed.

**Default:** `graph`

##### state

The graph state instance.

**Default:** `state`

##### deps

The dependencies instance.

**Default:** `deps`

##### inputs

The initial input data.

**Default:** `inputs`

##### next\_task

Get the next task(s) to be executed.

**Type:** `EndMarker`\[`OutputT`\] | `ErrorMarker` | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`GraphTask`\]

##### output

Get the final output if the graph has completed.

**Type:** `OutputT` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    graph: Graph[StateT, DepsT, InputT, OutputT],
    *,
    state: StateT,
    deps: DepsT,
    inputs: InputT,
    traceparent: str | None,
)
```

Initialize a graph run.

###### Parameters

**`graph`** : `Graph`\[`StateT`, `DepsT`, `InputT`, `OutputT`\]

The graph to execute

**`state`** : `StateT`

The graph state instance

**`deps`** : `DepsT`

The dependencies instance

**`inputs`** : `InputT`

The input data for the graph

**`traceparent`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

Optional trace parent for instrumentation

##### \_\_aiter\_\_

```python
def __aiter__() -> AsyncIterator[EndMarker[OutputT] | Sequence[GraphTask]]
```

Return self as an async iterator.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EndMarker`\[`OutputT`\] | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`GraphTask`\]\] -- Self for async iteration

##### \_\_anext\_\_

`@async`

```python
def __anext__() -> EndMarker[OutputT] | Sequence[GraphTask]
```

Get the next item in the async iteration.

###### Returns

`EndMarker`\[`OutputT`\] | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`GraphTask`\] -- The next execution result from the graph

###### Raises

-   `Exception` -- If a node raised an error and the caller has not recovered via `override_next()`.

##### next

`@async`

```python
def next(
    value: EndMarker[OutputT] | Sequence[GraphTaskRequest] | None = None,
) -> EndMarker[OutputT] | Sequence[GraphTask]
```

Advance the graph execution by one step.

This method allows for sending a value to the iterator, which is useful for resuming iteration or overriding intermediate results.

###### Returns

`EndMarker`\[`OutputT`\] | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`GraphTask`\] -- The next execution result: either an EndMarker, or sequence of GraphTasks

###### Parameters

**`value`** : `EndMarker`\[`OutputT`\] | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`GraphTaskRequest`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional value to send to the iterator

##### override\_next

```python
def override_next(value: Sequence[GraphTaskRequest] | EndMarker[OutputT]) -> None
```

Override the next pending step, allowing the graph to continue after an `End` or error.

This is used by hook systems (like `after_node_run` or `on_node_run_error`) to redirect the graph to a new node when the current step produced an `End` result or raised an error, or to signal early completion by passing an `EndMarker`.

Must only be called between iterations (not while an iteration is in flight).

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`value`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`GraphTaskRequest`\] | `EndMarker`\[`OutputT`\]

New task requests to execute next, or an `EndMarker` to signal completion.

### GraphBuilder

**Bases:** `Generic[StateT, DepsT, GraphInputT, GraphOutputT]`

A builder for constructing executable graph definitions.

GraphBuilder provides a fluent interface for defining nodes, edges, and routing in a graph workflow. It supports typed state, dependencies, and input/output validation.

#### Attributes

##### name

Optional name for the graph, if not provided the name will be inferred from the calling frame on the first call to a graph method.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `name`

##### state\_type

The type of the graph state.

**Type:** `TypeOrTypeExpression`\[`StateT`\] **Default:** `state_type`

##### deps\_type

The type of the dependencies.

**Type:** `TypeOrTypeExpression`\[`DepsT`\] **Default:** `deps_type`

##### input\_type

The type of the graph input data.

**Type:** `TypeOrTypeExpression`\[`GraphInputT`\] **Default:** `input_type`

##### output\_type

The type of the graph output data.

**Type:** `TypeOrTypeExpression`\[`GraphOutputT`\] **Default:** `output_type`

##### auto\_instrument

Whether to automatically create instrumentation spans.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `auto_instrument`

##### start\_node

Get the start node for the graph.

**Type:** `StartNode`\[`GraphInputT`\]

##### end\_node

Get the end node for the graph.

**Type:** `EndNode`\[`GraphOutputT`\]

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    name: str | None = None,
    state_type: TypeOrTypeExpression[StateT] = NoneType,
    deps_type: TypeOrTypeExpression[DepsT] = NoneType,
    input_type: TypeOrTypeExpression[GraphInputT] = NoneType,
    output_type: TypeOrTypeExpression[GraphOutputT] = NoneType,
    auto_instrument: bool = True,
)
```

Initialize a graph builder.

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional name for the graph, if not provided the name will be inferred from the calling frame on the first call to a graph method.

**`state_type`** : `TypeOrTypeExpression`\[`StateT`\] _Default:_ `NoneType`

The type of the graph state

**`deps_type`** : `TypeOrTypeExpression`\[`DepsT`\] _Default:_ `NoneType`

The type of the dependencies

**`input_type`** : `TypeOrTypeExpression`\[`GraphInputT`\] _Default:_ `NoneType`

The type of the graph input data

**`output_type`** : `TypeOrTypeExpression`\[`GraphOutputT`\] _Default:_ `NoneType`

The type of the graph output data

**`auto_instrument`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to automatically create instrumentation spans

##### step

```python
def step(
    *,
    node_id: str | None = None,
    label: str | None = None,
) -> Callable[[StepFunction[StateT, DepsT, InputT, OutputT]], Step[StateT, DepsT, InputT, OutputT]]
def step(
    call: StepFunction[StateT, DepsT, InputT, OutputT],
    *,
    node_id: str | None = None,
    label: str | None = None,
) -> Step[StateT, DepsT, InputT, OutputT]
```

Create a step from a step function.

This method can be used as a decorator or called directly to create a step node from an async function.

###### Returns

`Step`\[`StateT`, `DepsT`, `InputT`, `OutputT`\] | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`StepFunction`\[`StateT`, `DepsT`, `InputT`, `OutputT`\]\], `Step`\[`StateT`, `DepsT`, `InputT`, `OutputT`\]\] -- Either a Step instance or a decorator function

###### Parameters

**`call`** : `StepFunction`\[`StateT`, `DepsT`, `InputT`, `OutputT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The step function to wrap

**`node_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for the node

**`label`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional human-readable label

##### stream

```python
def stream(
    *,
    node_id: str | None = None,
    label: str | None = None,
) -> Callable[[StreamFunction[StateT, DepsT, InputT, OutputT]], Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]]
def stream(
    call: StreamFunction[StateT, DepsT, InputT, OutputT],
    *,
    node_id: str | None = None,
    label: str | None = None,
) -> Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]
def stream(
    call: StreamFunction[StateT, DepsT, InputT, OutputT] | None = None,
    *,
    node_id: str | None = None,
    label: str | None = None,
) -> Step[StateT, DepsT, InputT, AsyncIterable[OutputT]] | Callable[[StreamFunction[StateT, DepsT, InputT, OutputT]], Step[StateT, DepsT, InputT, AsyncIterable[OutputT]]]
```

Create a step from an async iterator (which functions like a "stream").

This method can be used as a decorator or called directly to create a step node from an async function.

###### Returns

`Step`\[`StateT`, `DepsT`, `InputT`, [`AsyncIterable`](https://docs.python.org/3/library/typing.html#typing.AsyncIterable)\[`OutputT`\]\] | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`StreamFunction`\[`StateT`, `DepsT`, `InputT`, `OutputT`\]\], `Step`\[`StateT`, `DepsT`, `InputT`, [`AsyncIterable`](https://docs.python.org/3/library/typing.html#typing.AsyncIterable)\[`OutputT`\]\]\] -- Either a Step instance or a decorator function

###### Parameters

**`call`** : `StreamFunction`\[`StateT`, `DepsT`, `InputT`, `OutputT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The step function to wrap

**`node_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for the node

**`label`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional human-readable label

##### add

```python
def add(*edges: EdgePath[StateT, DepsT]) -> None
```

Add one or more edge paths to the graph.

This method processes edge paths and automatically creates any necessary fork nodes for broadcasts and maps.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`*edges`** : `EdgePath`\[`StateT`, `DepsT`\] _Default:_ `()`

The edge paths to add to the graph

##### add\_edge

```python
def add_edge(
    source: Source[T],
    destination: Destination[T],
    *,
    label: str | None = None,
) -> None
```

Add a simple edge between two nodes.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`source`** : `Source`\[`T`\]

The source node

**`destination`** : `Destination`\[`T`\]

The destination node

**`label`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional label for the edge

##### add\_mapping\_edge

```python
def add_mapping_edge(
    source: Source[Iterable[T]],
    map_to: Destination[T],
    *,
    pre_map_label: str | None = None,
    post_map_label: str | None = None,
    fork_id: ForkID | None = None,
    downstream_join_id: JoinID | None = None,
) -> None
```

Add an edge that maps iterable data across parallel paths.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`source`** : `Source`\[[`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)\[`T`\]\]

The source node that produces iterable data

**`map_to`** : `Destination`\[`T`\]

The destination node that receives individual items

**`pre_map_label`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional label before the map operation

**`post_map_label`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional label after the map operation

**`fork_id`** : `ForkID` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for the fork node produced for this map operation

**`downstream_join_id`** : `JoinID` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID of a join node that will always be downstream of this map. Specifying this ensures correct handling if you try to map an empty iterable.

##### edge\_from

```python
def edge_from(
    *sources: Source[SourceOutputT],
) -> EdgePathBuilder[StateT, DepsT, SourceOutputT]
```

Create an edge path builder starting from the given source nodes.

###### Returns

`EdgePathBuilder`\[`StateT`, `DepsT`, `SourceOutputT`\] -- An EdgePathBuilder for constructing the complete edge path

###### Parameters

**`*sources`** : `Source`\[`SourceOutputT`\] _Default:_ `()`

The source nodes to start the edge path from

##### decision

```python
def decision(
    *,
    note: str | None = None,
    node_id: str | None = None,
) -> Decision[StateT, DepsT, Never]
```

Create a new decision node.

###### Returns

`Decision`\[`StateT`, `DepsT`, [`Never`](https://docs.python.org/3/library/typing.html#typing.Never)\] -- A new Decision node with no branches

###### Parameters

**`note`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional note to describe the decision logic

**`node_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for the node produced for this decision logic

##### match

```python
def match(
    source: TypeOrTypeExpression[SourceT],
    *,
    matches: Callable[[Any], bool] | None = None,
) -> DecisionBranchBuilder[StateT, DepsT, SourceT, SourceT, Never]
```

Create a decision branch matcher.

###### Returns

`DecisionBranchBuilder`\[`StateT`, `DepsT`, `SourceT`, `SourceT`, [`Never`](https://docs.python.org/3/library/typing.html#typing.Never)\] -- A DecisionBranchBuilder for constructing the branch

###### Parameters

**`source`** : `TypeOrTypeExpression`\[`SourceT`\]

The type or type expression to match against

**`matches`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\], [`bool`](https://docs.python.org/3/builtins/functions.html#bool)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional custom matching function

##### match\_node

```python
def match_node(
    source: type[SourceNodeT],
    *,
    matches: Callable[[Any], bool] | None = None,
) -> DecisionBranch[SourceNodeT]
```

Create a decision branch for `BaseNode` subclasses.

This is similar to `match()` but specifically designed for matching against `BaseNode` types.

###### Returns

`DecisionBranch`\[`SourceNodeT`\] -- A `DecisionBranch` for the `BaseNode` type

###### Parameters

**`source`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`SourceNodeT`\]

The `BaseNode` subclass to match against

**`matches`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\], [`bool`](https://docs.python.org/3/builtins/functions.html#bool)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional custom matching function

##### node

```python
def node(
    node_type: type[BaseNode[StateT, DepsT, GraphOutputT]],
) -> EdgePath[StateT, DepsT]
```

Create an edge path from a `BaseNode` class.

This method integrates a `BaseNode` subclass into the builder graph by analyzing its `run` return type hints and creating appropriate edges.

###### Returns

`EdgePath`\[`StateT`, `DepsT`\] -- An `EdgePath` representing the node and its connections

###### Parameters

**`node_type`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`BaseNode`\[`StateT`, `DepsT`, `GraphOutputT`\]\]

The `BaseNode` subclass to integrate

###### Raises

-   `GraphSetupError` -- If the node type is missing required type hints

##### build

```python
def build(
    validate_graph_structure: bool = True,
) -> Graph[StateT, DepsT, GraphInputT, GraphOutputT]
```

Build the final executable graph from the accumulated nodes and edges.

This method performs validation, normalization, and analysis of the graph structure to create a complete, executable graph instance.

###### Returns

`Graph`\[`StateT`, `DepsT`, `GraphInputT`, `GraphOutputT`\] -- A complete Graph instance ready for execution

###### Parameters

**`validate_graph_structure`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

whether to perform validation of the graph structure See the docstring of \_validate\_graph\_structure below for more details.

###### Raises

-   `ValueError` -- If the graph structure is invalid (e.g., join without parent fork)

### MermaidNode

A mermaid node.

### MermaidEdge

A mermaid edge.

### MermaidGraph

A mermaid graph.

### build\_mermaid\_graph

```python
def build_mermaid_graph(
    graph_nodes: dict[NodeID, AnyNode],
    graph_edges_by_source: dict[NodeID, list[Path]],
) -> MermaidGraph
```

Build a mermaid graph.

#### Returns

`MermaidGraph`

### StateT

Type variable for graph state.

**Default:** `TypeVar('StateT', infer_variance=True)`

### DepsT

Type variable for graph dependencies.

**Default:** `TypeVar('DepsT', infer_variance=True)`

### InputT

Type variable for graph inputs.

**Default:** `TypeVar('InputT', infer_variance=True)`

### OutputT

Type variable for graph outputs.

**Default:** `TypeVar('OutputT', infer_variance=True)`

### DEFAULT\_HIGHLIGHT\_CSS

The default CSS to use for highlighting nodes.

**Default:** `'fill:#fdff32'`

### StateDiagramDirection

Used to specify the direction of the state diagram generated by mermaid.

-   `'TB'`: Top to bottom, this is the default for mermaid charts.
-   `'LR'`: Left to right
-   `'RL'`: Right to left
-   `'BT'`: Bottom to top

**Default:** `Literal['TB', 'LR', 'RL', 'BT']`

---
