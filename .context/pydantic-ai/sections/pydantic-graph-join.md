# [pydantic_graph.join](https://pydantic.dev/docs/ai/api/pydantic_graph/join/)

# pydantic\_graph.join

Join operations and reducers for graph execution.

This module provides the core components for joining parallel execution paths in a graph, including various reducer types that aggregate data from multiple sources into a single output.

### JoinState

The state of a join during graph execution associated to a particular fork run.

### ReducerContext

**Bases:** `Generic[StateT, DepsT]`

Context information passed to reducer functions during graph execution.

The reducer context provides access to the current graph state and dependencies.

#### Attributes

##### state

The state of the graph run.

**Type:** `StateT`

##### deps

The deps for the graph run.

**Type:** `DepsT`

#### Methods

##### cancel\_sibling\_tasks

```python
def cancel_sibling_tasks()
```

Cancel all sibling tasks created from the same fork.

You can call this if you want your join to have early-stopping behavior.

### SupportsSum

**Bases:** [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

A protocol for a type that supports adding to itself.

### ReduceFirstValue

**Bases:** `Generic[T]`

A reducer that returns the first value it encounters, and cancels all other tasks.

#### Methods

##### \_\_call\_\_

```python
def __call__(ctx: ReducerContext[object, object], current: T, inputs: T) -> T
```

The reducer function.

###### Returns

`T`

### Join

**Bases:** `Generic[StateT, DepsT, InputT, OutputT]`

A join operation that synchronizes and aggregates parallel execution paths.

A join defines how to combine outputs from multiple parallel execution paths using a [`ReducerFunction`](https://pydantic.dev/docs/ai/api/pydantic_graph/join/#pydantic_graph.join.ReducerFunction). It specifies which fork it joins (if any) and manages the initialization of reducers.

#### Methods

##### as\_node

```python
def as_node(inputs: None = None) -> JoinNode[StateT, DepsT]
def as_node(inputs: InputT) -> JoinNode[StateT, DepsT]
```

Create a join node with bound inputs.

###### Returns

`JoinNode`\[`StateT`, `DepsT`\] -- A [`JoinNode`](https://pydantic.dev/docs/ai/api/pydantic_graph/join/#pydantic_graph.join.JoinNode) with this join and the bound inputs

###### Parameters

**`inputs`** : `InputT` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The input data to bind to this join, or None

### JoinNode

**Bases:** `BaseNode[StateT, DepsT, Any]`

A `BaseNode` that represents a builder join with bound inputs.

`JoinNode` lets a [`BaseNode`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.BaseNode) subclass hand off to a builder [`Join`](https://pydantic.dev/docs/ai/api/pydantic_graph/join/#pydantic_graph.join.Join) by wrapping the join together with the value it should receive as `inputs`. It is not meant to be run directly; returning a `JoinNode` from a `BaseNode.run` method tells the graph builder which join to invoke next.

#### Attributes

##### join

The step to execute.

**Type:** `Join`\[`StateT`, `DepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### inputs

The inputs bound to this step.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

#### Methods

##### run

`@async`

```python
def run(ctx: GraphRunContext[StateT, DepsT]) -> BaseNode[StateT, DepsT, Any] | End[Any]
```

Attempt to run the join node.

###### Returns

`BaseNode`\[`StateT`, `DepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | `End`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- The result of step execution

###### Parameters

**`ctx`** : `GraphRunContext`\[`StateT`, `DepsT`\]

The graph execution context

###### Raises

-   `NotImplementedError` -- Always raised as StepNode is not meant to be run directly

### reduce\_null

```python
def reduce_null(current: None, inputs: Any) -> None
```

A reducer that discards all input data and returns None.

#### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### reduce\_list\_append

```python
def reduce_list_append(current: list[T], inputs: T) -> list[T]
```

A reducer that appends to a list.

#### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`T`\]

### reduce\_list\_extend

```python
def reduce_list_extend(current: list[T], inputs: Iterable[T]) -> list[T]
```

A reducer that extends a list.

#### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`T`\]

### reduce\_dict\_update

```python
def reduce_dict_update(current: dict[K, V], inputs: Mapping[K, V]) -> dict[K, V]
```

A reducer that updates a dict.

#### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[`K`, `V`\]

### reduce\_sum

```python
def reduce_sum(current: NumericT, inputs: NumericT) -> NumericT
```

A reducer that sums numbers.

#### Returns

`NumericT`

### ReducerFunction

A function used for reducing inputs to a join node.

**Default:** `TypeAliasType('ReducerFunction', ContextReducerFunction[StateT, DepsT, InputT, OutputT] | PlainReducerFunction[InputT, OutputT], type_params=(StateT, DepsT, InputT, OutputT))`

---
