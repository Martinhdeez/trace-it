# [pydantic_ai.ui.ag_ui](https://pydantic.dev/docs/ai/api/ui/ag_ui/)

# pydantic\_ai.ui.ag\_ui

AG-UI protocol integration for Pydantic AI agents.

### AGUIEventStream

**Bases:** `UIEventStream[RunAgentInput, BaseEvent, AgentDepsT, OutputDataT]`

UI event stream transformer for the Agent-User Interaction (AG-UI) protocol.

#### Attributes

##### thread\_id

The AG-UI thread ID to report on `RUN_STARTED` and `RUN_FINISHED`.

A [`run_input`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.run_input) takes precedence: when one is given, its thread ID replaces whatever was passed here, with a `UserWarning`. Without a run input, set it to the ID the conversation already has in your own transport, or leave it to default to a new UUID -- but note that the default is minted per stream, so a conversation that spans more than one run needs to pass its own.

This identifies the conversation to the frontend. It is what [`AGUIAdapter`](https://pydantic.dev/docs/ai/api/ui/ag_ui/#pydantic_ai.ui.ag_ui.AGUIAdapter) maps onto the agent's `conversation_id` on the request path, so passing the conversation ID the agent run itself uses keeps the frontend and the agent's traces correlated.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `field(default_factory=_generate_id)`

##### run\_id

The AG-UI run ID to report on `RUN_STARTED` and `RUN_FINISHED`.

A [`run_input`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIEventStream.run_input) takes precedence: when one is given, its run ID replaces whatever was passed here, with a `UserWarning`. Without a run input, set it to the ID the run already has in your own transport, or leave it to default to a new UUID.

This is the protocol's run ID, not the agent run ID that [`UIAdapter.run_stream()`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.run_stream) takes as `run_id`; the two are never wired together.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `field(default_factory=_generate_id)`

#### Methods

##### handle\_event

`@async`

```python
def handle_event(event: NativeEvent) -> AsyncIterator[BaseEvent]
```

Override to set timestamps on all AG-UI events.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`BaseEvent`\]

### AGUIAdapter

**Bases:** `UIAdapter[RunAgentInput, Message, BaseEvent, AgentDepsT, OutputDataT]`

UI adapter for the Agent-User Interaction (AG-UI) protocol.

#### Attributes

##### ag\_ui\_version

AG-UI protocol version controlling behavior thresholds.

Accepts any version string (e.g. `'0.1.11'`). Defaults to the version detected from the installed `ag-ui-protocol` package.

Known thresholds:

-   `< 0.1.11`: emits `THINKING_*` events during streaming, drops `ThinkingPart` from `dump_messages` output.
-   `>= 0.1.11`: emits `REASONING_*` events with encrypted metadata during streaming, and includes `ThinkingPart` as `ReasoningMessage` in `dump_messages` output for full round-trip fidelity of thinking signatures and provider metadata.
-   `>= 0.1.15`: emits typed multimodal input content (`ImageInputContent`, `AudioInputContent`, `VideoInputContent`, `DocumentInputContent`) instead of generic `BinaryInputContent`.

`load_messages` always accepts `ReasoningMessage` and multimodal content types regardless of this setting, and `build_run_input` skips inbound content types the installed `ag-ui-protocol` predates rather than rejecting the request.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `DEFAULT_AG_UI_VERSION`

##### preserve\_file\_data

Whether to round-trip `FilePart` and `UploadedFile` through reserved `pydantic_ai_*` [activity messages](https://docs.ag-ui.com/concepts/messages).

Defaults to `False`. AG-UI has no native representation for agent-generated files ([`FilePart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FilePart)) or uploaded-file references ([`UploadedFile`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UploadedFile)), so when this is `True` they are serialized as sidecar activity messages on `dump_messages` and reconstructed on `load_messages`. A frontend only completes the round-trip if it echoes these activity messages back on the next request.

This is a representation setting, not a security one: honoring a reconstructed inbound `UploadedFile` still requires [`allow_uploaded_files`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.allow_uploaded_files), which the shared `sanitize_messages` step enforces regardless of this flag. Multimodal tool-return files are unaffected -- they ride inline in `ToolMessage.content`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### messages

Pydantic AI messages from the AG-UI run input.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### toolset

Toolset representing frontend tools from the AG-UI run input.

**Type:** [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### state

Frontend state from the AG-UI run input.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### conversation\_id

Conversation ID from the AG-UI `RunAgentInput.threadId`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### deferred\_tool\_results

Translate AG-UI `RunAgentInput.resume[]` into Pydantic AI `DeferredToolResults`.

See [docs.ag-ui.com/concepts/interrupts](https://docs.ag-ui.com/concepts/interrupts).

Each `ResumeEntry` is mapped to an approval keyed by the original `tool_call_id`. The payload is validated against the same Pydantic model whose JSON schema is advertised on `Interrupt.response_schema`, and the mapping is **deny-by-default**: approval requires a payload that validates with `approved=True`. Any other shape is treated as a denial so a malformed or hostile client cannot accidentally execute a tool that requires human approval.

-   `status == 'cancelled'` → `ToolDenied('Cancelled by user.')`
-   `payload.approved is True` with a valid `payload.editedArgs` dict → `ToolApproved(override_args=...)`
-   `payload.approved is True` without edits → `ToolApproved()`
-   Anything else (`False`, missing, `null`, non-bool `approved`, non-dict payload, a non-dict `editedArgs`, or a non-string `reason`) → `ToolDenied(payload.reason)` if `reason` is a non-empty string on a payload that validated, else `ToolDenied()` (which carries the default `"The tool call was denied."` message).

Returns `None` when `resume` is missing or empty, or when the installed ag-ui-protocol predates the interrupt lifecycle.

**Type:** [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### build\_run\_input

`@classmethod`

```python
def build_run_input(cls, body: bytes) -> RunAgentInput
```

Build an AG-UI run input object from the request body.

A message `role` or input content `type` introduced by a protocol version newer than the installed `ag-ui-protocol` is skipped with a warning rather than failing the whole request, per the backwards-compatibility policy in `pydantic_ai/ui/AGENTS.md`. Only items the installed models cannot dispatch at all are skipped: a body that is invalid for any other reason still raises, so a client bug isn't converted into silent misbehavior.

###### Returns

`RunAgentInput`

##### build\_event\_stream

```python
def build_event_stream(

) -> UIEventStream[RunAgentInput, BaseEvent, AgentDepsT, OutputDataT]
```

Build an AG-UI event stream transformer.

###### Returns

`UIEventStream`\[`RunAgentInput`, `BaseEvent`, `AgentDepsT`, `OutputDataT`\]

##### from\_request

`@async`

`@classmethod`

```python
def from_request(
    cls,
    request: Request,
    *,
    agent: AbstractAgent[AgentDepsT, OutputDataT],
    ag_ui_version: str = DEFAULT_AG_UI_VERSION,
    preserve_file_data: bool = False,
    manage_system_prompt: Literal['server', 'client'] = 'server',
    allowed_file_url_schemes: frozenset[str] = frozenset({'http', 'https'}),
    allowed_file_url_force_download: frozenset[ForceDownloadMode] = frozenset(),
    allow_uploaded_files: bool = False,
    **kwargs: Any,
) -> AGUIAdapter[AgentDepsT, OutputDataT]
```

Extends [`from_request`](https://pydantic.dev/docs/ai/api/ui/base/#pydantic_ai.ui.UIAdapter.from_request) with AG-UI-specific parameters.

###### Returns

`AGUIAdapter`\[`AgentDepsT`, `OutputDataT`\]

##### load\_messages

`@classmethod`

```python
def load_messages(
    cls,
    messages: Sequence[Message],
    *,
    preserve_file_data: bool = False,
) -> list[ModelMessage]
```

Transform AG-UI messages into Pydantic AI messages.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### dump\_messages

`@classmethod`

```python
def dump_messages(
    cls,
    messages: Sequence[ModelMessage],
    *,
    ag_ui_version: str = DEFAULT_AG_UI_VERSION,
    preserve_file_data: bool = False,
) -> list[Message]
```

Transform Pydantic AI messages into AG-UI messages.

Note: The round-trip `dump_messages` -> `load_messages` is not fully lossless:

-   `ModelRequest.metadata` and top-level `ModelResponse.provider_details` are lost. AG-UI has no trusted message-level carrier for framework or provider state; general client-controlled metadata must not be restored as server-side state.
-   `TextPart.id`, `.provider_name`, `.provider_details` are lost.
-   `ToolCallPart.id`, `.provider_name`, `.provider_details` are lost.
-   `ToolCallPart.args` and `NativeToolCallPart.args` that don't parse as a JSON object are rewritten to `'{"INVALID_JSON":"<raw args>"}'` (see [`args_as_json_str`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BaseToolCallPart.args_as_json_str)), so the raw string is no longer recoverable as args on reload. Unlike the live event stream, which emits them verbatim so streamed fragments stay concatenable, history has to hold a sendable value.
-   `NativeToolCallPart.id`, `.provider_details` are lost (only `.provider_name` survives via the prefixed tool call ID).
-   `NativeToolReturnPart.provider_details` is lost.
-   `tool_kind` is lost when `ag_ui_version < '0.1.11'` (before its `encrypted_value` carrier existed), so typed tool parts reload as their base classes.
-   `tool_kind` is not restored on error/denied tool returns (a typed return implies success to its readers), so those reload as plain `ToolReturnPart`.
-   A non-`'success'` `outcome` on a (native) tool return survives via the `encrypted_value` carrier from 0.1.11 (`ToolMessage` has no outcome slot). Below that, `'failed'` survives via `ToolMessage.error`, `'denied'` reloads as `'failed'`, and `'interrupted'` reloads as `'success'`.
-   `RetryPromptPart` becomes `ToolReturnPart` (or `UserPromptPart`) on reload.
-   A `NativeToolReturnPart` is always emitted directly after its `NativeToolCallPart`, so any part that originally sat between them -- e.g. a `CompactionPart` -- reloads after the pair instead. Provider adapters emit compaction parts outside call/return pairs, so this only affects hand-constructed histories.
-   `CachePoint` and `UploadedFile` content items are dropped (unless `preserve_file_data=True`).
-   `FileUrl.force_download` is dropped when `ag_ui_version < '0.1.15'` (before typed multimodal content gained a metadata carrier).
-   `ThinkingPart` is dropped when `ag_ui_version='0.1.10'`.
-   `FilePart` is silently dropped unless `preserve_file_data=True`.
-   `UploadedFile` in a multi-item `UserPromptPart` is split into a separate activity message when `preserve_file_data=True`, which reloads as a separate `UserPromptPart`.
-   `MultiModalContent` items in `ToolReturnPart`/`NativeToolReturnPart.content` always round-trip, regardless of `preserve_file_data`: the full content (files as base64/URL dicts) is serialized inline into the JSON `ToolMessage.content` and rehydrated on reload through the `ToolReturnContent` union. The same serialization is used for both history (`dump_messages`) and the live event stream (`ToolCallResultEvent.content`), so files survive either round-trip.
-   Part ordering within a `ModelResponse` may change when text follows tool calls.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`Message`\] -- A list of AG-UI Message objects.

###### Parameters

**`messages`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

A sequence of ModelMessage objects to convert.

**`ag_ui_version`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `DEFAULT_AG_UI_VERSION`

AG-UI protocol version controlling `ThinkingPart` emission.

**`preserve_file_data`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether to include `FilePart` and `UploadedFile` items as `ActivityMessage`s. (Multimodal tool-return files always ride inline in `ToolMessage.content` and are unaffected.)

### DEFAULT\_AG\_UI\_VERSION

The default AG-UI version, auto-detected from the installed `ag-ui-protocol` package.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `detect_ag_ui_version()`

---
