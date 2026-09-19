# [pydantic_graph.node](https://pydantic.dev/docs/ai/api/pydantic_graph/node/)

# pydantic\_graph.node

Core node types for graph construction and execution.

This module defines the fundamental node types used to build execution graphs, including start/end nodes and fork nodes for parallel execution.

### StartNode

**Bases:** `Generic[OutputT]`

Entry point node for graph execution.

The StartNode represents the beginning of a graph execution flow.

#### Attributes

##### id

Fixed identifier for the start node.

**Default:** `NodeID('__start__')`

### EndNode

**Bases:** `Generic[InputT]`

Terminal node representing the completion of graph execution.

The EndNode marks the successful completion of a graph execution flow and can collect the final output data.

#### Attributes

##### id

Fixed identifier for the end node.

**Default:** `NodeID('__end__')`

### Fork

**Bases:** `Generic[InputT, OutputT]`

Fork node that creates parallel execution branches.

A Fork node splits the execution flow into multiple parallel branches, enabling concurrent execution of downstream nodes. It can either map a sequence across multiple branches or duplicate data to each branch.

#### Attributes

##### id

Unique identifier for this fork node.

**Type:** `ForkID`

##### is\_map

Determines fork behavior.

If True, InputT must be Sequence\[OutputT\] and each element is sent to a separate branch. If False, InputT must be OutputT and the same data is sent to all branches.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### downstream\_join\_id

Optional identifier of a downstream join node that should be jumped to if mapping an empty iterable.

**Type:** `JoinID` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### StateT

Type variable for graph state.

**Default:** `TypeVar('StateT', infer_variance=True)`

### OutputT

Type variable for node output data.

**Default:** `TypeVar('OutputT', infer_variance=True)`

### InputT

Type variable for node input data.

**Default:** `TypeVar('InputT', infer_variance=True)`

---
