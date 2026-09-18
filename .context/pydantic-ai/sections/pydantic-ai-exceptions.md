# [pydantic_ai.exceptions](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/)

# pydantic\_ai.exceptions

### PydanticAIDeprecationWarning

**Bases:** [`UserWarning`](https://docs.python.org/3/builtins/exceptions.html#UserWarning)

Warning emitted when a deprecated Pydantic AI API is used.

Inherits from `UserWarning` instead of `DeprecationWarning` so that deprecations are visible by default at runtime, following the approach described in [https://sethmlarson.dev/deprecations-via-warnings-dont-work-for-python-libraries](https://sethmlarson.dev/deprecations-via-warnings-dont-work-for-python-libraries).

### CostCalculationFailedWarning

**Bases:** [`Warning`](https://docs.python.org/3/builtins/exceptions.html#Warning)

Warning raised when cost calculation fails.

### CostNotFoundWarning

**Bases:** [`Warning`](https://docs.python.org/3/builtins/exceptions.html#Warning)

Warning raised when cost is not found.

### ModelRetry

**Bases:** [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Exception to raise to request a model retry.

Can be raised from tool functions, output validators, and capability hooks (such as `after_model_request`, `after_tool_execute`, etc.) to send a retry prompt back to the model asking it to try again.

For a terminal failure the model should see but not retry, raise [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed) instead.

#### Attributes

##### message

The message to return to the model.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

#### Methods

##### \_\_get\_pydantic\_core\_schema\_\_

`@classmethod`

```python
def __get_pydantic_core_schema__(cls, _: Any, __: Any) -> core_schema.CoreSchema
```

Pydantic core schema to allow `ModelRetry` to be (de)serialized.

###### Returns

`core_schema.CoreSchema`

### ToolFailed

**Bases:** [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Exception to raise to report a terminal tool failure to the model.

Raise this when a tool call is done and has failed -- a missing resource, an unsupported operation, a definitive upstream error -- and you want the model to see the failure and adapt rather than try the same call again. Can be raised from tool functions, args validators, and tool validation/execution hooks.

Like [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry), this produces a failed tool result the model sees; unlike `ModelRetry` it does not prepend retry/correction instructions and does not consume the tool's retry budget. Bound repeated failures with [`UsageLimits`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.UsageLimits) at the run level instead.

#### Attributes

##### message

The failure message to return to the model.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

#### Methods

##### \_\_get\_pydantic\_core\_schema\_\_

`@classmethod`

```python
def __get_pydantic_core_schema__(cls, _: Any, __: Any) -> core_schema.CoreSchema
```

Pydantic core schema to allow `ToolFailed` to be (de)serialized.

###### Returns

`core_schema.CoreSchema`

### CallDeferred

**Bases:** [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Exception to raise when a tool call should be deferred.

See [tools docs](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#deferred-tools) for more information.

#### Constructor Parameters

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional dictionary of metadata to attach to the deferred tool call. This metadata will be available in `DeferredToolRequests.metadata` keyed by `tool_call_id`.

### ApprovalRequired

**Bases:** [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Exception to raise when a tool call requires human-in-the-loop approval.

See [tools docs](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval) for more information.

#### Constructor Parameters

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional dictionary of metadata to attach to the deferred tool call. This metadata will be available in `DeferredToolRequests.metadata` keyed by `tool_call_id`.

### SkipModelRequest

**Bases:** [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Exception to raise in before/wrap model request hooks to skip the model call.

The provided response will be used instead of calling the model.

Note: when raised in `before_model_request`, any message history modifications made by earlier capabilities in that hook will not be persisted to the agent's message history, since the request preparation is aborted.

### SkipToolValidation

**Bases:** [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Exception to raise in before/wrap tool validate hooks to skip validation.

The provided args will be used as the validated arguments.

### SkipToolExecution

**Bases:** [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Exception to raise in before/wrap tool execute hooks to skip execution.

The provided result will be used as the tool result.

### UserError

**Bases:** [`RuntimeError`](https://docs.python.org/3/builtins/exceptions.html#RuntimeError)

Error caused by a usage mistake by the application developer -- You!

#### Attributes

##### message

Description of the mistake.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

### UndrainedPendingMessagesError

**Bases:** [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError)

Error that used to be raised when an agent run ended with messages still queued via `enqueue`.

A bare `async for node in agent_run` loop used to skip the node hooks, so `'when_idle'` messages and end-of-run redirects (which drain in `after_node_run`) were stranded. Bare iteration now advances through [`AgentRun.next()`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.next) like every other way of driving a run, so pending messages always drain and this error is no longer raised. It is kept so existing `except` clauses keep working.

### AgentRunError

**Bases:** [`RuntimeError`](https://docs.python.org/3/builtins/exceptions.html#RuntimeError)

Base class for errors occurring during an agent run.

#### Attributes

##### message

The error message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

### RunCancelled

**Bases:** [`AgentRunError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.AgentRunError)

Raised when the agent run was cancelled by the application itself.

Raised by [`AgentRun.cancel()`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.cancel) and [`RunContext.cancel()`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.cancel). This is a normal, catchable application-level outcome: the run stopped because your own code asked it to. External cancellation of the task running the agent (`asyncio.Task.cancel()`, a timeout scope, workflow cancellation under durable execution) is infrastructure-level and keeps propagating as `asyncio.CancelledError` instead -- it is never translated into this exception, and when both race, the external cancellation wins. (On Python 3.10, which lacks `Task.uncancel()`, the race cannot be disambiguated and a requested first-party cancellation wins instead.)

Everything the run completed before the cancellation took effect -- including the partial response of an interrupted stream and the results of tool calls that finished -- is preserved in [`all_messages()`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled.all_messages): pass it as `message_history` to a new run (with a new user prompt or not) to resume the conversation; any tool calls that never produced a result are automatically closed out with synthesized `outcome='interrupted'` returns before the history is sent to a model.

Cancellation is terminal: capability hooks (`wrap_run`, `wrap_node_run`, `on_run_error`) may observe it and clean up, but cannot recover a cancelled run into a successful result.

#### Attributes

##### response

Return the last response from the message history.

**Type:** [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

##### timestamp

Return the timestamp of the last response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

##### usage

Return the usage of the cancelled run.

**Type:** [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage)

##### metadata

Metadata associated with this agent run, if configured.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### run\_id

The unique identifier for the agent run, or `None` if it was cancelled before starting.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### conversation\_id

The conversation identifier, or `None` if the run was cancelled before starting.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### from\_cancellation

`@classmethod`

```python
def from_cancellation(cls, exc: BaseException) -> RunCancelled | None
```

Recover run state from a cancellation-related exception.

External cancellation of a plain `agent.run()` keeps its standard asyncio semantics. Catch it with `except asyncio.CancelledError as exc`, then call `RunCancelled.from_cancellation(exc)` to access the partial run state attached by Pydantic AI. This also works with the `TimeoutError` raised by `asyncio.timeout()` or `asyncio.wait_for()`, whose exception chain contains the original `CancelledError`. An external `CancelledError` must keep propagating for timeouts and task groups to tear down correctly, so re-raise it after capturing the state rather than returning from the handler; only a first-party `RunCancelled` is yours to consume.

Passing a `RunCancelled` directly returns the same instance, providing uniform handling for first-party and external cancellation paths.

Python 3.11+ preserves the exception instance across an `await task` boundary. Python 3.10 recreates the `CancelledError` there, but chains the original exception -- and the attached run state -- via `__context__`, which this method traverses; the chain is attached only to the first `await` of the cancelled task, so later awaits of the same task see an unchained exception. Use `capture_run_messages()` as the fallback when only message history is needed.

###### Returns

[`RunCancelled`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### all\_messages

```python
def all_messages() -> list[ModelMessage]
```

Return the complete resumable history of the cancelled run.

This is a DETACHED snapshot of the run's message history at termination, ready to pass as `message_history` for a resumed run.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\] -- List of messages.

##### all\_messages\_json

```python
def all_messages_json() -> bytes
```

Return all messages from [`all_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled.all_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the messages.

##### new\_messages

```python
def new_messages() -> list[ModelMessage]
```

Return the messages produced during the cancelled run.

Messages provided via `message_history` and messages from older runs are excluded.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\] -- List of new messages.

##### new\_messages\_json

```python
def new_messages_json() -> bytes
```

Return new messages from [`new_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled.new_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the new messages.

### SuspendedResponseExpired

**Bases:** [`AgentRunError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.AgentRunError)

Raised when resuming a suspended response whose server-side job is no longer available.

Suspended/background jobs are only resumable within the provider's retention window (e.g. ~10 minutes for OpenAI background mode). Resuming a persisted suspended response after that window raises this instead of an opaque provider HTTP error; start a new run from the preceding messages to retry from scratch.

### UsageLimitExceeded

**Bases:** [`AgentRunError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.AgentRunError)

Error raised when a Model's usage exceeds the specified limits.

### ConcurrencyLimitExceeded

**Bases:** [`AgentRunError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.AgentRunError)

Error raised when the concurrency queue depth exceeds max\_queued.

### UnexpectedModelBehavior

**Bases:** [`AgentRunError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.AgentRunError)

Error caused by unexpected Model behavior, e.g. an unexpected response code.

#### Attributes

##### message

Description of the unexpected behavior.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

##### body

The body of the response, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `json.dumps(json.loads(body), indent=2)`

### ContentFilterError

**Bases:** [`UnexpectedModelBehavior`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UnexpectedModelBehavior)

Raised when content filtering is triggered by the model provider.

### ModelAPIError

**Bases:** [`AgentRunError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.AgentRunError)

Raised when a model provider API request fails.

#### Attributes

##### model\_name

The name of the model associated with the error.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `model_name`

### ModelHTTPError

**Bases:** [`ModelAPIError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelAPIError)

Raised when a model provider response has a status code of 4xx or 5xx.

#### Attributes

##### status\_code

The HTTP status code returned by the API.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `status_code`

##### body

The body of the response, if available.

**Type:** [`object`](https://docs.python.org/3/glossary.html#term-object) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `body`

##### headers

Response headers from the provider, with keys lowercased for consistent access.

For example, use `exc.headers.get('retry-after')` to read the `Retry-After` header regardless of provider casing. `None` when the provider does not supply headers (e.g. gRPC-based providers or synthesised errors).

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `{(k.lower()): v for k, v in (headers.items())} if headers is not None else None`

##### suggested\_model\_id

A close known model identifier suggested from a provider-confirmed model-name error.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `suggested_model_id`

##### retry\_after

Seconds to wait before retrying, parsed from the `Retry-After` response header.

Returns `None` when the header is absent or cannot be parsed. The header value is interpreted first as an integer number of seconds, then as an [HTTP-date](https://httpwg.org/specs/rfc9110.html#http.date) string.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### FallbackExceptionGroup

**Bases:** `ExceptionGroup[Any]`

A group of exceptions that can be raised when all fallback models fail.

### ToolRetryError

**Bases:** [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Exception used to signal a `ToolRetry` message should be returned to the LLM.

### ToolFailedError

**Bases:** [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Exception used to signal a failed `ToolReturnPart` should be returned to the LLM.

### IncompleteToolCall

**Bases:** [`UnexpectedModelBehavior`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UnexpectedModelBehavior)

Error raised when a model stops due to token limit while emitting a tool call.

### MessageHistoryMutatedWarning

**Bases:** [`Warning`](https://docs.python.org/3/builtins/exceptions.html#Warning)

Warning raised when in-place mutation of the message history is detected at the end of a run.

Mutating messages that are already part of the run's history in place (e.g. `ctx.messages[0].parts[0].content = '...'` from a tool) is not supported: the per-request `gen_ai.input.messages` span attribute caches each message's serialized form, so spans recorded after the mutation may not match the messages actually sent to the model. The run-level `pydantic_ai.all_messages` attribute is always serialized fresh and does reflect the mutation. To transform history mid-run, build new message or part objects instead -- e.g. with `dataclasses.replace`, passing the message a new `parts` list (replacing a message in the history and reassigning its `parts` list are both safe) -- for instance in a history processor ([`ProcessHistory`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ProcessHistory)).

The warning is best-effort: it's raised when a mutation is detected at the end of a successful run, which covers messages still present in the final history. Errored runs aren't checked -- with warnings configured as errors, the warning would displace the run's own exception. Its absence does not guarantee that no stale span was recorded.

---
