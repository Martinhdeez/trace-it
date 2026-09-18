# [pydantic_graph.exceptions](https://pydantic.dev/docs/ai/api/pydantic_graph/exceptions/)

# pydantic\_graph.exceptions

### GraphSetupError

**Bases:** [`TypeError`](https://docs.python.org/3/builtins/exceptions.html#TypeError)

Error caused by an incorrectly configured graph.

#### Attributes

##### message

Description of the mistake.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

### GraphBuildingError

**Bases:** [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

An error raised during graph-building.

#### Attributes

##### message

The error message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

### GraphValidationError

**Bases:** [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

An error raised during graph validation.

#### Attributes

##### message

The error message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

### GraphRuntimeError

**Bases:** [`RuntimeError`](https://docs.python.org/3/builtins/exceptions.html#RuntimeError)

Error caused by an issue during graph execution.

#### Attributes

##### message

The error message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

### UnsupportedEventLoopError

**Bases:** [`RuntimeError`](https://docs.python.org/3/builtins/exceptions.html#RuntimeError)

Error caused by calling a synchronous method on an event loop that cannot be driven by the caller.

Synchronous methods run their asynchronous implementation using `loop.run_until_complete()`, which not every event loop implements. Temporal's workflow event loop is one that doesn't: it can only be driven by Temporal.

Pydantic AI's synchronous methods report this as a `pydantic_ai.exceptions.UserError` instead.

#### Attributes

##### message

The error message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

---
