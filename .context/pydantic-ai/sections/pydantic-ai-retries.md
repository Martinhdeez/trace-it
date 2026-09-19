# [pydantic_ai.retries](https://pydantic.dev/docs/ai/api/pydantic-ai/retries/)

# pydantic\_ai.retries

Retries utilities based on tenacity, especially for HTTP requests.

This module provides HTTP transport wrappers and wait strategies that integrate with the tenacity library to add retry capabilities to HTTP requests. The transports can be used with HTTP clients that support custom transports (such as `httpx2`), while the wait strategies can be used with any tenacity retry decorator.

The module includes:

-   HTTPX2TenacityTransport: Synchronous `httpx2` transport with retry capabilities
-   AsyncHTTPX2TenacityTransport: Asynchronous `httpx2` transport with retry capabilities
-   wait\_retry\_after: Wait strategy that respects HTTP Retry-After headers

### RetryConfig

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

The configuration for tenacity-based retrying.

These are precisely the arguments to the tenacity `retry` decorator, and they are generally used internally by passing them to that decorator via `@retry(**config)` or similar.

All fields are optional, and if not provided, the default values from the `tenacity.retry` decorator will be used.

#### Attributes

##### sleep

A sleep strategy to use for sleeping between retries.

Tenacity's default for this argument is `tenacity.nap.sleep`.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`int`](https://docs.python.org/3/builtins/functions.html#int) | [`float`](https://docs.python.org/3/builtins/functions.html#float)\], [`None`](https://docs.python.org/3/builtins/constants.html#None) | [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]\]

##### stop

A stop strategy to determine when to stop retrying.

Tenacity's default for this argument is `tenacity.stop.stop_never`.

**Type:** `StopBaseT`

##### wait

A wait strategy to determine how long to wait between retries.

Tenacity's default for this argument is `tenacity.wait.wait_none`.

**Type:** `WaitBaseT`

##### retry

A retry strategy to determine which exceptions should trigger a retry.

Tenacity's default for this argument is `tenacity.retry.retry_if_exception_type()`.

**Type:** `SyncRetryBaseT` | `RetryBaseT`

##### before

A callable that is called before each retry attempt.

Tenacity's default for this argument is `tenacity.before.before_nothing`.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`RetryCallState`\], [`None`](https://docs.python.org/3/builtins/constants.html#None) | [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]\]

##### after

A callable that is called after each retry attempt.

Tenacity's default for this argument is `tenacity.after.after_nothing`.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`RetryCallState`\], [`None`](https://docs.python.org/3/builtins/constants.html#None) | [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]\]

##### before\_sleep

An optional callable that is called before sleeping between retries.

Tenacity's default for this argument is `None`.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`RetryCallState`\], [`None`](https://docs.python.org/3/builtins/constants.html#None) | [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### reraise

Whether to reraise the last exception if the retry attempts are exhausted, or raise a RetryError instead.

Tenacity's default for this argument is `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### retry\_error\_cls

The exception class to raise when the retry attempts are exhausted and `reraise` is False.

Tenacity's default for this argument is `tenacity.RetryError`.

**Type:** [`type`](https://docs.python.org/3/glossary.html#term-type)\[`RetryError`\]

##### retry\_error\_callback

An optional callable that is called when the retry attempts are exhausted and `reraise` is False.

Tenacity's default for this argument is `None`.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`RetryCallState`\], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) | [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### HTTPX2TenacityTransport

**Bases:** `BaseTransport`

Synchronous `httpx2` transport with Tenacity-based retry functionality.

This transport wraps another `httpx2` transport and adds retry capabilities using the tenacity library. It can be configured to retry requests based on various conditions such as specific exception types, response status codes, or custom validation logic.

The transport works by intercepting HTTP requests and responses, allowing the tenacity controller to determine when and how to retry failed requests. The validate\_response function can be used to convert HTTP responses into exceptions that trigger retries.

Requests whose body is a non-replayable stream cannot be retried: the first attempt consumes the stream, so a further attempt raises `httpx2.StreamConsumed`. Use a replayable body (e.g. bytes) for requests that should be retried.

#### Constructor Parameters

**`config`** : `RetryConfig`

The arguments to use for the tenacity `retry` decorator, including retry conditions, wait strategy, stop conditions, etc. See the tenacity docs for more info.

**`wrapped`** : `httpx2.BaseTransport` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The underlying transport to wrap and add retry functionality to. Defaults to a new `httpx2.HTTPTransport`.

**`validate_response`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`httpx2.Response`\], [`object`](https://docs.python.org/3/glossary.html#term-object)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callable that takes a Response and can raise an exception to be handled by the controller if the response should trigger a retry. Common use case is to raise exceptions for certain HTTP status codes. If None, no response validation is performed.

#### Methods

##### handle\_request

```python
def handle_request(request: httpx2.Request) -> httpx2.Response
```

Handle an HTTP request with retry logic.

###### Returns

`httpx2.Response` -- The HTTP response.

###### Parameters

**`request`** : `httpx2.Request`

The HTTP request to handle.

###### Raises

-   `RuntimeError` -- If the retry controller did not make any attempts.
-   `Exception` -- Any exception raised by the wrapped transport or validation function.

### AsyncHTTPX2TenacityTransport

**Bases:** `AsyncBaseTransport`

Asynchronous `httpx2` transport with Tenacity-based retry functionality.

This transport wraps another async `httpx2` transport and adds retry capabilities using the tenacity library. It can be configured to retry requests based on various conditions such as specific exception types, response status codes, or custom validation logic.

The transport works by intercepting HTTP requests and responses, allowing the tenacity controller to determine when and how to retry failed requests. The validate\_response function can be used to convert HTTP responses into exceptions that trigger retries.

Requests whose body is a non-replayable stream cannot be retried: the first attempt consumes the stream, so a further attempt raises `httpx2.StreamConsumed`. Use a replayable body (e.g. bytes) for requests that should be retried.

#### Constructor Parameters

**`config`** : `RetryConfig`

The arguments to use for the tenacity `retry` decorator, including retry conditions, wait strategy, stop conditions, etc. See the tenacity docs for more info.

**`wrapped`** : `httpx2.AsyncBaseTransport` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The underlying async transport to wrap and add retry functionality to. Defaults to a new `httpx2.AsyncHTTPTransport`.

**`validate_response`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`httpx2.Response`\], [`object`](https://docs.python.org/3/glossary.html#term-object)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callable that takes a Response and can raise an exception to be handled by the controller if the response should trigger a retry. Common use case is to raise exceptions for certain HTTP status codes. If None, no response validation is performed.

#### Methods

##### handle\_async\_request

`@async`

```python
def handle_async_request(request: httpx2.Request) -> httpx2.Response
```

Handle an async HTTP request with retry logic.

###### Returns

`httpx2.Response` -- The HTTP response.

###### Parameters

**`request`** : `httpx2.Request`

The HTTP request to handle.

###### Raises

-   `RuntimeError` -- If the retry controller did not make any attempts.
-   `Exception` -- Any exception raised by the wrapped transport or validation function.

### TenacityTransport

**Bases:** `BaseTransport`

Deprecated synchronous HTTPX transport with Tenacity-based retry functionality.

This transport wraps another BaseTransport and adds retry capabilities using the tenacity library. It can be configured to retry requests based on various conditions such as specific exception types, response status codes, or custom validation logic.

The transport works by intercepting HTTP requests and responses, allowing the tenacity controller to determine when and how to retry failed requests. The validate\_response function can be used to convert HTTP responses into exceptions that trigger retries.

#### Constructor Parameters

**`wrapped`** : `BaseTransport` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The underlying transport to wrap and add retry functionality to.

**`config`** : `RetryConfig`

The arguments to use for the tenacity `retry` decorator, including retry conditions, wait strategy, stop conditions, etc. See the tenacity docs for more info.

**`validate_response`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`Response`\], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callable that takes a Response and can raise an exception to be handled by the controller if the response should trigger a retry. Common use case is to raise exceptions for certain HTTP status codes. If None, no response validation is performed.

#### Methods

##### handle\_request

```python
def handle_request(request: Request) -> Response
```

Handle an HTTP request with retry logic.

###### Returns

`Response` -- The HTTP response.

###### Parameters

**`request`** : `Request`

The HTTP request to handle.

###### Raises

-   `RuntimeError` -- If the retry controller did not make any attempts.
-   `Exception` -- Any exception raised by the wrapped transport or validation function.

### AsyncTenacityTransport

**Bases:** `AsyncBaseTransport`

Deprecated asynchronous HTTPX transport with Tenacity-based retry functionality.

This transport wraps another AsyncBaseTransport and adds retry capabilities using the tenacity library. It can be configured to retry requests based on various conditions such as specific exception types, response status codes, or custom validation logic.

The transport works by intercepting HTTP requests and responses, allowing the tenacity controller to determine when and how to retry failed requests. The validate\_response function can be used to convert HTTP responses into exceptions that trigger retries.

#### Constructor Parameters

**`wrapped`** : `AsyncBaseTransport` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The underlying async transport to wrap and add retry functionality to.

**`config`** : `RetryConfig`

The arguments to use for the tenacity `retry` decorator, including retry conditions, wait strategy, stop conditions, etc. See the tenacity docs for more info.

**`validate_response`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`Response`\], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callable that takes a Response and can raise an exception to be handled by the controller if the response should trigger a retry. Common use case is to raise exceptions for certain HTTP status codes. If None, no response validation is performed.

#### Methods

##### handle\_async\_request

`@async`

```python
def handle_async_request(request: Request) -> Response
```

Handle an async HTTP request with retry logic.

###### Returns

`Response` -- The HTTP response.

###### Parameters

**`request`** : `Request`

The HTTP request to handle.

###### Raises

-   `RuntimeError` -- If the retry controller did not make any attempts.
-   `Exception` -- Any exception raised by the wrapped transport or validation function.

### wait\_retry\_after

```python
def wait_retry_after(
    fallback_strategy: Callable[[RetryCallState], float] | None = None,
    max_wait: float = 300,
) -> Callable[[RetryCallState], float]
```

Create a tenacity-compatible wait strategy that respects HTTP Retry-After headers.

This wait strategy checks if the exception contains an httpx or httpx2 HTTPStatusError with a Retry-After header, and if so, waits for the time specified in the header. If no header is present or parsing fails, it falls back to the provided strategy.

The Retry-After header can be in two formats:

-   An integer representing seconds to wait
-   An HTTP date string representing when to retry

#### Returns

[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`RetryCallState`\], [`float`](https://docs.python.org/3/builtins/functions.html#float)\] -- A wait function that can be used with tenacity retry decorators.

#### Parameters

**`fallback_strategy`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`RetryCallState`\], [`float`](https://docs.python.org/3/builtins/functions.html#float)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Wait strategy to use when no Retry-After header is present or parsing fails. Defaults to exponential backoff with max 60s.

**`max_wait`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) _Default:_ `300`

Maximum time to wait in seconds, regardless of header value. Defaults to 300 (5 minutes).

---
