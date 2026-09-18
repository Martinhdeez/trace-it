# [pydantic_ai.ui.vercel_ai](https://pydantic.dev/docs/ai/api/ui/vercel_ai/)

# pydantic\_ai.ui.vercel\_ai

Vercel AI protocol adapter for Pydantic AI agents.

This module provides classes for integrating Pydantic AI agents with the Vercel AI protocol, enabling streaming event-based communication for interactive AI applications.

Converted to Python from: [https://github.com/vercel/ai/blob/ai%405.0.34/packages/ai/src/ui/ui-messages.ts](https://github.com/vercel/ai/blob/ai%405.0.34/packages/ai/src/ui/ui-messages.ts)

### VercelAIEventStream

**Bases:** `UIEventStream[RequestData, BaseChunk, AgentDepsT, OutputDataT]`

UI event stream transformer for the Vercel AI protocol.

#### Attributes

##### sdk\_version

Vercel AI SDK version to target. Setting to 6 enables tool approval streaming; 7 emits the same wire as 6 (v7's data-stream protocol equals v6's).

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\[5, 6, 7\] **Default:** `5`

##### server\_message\_id

Optional server-generated message ID to include in the `StartChunk`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### VercelAIAdapter

**Bases:** `UIAdapter[RequestData, UIMessage, BaseChunk, AgentDepsT, OutputDataT]`

UI adapter for the Vercel AI protocol.

#### Attributes

##### sdk\_version

Vercel AI SDK version to target. Default is 5 for backwards compatibility.

Setting `sdk_version=6` enables tool approval streaming for human-in-the-loop workflows. `sdk_version=7` emits the same wire as 6 (v7's data-stream protocol equals v6's); it is accepted so the value reflects the client's real SDK major and reserves it for future v7-only chunks.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\[5, 6, 7\] **Default:** `5`

##### server\_message\_id

Optional server-generated message ID to include in the `StartChunk`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### deferred\_tool\_results

Extract deferred tool results from Vercel AI messages with approval responses.

**Type:** [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### messages

Pydantic AI messages from the Vercel AI run input.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### conversation\_id

Conversation ID from the top-level `id` field of the Vercel AI request body (the chat ID).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### build\_run\_input

`@classmethod`

```python
def build_run_input(cls, body: bytes) -> RequestData
```

Build a Vercel AI run input object from the request body.

###### Returns

`RequestData`

##### from\_request

`@async`

`@classmethod`

```python
def from_request(
    cls,
    request: Request,
    *,
    agent: AbstractAgent[AgentDepsT, OutputDataT],
    sdk_version: Literal[5, 6, 7] = 5,
    server_message_id: str | None = None,
    manage_system_prompt: Literal['server', 'client'] = 'server',
    allowed_file_url_schemes: frozenset[str] = frozenset({'http', 'https'}),
    allowed_file_url_force_download: frozenset[ForceDownloadMode] = frozenset(),
    allow_uploaded_files: bool = False,
    preserve_file_data: bool | None = None,
    **kwargs: Any,
) -> VercelAIAdapter[AgentDepsT, OutputDataT]
```

Extends [`from_request`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.from_request) with Vercel AI-specific parameters.

`preserve_file_data` is a deprecated alias for `allow_uploaded_files`.

###### Returns

`VercelAIAdapter`\[`AgentDepsT`, `OutputDataT`\]

##### dispatch\_request

`@async`

`@classmethod`

```python
def dispatch_request(
    cls,
    request: Request,
    *,
    agent: AbstractAgent[DispatchDepsT, DispatchOutputDataT],
    sdk_version: Literal[5, 6, 7] = 5,
    server_message_id: str | None = None,
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
    usage: RunUsage | None = None,
    metadata: AgentMetadata[DispatchDepsT] | None = None,
    infer_name: bool = True,
    toolsets: Sequence[AbstractToolset[DispatchDepsT]] | None = None,
    capabilities: Sequence[AbstractCapability[DispatchDepsT]] | None = None,
    on_complete: OnCompleteFunc[BaseChunk] | None = None,
    on_cancel: OnCancelFunc[BaseChunk] | None = None,
    manage_system_prompt: Literal['server', 'client'] = 'server',
    allowed_file_url_schemes: frozenset[str] = frozenset({'http', 'https'}),
    allowed_file_url_force_download: frozenset[ForceDownloadMode] = frozenset(),
    allow_uploaded_files: bool = False,
    preserve_file_data: bool | None = None,
    **kwargs: Any,
) -> Response
```

Extends [`dispatch_request`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.dispatch_request) with Vercel AI-specific parameters.

`preserve_file_data` is a deprecated alias for `allow_uploaded_files`.

###### Returns

`Response`

##### build\_event\_stream

```python
def build_event_stream(

) -> UIEventStream[RequestData, BaseChunk, AgentDepsT, OutputDataT]
```

Build a Vercel AI event stream transformer.

###### Returns

`UIEventStream`\[`RequestData`, `BaseChunk`, `AgentDepsT`, `OutputDataT`\]

##### load\_messages

`@classmethod`

```python
def load_messages(cls, messages: Sequence[UIMessage]) -> list[ModelMessage]
```

Transform Vercel AI messages into Pydantic AI messages.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### dump\_messages

`@classmethod`

```python
def dump_messages(
    cls,
    messages: Sequence[ModelMessage],
    *,
    generate_message_id: Callable[[ModelRequest | ModelResponse, Literal['system', 'user', 'assistant'], int], str] | None = None,
    sdk_version: Literal[5, 6, 7] = 5,
) -> list[UIMessage]
```

Transform Pydantic AI messages into Vercel AI messages.

Note: The round-trip `dump_messages` -> `load_messages` is not fully lossless for tool results. Successful, failed, and denied results each round-trip via their own part type (`ToolOutputAvailablePart` / `ToolOutputErrorPart` / `ToolOutputDeniedPart`), but a `RetryPromptPart` becomes a `ToolReturnPart` with `outcome='failed'` on reload (or a user text part when it has no `tool_name`), since the protocol has no separate retry concept -- both a retry prompt and a `ToolFailed` result map to `ToolOutputErrorPart`. A reloaded retry is therefore presented to the model as a definitive failure rather than a request to correct and retry; keep the conversation in-process rather than persisting through the Vercel AI wire format if you need retry semantics to survive a round-trip.

Tool calls lose one thing too: `ToolCallPart.args` that don't parse as a JSON object are rewritten to `{'INVALID_JSON': '<raw args>'}` (see [`args_as_dict`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BaseToolCallPart.args_as_dict)), so the raw string is no longer recoverable as args on reload.

Application keys in `ModelRequest.metadata` round-trip, but the reserved `__pydantic_ai__` namespace and top-level `ModelResponse.provider_details` do not. `UIMessage.metadata` is client-controlled, so framework and provider response state is not exposed or restored through it; see `_PydanticAIMessageMetadata`.

When `sdk_version=6`, tool calls that have no corresponding result in the message history are automatically detected as deferred and emitted with `state='approval-requested'`, so the frontend can render approve/reject buttons on reload. On v5, such tool calls are emitted with `state='input-available'` (approval states are v6-only).

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`UIMessage`\] -- A list of UIMessage objects in Vercel AI format

###### Parameters

**`messages`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

A sequence of ModelMessage objects to convert

**`generate_message_id`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest) | [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse), [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['system', 'user', 'assistant'\], [`int`](https://docs.python.org/3/builtins/functions.html#int)\], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional custom function to generate message IDs. If provided, it receives the message, the role ('system', 'user', or 'assistant'), and the message index (incremented per UIMessage appended), and should return a unique string ID. If not provided, uses `provider_response_id` for responses, run\_id-based IDs for messages with run\_id, or a deterministic UUID5 fallback.

**`sdk_version`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\[5, 6, 7\] _Default:_ `5`

Vercel AI SDK version to target: 5, 6, or 7. Defaults to 5 for backwards compatibility. Set to 6 to emit tool approval parts for deferred tool calls; 7 emits identically to 6 (v7's data-stream protocol equals v6's).

Vercel AI request types (UI messages).

Converted to Python from: [https://github.com/vercel/ai/blob/ai%406.0.57/packages/ai/src/ui/ui-messages.ts](https://github.com/vercel/ai/blob/ai%406.0.57/packages/ai/src/ui/ui-messages.ts)

Tool approval types (`ToolApprovalRequested`, `ToolApprovalResponded`) require AI SDK v6 or later.

### BaseUIPart

**Bases:** `CamelBaseModel`, `ABC`

Abstract base class for all UI parts.

### TextUIPart

**Bases:** `BaseUIPart`

A text part of a message.

#### Attributes

##### text

The text content.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### state

The state of the text part.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['streaming', 'done'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_metadata

The provider metadata.

**Type:** `ProviderMetadata` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### ReasoningUIPart

**Bases:** `BaseUIPart`

A reasoning part of a message.

#### Attributes

##### id

UI part ID from the AI SDK client; not mapped to `ThinkingPart.id`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `Field(default=None, exclude_if=(lambda value: value is None))`

##### text

The reasoning text.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### state

The state of the reasoning part.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['streaming', 'done'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_metadata

The provider metadata.

**Type:** `ProviderMetadata` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### SourceUrlUIPart

**Bases:** `BaseUIPart`

A source part of a message.

### SourceDocumentUIPart

**Bases:** `BaseUIPart`

A document source part of a message.

### FileUIPart

**Bases:** `BaseUIPart`

A file part of a message.

#### Attributes

##### media\_type

IANA media type of the file. @see [https://www.iana.org/assignments/media-types/media-types.xhtml](https://www.iana.org/assignments/media-types/media-types.xhtml)

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### filename

Optional filename of the file.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### url

The URL of the file. It can either be a URL to a hosted file or a [Data URL](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URLs).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_metadata

The provider metadata.

**Type:** `ProviderMetadata` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### StepStartUIPart

**Bases:** `BaseUIPart`

A step boundary part of a message.

### DataUIPart

**Bases:** `BaseUIPart`

Data part with dynamic type based on data name.

### ToolApprovalRequested

**Bases:** `CamelBaseModel`

Tool approval in requested state (awaiting user response).

#### Attributes

##### id

The approval request ID.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### ToolApprovalResponded

**Bases:** `CamelBaseModel`

Tool approval in responded state (user has approved or denied).

#### Attributes

##### id

The approval request ID.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### approved

Whether the user approved the tool call.

Deliberately strict: in Pydantic's default lax mode `{'approved': 1}` or `{'approved': 'true'}` would coerce to an approval, and this field is the client-controlled gate on tools declared `requires_approval=True`. A non-boolean value fails validation -- and so rejects the whole request -- instead of silently executing the call ([#6922](https://github.com/pydantic/pydantic-ai/issues/6922)).

`ToolApproval` is an undiscriminated union, so rejecting here only denies because `CamelBaseModel`'s `extra='forbid'` stops the part re-matching `ToolApprovalRequested` (which upstream declares `approved?: never`). Relaxing either would reopen the gate.

**Type:** `StrictBool`

##### reason

Optional reason for the approval or denial.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### ToolInputStreamingPart

**Bases:** `BaseUIPart`

Tool part in input-streaming state.

### ToolInputAvailablePart

**Bases:** `BaseUIPart`

Tool part in input-available state.

### ToolOutputAvailablePart

**Bases:** `BaseUIPart`

Tool part in output-available state.

### ToolOutputErrorPart

**Bases:** `BaseUIPart`

Tool part in output-error state.

### ToolApprovalRequestedPart

**Bases:** `BaseUIPart`

Tool part in approval-requested state (awaiting user decision).

### ToolApprovalRespondedPart

**Bases:** `BaseUIPart`

Tool part in approval-responded state (user approved/denied, execution pending).

### ToolOutputDeniedPart

**Bases:** `BaseUIPart`

Tool part in output-denied state (tool was denied, terminal state).

### DynamicToolInputStreamingPart

**Bases:** `BaseUIPart`

Dynamic tool part in input-streaming state.

### DynamicToolInputAvailablePart

**Bases:** `BaseUIPart`

Dynamic tool part in input-available state.

### DynamicToolOutputAvailablePart

**Bases:** `BaseUIPart`

Dynamic tool part in output-available state.

### DynamicToolOutputErrorPart

**Bases:** `BaseUIPart`

Dynamic tool part in output-error state.

### DynamicToolApprovalRequestedPart

**Bases:** `BaseUIPart`

Dynamic tool part in approval-requested state (awaiting user decision).

### DynamicToolApprovalRespondedPart

**Bases:** `BaseUIPart`

Dynamic tool part in approval-responded state (user approved/denied, execution pending).

### DynamicToolOutputDeniedPart

**Bases:** `BaseUIPart`

Dynamic tool part in output-denied state (tool was denied, terminal state).

### UIMessage

**Bases:** `CamelBaseModel`

A message as displayed in the UI by Vercel AI Elements.

#### Attributes

##### id

A unique identifier for the message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### role

The role of the message.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['system', 'user', 'assistant'\]

##### metadata

The metadata of the message.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### parts

The parts of the message. Use this for rendering the message in the UI. System messages should be avoided (set the system prompt on the server instead). They can have text parts. User messages can have text parts and file parts. Assistant messages can have text, reasoning, tool invocation, and file parts.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`UIMessagePart`\]

### SubmitMessage

**Bases:** `CamelBaseModel`

Submit message request.

### RegenerateMessage

**Bases:** `CamelBaseModel`

Ask the agent to regenerate a message.

### ProviderMetadata

Provider metadata.

**Default:** `dict[str, dict[str, JSONValue]]`

### ToolApproval

Union of tool approval states.

**Default:** `ToolApprovalRequested | ToolApprovalResponded`

### ToolUIPart

Union of all tool part types.

**Default:** `ToolInputStreamingPart | ToolInputAvailablePart | ToolOutputAvailablePart | ToolOutputErrorPart | ToolApprovalRequestedPart | ToolApprovalRespondedPart | ToolOutputDeniedPart`

### DynamicToolUIPart

Union of all dynamic tool part types.

**Default:** `DynamicToolInputStreamingPart | DynamicToolInputAvailablePart | DynamicToolOutputAvailablePart | DynamicToolOutputErrorPart | DynamicToolApprovalRequestedPart | DynamicToolApprovalRespondedPart | DynamicToolOutputDeniedPart`

### UIMessagePart

Union of all message part types.

**Default:** `TextUIPart | ReasoningUIPart | ToolUIPart | DynamicToolUIPart | SourceUrlUIPart | SourceDocumentUIPart | FileUIPart | DataUIPart | StepStartUIPart`

### RequestData

Union of all request data types.

**Default:** `Annotated[SubmitMessage | RegenerateMessage, Discriminator('trigger')]`

Vercel AI response types (SSE chunks).

Converted to Python from: [https://github.com/vercel/ai/blob/ai%406.0.57/packages/ai/src/ui-message-stream/ui-message-chunks.ts](https://github.com/vercel/ai/blob/ai%406.0.57/packages/ai/src/ui-message-stream/ui-message-chunks.ts)

Tool approval types (`ToolApprovalRequestChunk`, `ToolOutputDeniedChunk`) require AI SDK UI v6 or later.

### BaseChunk

**Bases:** `CamelBaseModel`, `ABC`

Abstract base class for response SSE events.

### TextStartChunk

**Bases:** `BaseChunk`

Text start chunk.

### TextDeltaChunk

**Bases:** `BaseChunk`

Text delta chunk.

### TextEndChunk

**Bases:** `BaseChunk`

Text end chunk.

### ReasoningStartChunk

**Bases:** `BaseChunk`

Reasoning start chunk.

### ReasoningDeltaChunk

**Bases:** `BaseChunk`

Reasoning delta chunk.

### ReasoningEndChunk

**Bases:** `BaseChunk`

Reasoning end chunk.

### ErrorChunk

**Bases:** `BaseChunk`

Error chunk.

### ToolInputStartChunk

**Bases:** `BaseChunk`

Tool input start chunk.

### ToolInputDeltaChunk

**Bases:** `BaseChunk`

Tool input delta chunk.

### ToolOutputAvailableChunk

**Bases:** `BaseChunk`

Tool output available chunk.

### ToolInputAvailableChunk

**Bases:** `BaseChunk`

Tool input available chunk.

### ToolInputErrorChunk

**Bases:** `BaseChunk`

Tool input error chunk.

Requires AI SDK UI v6 or later.

### ToolOutputErrorChunk

**Bases:** `BaseChunk`

Tool output error chunk.

### ToolApprovalRequestChunk

**Bases:** `BaseChunk`

Tool approval request chunk for human-in-the-loop approval.

Requires AI SDK UI v6 or later.

### ToolOutputDeniedChunk

**Bases:** `BaseChunk`

Tool output denied chunk when user denies tool execution.

Requires AI SDK UI v6 or later.

### SourceUrlChunk

**Bases:** `BaseChunk`

Source URL chunk.

### SourceDocumentChunk

**Bases:** `BaseChunk`

Source document chunk.

### FileChunk

**Bases:** `BaseChunk`

File chunk.

### DataChunk

**Bases:** `BaseChunk`

Data chunk with dynamic type.

### StartStepChunk

**Bases:** `BaseChunk`

Start step chunk.

### FinishStepChunk

**Bases:** `BaseChunk`

Finish step chunk.

### StartChunk

**Bases:** `BaseChunk`

Start chunk.

### FinishChunk

**Bases:** `BaseChunk`

Finish chunk.

### AbortChunk

**Bases:** `BaseChunk`

Abort chunk.

### MessageMetadataChunk

**Bases:** `BaseChunk`

Message metadata chunk.

### DoneChunk

**Bases:** `BaseChunk`

Done chunk.

### ProviderMetadata

Provider metadata.

**Default:** `dict[str, dict[str, JSONValue]]`

### FinishReason

Reason why the model finished generating.

**Default:** `Literal['stop', 'length', 'content-filter', 'tool-calls', 'error', 'other'] | None`

---
