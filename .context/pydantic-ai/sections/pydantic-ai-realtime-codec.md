# [pydantic_ai.realtime.codec](https://pydantic.dev/docs/ai/api/realtime/codec/)

# pydantic\_ai.realtime.codec

The lower-level _codec_ vocabulary, for implementing a realtime provider or consuming a [`RealtimeConnection`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeConnection) directly: the raw events a connection yields, the turn-control verbs and inputs it accepts, and the model-profile merge helpers. Most users only need the session-level API in [`pydantic_ai.realtime`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/).

Low-level _codec_ vocabulary for realtime providers.

Most users only need the session-level API in [`pydantic_ai.realtime`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime) ([`AgentRealtime.session`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.session), the events a session yields, and the content passed to [`RealtimeSession.send`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send)). This submodule holds the lower-level vocabulary used when _implementing_ a realtime provider or consuming a [`RealtimeConnection`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeConnection) directly: the raw codec events a connection yields to the session, the turn-control verbs and inputs a connection accepts, and the model-profile merge helpers.

### ToolResult

The result of a tool call, rendered for the wire and sent back to the model.

Built and sent by [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) after it settles a call: the string-only realtime tool channel and the retry/failure error-key wrapping mean the session renders the [`ToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturnPart) or [`RetryPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.RetryPromptPart) it records in history down to this flat shape, so every provider sends exactly the same rendering.

#### Attributes

##### tool\_call\_id

Identifier of the `ToolCall` this result answers.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### output

The tool's output, rendered as a string.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### content

Additional user content to send after the tool output when the provider supports it.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`UserContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserContent)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### TextContext

A text item added to the conversation as context, without asking the model to respond (like an image).

### CommitAudio

Commit the buffered input audio as a user turn (manual turn-taking / push-to-talk).

Only needed when automatic voice activity detection is disabled; with server-side VAD the provider commits audio and triggers a response automatically.

### ClearAudio

Discard any buffered, uncommitted input audio.

### CreateResponse

Ask the model to generate a response now (manual turn-taking, after `CommitAudio`).

### CancelResponse

Cancel the model's in-progress response (maps to the provider's response-cancel).

### TruncateOutput

Truncate the model's current audio output at `audio_end_ms`.

After a barge-in the user only heard part of the model's audio. Truncating tells the provider how much was actually played, so its stored transcript matches and the conversation context stays consistent. The provider resolves which output item to truncate from its own state.

#### Attributes

##### audio\_end\_ms

Milliseconds of the current output audio that were actually played before the interruption.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

### AudioDelta

A chunk of audio output from the model.

#### Attributes

##### data

Raw PCM audio bytes. The sample rate is provider-specific.

**Type:** [`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes)

##### item\_id

Provider item ID for the spoken output this chunk belongs to, when available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### OutputTranscript

The model's textual output (partial or final): an audio transcript, or plain text output.

#### Attributes

##### text

Transcript text. A partial event carries the incremental delta; a final event the full turn.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### is\_final

Whether this is the final transcript for the turn.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### output\_text

Whether this is the model's plain text output (`output_modalities=('text',)`) rather than a transcription of spoken audio. Text output becomes a [`TextPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.TextPart); an audio transcript becomes a [`SpeechPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### item\_id

Provider item ID for the spoken output, when available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### InputTranscript

A transcription of the user's audio input (partial or final).

Providers with per-item IDs use `item_id` to associate interleaved transcripts with the correct user turn. Providers without them retain arrival-order association.

#### Attributes

##### text

Transcript text.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### is\_final

Whether this is the final transcript for the user's turn.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### item\_id

Provider item ID for the user's turn, when available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### cumulative

Whether `text` is the whole transcript so far rather than an incremental piece.

Speech recognition is revisable, and a provider that streams cumulative snapshots may correct what it already transcribed instead of only extending it. Setting this lets the session adopt each snapshot as authoritative rather than guessing from prefixes whether the text appends; it surfaces the difference to callers as a [`SpeechPartDelta.transcript`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPartDelta.transcript) carrying the corrected whole. Leave `False` for incremental deltas.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

### ToolCall

The model is requesting a tool call.

#### Attributes

##### tool\_call\_id

Provider-assigned identifier for this call.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### tool\_name

Name of the tool to invoke.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### args

Raw JSON-encoded arguments. May be an empty string if the model sent no arguments.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### response\_usage\_follows

Whether per-response [`SessionUsage`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.SessionUsage) will follow this call before the provider's response is complete.

OpenAI-protocol providers report calls before `response.done`, which carries usage; the session uses this signal to keep all calls and their usage on the same `ModelResponse`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### item\_id

Provider conversation-item ID for this call, when available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### ToolCallCancelled

The model cancelled in-flight tool calls (e.g. the user barged in before they finished).

Gemini Live sends this as `toolCallCancellation`; the session cancels the matching running tool tasks so their now-unwanted results are never sent back to the model.

#### Attributes

##### tool\_call\_ids

Identifiers of the [`ToolCall`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.ToolCall)s that were cancelled.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

### ResponseDone

The provider reported that its current response is done.

This codec event is consumed by the session to finalize a [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse). Providers do not necessarily report a terminal for every model response the session records in history.

#### Attributes

##### interrupted

Whether the response ended because it was cancelled (e.g. the user barged in).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### provider\_response\_id

Provider-assigned ID for the completed response, when available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### finish\_reason

Normalized reason the provider finished the response, when available.

**Type:** [`FinishReason`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FinishReason) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Raw provider terminal status details retained on the finalized response, when available.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['response\_done'\] **Default:** `'response_done'`

### SessionUsage

Usage reported by the provider for a model response or another run-level operation.

#### Attributes

##### usage

Normalized usage ready to accumulate into a `RunUsage`.

**Type:** [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage)

##### provider\_response\_id

Provider-assigned ID for the response this usage belongs to, when available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### finish\_reason

Normalized completion reason for the response this usage belongs to, when available.

**Type:** [`FinishReason`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FinishReason) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### response\_scoped

Whether this usage belongs to a specific model response.

`True`, the default, accumulates it both into the run total and the response's `ModelResponse.usage`. `False` is run-level only, e.g. input audio transcription usage, which is billed on a separate model/meter and is accumulated into the run's `RunUsage` but attributed to no `ModelResponse`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['session\_usage'\] **Default:** `'session_usage'`

### ConversationCreated

An OpenAI-protocol server assigned a conversation ID.

This is a codec-level control event. Providers consume it during their handshake when possible; the session silently consumes any instance that reaches the live stream.

#### Attributes

##### conversation\_id

Provider-assigned conversation ID.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### ConversationItemCreated

An OpenAI-protocol server reported a conversation item.

xAI uses `replayed=True` for item events emitted during the resume handshake. The session consumes those items and remembers their newly assigned IDs so any follow-on content or tool events aren't appended or executed again.

#### Attributes

##### item\_id

Provider-assigned conversation-item ID, when present.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_call\_id

Provider-assigned tool-call ID, for function call and result items.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### replayed

Whether the provider identified this item as part of a resumption replay.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

### RealtimeConnection

**Bases:** `ABC`

A live connection to a realtime model.

Providers implement this to handle protocol-specific framing (WebSocket frames, HTTP/2 messages, etc.). Content is fed in via [`send`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeConnection.send) and events are consumed by iterating the connection.

#### Attributes

##### transport\_errors

The exception types this connection's transport raises when the link to the provider fails.

A [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) maps these to [`RealtimeError`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeError) so a failed send surfaces as the same typed error as a failed receive, instead of leaking a `websockets` or provider-SDK exception the caller has no reason to expect from a model call. Leave empty if `send` already raises typed errors.

The mapping covers the whole of [`send`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeConnection.send), so anything it does _besides_ writing to the transport -- converting content, downloading media -- must not raise these types, or a local failure would be reported as a lost connection. Do that work before the first frame goes out.

**Type:** [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[[`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)\], ...\] **Default:** `()`

##### model\_name

The model id the server reported serving this session, when the provider reports one.

Captured from the connect handshake (e.g. the OpenAI protocol's `session.created`). It can differ from the requested model id: xAI accepts any model slug and silently substitutes its current default, reporting the actually-served model only here. `None` when the provider doesn't report one (e.g. Gemini Live). The session stamps this on each [`ModelResponse.model_name`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse.model_name), mirroring how request-response models record the response's reported model rather than the requested one.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### input\_transcription\_enabled

Whether this connection will emit [`InputTranscript`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.InputTranscript) events for the user's audio.

Providers that transcribe the user's input (the default) leave this `True`. When it is `False`, no transcript arrives, so [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) finalizes a user turn from retained input audio instead (see `audio_retention`). Defaults to `True` so a connection that doesn't override it never triggers the audio-only path (which would risk a duplicate turn if transcripts did arrive).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### interrupts\_response\_on\_speech

Whether the configured turn detection makes the _server_ cancel the active response when user speech starts.

OpenAI-protocol server VAD with `interrupt_response` enabled (the default) cancels the in-progress response on speech onset by itself. A client cancel sent at that same moment can race the server's own cancellation and be applied to the _next_ response instead, silencing the reply to the barge-in -- so the session's automatic barge-in handling sends only the truncation when this is `True`. Defaults to `False`, which keeps the client-side cancel.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### reconnect\_restores\_in\_flight\_state

Whether a reconnect continues the response and tool calls that were in flight when the socket dropped.

Otherwise it only brings back the finalized conversation. Native session resumption (xAI Grok Voice) restores the in-flight generation server-side, and Gemini Live settles the cut turn in the connection before its [`RealtimeSessionReconnectEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSessionReconnectEvent), so in both the [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) must not settle again and trusts `state_restored`. Local replay (OpenAI, Azure OpenAI) restores only finalized turns, so the session settles the interrupted turn itself and reports `state_restored=False`. Defaults to `True`; the OpenAI connection overrides it.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### Methods

##### send

`@abstractmethod`

`@async`

```python
def send(content: RealtimeInput) -> None
```

Feed content into the session.

Concrete connections accept provider-specific data and control inputs. OpenAI accepts audio, text, images, tool results, manual turn controls, cancellation, and truncation; Gemini accepts audio, text, images, and tool results. A high-level [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) checks profile-gated operations and raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError), as does a connection handed an input it can't send.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### \_\_aiter\_\_

`@abstractmethod`

```python
def __aiter__() -> AsyncIterator[RealtimeCodecEvent]
```

Iterate over events received from the model.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`RealtimeCodecEvent`\]

##### set\_message\_history

```python
def set_message_history(message_history: Callable[[], Sequence[ModelMessage]]) -> None
```

Tell the connection how to read the message history as it currently stands.

A [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) calls this when it takes ownership of the connection, so a provider that loses server-side state on [reconnect](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.ReconnectPolicy) can replay the conversation into the new session instead of resuming with total amnesia. The session's history grows as the call goes on, hence a callable rather than a snapshot.

A no-op by default: providers with native session resumption (Gemini Live, xAI) have nothing to replay, and one that can't seed a session at all has nowhere to put it.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### merge\_realtime\_profile

```python
def merge_realtime_profile(
    base: RealtimeModelProfile | None,
    *overrides: RealtimeModelProfile | None,
) -> RealtimeModelProfile
```

Merge realtime profiles, with later layers overriding earlier ones.

#### Returns

`RealtimeModelProfile`

### RealtimeSessionInput

The content types a caller feeds into [`RealtimeSession.send`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send).

Session content only, in the shared message vocabulary: a `str` is a complete text turn, and [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) carries an image frame, WAV audio (unwrapped to raw PCM before it is streamed, matching the history-seeding path), or a raw PCM chunk (`media_type='audio/pcm'`). The session normalizes these before forwarding them to the connection. Turn-control verbs (`CommitAudio`, `ClearAudio`, `CreateResponse`, `CancelResponse`, `TruncateOutput`) are connection-level vocabulary driven through the dedicated `RealtimeSession` methods (`commit_audio()`, `clear_audio()`, `create_response()`, `interrupt()`), and [`ToolResult`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.ToolResult) is sent by the session itself when a tool completes -- neither is accepted by `send()`.

**Default:** `TypeAliasType('RealtimeSessionInput', 'str | BinaryContent')`

### DEFAULT\_AUDIO\_SAMPLE\_RATE

The sample rate, in Hz, assumed for PCM audio when a realtime model profile doesn't specify one.

**Default:** `24000`

### DEFAULT\_REALTIME\_PROFILE

Default realtime model profile values.

**Type:** `RealtimeModelProfile` **Default:** `{'supports_image_input': False, 'supports_manual_turn_control': False, 'supports_interruption': False, 'supports_output_truncation': False, 'supports_text_output': True, 'supports_session_seeding': False, 'supports_webrtc': False, 'supports_seeding_images': False, 'supports_seeding_audio': False, 'supports_async_tool_calls': False, 'supports_tool_return_schema': False, 'supported_native_tools': frozenset(), 'emits_input_speech_events': False, 'audio_input_sample_rate': DEFAULT_AUDIO_SAMPLE_RATE, 'audio_output_sample_rate': DEFAULT_AUDIO_SAMPLE_RATE, 'context_window': None}`

### RealtimeInput

Union of content types accepted by [`RealtimeConnection.send`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeConnection.send).

The connection-level counterpart of [`RealtimeSessionInput`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSessionInput), already normalized: a `str` is a complete text turn that solicits a response, [`TextContext`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.TextContext) is text added without soliciting a response, a [`BinaryAudio`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryAudio) carries a raw mono PCM16 chunk at the model's [`audio_input_sample_rate`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.audio_input_sample_rate) (`media_type='audio/pcm'`), and a [`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage) an image frame. The connection additionally accepts the turn-control verbs and [`ToolResult`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.ToolResult), which [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) sends on the caller's behalf.

**Default:** `TypeAliasType('RealtimeInput', 'str | TextContext | BinaryAudio | BinaryImage | CommitAudio | ClearAudio | CreateResponse | CancelResponse | TruncateOutput | ToolResult')`

### RealtimeCodecEvent

Union of the low-level codec events yielded by [`RealtimeConnection`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeConnection).

This is the provider-facing vocabulary: providers translate their wire protocol into these events, and [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) translates them again into the shared [`RealtimeEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeEvent) vocabulary while building [`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage) history.

**Default:** `TypeAliasType('RealtimeCodecEvent', AudioDelta | OutputTranscript | InputTranscript | ToolCall | ToolCallCancelled | ResponseDone | RealtimeInputSpeechStartEvent | RealtimeResponseInterruptedEvent | RealtimeInputSpeechEndEvent | RealtimeOutputSpeechStartEvent | RealtimeOutputSpeechEndEvent | RealtimeInputTranscriptionErrorEvent | SessionUsage | RealtimeSessionReconnectEvent | ConversationCreated | ConversationItemCreated | PartStartEvent | PartEndEvent | RealtimeSessionErrorEvent)`

---
