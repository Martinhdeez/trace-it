# [pydantic_ai.result](https://pydantic.dev/docs/ai/api/pydantic-ai/result/)

# pydantic\_ai.result

### AgentStream

**Bases:** `Generic[AgentDepsT, OutputDataT]`

#### Attributes

##### cancelled

Whether the stream has been cancelled via `cancel()`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### run\_id

The unique identifier for the agent run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### conversation\_id

The unique identifier for the conversation this run belongs to.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### metadata

Metadata associated with this agent run, if configured.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### response

Get the current state of the response.

**Type:** `_messages.ModelResponse`

##### usage

Return the usage of the whole run.

Note

This won't return the full usage until the stream is finished.

**Type:** [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

#### Methods

##### stream\_output

`@async`

```python
def stream_output(*, debounce_by: float | None = 0.1) -> AsyncIterator[OutputDataT]
```

Asynchronously stream the (validated) agent outputs.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`OutputDataT`\]

##### stream\_response

`@async`

```python
def stream_response(
    *,
    debounce_by: float | None = 0.1,
) -> AsyncIterator[_messages.ModelResponse]
```

Asynchronously stream the (unvalidated) model responses for the agent.

Yields `ModelResponse` snapshots -- `state='incomplete'` while streaming is in flight, followed by one final `state='complete'` snapshot (or `'interrupted'` if `cancel()` was called). If the underlying response already has accumulated content when this is called, a pre-stream yield surfaces it before iteration begins.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`_messages.ModelResponse`\]

##### stream\_text

`@async`

```python
def stream_text(
    *,
    delta: bool = False,
    debounce_by: float | None = 0.1,
) -> AsyncIterator[str]
```

Stream the text result as an async iterable.

Note

[`TextOutput`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.TextOutput) functions are not applied -- use [`stream_output()`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.AgentStream.stream_output) instead. Result validators will NOT be called on the text result if `delta=True`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

###### Parameters

**`delta`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

if `True`, yield each chunk of text as it is received, if `False` (default), yield the full text up to the current point.

**`debounce_by`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `0.1`

by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing. Debouncing is particularly important for long structured responses to reduce the overhead of performing validation as each token is received.

##### cancel

`@async`

```python
def cancel() -> None
```

Cancel local stream consumption and request provider shutdown.

Whether this stops remote generation or closes the underlying transport depends on the provider SDK.

This stops only the current model response; the run continues. To end the whole run, use [`AgentRun.cancel()`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.cancel) or [`RunContext.cancel()`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.cancel).

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### drain

`@async`

```python
def drain() -> None
```

Consume all remaining events from the stream, discarding them.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_output

`@async`

```python
def get_output() -> OutputDataT
```

Stream the whole response, validate the output and return it.

###### Returns

`OutputDataT`

##### validate\_response\_output

`@async`

```python
def validate_response_output(
    message: _messages.ModelResponse,
    *,
    allow_partial: bool = False,
) -> OutputDataT
```

Validate a structured result message.

###### Returns

`OutputDataT`

##### \_\_aiter\_\_

```python
def __aiter__() -> AsyncIterator[AgentStreamEvent]
```

Stream [`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent)s, interleaving events emitted into the run's event buffer.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[[`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent)\]

##### aclose\_events

`@async`

```python
def aclose_events() -> None
```

Close the event stream when a consumer walks away before exhausting it.

The event iterator owns the capability chain, which can otherwise stay suspended with resources held, like a `ProcessEventStream` handler task parked on its receive stream.

Any in-flight shared pull is cancelled and drained before the iterator is closed. The close is shielded because graph teardown can run inside an already-cancelled scope.

The closed iterator is kept in place rather than discarded, so a later `__aiter__()` ends immediately instead of building a second chain (and a second handler) over a spent stream.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### StreamedRunResult

**Bases:** `Generic[AgentDepsT, OutputDataT]`

Result of a streamed run that returns structured data via a tool call.

#### Attributes

##### is\_complete

Whether the stream has all been received.

This is set to `True` when one of [`stream_output`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.stream_output), [`stream_text`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.stream_text), [`stream_response`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.stream_response) or [`get_output`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.get_output) completes.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `field(default=False, init=False)`

##### response

Return the current state of the response.

**Type:** `_messages.ModelResponse`

##### metadata

Metadata associated with this agent run, if configured.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### usage

Return the usage of the whole run.

Note

This won't return the full usage until the stream is finished.

**Type:** [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

##### run\_id

The unique identifier for the agent run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### conversation\_id

The unique identifier for the conversation this run belongs to.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### cancelled

Whether the stream has been cancelled via `cancel()`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### Methods

##### all\_messages

```python
def all_messages(
    *,
    output_tool_return_content: str | None = None,
) -> list[_messages.ModelMessage]
```

Return the history of \_messages.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\] -- List of messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### all\_messages\_json

```python
def all_messages_json(*, output_tool_return_content: str | None = None) -> bytes
```

Return all messages from [`all_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.all_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### new\_messages

```python
def new_messages(
    *,
    output_tool_return_content: str | None = None,
) -> list[_messages.ModelMessage]
```

Return the messages produced during this run.

Messages provided via `message_history` and messages from older runs are excluded.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\] -- List of new messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### new\_messages\_json

```python
def new_messages_json(*, output_tool_return_content: str | None = None) -> bytes
```

Return new messages from [`new_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.new_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the new messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### stream\_output

`@async`

```python
def stream_output(*, debounce_by: float | None = 0.1) -> AsyncIterator[OutputDataT]
```

Stream the output as an async iterable.

The pydantic validator for structured data will be called in [partial mode](https://docs.pydantic.dev/dev/concepts/experimental/#partial-validation) on each iteration.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`OutputDataT`\] -- An async iterable of the response data.

###### Parameters

**`debounce_by`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `0.1`

by how much (if at all) to debounce/group the output chunks by. `None` means no debouncing. Debouncing is particularly important for long structured outputs to reduce the overhead of performing validation as each token is received.

##### stream\_text

`@async`

```python
def stream_text(
    *,
    delta: bool = False,
    debounce_by: float | None = 0.1,
) -> AsyncIterator[str]
```

Stream the text result as an async iterable.

Note

[`TextOutput`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.TextOutput) functions are not applied -- use [`stream_output()`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.stream_output) instead. Result validators will NOT be called on the text result if `delta=True`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

###### Parameters

**`delta`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

if `True`, yield each chunk of text as it is received, if `False` (default), yield the full text up to the current point.

**`debounce_by`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `0.1`

by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing. Debouncing is particularly important for long structured responses to reduce the overhead of performing validation as each token is received.

##### stream\_response

`@async`

```python
def stream_response(
    *,
    debounce_by: float | None = 0.1,
) -> AsyncIterator[_messages.ModelResponse]
```

Stream the response as an async iterable of `ModelResponse` snapshots.

Each yielded `ModelResponse` is the current state of the response: `response.state` is `'incomplete'` while streaming is in flight and `'complete'` (or `'interrupted'` if [`cancel()`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.cancel) was called) on the final yield.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`_messages.ModelResponse`\] -- An async iterable of `ModelResponse` snapshots.

###### Parameters

**`debounce_by`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `0.1`

by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing. Debouncing is particularly important for long structured responses to reduce the overhead of performing validation as each token is received.

##### get\_output

`@async`

```python
def get_output() -> OutputDataT
```

Stream the whole response, validate and return it.

###### Returns

`OutputDataT`

##### validate\_response\_output

`@async`

```python
def validate_response_output(
    message: _messages.ModelResponse,
    *,
    allow_partial: bool = False,
) -> OutputDataT
```

Validate a structured result message.

###### Returns

`OutputDataT`

##### cancel

`@async`

```python
def cancel() -> None
```

Cancel local stream consumption and request provider shutdown.

Whether this stops remote generation or closes the underlying transport depends on the provider SDK.

The interrupted response state is recorded in the message history so that `all_messages()` includes it.

This stops only the current model response; the run continues. To end the whole run, use [`AgentRun.cancel()`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.cancel) or [`RunContext.cancel()`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.cancel).

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### StreamedRunResultSync

**Bases:** `Generic[AgentDepsT, OutputDataT]`

Synchronous wrapper for [`StreamedRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult) that only exposes sync methods.

All of the run's async work happens on the caller's event loop. Context-manager and iterator lifecycles remain in stable tasks, so cancel scopes entered and exited by the agent graph never straddle tasks and OpenTelemetry spans stay correctly nested. The wrapper must be used and closed on the thread where it was created.

This is a synchronous context manager; the underlying stream is cleaned up on exit:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

def main():
    with agent.run_stream_sync('What is the capital of the UK?') as response:
        print(response.get_output())
        #> The capital of the UK is London.
```

Using it without a `with` block also works for backwards compatibility. Garbage collection requests best-effort cleanup on the owner loop, but it cannot drive a stopped owner loop from another thread or while another loop is running. A `with` block should be used whenever deterministic cleanup matters.

#### Attributes

##### response

Return the current state of the response.

**Type:** `_messages.ModelResponse`

##### usage

Return the usage of the whole run.

Note

This won't return the full usage until the stream is finished.

**Type:** [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

##### run\_id

The unique identifier for the agent run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### conversation\_id

The unique identifier for the conversation this run belongs to.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### metadata

Metadata associated with this agent run, if configured.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### is\_complete

Whether the stream has all been received.

This is set to `True` when one of [`stream_output`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResultSync.stream_output), [`stream_text`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResultSync.stream_text), [`stream_response`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResultSync.stream_response) or [`get_output`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResultSync.get_output) completes.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### Methods

##### all\_messages

```python
def all_messages(
    *,
    output_tool_return_content: str | None = None,
) -> list[_messages.ModelMessage]
```

Return the history of messages.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\] -- List of messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### all\_messages\_json

```python
def all_messages_json(*, output_tool_return_content: str | None = None) -> bytes
```

Return all messages from [`all_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResultSync.all_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### new\_messages

```python
def new_messages(
    *,
    output_tool_return_content: str | None = None,
) -> list[_messages.ModelMessage]
```

Return the messages produced during this run.

Messages provided via `message_history` and messages from older runs are excluded.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\] -- List of new messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### new\_messages\_json

```python
def new_messages_json(*, output_tool_return_content: str | None = None) -> bytes
```

Return new messages from [`new_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResultSync.new_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the new messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### stream\_output

```python
def stream_output(*, debounce_by: float | None = 0.1) -> Iterator[OutputDataT]
```

Stream the output as an iterable.

The pydantic validator for structured data will be called in [partial mode](https://docs.pydantic.dev/dev/concepts/experimental/#partial-validation) on each iteration.

###### Returns

[`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)\[`OutputDataT`\] -- An iterable of the response data.

###### Parameters

**`debounce_by`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `0.1`

by how much (if at all) to debounce/group the output chunks by. `None` means no debouncing. Debouncing is particularly important for long structured outputs to reduce the overhead of performing validation as each token is received.

##### stream\_text

```python
def stream_text(
    *,
    delta: bool = False,
    debounce_by: float | None = 0.1,
) -> Iterator[str]
```

Stream the text result as an iterable.

Note

[`TextOutput`](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.TextOutput) functions are not applied -- use [`stream_output()`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResultSync.stream_output) instead. Result validators will NOT be called on the text result if `delta=True`.

###### Returns

[`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

###### Parameters

**`delta`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

if `True`, yield each chunk of text as it is received, if `False` (default), yield the full text up to the current point.

**`debounce_by`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `0.1`

by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing. Debouncing is particularly important for long structured responses to reduce the overhead of performing validation as each token is received.

##### stream\_response

```python
def stream_response(
    *,
    debounce_by: float | None = 0.1,
) -> Iterator[_messages.ModelResponse]
```

Stream the response as an iterable of `ModelResponse` snapshots.

Each yielded `ModelResponse` is the current state of the response: `response.state` is `'incomplete'` while streaming is in flight and `'complete'` on the final yield.

###### Returns

[`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)\[`_messages.ModelResponse`\] -- An iterable of `ModelResponse` snapshots.

###### Parameters

**`debounce_by`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `0.1`

by how much (if at all) to debounce/group the response chunks by. `None` means no debouncing. Debouncing is particularly important for long structured responses to reduce the overhead of performing validation as each token is received.

##### get\_output

```python
def get_output() -> OutputDataT
```

Stream the whole response, validate and return it.

###### Returns

`OutputDataT`

##### validate\_response\_output

```python
def validate_response_output(
    message: _messages.ModelResponse,
    *,
    allow_partial: bool = False,
) -> OutputDataT
```

Validate a structured result message.

###### Returns

`OutputDataT`

---
