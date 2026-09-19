# [pydantic_graph.basenode](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/)

# pydantic\_graph.basenode

### GraphRunContext

**Bases:** `Generic[StateT, DepsT]`

Context for a graph.

#### Attributes

##### state

The state of the graph.

**Type:** `StateT`

##### deps

Dependencies for the graph.

**Type:** `DepsT`

### BaseNode

**Bases:** `ABC`, `Generic[StateT, DepsT, NodeRunEndT]`

Base class for a node.

#### Methods

##### run

`@abstractmethod`

`@async`

```python
def run(
    ctx: GraphRunContext[StateT, DepsT],
) -> BaseNode[StateT, DepsT, Any] | End[NodeRunEndT]
```

Run the node.

This is an abstract method that must be implemented by subclasses.

Return types used at runtime

The return type of this method are read by `pydantic_graph` at runtime and used to define which nodes can be called next in the graph, and enforced when running the graph.

###### Returns

`BaseNode`\[`StateT`, `DepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | `End`\[`NodeRunEndT`\] -- The next node to run or [`End`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.End) to signal the end of the graph.

###### Parameters

**`ctx`** : `GraphRunContext`\[`StateT`, `DepsT`\]

The graph context.

##### get\_node\_id

`@cached`

`@classmethod`

```python
def get_node_id(cls) -> str
```

Get the ID of the node.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### End

**Bases:** `Generic[RunEndT]`

Type to return from a node to signal the end of the graph.

#### Attributes

##### data

Data to return from the graph.

**Type:** `RunEndT`

### Edge

Annotation to apply a label to an edge in a graph.

#### Attributes

##### label

Label for the edge.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### StateT

Type variable for the state in a graph.

**Default:** `TypeVar('StateT', default=object)`

### DepsT

Type variable for the dependencies of a graph and node.

**Default:** `TypeVar('DepsT', default=object, contravariant=True)`

### RunEndT

Covariant type variable for the return type of a graph [`run`](https://pydantic.dev/docs/ai/api/pydantic_graph/graph_builder/#pydantic_graph.graph_builder.Graph.run).

**Default:** `TypeVar('RunEndT', covariant=True, default=object)`

### NodeRunEndT

Covariant type variable for the return type of a node [`run`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.BaseNode.run).

**Default:** `TypeVar('NodeRunEndT', covariant=True, default=Never)`

---
