# [pydantic_graph.decision](https://pydantic.dev/docs/ai/api/pydantic_graph/decision/)

# pydantic\_graph.decision

Decision node implementation for conditional branching in graph execution.

This module provides the Decision node type and related classes for implementing conditional branching logic in parallel control flow graphs. Decision nodes allow the graph to choose different execution paths based on runtime conditions.

### Decision

**Bases:** `Generic[StateT, DepsT, HandledT]`

Decision node for conditional branching in graph execution.

A Decision node evaluates conditions and routes execution to different branches based on the input data type or custom matching logic.

#### Attributes

##### id

Unique identifier for this decision node.

**Type:** `NodeID`

##### branches

List of branches that can be taken from this decision.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`DecisionBranch`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]

##### note

Optional documentation note for this decision.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### branch

```python
def branch(branch: DecisionBranch[T]) -> Decision[StateT, DepsT, HandledT | T]
```

Add a new branch to this decision.

###### Returns

`Decision`\[`StateT`, `DepsT`, `HandledT` | `T`\] -- A new Decision with the additional branch.

###### Parameters

**`branch`** : `DecisionBranch`\[`T`\]

The branch to add to this decision.

### DecisionBranch

**Bases:** `Generic[SourceT]`

Represents a single branch within a decision node.

Each branch defines the conditions under which it should be taken and the path to follow when those conditions are met.

Note: with the current design, it is actually _critical_ that this class is invariant in SourceT for the sake of type-checking that inputs to a Decision are actually handled. See the `# type: ignore` comment in `tests.graph.builder.test_graph_edge_cases.test_decision_no_matching_branch` for an example of how this works.

#### Attributes

##### source

The expected type of data for this branch.

This is necessary for exhaustiveness-checking when handling the inputs to a decision node.

**Type:** `TypeOrTypeExpression`\[`SourceT`\]

##### matches

An optional predicate function used to determine whether input data matches this branch.

If `None`, default logic is used which attempts to check the value for type-compatibility with the `source` type:

-   If `source` is `Any` or `object`, the branch will always match
-   If `source` is a `Literal` type, this branch will match if the value is one of the parametrizing literal values
-   If `source` is any other type, the value will be checked for matching using `isinstance`

Inputs are tested against each branch of a decision node in order, and the path of the first matching branch is used to handle the input value.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\], [`bool`](https://docs.python.org/3/builtins/functions.html#bool)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### path

The execution path to follow when an input value matches this branch of a decision node.

This can include transforming, mapping, and broadcasting the output before sending to the next node or nodes.

The path can also include position-aware labels which are used when generating mermaid diagrams.

**Type:** `Path`

##### destinations

The destination nodes that can be referenced by DestinationMarker in the path.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`AnyDestinationNode`\]

### DecisionBranchBuilder

**Bases:** `Generic[StateT, DepsT, OutputT, SourceT, HandledT]`

Builder for constructing decision branches with fluent API.

This builder provides methods to configure branches with destinations, forks, and transformations in a type-safe manner.

Instances of this class should be created using [`GraphBuilder.match`](https://pydantic.dev/docs/ai/api/pydantic_graph/graph_builder/#pydantic_graph.graph_builder.GraphBuilder), not created directly.

#### Methods

##### to

```python
def to(
    destination: DestinationNode[StateT, DepsT, OutputT] | type[BaseNode[StateT, DepsT, Any]],
    /,
    *extra_destinations: DestinationNode[StateT, DepsT, OutputT] | type[BaseNode[StateT, DepsT, Any]],
    fork_id: str | None = None,
) -> DecisionBranch[SourceT]
```

Set the destination(s) for this branch.

###### Returns

`DecisionBranch`\[`SourceT`\] -- A completed DecisionBranch with the specified destinations.

###### Parameters

**`destination`** : `DestinationNode`\[`StateT`, `DepsT`, `OutputT`\] | [`type`](https://docs.python.org/3/glossary.html#term-type)\[`BaseNode`\[`StateT`, `DepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]

The primary destination node.

**`*extra_destinations`** : `DestinationNode`\[`StateT`, `DepsT`, `OutputT`\] | [`type`](https://docs.python.org/3/glossary.html#term-type)\[`BaseNode`\[`StateT`, `DepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] _Default:_ `()`

Additional destination nodes.

**`fork_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional node ID to use for the resulting broadcast fork if multiple destinations are provided.

##### broadcast

```python
def broadcast(
    get_forks: Callable[[Self], Sequence[DecisionBranch[SourceT]]],
    /,
    *,
    fork_id: str | None = None,
) -> DecisionBranch[SourceT]
```

Broadcast this decision branch into multiple destinations.

###### Returns

`DecisionBranch`\[`SourceT`\] -- A completed DecisionBranch with the specified destinations.

###### Parameters

**`get_forks`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`Self`](https://docs.python.org/3/library/typing.html#typing.Self)\], [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`DecisionBranch`\[`SourceT`\]\]\]

The callback that will return a sequence of decision branches to broadcast to.

**`fork_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional node ID to use for the resulting broadcast fork.

##### transform

```python
def transform(
    func: TransformFunction[StateT, DepsT, OutputT, NewOutputT],
    /,
) -> DecisionBranchBuilder[StateT, DepsT, NewOutputT, SourceT, HandledT]
```

Apply a transformation to the branch's output.

###### Returns

`DecisionBranchBuilder`\[`StateT`, `DepsT`, `NewOutputT`, `SourceT`, `HandledT`\] -- A new DecisionBranchBuilder where the provided transform is applied prior to generating the final output.

###### Parameters

**`func`** : `TransformFunction`\[`StateT`, `DepsT`, `OutputT`, `NewOutputT`\]

Transformation function to apply.

##### map

```python
def map(
    *,
    fork_id: str | None = None,
    downstream_join_id: str | None = None,
) -> DecisionBranchBuilder[StateT, DepsT, T, SourceT, HandledT]
```

Spread the branch's output.

To do this, the current output must be iterable, and any subsequent steps in the path being built for this branch will be applied to each item of the current output in parallel.

###### Returns

`DecisionBranchBuilder`\[`StateT`, `DepsT`, `T`, `SourceT`, `HandledT`\] -- A new DecisionBranchBuilder where mapping is performed prior to generating the final output.

###### Parameters

**`fork_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for the fork, defaults to a generated value

**`downstream_join_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID of a downstream join node which is involved when mapping empty iterables

##### label

```python
def label(
    label: str,
) -> DecisionBranchBuilder[StateT, DepsT, OutputT, SourceT, HandledT]
```

Apply a label to the branch at the current point in the path being built.

These labels are only used in generated mermaid diagrams.

###### Returns

`DecisionBranchBuilder`\[`StateT`, `DepsT`, `OutputT`, `SourceT`, `HandledT`\] -- A new DecisionBranchBuilder where the label has been applied at the end of the current path being built.

###### Parameters

**`label`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The label to apply.

### StateT

Type variable for graph state.

**Default:** `TypeVar('StateT', infer_variance=True)`

### DepsT

Type variable for graph dependencies.

**Default:** `TypeVar('DepsT', infer_variance=True)`

### HandledT

Type variable used to track types handled by the branches of a Decision.

**Default:** `TypeVar('HandledT', infer_variance=True)`

### T

Generic type variable.

**Default:** `TypeVar('T', infer_variance=True)`

### SourceT

Type variable for source data for a DecisionBranch.

**Default:** `TypeVar('SourceT', infer_variance=True)`

### OutputT

Type variable for the output data of a node.

**Default:** `TypeVar('OutputT', infer_variance=True)`

### NewOutputT

Type variable for transformed output.

**Default:** `TypeVar('NewOutputT', infer_variance=True)`

---
