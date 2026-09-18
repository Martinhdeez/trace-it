# [pydantic_ai — Concurrency](https://pydantic.dev/docs/ai/api/pydantic-ai/concurrency/)

# pydantic\_ai -- Concurrency

### ConcurrencyLimitedModel

**Bases:** `WrapperModel`

A model wrapper that limits concurrent requests to the underlying model.

This wrapper applies concurrency limiting at the model level, ensuring that the number of concurrent requests to the model does not exceed the configured limit. This is useful for:

-   Respecting API rate limits
-   Managing resource usage
-   Sharing a concurrency pool across multiple models

Example usage:

```python
from pydantic_ai import Agent
from pydantic_ai.models.concurrency import ConcurrencyLimitedModel

# Limit to 5 concurrent requests
model = ConcurrencyLimitedModel('openai:gpt-4o', limiter=5)
agent = Agent(model)

# Or share a limiter across multiple models
from pydantic_ai import ConcurrencyLimiter  # noqa E402

shared_limiter = ConcurrencyLimiter(max_running=10, name='openai-pool')
model1 = ConcurrencyLimitedModel('openai:gpt-4o', limiter=shared_limiter)
model2 = ConcurrencyLimitedModel('openai:gpt-4o-mini', limiter=shared_limiter)
```

#### Methods

##### \_\_init\_\_

```python
def __init__(
    wrapped: Model | KnownModelName,
    limiter: int | ConcurrencyLimit | AbstractConcurrencyLimiter,
)
```

Initialize the ConcurrencyLimitedModel.

###### Parameters

**`wrapped`** : `Model` | `KnownModelName`

The model to wrap, either a Model instance or a known model name.

**`limiter`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`ConcurrencyLimit`](https://pydantic.dev/docs/ai/api/pydantic-ai/concurrency/#pydantic_ai.ConcurrencyLimit) | [`AbstractConcurrencyLimiter`](https://pydantic.dev/docs/ai/api/pydantic-ai/concurrency/#pydantic_ai.AbstractConcurrencyLimiter)

The concurrency limit configuration. Can be:

-   An `int`: Simple limit on concurrent operations (unlimited queue).
-   A `ConcurrencyLimit`: Full configuration with optional backpressure.
-   An `AbstractConcurrencyLimiter`: A pre-created limiter for sharing across models.

##### request

`@async`

```python
def request(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> ModelResponse
```

Make a request to the model with concurrency limiting.

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

##### count\_tokens

`@async`

```python
def count_tokens(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> RequestUsage
```

Count tokens with concurrency limiting.

###### Returns

[`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage)

##### request\_stream

`@async`

```python
def request_stream(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
    run_context: RunContext[Any] | None = None,
) -> AsyncGenerator[StreamedResponse]
```

Make a streaming request to the model with concurrency limiting.

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[`StreamedResponse`\]

### limit\_model\_concurrency

```python
def limit_model_concurrency(
    model: Model | KnownModelName,
    limiter: AnyConcurrencyLimit,
) -> Model
```

Wrap a model with concurrency limiting.

This is a convenience function to wrap a model with concurrency limiting. If the limiter is None, the model is returned unchanged.

Example:

```python
from pydantic_ai.models.concurrency import limit_model_concurrency

model = limit_model_concurrency('openai:gpt-4o', limiter=5)
```

#### Returns

`Model` -- The wrapped model with concurrency limiting, or the original model if limiter is None.

#### Parameters

**`model`** : `Model` | `KnownModelName`

The model to wrap.

**`limiter`** : [`AnyConcurrencyLimit`](https://pydantic.dev/docs/ai/api/pydantic-ai/concurrency/#pydantic_ai.AnyConcurrencyLimit)

The concurrency limit configuration.

### AbstractConcurrencyLimiter

**Bases:** `ABC`

Abstract base class for concurrency limiters.

Subclass this to create custom concurrency limiters (e.g., Redis-backed distributed limiters).

Example:

```python
from pydantic_ai.concurrency import AbstractConcurrencyLimiter


class RedisConcurrencyLimiter(AbstractConcurrencyLimiter):
    def __init__(self, redis_client, key: str, max_running: int):
        self._redis = redis_client
        self._key = key
        self._max_running = max_running

    async def acquire(self, source: str) -> None:
        # Implement Redis-based distributed locking
        ...

    def release(self) -> None:
        # Release the Redis lock
        ...
```

#### Methods

##### acquire

`@abstractmethod`

`@async`

```python
def acquire(source: str) -> None
```

Acquire a slot, waiting if necessary.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`source`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Identifier for observability (e.g., 'model:gpt-4o').

##### release

`@abstractmethod`

```python
def release() -> None
```

Release a slot.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### ConcurrencyLimiter

**Bases:** [`AbstractConcurrencyLimiter`](https://pydantic.dev/docs/ai/api/pydantic-ai/concurrency/#pydantic_ai.AbstractConcurrencyLimiter)

A concurrency limiter that tracks waiting operations for observability.

This class wraps an anyio.CapacityLimiter and tracks the number of waiting operations. When an operation has to wait to acquire a slot, a span is created for observability purposes.

#### Attributes

##### name

Name of the limiter for observability.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### waiting\_count

Number of operations currently waiting to acquire a slot.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### running\_count

Number of operations currently running.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### available\_count

Number of slots available.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### max\_running

Maximum concurrent operations allowed.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    max_running: int,
    *,
    max_queued: int | None = None,
    name: str | None = None,
    tracer: Tracer | None = None,
)
```

Initialize the ConcurrencyLimiter.

###### Parameters

**`max_running`** : [`int`](https://docs.python.org/3/builtins/functions.html#int)

Maximum number of concurrent operations. Must be >= 1.

**`max_queued`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Maximum queue depth before raising ConcurrencyLimitExceeded. Must be >= 0.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional name for this limiter, used for observability when sharing a limiter across multiple models or agents.

**`tracer`** : `Tracer` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

OpenTelemetry tracer for span creation.

###### Raises

-   `UserError` -- If `max_running` is less than 1, or `max_queued` is less than 0.

##### from\_limit

`@classmethod`

```python
def from_limit(
    cls,
    limit: int | ConcurrencyLimit,
    *,
    name: str | None = None,
    tracer: Tracer | None = None,
) -> Self
```

Create a ConcurrencyLimiter from a ConcurrencyLimit configuration.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self) -- A configured ConcurrencyLimiter.

###### Parameters

**`limit`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`ConcurrencyLimit`](https://pydantic.dev/docs/ai/api/pydantic-ai/concurrency/#pydantic_ai.ConcurrencyLimit)

Either an int for simple limiting or a ConcurrencyLimit for full config.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional name for this limiter, used for observability.

**`tracer`** : `Tracer` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

OpenTelemetry tracer for span creation.

##### acquire

`@async`

```python
def acquire(source: str) -> None
```

Acquire a slot, creating a span if waiting is required.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`source`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Identifier for the source of this acquisition (e.g., 'agent:my-agent' or 'model:gpt-4').

##### release

```python
def release() -> None
```

Release a slot.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### ConcurrencyLimit

Configuration for concurrency limiting with optional backpressure.

#### Constructor Parameters

**`max_running`** : [`int`](https://docs.python.org/3/builtins/functions.html#int)

Maximum number of concurrent operations allowed. Must be >= 1.

**`max_queued`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Maximum number of operations waiting in the queue. Must be >= 0. If None, the queue is unlimited. If exceeded, raises `ConcurrencyLimitExceeded`.

### AnyConcurrencyLimit

Type alias for concurrency limit configuration.

Can be:

-   An `int`: Simple limit on concurrent operations (unlimited queue).
-   A `ConcurrencyLimit`: Full configuration with optional backpressure.
-   An `AbstractConcurrencyLimiter`: A pre-created limiter instance for sharing across multiple models/agents.
-   `None`: No concurrency limiting (default).

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `'int | ConcurrencyLimit | AbstractConcurrencyLimiter | None'`

### ConcurrencyLimitExceeded

**Bases:** [`AgentRunError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.AgentRunError)

Error raised when the concurrency queue depth exceeds max\_queued.

---
