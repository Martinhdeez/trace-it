# [pydantic_ai.models.fallback](https://pydantic.dev/docs/ai/api/models/fallback/)

# pydantic\_ai.models.fallback

### ResponseRejected

**Bases:** [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Raised within a `FallbackExceptionGroup` when model responses are rejected by a response handler.

### FallbackModel

**Bases:** `Model`

A model that uses one or more fallback models upon failure.

Apart from `__init__`, all methods are private or match those of the base class.

#### Attributes

##### model\_name

The model name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### model\_id

The fully qualified model identifier, combining the wrapped models' IDs.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### context\_window

The smallest known context window among the candidate models, or `None` if none is known.

Any candidate may end up answering, and history that fits the smallest window fits them all, so compacting against it errs towards compacting early rather than overflowing a fallback. Candidates with an unknown window don't constrain the result.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    default_model: Model | KnownModelName | str,
    *fallback_models: Model | KnownModelName | str,
    fallback_on: FallbackOn = (ModelAPIError,),
)
```

Initialize a fallback model instance.

###### Parameters

**`default_model`** : `Model` | `KnownModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The name or instance of the default model to use.

**`fallback_models`** : `Model` | `KnownModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `()`

The names or instances of the fallback models to use upon failure.

**`fallback_on`** : `FallbackOn` _Default:_ `(ModelAPIError,)`

Conditions that trigger fallback to the next model. Accepts:

-   A tuple of exception types: `(ModelAPIError, RateLimitError)`
-   An exception handler (sync or async): `lambda exc: isinstance(exc, MyError)`
-   A response handler (sync or async): `def check(r: ModelResponse) -> bool`
-   A sequence mixing all of the above: `[ModelAPIError, exc_handler, response_handler]`

Handler type is auto-detected by inspecting type hints on the first parameter. If the first parameter is hinted as `ModelResponse`, it's a response handler. Otherwise (including untyped handlers and lambdas), it's an exception handler.

##### \_\_aenter\_\_

`@async`

```python
def __aenter__() -> FallbackModel
```

Enter all sub-models so their providers can manage HTTP client lifecycle.

###### Returns

`FallbackModel`

##### \_\_aexit\_\_

`@async`

```python
def __aexit__(
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: TracebackType | None,
) -> bool | None
```

Exit all sub-models, closing their providers' HTTP clients.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### request

`@async`

```python
def request(
    messages: list[ModelMessage],
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> ModelResponse
```

Try each model in sequence until one succeeds.

In case of failure, raise a FallbackExceptionGroup with all exceptions.

If a previous response set `state='suspended'`, the request is routed directly to the pinned continuation model, bypassing the fallback chain. If the pinned model raises a fallback-eligible error during continuation, the messages are rewound (stripping the suspended response and trailing continuation request) and the normal fallback chain is tried.

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

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

Try each model in sequence until one succeeds.

If a previous response set `state='suspended'`, the request is routed directly to the pinned continuation model, bypassing the fallback chain. If the pinned model raises a fallback-eligible error while opening the stream, the messages are rewound and the normal fallback chain is tried. Mid-stream failures still propagate.

###### Returns

[`AsyncGenerator`](https://docs.python.org/3/library/typing.html#typing.AsyncGenerator)\[`StreamedResponse`\]

##### cancel\_suspended\_response

`@async`

```python
def cancel_suspended_response(response: ModelResponse) -> None
```

Cancel a suspended continuation on the underlying model holding the server-side job.

When the response carries a continuation pin, resolve that model and delegate to it. Resolve the pin directly from metadata rather than via `_get_continuation_model`: the cancel path is driven by `_ContinuationStreamedResponse.get()`, whose `state` is already `'interrupted'`/`'incomplete'`/`'complete'` (never `'suspended'`) by the time cancellation unwinds, so gating on `state == 'suspended'` here would never find the pin.

When no pin resolves, the response can still hold a live server-side job: the pin is only stamped when a segment _ends_ suspended, so a streamed background job cancelled during its first segment (e.g. OpenAI background mode, marked by `provider_details['background']` + `provider_response_id`) has no pin yet. Best-effort delegate to every inner model so the job is torn down rather than leaked. This is safe because each model's own cancel guard is strict (OpenAI only acts on its own `background` marker with a matching `provider_name`; others no-op), and a raising model doesn't stop the rest.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### ExceptionHandler

A sync or async callable that decides whether an exception should trigger fallback.

**Default:** `Callable[[Exception], Awaitable[bool]] | Callable[[Exception], bool]`

### ResponseHandler

A sync or async callable that decides whether a model response should trigger fallback.

**Default:** `Callable[[ModelResponse], Awaitable[bool]] | Callable[[ModelResponse], bool]`

### FallbackOn

The type of the `fallback_on` parameter to [`FallbackModel`](https://pydantic.dev/docs/ai/api/models/fallback/#pydantic_ai.models.fallback.FallbackModel).

**Default:** `type[Exception] | tuple[type[Exception], ...] | ExceptionHandler | ResponseHandler | Sequence[type[Exception] | ExceptionHandler | ResponseHandler]`

---
