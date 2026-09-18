# [pydantic_ai.ui](https://pydantic.dev/docs/ai/api/ui/base/)

# pydantic\_ai.ui

### BuilderCheckpoint

Opaque snapshot of `MessagesBuilder` state, used to query what `add()` touched after the snapshot.

Intended as an in-process correlation token: `last_message` holds a live `ModelMessage` reference whose identity matters for the matching `last_modified` lookup, so checkpoints are not meaningful across pickle/JSON roundtrips. Callers must also avoid mutating `last_message.parts` in place between snapshot and query -- `MessagesBuilder.add` reassigns the list rather than mutating it, but external in-place edits would silently invalidate `last_message_part_count`.

### MessagesBuilder

Helper class to build Pydantic AI messages from request/response parts.

#### Methods

##### add

```python
def add(part: ModelRequestPart | ModelResponsePart) -> None
```

Add a new part, creating a new request or response message if necessary.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### checkpoint

```python
def checkpoint() -> BuilderCheckpoint
```

Snapshot the current builder state. Pair with [`last_modified`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.MessagesBuilder.last_modified).

###### Returns

`BuilderCheckpoint`

##### last\_modified

```python
def last_modified(
    checkpoint: BuilderCheckpoint,
    *,
    of_type: type[ModelRequest] | type[ModelResponse],
) -> ModelMessage | None
```

Find the most recently created or extended `ModelMessage` of `of_type` since `checkpoint`.

A single round of `add()` calls can either grow the previous tail's parts list (if the new part matches the tail's type) or append fresh messages (which can be more than one when e.g. tool-return parts follow a response). Callers that need to attribute side metadata to a logical "the message I just built" use this rather than re-deriving it from `messages`.

###### Returns

[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### UIEventStream

**Bases:** `ABC`, `Generic[RunInputT, EventT, AgentDepsT, OutputDataT]`

Base class for UI event stream transformers.

This class is responsible for transforming Pydantic AI events into protocol-specific events.

#### Attributes

##### run\_input

The protocol-specific run input object the stream was built from, if any.

`None` when the stream is used as a standalone encoder, transforming events that reached it over a transport of their own -- a durable execution workflow, a queue, a websocket fan-out -- rather than over the HTTP request a [`UIAdapter`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter) serves. A subclass that needs a value the run input carries takes it as a field of its own, overwritten by the run input's value when one is given.

**Type:** `RunInputT` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### accept

The `Accept` header value of the request, used to determine how to encode the protocol-specific events for the streaming response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### message\_id

The message ID to use for the next event.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `field(default_factory=(lambda: str(uuid4())))`

##### response\_headers

Response headers to return to the frontend.

**Type:** [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### cancelled

The cancellation carrying the run's resumable state, once the stream has ended with a first-party cancellation.

**Type:** [`RunCancelled`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### content\_type

Get the content type for the event stream, compatible with the `Accept` header value.

By default, this returns the Server-Sent Events content type (`text/event-stream`). If a subclass supports other types as well, it should consider `self.accept` in [`encode_event()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.encode_event) and return the resulting content type.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### new\_message\_id

```python
def new_message_id() -> str
```

Generate and store a new message ID.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### encode\_event

`@abstractmethod`

```python
def encode_event(event: EventT) -> str
```

Encode a protocol-specific event as a string.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### encode\_stream

`@async`

```python
def encode_stream(stream: AsyncIterator[EventT]) -> AsyncIterator[str]
```

Encode a stream of protocol-specific events as strings according to the `Accept` header value.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### streaming\_response

```python
def streaming_response(stream: AsyncIterator[EventT]) -> StreamingResponse
```

Generate a streaming response from a stream of protocol-specific events.

###### Returns

`StreamingResponse`

##### transform\_stream

`@async`

```python
def transform_stream(
    stream: AsyncIterator[NativeEvent],
    on_complete: OnCompleteFunc[EventT] | None = None,
    on_cancel: OnCancelFunc[EventT] | None = None,
) -> AsyncIterator[EventT]
```

Transform a stream of Pydantic AI events into protocol-specific events.

This method dispatches to specific hooks and `handle_*` methods that subclasses can override:

-   [`before_stream()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.before_stream)
-   [`after_stream()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.after_stream)
-   [`on_cancelled()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.on_cancelled)
-   [`on_error()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.on_error)
-   [`before_request()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.before_request)
-   [`after_request()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.after_request)
-   [`before_response()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.before_response)
-   [`after_response()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.after_response)
-   [`handle_event()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_event)

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`stream`** : [`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`NativeEvent`\]

The stream of Pydantic AI events to transform.

**`on_complete`** : `OnCompleteFunc`\[`EventT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callback function called when the agent run completes successfully. The callback receives the completed [`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult) and can optionally yield additional protocol-specific events.

**`on_cancel`** : `OnCancelFunc`\[`EventT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callback function called when the agent run ends in first-party cancellation. The callback receives the [`RunCancelled`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled), making this the place to persist `cancelled.all_messages()`, and can optionally yield additional protocol-specific events.

##### handle\_event

`@async`

```python
def handle_event(event: NativeEvent) -> AsyncIterator[EventT]
```

Transform a Pydantic AI event into one or more protocol-specific events.

This method dispatches to specific `handle_*` methods based on event type:

-   [`PartStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartStartEvent) -> [`handle_part_start()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_part_start)
-   [`PartDeltaEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartDeltaEvent) -> `handle_part_delta`
-   [`PartEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartEndEvent) -> `handle_part_end`
-   [`FinalResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FinalResultEvent) -> `handle_final_result`
-   [`EnqueuedMessagesEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.EnqueuedMessagesEvent) -> `handle_enqueued_messages`
-   [`FunctionToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolCallEvent) -> `handle_function_tool_call`
-   [`FunctionToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolResultEvent) -> `handle_function_tool_result`
-   [`ToolAvailabilityDeltaEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolAvailabilityDeltaEvent) -> `handle_tool_availability_delta`
-   [`OutputToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.OutputToolCallEvent) -> `handle_output_tool_call`
-   [`OutputToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.OutputToolResultEvent) -> `handle_output_tool_result`
-   [`DeferredToolRequestsEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.DeferredToolRequestsEvent) -> `handle_deferred_tool_requests`
-   [`DeferredToolResultsEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.DeferredToolResultsEvent) -> `handle_deferred_tool_results`
-   [`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent) -> `handle_custom_event`
-   [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent) -> `handle_capability_event`
-   [`AgentRunResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResultEvent) -> `handle_run_result`

Subclasses are encouraged to override the individual `handle_*` methods rather than this one. If you need specific behavior for all events, make sure you call the super method.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

##### handle\_part\_start

`@async`

```python
def handle_part_start(event: PartStartEvent) -> AsyncIterator[EventT]
```

Handle a `PartStartEvent`.

This method dispatches to specific `handle_*` methods based on part type:

-   [`TextPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.TextPart) -> [`handle_text_start()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_text_start)
-   [`ThinkingPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ThinkingPart) -> [`handle_thinking_start()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_thinking_start)
-   [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart) -> [`handle_tool_call_start()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_tool_call_start)
-   [`NativeToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolCallPart) -> [`handle_builtin_tool_call_start()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_builtin_tool_call_start)
-   [`NativeToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolReturnPart) -> [`handle_builtin_tool_return()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_builtin_tool_return)
-   [`FilePart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FilePart) -> [`handle_file()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_file)
-   [`CompactionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CompactionPart) -> [`handle_compaction()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_compaction)

Subclasses are encouraged to override the individual `handle_*` methods rather than this one. If you need specific behavior for all part start events, make sure you call the super method.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`PartStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartStartEvent)

The part start event.

##### handle\_part\_delta

`@async`

```python
def handle_part_delta(event: PartDeltaEvent) -> AsyncIterator[EventT]
```

Handle a PartDeltaEvent.

This method dispatches to specific `handle_*_delta` methods based on part delta type:

-   [`TextPartDelta`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.TextPartDelta) -> [`handle_text_delta()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_text_delta)
-   [`ThinkingPartDelta`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ThinkingPartDelta) -> [`handle_thinking_delta()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_thinking_delta)
-   [`ToolCallPartDelta`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPartDelta) -> [`handle_tool_call_delta()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_tool_call_delta)

Subclasses are encouraged to override the individual `handle_*_delta` methods rather than this one. If you need specific behavior for all part delta events, make sure you call the super method.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`PartDeltaEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartDeltaEvent)

The PartDeltaEvent.

##### handle\_part\_end

`@async`

```python
def handle_part_end(event: PartEndEvent) -> AsyncIterator[EventT]
```

Handle a `PartEndEvent`.

This method dispatches to specific `handle_*_end` methods based on part type:

-   [`TextPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.TextPart) -> [`handle_text_end()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_text_end)
-   [`ThinkingPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ThinkingPart) -> [`handle_thinking_end()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_thinking_end)
-   [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart) -> [`handle_tool_call_end()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_tool_call_end)
-   [`NativeToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolCallPart) -> [`handle_builtin_tool_call_end()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.handle_builtin_tool_call_end)

Subclasses are encouraged to override the individual `handle_*_end` methods rather than this one. If you need specific behavior for all part end events, make sure you call the super method.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`PartEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartEndEvent)

The part end event.

##### before\_stream

`@async`

```python
def before_stream() -> AsyncIterator[EventT]
```

Yield events before agent streaming starts.

This hook is called before any agent events are processed. Override this to inject custom events at the start of the stream.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

##### after\_stream

`@async`

```python
def after_stream() -> AsyncIterator[EventT]
```

Yield events after agent streaming completes.

This hook is called after all agent events have been processed. Override this to inject custom events at the end of the stream.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

##### on\_error

`@async`

```python
def on_error(error: Exception) -> AsyncIterator[EventT]
```

Handle errors that occur during streaming.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`error`** : [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

The error that occurred during streaming.

##### on\_cancelled

`@async`

```python
def on_cancelled(cancelled: RunCancelled) -> AsyncIterator[EventT]
```

Handle a first-party cancellation raised during streaming.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

##### before\_request

`@async`

```python
def before_request() -> AsyncIterator[EventT]
```

Yield events before a model request is processed.

Override this to inject custom events at the start of the request.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

##### after\_request

`@async`

```python
def after_request() -> AsyncIterator[EventT]
```

Yield events after a model request is processed.

Override this to inject custom events at the end of the request.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

##### before\_response

`@async`

```python
def before_response() -> AsyncIterator[EventT]
```

Yield events before a model response is processed.

Override this to inject custom events at the start of the response.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

##### after\_response

`@async`

```python
def after_response() -> AsyncIterator[EventT]
```

Yield events after a model response is processed.

Override this to inject custom events at the end of the response.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

##### handle\_text\_start

`@async`

```python
def handle_text_start(
    part: TextPart,
    follows_text: bool = False,
) -> AsyncIterator[EventT]
```

Handle the start of a `TextPart`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`part`** : [`TextPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.TextPart)

The text part.

**`follows_text`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether the part is directly preceded by another text part. In this case, you may want to yield a "text-delta" event instead of a "text-start" event.

##### handle\_text\_delta

`@async`

```python
def handle_text_delta(delta: TextPartDelta) -> AsyncIterator[EventT]
```

Handle a `TextPartDelta`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`delta`** : [`TextPartDelta`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.TextPartDelta)

The text part delta.

##### handle\_text\_end

`@async`

```python
def handle_text_end(
    part: TextPart,
    followed_by_text: bool = False,
) -> AsyncIterator[EventT]
```

Handle the end of a `TextPart`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`part`** : [`TextPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.TextPart)

The text part.

**`followed_by_text`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether the part is directly followed by another text part. In this case, you may not want to yield a "text-end" event yet.

##### handle\_thinking\_start

`@async`

```python
def handle_thinking_start(
    part: ThinkingPart,
    follows_thinking: bool = False,
) -> AsyncIterator[EventT]
```

Handle the start of a `ThinkingPart`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`part`** : [`ThinkingPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ThinkingPart)

The thinking part.

**`follows_thinking`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether the part is directly preceded by another thinking part. In this case, you may want to yield a "thinking-delta" event instead of a "thinking-start" event.

##### handle\_thinking\_delta

`@async`

```python
def handle_thinking_delta(delta: ThinkingPartDelta) -> AsyncIterator[EventT]
```

Handle a `ThinkingPartDelta`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`delta`** : [`ThinkingPartDelta`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ThinkingPartDelta)

The thinking part delta.

##### handle\_thinking\_end

`@async`

```python
def handle_thinking_end(
    part: ThinkingPart,
    followed_by_thinking: bool = False,
) -> AsyncIterator[EventT]
```

Handle the end of a `ThinkingPart`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`part`** : [`ThinkingPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ThinkingPart)

The thinking part.

**`followed_by_thinking`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether the part is directly followed by another thinking part. In this case, you may not want to yield a "thinking-end" event yet.

##### handle\_tool\_call\_start

`@async`

```python
def handle_tool_call_start(part: ToolCallPart) -> AsyncIterator[EventT]
```

Handle the start of a `ToolCallPart`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`part`** : [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart)

The tool call part.

##### handle\_tool\_call\_delta

`@async`

```python
def handle_tool_call_delta(delta: ToolCallPartDelta) -> AsyncIterator[EventT]
```

Handle a `ToolCallPartDelta`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`delta`** : [`ToolCallPartDelta`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPartDelta)

The tool call part delta.

##### handle\_tool\_call\_end

`@async`

```python
def handle_tool_call_end(part: ToolCallPart) -> AsyncIterator[EventT]
```

Handle the end of a `ToolCallPart`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`part`** : [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart)

The tool call part.

##### handle\_builtin\_tool\_call\_start

`@async`

```python
def handle_builtin_tool_call_start(part: NativeToolCallPart) -> AsyncIterator[EventT]
```

Handle a `NativeToolCallPart` at start.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`part`** : [`NativeToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolCallPart)

The builtin tool call part.

##### handle\_builtin\_tool\_call\_end

`@async`

```python
def handle_builtin_tool_call_end(part: NativeToolCallPart) -> AsyncIterator[EventT]
```

Handle the end of a `NativeToolCallPart`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`part`** : [`NativeToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolCallPart)

The builtin tool call part.

##### handle\_builtin\_tool\_return

`@async`

```python
def handle_builtin_tool_return(part: NativeToolReturnPart) -> AsyncIterator[EventT]
```

Handle a `NativeToolReturnPart`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`part`** : [`NativeToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolReturnPart)

The builtin tool return part.

##### handle\_file

`@async`

```python
def handle_file(part: FilePart) -> AsyncIterator[EventT]
```

Handle a `FilePart`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`part`** : [`FilePart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FilePart)

The file part.

##### handle\_compaction

`@async`

```python
def handle_compaction(part: CompactionPart) -> AsyncIterator[EventT]
```

Handle a `CompactionPart`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`part`** : [`CompactionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CompactionPart)

The compaction part.

##### handle\_final\_result

`@async`

```python
def handle_final_result(event: FinalResultEvent) -> AsyncIterator[EventT]
```

Handle a `FinalResultEvent`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`FinalResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FinalResultEvent)

The final result event.

##### handle\_enqueued\_messages

`@async`

```python
def handle_enqueued_messages(event: EnqueuedMessagesEvent) -> AsyncIterator[EventT]
```

Handle an `EnqueuedMessagesEvent` (messages enqueued via [`RunContext.enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue) delivered into the run).

By default no protocol events are emitted. Override this to surface the delivered messages to the frontend.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`EnqueuedMessagesEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.EnqueuedMessagesEvent)

The enqueued messages event.

##### handle\_function\_tool\_call

`@async`

```python
def handle_function_tool_call(event: FunctionToolCallEvent) -> AsyncIterator[EventT]
```

Handle a `FunctionToolCallEvent`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`FunctionToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolCallEvent)

The function tool call event.

##### handle\_function\_tool\_result

`@async`

```python
def handle_function_tool_result(event: FunctionToolResultEvent) -> AsyncIterator[EventT]
```

Handle a `FunctionToolResultEvent`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`FunctionToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolResultEvent)

The function tool result event.

##### handle\_tool\_availability\_delta

`@async`

```python
def handle_tool_availability_delta(
    event: ToolAvailabilityDeltaEvent,
) -> AsyncIterator[EventT]
```

Handle a `ToolAvailabilityDeltaEvent`.

By default no protocol events are emitted. Override this to surface newly available tools to the frontend.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`ToolAvailabilityDeltaEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolAvailabilityDeltaEvent)

The tool availability delta event.

##### handle\_output\_tool\_call

`@async`

```python
def handle_output_tool_call(event: OutputToolCallEvent) -> AsyncIterator[EventT]
```

Handle an `OutputToolCallEvent` (the model's "submit final answer" call).

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`OutputToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.OutputToolCallEvent)

The output tool call event.

##### handle\_output\_tool\_result

`@async`

```python
def handle_output_tool_result(event: OutputToolResultEvent) -> AsyncIterator[EventT]
```

Handle an `OutputToolResultEvent` (the result of an output tool call).

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`OutputToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.OutputToolResultEvent)

The output tool result event.

##### handle\_custom\_event

`@async`

```python
def handle_custom_event(event: CustomEvent) -> AsyncIterator[EventT]
```

Handle a `CustomEvent` emitted during the run via `emit`.

The default implementation drops the event. Protocol adapters override this to map custom events onto their own event/chunk types.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent)

The custom event.

##### handle\_capability\_event

`@async`

```python
def handle_capability_event(event: CapabilityEvent) -> AsyncIterator[EventT]
```

Handle a `CapabilityEvent` emitted during the run.

Capability events are internal coordination signals and are not forwarded to frontends by default. Applications can subscribe and re-emit one as a `CustomEvent`; protocol adapter subclasses can override this method when the protocol has a suitable representation.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent)

The capability event.

##### handle\_deferred\_tool\_requests

`@async`

```python
def handle_deferred_tool_requests(
    event: DeferredToolRequestsEvent,
) -> AsyncIterator[EventT]
```

Handle a `DeferredToolRequestsEvent` (a batch of tool calls awaiting approval or external execution).

By default no protocol events are emitted: a run that ends on deferred calls surfaces them via its [`DeferredToolRequests`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolRequests) output instead. Override this to notify the frontend mid-stream, e.g. when a [`HandleDeferredToolCalls`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.HandleDeferredToolCalls) handler resolves the calls without ending the run.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`DeferredToolRequestsEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.DeferredToolRequestsEvent)

The deferred tool requests event.

##### handle\_deferred\_tool\_results

`@async`

```python
def handle_deferred_tool_results(
    event: DeferredToolResultsEvent,
) -> AsyncIterator[EventT]
```

Handle a `DeferredToolResultsEvent` (deferred tool calls resolved by a handler during the run).

By default no protocol events are emitted; the resolved calls execute and emit their own [`FunctionToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolResultEvent)s.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`DeferredToolResultsEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.DeferredToolResultsEvent)

The deferred tool results event.

##### handle\_run\_result

`@async`

```python
def handle_run_result(event: AgentRunResultEvent) -> AsyncIterator[EventT]
```

Handle an `AgentRunResultEvent`.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`event`** : [`AgentRunResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResultEvent)

The agent run result event.

### StateHandler

**Bases:** [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Protocol for state handlers in agent runs. Requires the class to be a dataclass with a `state` field.

#### Attributes

##### state

Get the current state of the agent run.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### StateDeps

**Bases:** `Generic[StateT]`

Dependency type that holds state.

This class is used to manage the state of an agent run. It allows setting the state of the agent run with a specific type of state model, which must be a subclass of `BaseModel`.

The state is set using the `state` setter by the `Adapter` when the run starts.

Implements the `StateHandler` protocol.

### UIAdapter

**Bases:** `ABC`, `Generic[RunInputT, MessageT, EventT, AgentDepsT, OutputDataT]`

Base class for UI adapters.

This class is responsible for transforming agent run input received from the frontend into arguments for `Agent.run_stream_events()`, running the agent, and then transforming Pydantic AI events into protocol-specific events.

The event stream transformation is handled by a protocol-specific [`UIEventStream`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream) subclass.

#### Attributes

##### agent

The Pydantic AI agent to run.

**Type:** `AbstractAgent`\[`AgentDepsT`, `OutputDataT`\]

##### run\_input

The protocol-specific run input object.

**Type:** `RunInputT`

##### accept

The `Accept` header value of the request, used to determine how to encode the protocol-specific events for the streaming response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### manage\_system\_prompt

Who owns the system prompt.

Only affects `system_prompt` -- [`instructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.instructions) are always injected by the agent on every request regardless of this setting.

`'server'` (default): the agent's configured `system_prompt` is authoritative. Any `SystemPromptPart` sent by the frontend is stripped with a warning (since a malicious client could otherwise inject arbitrary instructions via crafted API requests), and the agent's own system prompt is reinjected at the head of the first request via the [`ReinjectSystemPrompt`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ReinjectSystemPrompt) capability.

`'client'`: the frontend owns the system prompt. Frontend `SystemPromptPart`s are preserved as-is, and the agent's configured `system_prompt` is not injected -- the caller is fully responsible for sending it on every turn if desired. To opt into the same fallback-to-configured behavior as server mode, add the [`ReinjectSystemPrompt`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ReinjectSystemPrompt) capability to your agent.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['server', 'client'\] **Default:** `'server'`

##### allowed\_file\_url\_schemes

URL schemes that are allowed for [`FileUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl) parts ([`ImageUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ImageUrl), [`DocumentUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.DocumentUrl), [`VideoUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.VideoUrl), [`AudioUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AudioUrl)) in client-submitted messages.

Defaults to `{'http', 'https'}`. Parts whose URL scheme is not in this set are dropped with a warning before the messages are passed to the agent. This applies both to file URLs in user content and to those nested in tool return parts.

Non-HTTP schemes like `s3://` (Bedrock) or `gs://` (Google Cloud) cause the model provider to fetch the object using the server-side IAM role or service account, so a client that can supply arbitrary URLs can read anything that identity can reach. HTTPS URLs are safe to forward because the provider fetches them with its own public credentials, and the library's own [`download_item`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.download_item) path applies SSRF protection when it has to download them itself.

For uploads initiated in the browser, prefer pre-signed `https://` URLs over cloud-storage schemes. To opt into a cloud-storage scheme after auditing your frontend, add it to this set, e.g. `frozenset({'http', 'https', 's3'})`.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `frozenset({'http', 'https'})`

##### allowed\_file\_url\_force\_download

Additional [`FileUrl.force_download`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl.force_download) values allowed on [`FileUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl) parts in client-submitted messages.

`False` (the safe default that the sanitizer resets to) is always permitted regardless of whether it appears in this set. Values listed here are the _additional_ `force_download` values that are trusted from the client. Defaults to `frozenset()`, so by default both `True` and `'allow-local'` are reset to `False` with a warning before the messages are passed to the agent. This applies both to file URLs in user content and to those nested in tool return parts.

`force_download=True` makes the server download the file itself instead of letting the model provider fetch it. `force_download='allow-local'` additionally opts the URL out of the SSRF private-IP block in [`download_item`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.download_item), which lets a client probe internal services. Neither is safe to honor from untrusted client input by default.

To opt into a value after auditing your frontend, add it to this set, e.g. `frozenset({True})` or `frozenset({True, 'allow-local'})`.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[`ForceDownloadMode`\] **Default:** `frozenset()`

##### allow\_uploaded\_files

Whether to honor [`UploadedFile`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UploadedFile) references from client-submitted messages.

Defaults to `False`. By default, `UploadedFile` items in client-submitted messages are dropped with a warning before the messages are passed to the agent, mirroring how [`allowed_file_url_schemes`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.allowed_file_url_schemes) filters [`FileUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl) parts. This applies both to uploaded files in user content and to those nested in tool return parts.

Like a non-HTTP `FileUrl`, an `UploadedFile` references an object that the model provider fetches using the server-side IAM role or service account, so a client that can supply arbitrary file references can read anything that identity can reach. Uploaded files should therefore only be accepted from trusted frontends.

Set to `True` to honor client-submitted uploaded files after auditing your frontend.

This is a purely inbound, security-oriented setting. It does not affect what the adapter sends _to_ the client: file content the agent produces is always serialized on the way out.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### messages

Pydantic AI messages from the protocol-specific run input.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### toolset

Toolset representing frontend tools from the protocol-specific run input.

**Type:** [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### state

Frontend state from the protocol-specific run input.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### deferred\_tool\_results

Deferred tool results extracted from the request, used for tool approval workflows.

**Type:** [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### conversation\_id

Conversation ID extracted from the protocol-specific run input.

Used to correlate multiple agent runs that share message history. Returned as the `gen_ai.conversation.id` OpenTelemetry span attribute on each run.

Subclasses for protocols that carry a conversation/thread/chat ID should override this (e.g. AG-UI's `RunAgentInput.threadId`, Vercel AI's top-level chat `id`).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### from\_request

`@async`

`@classmethod`

```python
def from_request(
    cls,
    request: Request,
    *,
    agent: AbstractAgent[AgentDepsT, OutputDataT],
    manage_system_prompt: Literal['server', 'client'] = 'server',
    allowed_file_url_schemes: frozenset[str] = frozenset({'http', 'https'}),
    allowed_file_url_force_download: frozenset[ForceDownloadMode] = frozenset(),
    allow_uploaded_files: bool = False,
    **kwargs: Any,
) -> Self
```

Create an adapter from a request.

Extra keyword arguments are forwarded to the adapter constructor, allowing subclasses to accept additional adapter-specific parameters.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self)

##### build\_run\_input

`@abstractmethod`

`@classmethod`

```python
def build_run_input(cls, body: bytes) -> RunInputT
```

Build a protocol-specific run input object from the request body.

###### Returns

`RunInputT`

##### load\_messages

`@abstractmethod`

`@classmethod`

```python
def load_messages(cls, messages: Sequence[MessageT]) -> list[ModelMessage]
```

Transform protocol-specific messages into Pydantic AI messages.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### dump\_messages

`@classmethod`

```python
def dump_messages(cls, messages: Sequence[ModelMessage]) -> list[MessageT]
```

Transform Pydantic AI messages into protocol-specific messages.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`MessageT`\]

##### build\_event\_stream

`@abstractmethod`

```python
def build_event_stream() -> UIEventStream[RunInputT, EventT, AgentDepsT, OutputDataT]
```

Build a protocol-specific event stream transformer.

###### Returns

`UIEventStream`\[`RunInputT`, `EventT`, `AgentDepsT`, `OutputDataT`\]

##### sanitize\_messages

```python
def sanitize_messages(
    messages: Sequence[ModelMessage],
    *,
    deferred_tool_results: DeferredToolResults | None = None,
) -> list[ModelMessage]
```

Strip parts of client-submitted messages that aren't trusted from the client.

Called on the messages produced from the protocol-specific run input before they're passed to the agent. Caller-supplied `message_history` is not passed through this method -- it is trusted as coming from server-side persistence. Use [`sanitize_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.sanitize_messages) before passing `message_history` that came from an untrusted client.

Delegates to [`sanitize_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.sanitize_messages) -- see its docstring for the full list of what's stripped -- with these adapter-specific settings:

-   [`SystemPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SystemPromptPart)s are stripped only when [`manage_system_prompt`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.manage_system_prompt) is `'server'`, and the agent's configured `system_prompt` is reinjected by [`ReinjectSystemPrompt`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ReinjectSystemPrompt) on the next model request.
-   File URL schemes and `force_download` values are checked against [`allowed_file_url_schemes`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.allowed_file_url_schemes) and [`allowed_file_url_force_download`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.allowed_file_url_force_download), and [`UploadedFile`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UploadedFile)s are kept only when [`allow_uploaded_files`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.allow_uploaded_files) is `True`.
-   Tool calls at the end of the history are kept when they correspond to a resolution in `deferred_tool_results`, so human-in-the-loop resumption continues to work.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### transform\_stream

```python
def transform_stream(
    stream: AsyncIterator[NativeEvent],
    on_complete: OnCompleteFunc[EventT] | None = None,
    on_cancel: OnCancelFunc[EventT] | None = None,
) -> AsyncIterator[EventT]
```

Transform a stream of Pydantic AI events into protocol-specific events.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`stream`** : [`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`NativeEvent`\]

The stream of Pydantic AI events to transform.

**`on_complete`** : `OnCompleteFunc`\[`EventT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callback function called when the agent run completes successfully. The callback receives the completed [`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult) and can optionally yield additional protocol-specific events.

**`on_cancel`** : `OnCancelFunc`\[`EventT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callback function called when the agent run ends in first-party cancellation. The callback receives the [`RunCancelled`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled) and can optionally yield additional protocol-specific events.

##### encode\_stream

```python
def encode_stream(stream: AsyncIterator[EventT]) -> AsyncIterator[str]
```

Encode a stream of protocol-specific events as strings according to the `Accept` header value.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

###### Parameters

**`stream`** : [`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

The stream of protocol-specific events to encode.

##### streaming\_response

```python
def streaming_response(stream: AsyncIterator[EventT]) -> StreamingResponse
```

Generate a streaming response from a stream of protocol-specific events.

###### Returns

`StreamingResponse`

###### Parameters

**`stream`** : [`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

The stream of protocol-specific events to encode.

##### run\_stream\_native

```python
def run_stream_native(
    *,
    output_type: OutputSpec[Any] | None = None,
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: Model | KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AbstractCapability[AgentDepsT]] | None = None,
) -> AsyncIterator[NativeEvent]
```

Run the agent with the protocol-specific run input and stream Pydantic AI events.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`NativeEvent`\]

###### Parameters

**`output_type`** : `OutputSpec`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : `Model` | `KnownModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : [`UsageLimits`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.UsageLimits) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional token for cancelling this run from another task.

**`usage`** : [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`AbstractCapability`\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities. Use `capabilities=[NativeTool(...)]` to add provider-side native tools per request.

##### run\_stream

```python
def run_stream(
    *,
    output_type: OutputSpec[Any] | None = None,
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: Model | KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[AgentDepsT] = None,
    deps: AgentDepsT = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: RunUsage | None = None,
    metadata: AgentMetadata[AgentDepsT] | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[AgentDepsT]] | None = None,
    capabilities: Sequence[AbstractCapability[AgentDepsT]] | None = None,
    on_complete: OnCompleteFunc[EventT] | None = None,
    on_cancel: OnCancelFunc[EventT] | None = None,
) -> AsyncIterator[EventT]
```

Run the agent with the protocol-specific run input and stream protocol-specific events.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`EventT`\]

###### Parameters

**`output_type`** : `OutputSpec`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : `Model` | `KnownModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`AgentDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `AgentDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : [`UsageLimits`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.UsageLimits) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional token for cancelling this run from another task.

**`usage`** : [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`AbstractCapability`\[`AgentDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities. Use `capabilities=[NativeTool(...)]` to add provider-side native tools per request.

**`on_complete`** : `OnCompleteFunc`\[`EventT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callback function called when the agent run completes successfully. The callback receives the completed [`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult) and can optionally yield additional protocol-specific events.

**`on_cancel`** : `OnCancelFunc`\[`EventT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callback function called when the agent run ends in first-party cancellation. The callback receives the [`RunCancelled`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled) and can optionally yield additional protocol-specific events.

##### dispatch\_request

`@async`

`@classmethod`

```python
def dispatch_request(
    cls,
    request: Request,
    *,
    agent: AbstractAgent[DispatchDepsT, DispatchOutputDataT],
    message_history: Sequence[ModelMessage] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    conversation_id: str | None = None,
    run_id: str | None = None,
    model: Model | KnownModelName | str | None = None,
    instructions: _instructions.AgentInstructions[DispatchDepsT] = None,
    deps: DispatchDepsT = None,
    output_type: OutputSpec[Any] | None = None,
    model_settings: ModelSettings | None = None,
    usage_limits: UsageLimits | None = None,
    cancellation_token: CancellationToken | None = None,
    usage: RunUsage | None = None,
    metadata: AgentMetadata[DispatchDepsT] | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[DispatchDepsT]] | None = None,
    capabilities: Sequence[AbstractCapability[DispatchDepsT]] | None = None,
    on_complete: OnCompleteFunc[EventT] | None = None,
    on_cancel: OnCancelFunc[EventT] | None = None,
    manage_system_prompt: Literal['server', 'client'] = 'server',
    allowed_file_url_schemes: frozenset[str] = frozenset({'http', 'https'}),
    allowed_file_url_force_download: frozenset[ForceDownloadMode] = frozenset(),
    allow_uploaded_files: bool = False,
    **kwargs: Any,
) -> Response
```

Handle a protocol-specific HTTP request by running the agent and returning a streaming response of protocol-specific events.

Extra keyword arguments are forwarded to [`from_request`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.from_request), allowing subclasses to accept additional adapter-specific parameters.

###### Returns

`Response` -- A streaming Starlette response with protocol-specific events encoded per the request's `Accept` header value.

###### Parameters

**`request`** : `Request`

The incoming Starlette/FastAPI request.

**`agent`** : `AbstractAgent`\[`DispatchDepsT`, `DispatchOutputDataT`\]

The agent to run.

**`output_type`** : `OutputSpec`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom output type to use for this run, `output_type` may only be used if the agent has no output validators since output validators would expect an argument that matches the agent's output type.

**`message_history`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

History of the conversation so far.

**`deferred_tool_results`** : [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional results for deferred tool calls in the message history.

**`conversation_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

ID of the conversation this run belongs to. Pass `'new'` to start a fresh conversation, ignoring any `conversation_id` already on `message_history`. If omitted, falls back to the most recent `conversation_id` on `message_history` or a freshly generated UUID7.

**`run_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional ID for this agent run. Unlike `conversation_id`, never inherited from `message_history`. Passing an empty string, or a value that already appears on `message_history`, raises `UserError` because both break `new_messages()`; use `conversation_id` to correlate across turns or deferred-tool resume. If omitted, a fresh UUID7 is generated.

**`model`** : `Model` | `KnownModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model to use for this run, required if `model` was not set when creating the agent.

**`instructions`** : [`_instructions.AgentInstructions`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentInstructions)\[`DispatchDepsT`\] _Default:_ `None`

Optional additional instructions to use for this run.

**`deps`** : `DispatchDepsT` _Default:_ `None`

Optional dependencies to use for this run.

**`model_settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to use for this model's request.

**`usage_limits`** : [`UsageLimits`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.UsageLimits) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional limits on model request count or token usage.

**`cancellation_token`** : [`CancellationToken`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.CancellationToken) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional token for cancelling this run from another task.

**`usage`** : [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional usage to start with, useful for resuming a conversation or agents used in tools.

**`metadata`** : `AgentMetadata`\[`DispatchDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata to attach to this run. Accepts a dictionary or a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); merged with the agent's configured metadata.

**`infer_name`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to try to infer the agent name from the call frame if it's not set.

**`toolsets`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`DispatchDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional toolsets for this run.

**`capabilities`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`AbstractCapability`\[`DispatchDepsT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for this run, merged with the agent's configured capabilities. Use `capabilities=[NativeTool(...)]` to add provider-side native tools per request.

**`on_complete`** : `OnCompleteFunc`\[`EventT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callback function called when the agent run completes successfully. The callback receives the completed [`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult) and can optionally yield additional protocol-specific events.

**`on_cancel`** : `OnCancelFunc`\[`EventT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional callback function called when the agent run ends in first-party cancellation. The callback receives the [`RunCancelled`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled) and can optionally yield additional protocol-specific events.

**`manage_system_prompt`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['server', 'client'\] _Default:_ `'server'`

Who owns the system prompt. See [`UIAdapter.manage_system_prompt`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.manage_system_prompt).

**`allowed_file_url_schemes`** : [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] _Default:_ `frozenset({'http', 'https'})`

URL schemes allowed for file URL parts from the client. See [`UIAdapter.allowed_file_url_schemes`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.allowed_file_url_schemes).

**`allowed_file_url_force_download`** : [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[`ForceDownloadMode`\] _Default:_ `frozenset()`

Additional `FileUrl.force_download` values allowed on file URL parts from the client (beyond `False`, which is always allowed). See [`UIAdapter.allowed_file_url_force_download`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.allowed_file_url_force_download).

**`allow_uploaded_files`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether to honor `UploadedFile` references from client-submitted messages. See [`UIAdapter.allow_uploaded_files`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.allow_uploaded_files).

**`**kwargs`** : [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) _Default:_ `{}`

Additional keyword arguments forwarded to [`from_request`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.from_request).

### SSE\_CONTENT\_TYPE

Content type header value for Server-Sent Events (SSE).

**Default:** `'text/event-stream'`

### NativeEvent

Type alias for the native event type, which is either an `AgentStreamEvent` or an `AgentRunResultEvent`.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `AgentStreamEvent | AgentRunResultEvent[Any]`

### OnCompleteFunc

Callback function type that receives the `AgentRunResult` of the completed run. Can be sync, async, or an async generator of protocol-specific events.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `_CallbackFunc[AgentRunResult[Any], EventT]`

### OnCancelFunc

Callback function type that receives the `RunCancelled` of the cancelled run. Can be sync, async, or an async generator of protocol-specific events.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `_CallbackFunc[RunCancelled, EventT]`

---
