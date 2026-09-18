# [pydantic_evals.otel](https://pydantic.dev/docs/ai/api/pydantic_evals/otel/)

# pydantic\_evals.otel

### SpanTreeRecordingError

**Bases:** [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

An exception that is used to provide the reason why a SpanTree was not recorded by `context_subtree`.

This may be due to missing dependencies, a tracer provider not having been set, or a custom TracerProvider that does not support `add_span_processor`.

#### Methods

##### \_\_get\_pydantic\_core\_schema\_\_

`@classmethod`

```python
def __get_pydantic_core_schema__(cls, _: Any, __: Any) -> core_schema.CoreSchema
```

Pydantic core schema to allow `SpanTreeRecordingError` to be (de)serialized.

Only the human-readable `message` is preserved by design: the exception's `__context__`, `__cause__`, and traceback (e.g. the underlying `ImportError` chained in `context_subtree`) are dropped on serialization and not reconstructed on the way back.

###### Returns

`core_schema.CoreSchema`

### SpanQuery

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

A serializable query for filtering SpanNodes based on various conditions.

All fields are optional and combined with AND logic by default.

#### Attributes

##### has\_attributes

Attribute values are compared with equality; a dict or list value also matches an attribute stored as its JSON serialization, since OTel attributes cannot hold nested objects and instrumentation libraries like Logfire store them as JSON strings. A list value also matches an attribute stored as a tuple.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### stop\_recursing\_when

If present, stop recursing through ancestors or descendants at nodes that match this condition.

**Type:** `SpanQuery`

### SpanNode

A node in the span tree; provides references to parents/children for easy traversal and queries.

#### Attributes

##### status

The span's status; `'error'` if the operation the span represents raised an exception.

**Type:** `SpanStatus` **Default:** `'unset'`

##### duration

Return the span's duration as a timedelta.

**Type:** `timedelta`

##### descendants

Return all descendants of this node in DFS order.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`SpanNode`\]

##### ancestors

Return all ancestors of this node.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`SpanNode`\]

#### Methods

##### add\_child

```python
def add_child(child: SpanNode) -> None
```

Attach a child node to this node's list of children.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### find\_children

```python
def find_children(predicate: SpanQuery | SpanPredicate) -> list[SpanNode]
```

Return all immediate children that satisfy the given predicate.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`SpanNode`\]

##### first\_child

```python
def first_child(predicate: SpanQuery | SpanPredicate) -> SpanNode | None
```

Return the first immediate child that satisfies the given predicate, or None if none match.

###### Returns

`SpanNode` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### any\_child

```python
def any_child(predicate: SpanQuery | SpanPredicate) -> bool
```

Returns True if there is at least one child that satisfies the predicate.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### find\_descendants

```python
def find_descendants(
    predicate: SpanQuery | SpanPredicate,
    stop_recursing_when: SpanQuery | SpanPredicate | None = None,
) -> list[SpanNode]
```

Return all descendant nodes that satisfy the given predicate in DFS order.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`SpanNode`\]

##### first\_descendant

```python
def first_descendant(
    predicate: SpanQuery | SpanPredicate,
    stop_recursing_when: SpanQuery | SpanPredicate | None = None,
) -> SpanNode | None
```

DFS: Return the first descendant (in DFS order) that satisfies the given predicate, or `None` if none match.

###### Returns

`SpanNode` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### any\_descendant

```python
def any_descendant(
    predicate: SpanQuery | SpanPredicate,
    stop_recursing_when: SpanQuery | SpanPredicate | None = None,
) -> bool
```

Returns `True` if there is at least one descendant that satisfies the predicate.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### find\_ancestors

```python
def find_ancestors(
    predicate: SpanQuery | SpanPredicate,
    stop_recursing_when: SpanQuery | SpanPredicate | None = None,
) -> list[SpanNode]
```

Return all ancestors that satisfy the given predicate.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`SpanNode`\]

##### first\_ancestor

```python
def first_ancestor(
    predicate: SpanQuery | SpanPredicate,
    stop_recursing_when: SpanQuery | SpanPredicate | None = None,
) -> SpanNode | None
```

Return the closest ancestor that satisfies the given predicate, or `None` if none match.

###### Returns

`SpanNode` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### any\_ancestor

```python
def any_ancestor(
    predicate: SpanQuery | SpanPredicate,
    stop_recursing_when: SpanQuery | SpanPredicate | None = None,
) -> bool
```

Returns True if any ancestor satisfies the predicate.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### matches

```python
def matches(query: SpanQuery | SpanPredicate) -> bool
```

Check if the span node matches the query conditions or predicate.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### repr\_xml

```python
def repr_xml(
    include_children: bool = True,
    include_trace_id: bool = False,
    include_span_id: bool = False,
    include_start_timestamp: bool = False,
    include_duration: bool = False,
) -> str
```

Return an XML-like string representation of the node.

Optionally includes children, trace\_id, span\_id, start\_timestamp, and duration.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### SpanTree

A container that builds a hierarchy of SpanNode objects from a list of finished spans.

You can then search or iterate the tree to make your assertions (using DFS for traversal).

#### Methods

##### add\_spans

```python
def add_spans(spans: list[SpanNode]) -> None
```

Add a list of spans to the tree, rebuilding the tree structure.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### find

```python
def find(predicate: SpanQuery | SpanPredicate) -> list[SpanNode]
```

Find all nodes in the entire tree that match the predicate, scanning from each root in DFS order.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`SpanNode`\]

##### first

```python
def first(predicate: SpanQuery | SpanPredicate) -> SpanNode | None
```

Find the first node that matches a predicate, scanning from each root in DFS order. Returns `None` if not found.

###### Returns

`SpanNode` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### any

```python
def any(predicate: SpanQuery | SpanPredicate) -> bool
```

Returns True if any node in the tree matches the predicate.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### \_\_iter\_\_

```python
def __iter__() -> Iterator[SpanNode]
```

Return an iterator over all nodes in the tree.

###### Returns

[`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)\[`SpanNode`\]

##### repr\_xml

```python
def repr_xml(
    include_children: bool = True,
    include_trace_id: bool = False,
    include_span_id: bool = False,
    include_start_timestamp: bool = False,
    include_duration: bool = False,
) -> str
```

Return an XML-like string representation of the tree, optionally including children, trace\_id, span\_id, duration, and timestamps.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### SpanStatus

The status of a span, mirroring `opentelemetry.trace.StatusCode`.

**Default:** `Literal['unset', 'ok', 'error']`

---
