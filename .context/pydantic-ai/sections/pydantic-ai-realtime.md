# [pydantic_ai.realtime](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/)

# pydantic\_ai.realtime

Support for **realtime, bidirectional speech-to-speech models** (OpenAI Realtime, Azure OpenAI, Gemini Live, xAI Grok Voice, and any other provider that streams audio in and out over a persistent connection).

Unlike [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model), which is request-response, a realtime model opens a long-lived connection: you stream audio (or text/images) in, and consume audio, transcripts, and tool calls as they arrive. The high-level entry point is `Agent.realtime()`, followed by [`AgentRealtime.session()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.session), which wires the agent's tools and instructions into a session and runs the tool loop for you. See the [Realtime guide](https://pydantic.dev/docs/ai/realtime/overview/) for a walkthrough.

The flow of a session:

```mermaid
graph LR
    App -- "send(): RealtimeSessionInput" --> S[RealtimeSession]
    S -- "send(): RealtimeInput" --> C[RealtimeConnection]
    M[RealtimeModel] -- "connect()" --> C
    C -- "RealtimeCodecEvent" --> S
    S -- "RealtimeEvent" --> App
```

A [`RealtimeModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel) opens a [`RealtimeConnection`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeConnection) (the provider-specific transport). A [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) wraps that connection: it translates the low-level codec events into the shared message/part event vocabulary from [`pydantic_ai.messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages), builds ordinary [`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage) history, and executes tools automatically -- intercepting each [`ToolCall`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.ToolCall), running it, sending the [`ToolResult`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.ToolResult) back, and emitting a [`FunctionToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolCallEvent) then a [`FunctionToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolResultEvent). Every tool runs in the background, so a slow one never blocks the session; whether the _model_ keeps speaking meanwhile is provider-specific (see [Concurrent tool execution](https://pydantic.dev/docs/ai/realtime/tools/#concurrent-tool-execution)).

**Provider abstractions & session**

Object

Role

[`RealtimeModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel)

Provider ABC; `connect()` opens a connection.

[`RealtimeModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings)

Settings shared by realtime providers.

[`TurnDetection`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.TurnDetection)

Cross-provider automatic VAD sensitivity, padding, and silence configuration.

[`KnownRealtimeModelName`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.KnownRealtimeModelName) / [`infer_realtime_model`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.infer_realtime_model)

Provider-prefixed model IDs and inference.

[`RealtimeConnection`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeConnection)

Provider ABC; `send()` content in, iterate events out.

[`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession)

Wraps a connection with automatic concurrent tool dispatch.

**Browser / WebRTC** -- for browser voice agents, the media flows browser ↔ provider directly while the backend runs a control-plane sideband (OpenAI and Azure OpenAI; see [Connecting a frontend](https://pydantic.dev/docs/ai/realtime/deployment/#browser-webrtc-server-sideband)):

Object

Role

[`RealtimeModel.answer_webrtc_offer`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.answer_webrtc_offer)

Relay the browser's SDP offer; return the SDP answer and a [`WebRTCAnswer`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.WebRTCAnswer) / [`WebRTCSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.WebRTCSession).

[`RealtimeModel.create_client_secret`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.create_client_secret)

Mint an ephemeral [`RealtimeClientSecret`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeClientSecret) for a browser client.

[`AgentRealtime.session(provider_session=...)`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.session)

Attach the sideband session to a [`RealtimeProviderSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeProviderSession) (e.g. a [`WebRTCSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.WebRTCSession)) and run the agent.

**Inputs** -- [`RealtimeSession.send`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send) accepts session content only, in the shared message vocabulary ([`RealtimeSessionInput`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSessionInput)): plain `str`, image/audio [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) (including [`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage) and [`BinaryAudio`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryAudio)), or a sequence of these. A string solicits a response, while an image is context-only by default; use `respond` to override either behavior. Turn-taking and interruption go through the dedicated [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) methods (`commit_audio()`, `clear_audio()`, `create_response()`, `interrupt()`), not `send()`. Use [`RealtimeSession.enqueue()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.enqueue) to queue text or system prompt parts for delivery after the active response, or once the model is idle.

**Consumption views** -- [`RealtimeSession.stream_audio()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_audio) yields model audio chunks ready for playback, while [`RealtimeSession.stream_transcripts()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_transcripts) yields finalized speech from both speakers or live deltas with `delta=True`. These bounded views can run concurrently with each other and with the session's raw event iterator. [`RealtimeSession.close()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.close) ends the session and every live view; [`RealtimeSession.closed`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.closed) exposes its state.

The low-level [`RealtimeConnection.send`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeConnection.send) accepts the normalized [`RealtimeInput`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeInput) -- a `str` text turn, a [`TextContext`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.TextContext) item added without soliciting a reply, a raw-PCM [`BinaryAudio`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryAudio) chunk, or a [`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage) frame -- which additionally includes the turn-control verbs ([`CommitAudio`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.CommitAudio), [`ClearAudio`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.ClearAudio), [`CreateResponse`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.CreateResponse), [`CancelResponse`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.CancelResponse), and [`TruncateOutput`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.TruncateOutput)) that those session methods emit, plus [`ToolResult`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.ToolResult) -- which the session sends itself as each tool completes.

**Connection events** -- [`RealtimeCodecEvent`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeCodecEvent), the low-level codec vocabulary yielded by a connection: [`AudioDelta`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.AudioDelta), [`OutputTranscript`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.OutputTranscript), [`InputTranscript`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.InputTranscript), [`ToolCall`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.ToolCall), [`ToolCallCancelled`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.ToolCallCancelled), [`ResponseDone`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.ResponseDone), [`RealtimeInputSpeechStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeInputSpeechStartEvent), [`RealtimeInputSpeechEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeInputSpeechEndEvent), [`RealtimeResponseInterruptedEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeResponseInterruptedEvent), [`RealtimeSessionReconnectEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSessionReconnectEvent), [`SessionUsage`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.SessionUsage), and [`RealtimeSessionErrorEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSessionErrorEvent).

**Session events** -- [`RealtimeEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeEvent), yielded by a session. The session translates codec events into the shared vocabulary from [`pydantic_ai.messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages): content streams as [`PartStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartStartEvent) / [`PartDeltaEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartDeltaEvent) / [`PartEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartEndEvent) (carrying [`SpeechPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart)s and [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart)s), tool execution as [`FunctionToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolCallEvent) / [`FunctionToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolResultEvent), inline deferred handling as [`DeferredToolRequestsEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.DeferredToolRequestsEvent) / [`DeferredToolResultsEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.DeferredToolResultsEvent), and the rest as the control-plane events above (`RealtimeInputSpeechStartEvent`, `RealtimeInputSpeechEndEvent`, `RealtimeResponseInterruptedEvent`, `RealtimeSessionReconnectEvent`, and `RealtimeSessionErrorEvent`), plus [`RealtimeTurnCompleteEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeTurnCompleteEvent), which the session synthesizes rather than reading off the wire. Usage updates are accumulated on the session and are not yielded.

The lower-level codec vocabulary is documented in [`pydantic_ai.realtime.codec`](https://pydantic.dev/docs/ai/api/realtime/codec/), and each provider in its own module: [`pydantic_ai.realtime.openai`](https://pydantic.dev/docs/ai/api/realtime/openai/), [`pydantic_ai.realtime.google`](https://pydantic.dev/docs/ai/api/realtime/google/), [`pydantic_ai.realtime.xai`](https://pydantic.dev/docs/ai/api/realtime/xai/), and [`pydantic_ai.realtime.azure`](https://pydantic.dev/docs/ai/api/realtime/azure/).

Realtime multimodal session support for bidirectional streaming models.

This package adds support for native speech-to-speech models (OpenAI Realtime, Azure OpenAI, Gemini Live, and xAI Grok Voice) which use a persistent bidirectional connection rather than the request-response pattern of the standard [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) interface.

The provider-agnostic pieces mirror the request-response layout: `pydantic_ai.realtime.model` holds [`RealtimeModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel) and model inference, `pydantic_ai.realtime.settings` the settings vocabulary, `pydantic_ai.realtime.profiles` the model profiles, and [`pydantic_ai.realtime.codec`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec) the low-level connection vocabulary; concrete providers live in submodules (e.g. `pydantic_ai.realtime.openai`). The high-level entry point is `Agent.realtime`, followed by [`AgentRealtime.session`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.session).

A session translates the low-level codec events (the connection-facing `RealtimeCodecEvent` vocabulary) into the shared message/part event vocabulary from [`pydantic_ai.messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages) ([`PartStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartStartEvent), [`FunctionToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolCallEvent), ...), plus the realtime control-plane events defined below.

### RealtimeModelProfile

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Describes what a [`RealtimeModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel) supports, so a session can tailor its behavior to the model.

Mirrors the shape and `supports_`\-prefixed naming of [`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) for the standard request-response [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model), which realtime models don't share a hierarchy with.

A [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) reads these flags to reject unsupported operations with a clear error _before_ sending them, rather than letting the provider fail mid-session. Read a model's via [`RealtimeModel.profile`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.profile); each flag maps to the session methods a provider may not support.

All fields are optional. Consumers treat absent boolean flags as `False` -- except the handful documented below as defaulting to `True`, which describe a capability every provider has unless it says otherwise -- absent `supported_native_tools` as empty, absent sample rates as the values in [`DEFAULT_REALTIME_PROFILE`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.DEFAULT_REALTIME_PROFILE), and an absent `context_window` as unknown.

#### Attributes

##### supports\_image\_input

Whether the model accepts discrete image/video frames via image [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) passed to [`send`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_manual\_turn\_control

Whether the model supports manual turn-taking -- [`commit_audio`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.commit_audio), [`clear_audio`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.clear_audio), and [`create_response`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.create_response) (push-to-talk). When `False` the model drives turn-taking itself via automatic voice activity detection.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_interruption

Whether the model supports server-side interruption -- cancelling the model's in-progress response via [`interrupt`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.interrupt).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_output\_truncation

Whether the model can truncate its in-progress audio output to the point the user actually heard, via the `played_ms` argument of [`interrupt`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.interrupt).

Distinct from [`supports_interruption`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile.supports_interruption): a provider may support cancelling a response (barge-in) without supporting output truncation. OpenAI supports both; xAI Grok Voice supports cancellation but not truncation.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_text\_output

Whether the model can generate text instead of speech, via [`output_modality='text'`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings.output_modality).

Defaults to `True`: a realtime model that only speaks is the exception, not the rule. When `False`, `Agent.realtime` rejects `output_modality='text'` with a [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) before connecting, rather than letting the provider fail the handshake (Gemini Live answers `1007 The requested combination of response modalities (TEXT) is not supported by the model`) or, worse, silently produce speech anyway (xAI).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_session\_seeding

Whether the model can seed a session with prior conversation (`message_history`).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_webrtc

Whether the model supports browser WebRTC signaling, ephemeral client secrets, and a server-side control-plane sideband via [`answer_webrtc_offer`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.answer_webrtc_offer), [`create_client_secret`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.create_client_secret), and [`connect_webrtc`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.connect_webrtc).

Supported by OpenAI and Azure OpenAI. Gemini Live and xAI Grok Voice are WebSocket-only.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_seeding\_images

Whether prior images can be included when seeding a session with `message_history`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_seeding\_audio

Whether retained user audio can be included when seeding a session with `message_history`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_thinking

Whether the model supports reasoning/thinking configuration via the [`thinking`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings.thinking) setting -- OpenAI's `gpt-realtime-2*` reasoning models, Gemini's native-audio models, and xAI's `grok-voice-latest` and `grok-voice-think-*` models. When `False` (the default), a `thinking` setting is silently ignored rather than sent to a model that would reject it.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_async\_tool\_calls

Whether the model runs tool calls asynchronously without blocking generation.

Gemini Live maps this to `Behavior.NON_BLOCKING` on function declarations and `FunctionResponseScheduling.INTERRUPT` on function responses.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supports\_tool\_return\_schema

Whether the model natively renders a tool's [`return_schema`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition.return_schema) (Gemini Live's function-declaration `response` schema). Where it can't, a tool that opted in via `include_return_schema` gets the schema injected into its description instead, exactly as on a standard [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### supported\_native\_tools

The [native tools](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.AbstractNativeTool) the model runs server-side, e.g. [`WebSearchTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.WebSearchTool).

`Agent.realtime` validates the session's native tools against this set before connecting, raising a [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) that names any the model doesn't support -- mirroring the classic [`Model.supported_native_tools`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model.supported_native_tools) check.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

##### emits\_input\_speech\_events

Whether the provider reports when the user starts and stops speaking, as [`RealtimeInputSpeechStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeInputSpeechStartEvent) and [`RealtimeInputSpeechEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeInputSpeechEndEvent).

`emits_` rather than `supports_` because this describes events that appear in the stream, not an operation the session can invoke. The OpenAI-protocol providers (OpenAI, Azure OpenAI, xAI) emit them; Gemini Live does not -- a UI that shows a "listening" indicator should read this flag rather than wait for events that will never arrive.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### audio\_input\_sample\_rate

The sample rate, in Hz, expected for raw PCM audio input.

Read it via [`RealtimeSession.audio_input_sample_rate`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.audio_input_sample_rate) (or [`RealtimeModel.audio_input_sample_rate`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.audio_input_sample_rate) before a session exists), which fall back to the default when a profile omits it.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### audio\_output\_sample\_rate

The sample rate, in Hz, produced in raw PCM audio output deltas.

Read it via [`RealtimeSession.audio_output_sample_rate`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.audio_output_sample_rate) (or [`RealtimeModel.audio_output_sample_rate`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.audio_output_sample_rate) before a session exists), which fall back to the default when a profile omits it.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### context\_window

The maximum number of tokens the model can hold in a session, input and output combined. Default: `None` (unknown).

When no profile layer sets this, [`RealtimeModel.profile`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.profile) fills it in from [genai-prices](https://github.com/pydantic/genai-prices) data if the model is known there. Set it explicitly for models it doesn't know, e.g. `profile={'context_window': 128_000}`. Read it via [`RealtimeModel.context_window`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.context_window).

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### TurnDetection

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Cross-provider automatic voice-activity detection (VAD) knobs.

Set as [`RealtimeModelSettings.turn_detection`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings) to turn automatic detection on with these settings. (Pass `True` for the provider defaults, or `False` to disable it entirely for push-to-talk.) Each field maps to the closest knob on each provider; for finer, provider-specific control use the provider-prefixed escape hatch (`openai_turn_detection`, `xai_turn_detection`, `google_vad`), which fully overrides this when set.

#### Attributes

##### sensitivity

How readily the provider detects turn boundaries (speech start/end). Higher is snappier but more prone to false triggers. Defaults to the provider default. Maps per provider: **OpenAI / Azure / xAI** → server-VAD `threshold` (`low`≈0.7, `medium`≈0.5, `high`≈0.3); **Gemini** → both start and end sensitivity (`low`→`low`, `high`→`high`, `medium` leaves the provider default).

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['low', 'medium', 'high'\]

##### prefix\_padding\_ms

Audio retained before detected speech onset, in milliseconds. Honored by OpenAI, xAI, and Gemini. Defaults to the provider default.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### silence\_duration\_ms

Silence required to mark the end of speech, in milliseconds. Honored by OpenAI, xAI, and Gemini. Defaults to the provider default.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

### RealtimeError

**Bases:** [`ModelAPIError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelAPIError)

A realtime connection or protocol failure: the session could not be opened, or is over.

Raised when the handshake fails, the provider closes the session, a send fails, or [reconnecting](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.ReconnectPolicy) gives up. A rejected WebSocket upgrade is the exception: it carries an HTTP status, so it raises [`ModelHTTPError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelHTTPError) like a regular request.

A subclass of [`ModelAPIError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelAPIError), since losing the connection to a realtime provider is the same kind of failure as a request-response call that couldn't reach the API. Catch it specifically to separate the session's own failures from those of any text agent the session [delegates to](https://pydantic.dev/docs/ai/realtime/tools/#delegating-work-during-a-call).

### RealtimeClientSecret

An ephemeral client secret (short-lived token) that a browser can use to talk to a provider directly.

Minted server-side by [`create_client_secret`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.create_client_secret) so a long-lived API key never reaches the browser. The token is bound to a session configuration (instructions, tools, voice, VAD) and expires quickly (OpenAI: about a minute).

#### Attributes

##### value

The ephemeral secret to hand to the browser client.

Kept out of the `repr` so logging or inspecting the object doesn't leak the live token into logs.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `field(repr=False)`

##### expires\_at

When the secret expires (timezone-aware UTC).

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

##### provider\_details

Raw provider fields returned alongside the secret (e.g. the resolved `session` object).

Kept out of the `repr` alongside `value`: the resolved `session` carries the instructions and tool definitions, so a logged `repr` would otherwise expose them. Access the field explicitly to read it.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, repr=False)`

### RealtimeModelSettings

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Settings to configure a realtime model session.

Defines the common settings vocabulary used across realtime model providers. Unsupported settings are silently ignored. Providers with additional generation parameters extend it, e.g. [`GoogleRealtimeModelSettings`](https://pydantic.dev/docs/ai/api/realtime/google/#pydantic_ai.realtime.google.GoogleRealtimeModelSettings).

#### Attributes

##### max\_tokens

The maximum number of tokens to generate per response before stopping.

Supported by: OpenAI, Azure OpenAI, Gemini, and xAI.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### parallel\_tool\_calls

Whether to allow parallel tool calls.

Supported by: OpenAI, Azure OpenAI, and xAI.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### tool\_choice

Control which function tools the model can use.

See the [Tool Choice guide](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#tool-choice) for detailed documentation. Every form is resolved exactly as it is for a standard run, including the error a name that matches no tool raises; a session has no output tools, so [`ToolOrOutput`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ToolOrOutput) restricts the function tools while leaving the model free to just speak.

`'none'` and function-tool allow-lists are enforced on every provider by restricting the tools advertised when the session is created. OpenAI, Azure OpenAI, and xAI additionally support declarative `'auto'` and `'required'` choices. Gemini has no declarative tool-choice configuration, so `'required'` is ignored and allow-lists restrict availability without requiring a tool call.

Supported by: OpenAI, Azure OpenAI, Gemini (`'none'` and function-tool allow-lists only), and xAI.

**Type:** [`ToolChoice`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ToolChoice)

##### input\_transcription\_model

Model used to transcribe the user's audio input, so their turns are captured into history.

`'auto'` (the default) uses the provider's recommended realtime transcription model; pass a specific id (e.g. `'gpt-4o-transcribe'`) to pin one, or `None` to disable transcription (see `audio_retention` to retain the raw audio instead).

`None` turns transcription off on every provider. A _pinned_ id applies only to the providers that transcribe with a separate model -- Gemini transcribes natively, with no model to point at, and ignores it (`google_input_transcription` configures Gemini's own transcription).

Supported by: OpenAI, Azure OpenAI, Gemini (`None` only), and xAI.

**Type:** `KnownRealtimeTranscriptionModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### output\_modality

The single modality generated by the model. Defaults to `'audio'`.

Unlike the other settings here, an unsupported value is _not_ silently ignored: a model whose profile reports [`supports_text_output=False`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile.supports_text_output) raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) before connecting, because a session that quietly spoke instead of writing would be worse than one that didn't start.

Supported by: OpenAI and Azure OpenAI. Gemini Live and xAI always generate audio -- read the spoken answer from the transcript on the [`SpeechPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart) instead.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['audio', 'text'\]

##### thinking

Enable or configure reasoning/thinking, mirroring the unified [`thinking`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings.thinking) setting on the request-response models.

`True` enables it at the provider default, and `'minimal'`/`'low'`/`'medium'`/`'high'`/`'xhigh'` selects an effort level. `False` disables thinking on Gemini and xAI (sent as `reasoning.effort: 'none'` there). OpenAI realtime does not accept a disabled effort, so `False` omits `reasoning` and leaves the model's default behavior unchanged. OpenAI and Gemini apply it only to models whose profile reports [`supports_thinking`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile.supports_thinking). Other models silently ignore it. Providers with a richer native config expose it separately (e.g. Gemini's `google_thinking_config`), which takes precedence.

Supported by: OpenAI `gpt-realtime-2*` models, Gemini native-audio models, and xAI's reasoning Grok Voice models (`grok-voice-latest` and the `grok-voice-think-*` family).

**Type:** `ThinkingLevel`

##### turn\_detection

Automatic voice-activity detection (VAD) / turn-taking. Modeled on [`thinking`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings.thinking):

-   Absent (the default) or `True`: automatic turn detection on, at the provider's defaults.
-   `False`: disable it -- push-to-talk, drive turns manually with `commit_audio()` / `create_response()` (only on providers whose [model profile](#model-profile) reports `supports_manual_turn_control`).
-   [`TurnDetection`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.TurnDetection): on, with specific cross-provider knobs.

For finer, provider-specific control use the provider-prefixed setting documented on each provider's settings type (`openai_turn_detection`, `xai_turn_detection`, `google_vad`); when present it fully overrides this field.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | `TurnDetection`

##### handshake\_timeout

Seconds to wait for a realtime protocol handshake event. Defaults to `30.0`.

Supported by: OpenAI, Azure OpenAI, and xAI.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

##### reconnect

[`ReconnectPolicy`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.ReconnectPolicy) to transparently recover from a dropped connection. Without a policy, an unexpectedly closed connection is fatal: the low-level connection reports a non-recoverable session error and `RealtimeSession` raises [`RealtimeError`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeError) from iteration.

What server-side state survives a reconnect depends on the provider (see [`ReconnectPolicy`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.ReconnectPolicy)). Setting a policy enables native session resumption on the providers that offer it: xAI always, and Gemini unless `google_enable_session_resumption=False` is set explicitly -- that combination raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) at connect time, since a re-dial without resumption would lose the conversation.

Supported by: OpenAI, Azure OpenAI, Gemini, and xAI.

**Type:** `ReconnectPolicy`

### RealtimeProviderSession

**Bases:** [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

A handle to a provider-side realtime session that a server sideband connection can attach to.

The transport-neutral contract that `Agent.realtime` accepts as `provider_session`: it needs only the owning provider (to check the attaching model matches) and an opaque session identifier (to address the control-plane connection). Different transports satisfy it with their own handle types -- a WebRTC HTTP relay yields a [`WebRTCSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.WebRTCSession); a provider that negotiates over a WebSocket can supply its own.

#### Attributes

##### provider\_name

The provider that owns the session (e.g. `'openai'` or `'azure'`); must match the model attaching to it.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### session\_id

The provider-assigned identifier used to address the session's control-plane connection.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### WebRTCSession

A [`RealtimeProviderSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeProviderSession) for a WebRTC call.

Produced by [`answer_webrtc_offer`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.answer_webrtc_offer) and passed as `provider_session` to `Agent.realtime` to run the agent loop over the call's control plane while the browser owns the audio.

#### Attributes

##### provider\_name

The provider that owns the call (e.g. `'openai'` or `'azure'`); must match the model attaching to it.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### session\_id

The provider-assigned call identifier (OpenAI/Azure return it as the `call_id` in the `Location` header).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_details

Raw provider details about the call (e.g. the original `Location` header).

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### call\_id

Alias for [`session_id`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.WebRTCSession.session_id) under the OpenAI/Azure wire name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### WebRTCAnswer

The provider's WebRTC SDP answer plus the [`WebRTCSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.WebRTCSession) to attach to.

Return `sdp` to the browser to complete the WebRTC handshake, then pass `session` as `provider_session` to `Agent.realtime` to run the sideband session.

#### Attributes

##### sdp

The provider's SDP answer, to send back to the browser as the remote description.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### session

The call handle the server sideband session attaches to.

**Type:** `WebRTCSession`

### RealtimeModel

**Bases:** [`AbstractModel`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.AbstractModel)

Abstract base class for realtime model providers.

[`RealtimeModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel) and the request-response [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) share [`AbstractModel`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.AbstractModel). A realtime model opens a persistent bidirectional connection for streaming content in and out.

Like [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model), the `settings` attribute and the `model_settings` passed to `connect` are typed as the shared [`RealtimeModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings); each provider narrows to its own `TypedDict` subclass internally with a `cast` (as the request-response models do for `ModelSettings`), rather than the base class being generic over the settings type.

#### Attributes

##### settings

Model settings used as defaults for realtime sessions.

**Type:** `RealtimeModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `settings`

##### model\_name

The model name, e.g. `gpt-realtime`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### base\_url

The provider API base URL, when this model is backed by a provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### profile

The realtime model profile.

Resolution order mirrors [`Model.profile`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model.profile) (later layers override earlier ones):

1.  [`DEFAULT_REALTIME_PROFILE`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.DEFAULT_REALTIME_PROFILE) -- base values for every key.
2.  The provider's `realtime_model_profile(model_name)` result -- provider-specific defaults.
3.  A best-effort `context_window` value from [genai-prices](https://github.com/pydantic/genai-prices), unless the provider or a partial user profile explicitly set the field (including to `None`).
4.  The user's `profile=` argument -- a partial dict merged on top, OR a callable `(resolved) -> profile` for full control.

Then `supported_native_tools` is intersected with what this model class actually implements, so the resolved profile is the single source of truth for what is usable.

**Type:** `RealtimeModelProfile`

##### context\_window

The resolved profile's [`context_window`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile.context_window).

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### audio\_input\_sample\_rate

The sample rate, in Hz, expected for raw PCM audio input.

Also available on the session as [`RealtimeSession.audio_input_sample_rate`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.audio_input_sample_rate); read it here when audio capture must be configured before a session exists.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### audio\_output\_sample\_rate

The sample rate, in Hz, of the raw PCM audio the model produces.

Also available on the session as [`RealtimeSession.audio_output_sample_rate`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.audio_output_sample_rate); read it here when audio playback must be configured before a session exists.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    settings: RealtimeModelSettings | None = None,
    profile: RealtimeModelProfileSpec | None = None,
) -> None
```

Store the model-level `settings` and `profile=` layers, as [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model)'s constructor does.

Also loads genai-prices' data snapshot, which [`profile`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.profile) consults for `context_window`, so that one-time cost stays off the event loop.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### supported\_native\_tools

`@classmethod`

```python
def supported_native_tools(cls) -> frozenset[type[AbstractNativeTool]]
```

Return the native tool types implemented by this realtime model class.

###### Returns

[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`AbstractNativeTool`\]\]

##### connect

`@abstractmethod`

```python
def connect(
    *,
    messages: Sequence[ModelMessage],
    model_settings: RealtimeModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> AbstractAsyncContextManager[RealtimeConnection]
```

Open a connection to the realtime model.

###### Returns

`AbstractAsyncContextManager`\[`RealtimeConnection`\] -- An async context manager yielding a [`RealtimeConnection`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeConnection).

###### Parameters

**`messages`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

Prior conversation and the current request carrying session instructions, projected to the provider's initial conversation items. Replayable text, transcripts, thinking, tool rounds, images, and retained user audio are seeded according to the model profile; content the provider cannot represent raises `UserError`.

**`model_settings`** : `RealtimeModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

Optional provider-specific settings.

**`model_request_parameters`** : `ModelRequestParameters`

Function and native tools available to the session.

##### connect\_webrtc

```python
def connect_webrtc(
    session: RealtimeProviderSession,
    *,
    messages: Sequence[ModelMessage],
    model_settings: RealtimeModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> AbstractAsyncContextManager[RealtimeConnection]
```

Attach a control-plane (sideband) connection to an existing provider-side `session`.

The returned connection runs the agent loop over the session's control channel while the browser exchanges audio with the provider directly, so the sideband doesn't own the audio transport. Only realtime models whose provider supports WebRTC server-side controls (OpenAI and Azure OpenAI) implement this; the default raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) and points callers to the WebSocket transport.

###### Returns

`AbstractAsyncContextManager`\[`RealtimeConnection`\]

##### create\_client\_secret

`@async`

```python
def create_client_secret(
    *,
    instructions: str | None = None,
    tools: Sequence[ToolDefinition] | None = None,
    model_settings: RealtimeModelSettings | None = None,
    expires_after_seconds: int | None = None,
) -> RealtimeClientSecret
```

Mint an ephemeral [`RealtimeClientSecret`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeClientSecret) for a browser client.

Binds the token to the given session configuration so a browser can open a realtime connection directly without ever holding a long-lived API key. Only implemented by providers that support ephemeral tokens (OpenAI and Azure OpenAI); the default raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) and points callers to the WebSocket transport.

###### Returns

`RealtimeClientSecret`

##### answer\_webrtc\_offer

`@async`

```python
def answer_webrtc_offer(
    sdp_offer: str,
    *,
    instructions: str | None = None,
    tools: Sequence[ToolDefinition] | None = None,
    model_settings: RealtimeModelSettings | None = None,
) -> WebRTCAnswer
```

Relay a browser's WebRTC SDP offer to the provider and return the SDP answer plus a [`WebRTCSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.WebRTCSession).

This is the secure signaling path: the server (holding the API key) negotiates the WebRTC call on the browser's behalf, so the browser never sees a token. Return [`WebRTCAnswer.sdp`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.WebRTCAnswer.sdp) to the browser, then pass [`WebRTCAnswer.session`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.WebRTCAnswer.session) as `provider_session` to `Agent.realtime`. Only implemented by providers that support WebRTC (OpenAI and Azure OpenAI); the default raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) and points callers to the WebSocket transport.

###### Returns

`WebRTCAnswer`

### TranscriptUpdate

One incremental transcript update, carrying everything needed to render it.

Yielded by [`RealtimeSession.stream_transcripts(delta=True)`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_transcripts). A realtime session is duplex, so both speakers' transcripts stream at the same time and a caption UI needs to know not just _what_ was said but _which_ turn to put it in -- otherwise two consecutive turns by the same speaker run together.

#### Attributes

##### index

Identifies the turn this update belongs to, stable for the life of the session.

Use it as the key for whatever you render a turn into: every update with the same `index` belongs to the same speech part.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### speaker

Who is speaking.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['user', 'assistant'\]

##### delta

The text this update added, when it added any.

Empty when the provider _revised_ the turn instead of extending it -- speech recognition is revisable, and a correction can't be expressed as an addition. Render `transcript` and this never matters.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### transcript

The full transcript of this turn so far.

Render this, keyed on `index`, and captions are correct whatever the provider does: no accumulating, no special case for a revision, and a dropped update (if a consumer fell behind) self-corrects on the next one.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### ReconnectPolicy

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

How to recover when a realtime connection drops mid-session.

Set as the `reconnect` key of [`RealtimeModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings), either as a model-level default (`settings=`) or per session (`model_settings=`).

On a dropped connection the session is re-dialed and its configuration (instructions, tools, voice, ...) re-applied, emitting a [`RealtimeSessionReconnectEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSessionReconnectEvent) event. What server-side state survives depends on the provider: OpenAI Realtime and Azure OpenAI start a fresh turn (the audio buffer and prior turns are lost), while Gemini Live and xAI restore prior turns through native session resumption, enabled automatically whenever a reconnect policy is set (Gemini honors an explicit `google_enable_session_resumption=False` opt-out by refusing the combination with a [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError)).

#### Attributes

##### max\_attempts

Number of re-dial attempts per drop before giving up and raising [`RealtimeError`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeError). Defaults to `3`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### max\_reconnects

Total successful reconnects allowed for the life of the session.

`max_attempts` bounds the retries for a single drop, and resets once a dial succeeds, so on its own it cannot stop a session that reconnects, drops, and reconnects forever. This bounds the whole session instead.

The default is generous for the case this exists to serve: providers end sessions at a duration cap (OpenAI at 60 minutes) and a long-running session legitimately renews at that boundary, so 50 covers days of continuous conversation. It only bites a server that hangs up as fast as we dial. Defaults to `50`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### base\_delay

Base backoff delay in seconds; doubles each attempt up to `max_delay`. Defaults to `0.5`.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

##### max\_delay

Maximum backoff delay in seconds. Defaults to `30.0`.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

##### jitter

Whether to apply random jitter to each backoff delay to avoid thundering herds. Defaults to `True`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### RealtimeSession

Wraps a [`RealtimeConnection`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeConnection), building message history and auto-executing tools.

The session translates the connection's low-level codec events into the shared message/part event vocabulary from [`pydantic_ai.messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages) and accumulates ordinary [`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage) history as the conversation proceeds, so a session can hand off to [`Agent.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) via [`all_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.all_messages):

-   assistant speech becomes [`PartStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartStartEvent) / [`PartDeltaEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartDeltaEvent) / [`PartEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartEndEvent) events carrying a [`SpeechPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart) (`speaker='assistant'`), finalized into a [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse) at the end of the turn;
-   user speech becomes the same part events with `speaker='user'`, finalized into a [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest);
-   a tool call becomes a [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart) (start/end) plus a [`FunctionToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolCallEvent) when execution starts and a [`FunctionToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolResultEvent) carrying a normalized [`ToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturnPart) or [`RetryPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.RetryPromptPart) when it settles.

Tools always run concurrently with the session. The session keeps streaming events while a tool runs, so the model can keep speaking and user speech keeps being processed, then sends the result back over the connection once it is ready. This mirrors how a person can keep talking while work happens.

Tool outcomes use the same normalized history shapes as a classic agent run: retries become [`RetryPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.RetryPromptPart)s, denials retain their `outcome`, and structured returns preserve `content`, `metadata`, and typed `tool_kind` identity. Realtime tool-output channels are string-only, so the structured part is rendered only when it is sent. OpenAI-protocol connections send additional user content as a follow-up conversation item; Gemini includes a text fallback in its tool response. If the provider cancels an in-flight call, the session records a synthetic interrupted return for valid history but does not send that abandoned result to the provider.

History is accumulated in the order events are reported. Provider item IDs keep interleaved input transcripts associated with their correct user turns; providers without item IDs retain arrival-order association. Tool results are the exception: a tool's [`FunctionToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolResultEvent) streams whenever the tool finishes (possibly after later turns), but in [`all_messages()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.all_messages) its result part is placed directly after the response carrying its call -- request-response APIs require that adjacency, so the history stays valid for a handoff to a standard [`Agent.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run).

Images and video frames streamed with [`send`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send) are stored as ordinary user image turns by default. Set `retain_images_every_n` above `1` to sample high-rate frame streams, and `retain_images_max` (default `100`) to bound how many stay in history -- the oldest retained image is evicted first, so a long-running stream can't grow memory without limit.

When constructing a session directly, use it as an async context manager. The context owns the receive pump, background tool tasks, and instrumentation spans; iteration only reads its event queue. [`AgentRealtime.session`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.session) enters the session before yielding it, so the usual agent API remains a single `async with` block.

#### Attributes

##### usage

Cumulative token usage and tool-call counts for the session, updated as events stream in.

Pass `usage` to `Agent.realtime` to accumulate into a shared [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage); otherwise a fresh one is used.

**Default:** `usage if usage is not None else RunUsage()`

##### closed

Whether the session has been closed.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### result

The final result once the session context has exited, otherwise `None`.

**Type:** [`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### profile

What the connected model supports, as [`RealtimeModel.profile`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModel.profile).

Available here because the session is what a call actually holds: `agent.realtime()` accepts a model _name_ and builds the model itself, leaving nothing else to read the profile from. The audio sample rates have their own dedicated properties -- [`audio_input_sample_rate`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.audio_input_sample_rate) and [`audio_output_sample_rate`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.audio_output_sample_rate) -- so most code never needs to read the profile directly.

**Type:** `RealtimeModelProfile`

##### audio\_input\_sample\_rate

The sample rate, in Hz, of the raw PCM audio this session expects.

Resample the microphone to this rate before [`send_audio`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send_audio): audio sent at the wrong rate is heard as a chipmunk (or slow-motion voice) rather than reported as an error.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### audio\_output\_sample\_rate

The sample rate, in Hz, of the raw PCM audio [`stream_audio()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_audio) yields.

Play output at this rate; it can differ from [`audio_input_sample_rate`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.audio_input_sample_rate) (Gemini Live, for example, listens at 16 kHz and speaks at 24 kHz).

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### played\_audio\_bytes

The playback position of the session's single [`stream_audio()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_audio) consumer, in raw PCM bytes.

A chunk counts as played once the consumer comes back for the next one, so under the documented playback pattern -- write each chunk to the device and wait until it is consumed before pulling the next -- this is the position at the last chunk boundary the device reached, the same value a hand-rolled counter incremented after each write would report. The chunk being written is not counted until it is done, so barge-in attributes at most one chunk less than was really heard, never more. A consumer that instead buffers ahead reads too far; count actual device consumption yourself in that case. Made to be passed to [`interrupt(played_bytes=...)`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.interrupt) on barge-in. Requires exactly one active `stream_audio()` iterator, like that call.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

#### Methods

##### close

`@async`

```python
def close() -> None
```

Close the session and end its live stream views.

This method is idempotent. Active [`stream_audio()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_audio) and [`stream_transcripts()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_transcripts) iterators finish cleanly, with any buffered items discarded. The surrounding model context owns the underlying connection, so it remains open until that context exits.

A tool can call this method through [`ctx.realtime_session`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.realtime_session) to hang up. The calling tool does not resume, and its call is recorded as interrupted.

Raises whatever ended the session -- a provider hangup, an exceeded `usage_limits`, or a failed tool -- if the event stream was never iterated, since there was nowhere else for it to surface.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### stream\_audio

```python
def stream_audio() -> AsyncIterator[bytes]
```

Stream model audio chunks ready for playback.

The iterator contains only live model audio, in playback order. It never repeats retained audio from finalized speech parts. On a WebRTC sideband the browser owns the audio path, so this raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError); consume the browser's remote media track instead.

The subscription starts when this method is called, so audio the model produces between the call and the consumer's first iteration is buffered rather than missed. A view handed to `asyncio.create_task` therefore misses nothing while waiting for its first turn on the event loop. Each iterator has a 32-chunk buffer. If its consumer falls behind (or never starts), the oldest chunk is dropped so audio playback cannot stall tool execution, turn tracking, or the main event stream; an unconsumed view keeps that bounded buffer until it is collected. A device-paced consumer also feeds [`played_audio_bytes`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.played_audio_bytes), and on barge-in [`interrupt(played_bytes=...)`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.interrupt) discards buffered chunks the user will never hear, so a playback loop can iterate one stream for the whole session. Closing the session discards buffered chunks and ends the iterator cleanly. If a tool fails while the event stream has no consumer, this view ends and the error is raised when the session closes.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes)\]

##### stream\_transcripts

```python
def stream_transcripts(*, delta: Literal[False] = False) -> AsyncIterator[SpeechPart]
def stream_transcripts(*, delta: Literal[True]) -> AsyncIterator[TranscriptUpdate]
```

Stream speech transcripts for both the user and assistant.

By default, yields finalized [`SpeechPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart) instances -- one per completed turn, carrying its `speaker` and full `transcript`.

Pass `delta=True` for live captions, which yields [`TranscriptUpdate`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.TranscriptUpdate)s carrying the new text, the turn's full transcript so far, the speaker, and an `index` identifying the turn. Both speakers stream at once, so that `index` is what lets a UI keep two turns apart instead of running them together. Empty updates and finalized parts without a transcript are omitted.

Final transcripts and deltas are separate subscriptions, so one never crowds out the other. The subscription starts when this method is called, so nothing said between the call and the consumer's first iteration is missed. Each iterator buffers up to 512 items; if its consumer falls behind (or never starts), the oldest is dropped, because captioning must not be able to stall tool execution, turn tracking, or the main event stream. Closing the session discards buffered items and ends the iterator cleanly; an unconsumed view otherwise keeps its bounded buffer until it is collected. If a tool fails while the event stream has no consumer, this view ends and the error is raised when the session closes.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[[`SpeechPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart) | `TranscriptUpdate`\]

##### all\_messages

```python
def all_messages() -> list[ModelMessage]
```

A snapshot of the seeded history plus messages recorded during this session.

Returns a copy, so the result doesn't change as the session continues. Feed it into [`Agent.run(message_history=...)`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run) to hand the conversation off to a standard agent run. Images streamed with `send()` are recorded according to `retain_images_every_n`, bounded by `retain_images_max`.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### new\_messages

```python
def new_messages() -> list[ModelMessage]
```

A snapshot of the messages created during this session (excluding the seeded history).

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### send

`@async`

```python
def send(
    content: RealtimeSessionInput | Sequence[RealtimeSessionInput],
    *,
    respond: bool | None = None,
) -> None
```

Feed content into the session.

A `str` is a complete text turn that the model replies to. Do not follow `send('...')` with `create_response()`: that asks for two responses. An image is added as context without soliciting a response, while audio is streamed into the input buffer.

Set `respond=False` to add text or an image as context without soliciting a response. Set `respond=True` to solicit a response to text or an image; this requires manual turn control for images. `respond=True` cannot be used with audio. For a sequence, an explicit `respond` value adds every item except the last as context and applies that value to the last item. With the default `respond=None`, each item keeps its usual behavior.

Accepts the shared message vocabulary: plain text as a `str`, image/audio [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) (including [`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage) and [`BinaryAudio`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryAudio)), or a sequence of these inputs, dispatched in order. Text and retained images are recorded in session history; audio is recorded later through its transcript and/or `audio_retention`. `retain_images_every_n=1` records every image, while larger values keep the first image and then one of every `N`; `retain_images_max` bounds how many stay recorded, evicting the oldest first. Sending an image is gated on the model profile's image-input support and raises `UserError` when it is unsupported.

`send()` accepts session content only. Turn-control verbs (`CommitAudio`, `ClearAudio`, `CreateResponse`, `CancelResponse`, `TruncateOutput`) are driven through the dedicated methods (`commit_audio()`, `clear_audio()`, `create_response()`, `interrupt()`), and [`ToolResult`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.ToolResult) is sent by the session itself as each tool completes (see `_execute_tool`) -- neither is accepted here.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### enqueue

```python
def enqueue(
    *content: EnqueueContent,
    priority: PendingMessagePriority = 'asap',
) -> str | None
```

Enqueue content to be delivered to the model when the session is ready for it.

Use this from code driving the session. For tools, use [`RunContext.enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue). Unlike [`send()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send), which is delivered immediately even while the model is speaking, enqueued content waits for the appropriate turn boundary and triggers a model response when delivered.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- The `enqueue_id` of the queued message, or `None` when there was nothing to enqueue.

###### Parameters

**`*content`** : `EnqueueContent` _Default:_ `()`

One or more [`EnqueueContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.EnqueueContent) items. Realtime delivery supports text parts and [`SystemPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SystemPromptPart)s, which are joined into one user turn. System parts use the `<system>...</system>` convention to indicate that the text is not the person speaking; that marks where it came from, not that it should be handled silently. The model still gets a turn and decides whether to reply, call a tool, or move on. To add context without prompting a turn at all, use [`send(..., respond=False)`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send). The delivered turn is recorded in history as a [`UserPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserPromptPart). Calling with no positional arguments is a no-op.

**`priority`** : `PendingMessagePriority` _Default:_ `'asap'`

When to deliver: `'asap'` (default) -- as soon as no reply is being generated; a reply already in progress is allowed to finish first. `'when_idle'` -- only once the model is idle: no response is in flight and all `'asap'` items have been delivered.

###### Raises

-   `UserError` -- If the session has not been entered or is closed, or the content cannot be delivered over the live input channel.

##### send\_audio

`@async`

```python
def send_audio(data: bytes | AsyncIterable[bytes]) -> None
```

Stream mono PCM16 audio to the model: a single chunk, or an async iterable of chunks.

Given an async iterable -- a microphone stream, a WebSocket receive loop -- each chunk is forwarded as it arrives and the call returns when the iterable is exhausted, so a whole capture loop can be one task: `asyncio.create_task(session.send_audio(microphone))`.

Resample the audio to [`audio_input_sample_rate`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.audio_input_sample_rate) first (24 kHz on the OpenAI-protocol providers, 16 kHz on Gemini): raw bytes carry no rate, so the wrong one is heard as a chipmunk rather than reported.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### commit\_audio

`@async`

```python
def commit_audio() -> None
```

Commit buffered input audio as a user turn (manual turn-taking / push-to-talk).

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### clear\_audio

`@async`

```python
def clear_audio() -> None
```

Discard buffered, uncommitted input audio.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### create\_response

`@async`

```python
def create_response() -> None
```

Ask the model to respond now (manual turn-taking, after `commit_audio`).

If a response is already in flight, the request is held until it completes and is dropped if the user barges in. Returning does not mean the model has started speaking.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### interrupt

`@async`

```python
def interrupt(*, played_ms: int | None = None) -> None
def interrupt(*, played_bytes: int) -> bool
```

Barge-in: cancel the model's in-progress response, optionally truncating its audio first.

This is server-side only -- it stops generation and (when a playback position is given) syncs the provider's transcript to what was actually heard.

With `played_ms`, the caller owns all playback accounting: flushing locally buffered playback is the caller's responsibility, and deciding whether to interrupt at all is too.

With `played_bytes`, the session owns the rest: it attributes the position to the current turn (adjusting for audio the stream dropped or that predates the subscription), discards buffered audio the user will never hear -- chunks already queued, and the cancelled response's stragglers as they arrive -- then truncates and cancels, returning `True`. The cancel is left out while the provider has a speech segment open on a model whose own turn detection stops the response being spoken over, where a client cancel racing it can be applied to the _next_ response; an interruption raised outside a speech segment always cancels. On a model without output truncation the unheard audio is still flushed and the response cancelled; only the provider-side transcript sync is unavailable. When everything emitted was already played there is nothing to cut off: a reply that has not reached its first audio chunk is cancelled untruncated, since it is about to speak over the user, and otherwise nothing is sent and `False` is returned -- reporting an interruption anyway would make the provider discard part of a completed reply. This form needs exactly one [`stream_audio()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_audio) iterator, kept for the session's lifetime; with several (or none) the position is ambiguous and a [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) is raised -- keep your own accounting and pass `played_ms` instead.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`played_ms`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Playback position in milliseconds from the start of the model's current audio output. When given, the model's output audio and its transcript are truncated to this point before the response is cancelled.

**`played_bytes`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Playback position as the total raw PCM bytes actually played from the session's single `stream_audio()` iterator. Mutually exclusive with `played_ms`.

##### \_\_aiter\_\_

`@async`

```python
def __aiter__() -> AsyncIterator[RealtimeEvent]
```

Read translated events from the session queue without owning session resources.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`RealtimeEvent`\]

### RealtimeTurnCompleteEvent

The model exchange is over: generation and tool work are complete.

It is synthesized by the session once no tool calls are still running and no further response is in flight. Input transcription can finish after this event. On WebRTC sidebands, provider playback can also continue until [`RealtimeOutputSpeechEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeOutputSpeechEndEvent).

#### Attributes

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_turn\_complete'\] **Default:** `'realtime_turn_complete'`

### RealtimeInputSpeechStartEvent

The provider detected that the user started speaking.

Useful for barge-in: stop playing any buffered model audio when this arrives, since the model's in-progress turn is being interrupted.

Reported by OpenAI, Azure OpenAI, and xAI. Gemini Live does not report speech onset.

#### Attributes

##### item\_id

Provider id of the user input item this speech segment belongs to, when reported.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_input\_speech\_start'\] **Default:** `'realtime_input_speech_start'`

### RealtimeResponseInterruptedEvent

The provider cut the model's in-progress response short.

Arrives as soon as the provider interrupts, ahead of its response terminal, so it's the point at which to flush buffered model audio.

Reported by Gemini Live, which interrupts server-side when it hears the user speak. The other providers report the user's speech onset as [`RealtimeInputSpeechStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeInputSpeechStartEvent) and leave the cancellation to [`interrupt`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.interrupt), so they never report this.

#### Attributes

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_response\_interrupted'\] **Default:** `'realtime_response_interrupted'`

### RealtimeInputSpeechEndEvent

The provider detected that the user stopped speaking.

Useful as a 'processing' indicator: the user's turn has ended and the model is about to respond.

#### Attributes

##### item\_id

Provider id of the user input item this speech segment belongs to, when reported.

Used to attach retained input audio (`audio_retention='input_audio'`/`'all'`) to the right user turn when turns overlap, since transcripts for different items can finalize out of order.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_input\_speech\_end'\] **Default:** `'realtime_input_speech_end'`

### RealtimeOutputSpeechStartEvent

The provider started playing the model's audio to the listener.

Only reported where the provider, rather than your code, holds the audio on its way to the listener: on a [WebRTC sideband](https://pydantic.dev/docs/ai/realtime/deployment/#browser-webrtc-server-sideband) the media flows browser ↔ provider, so the session never sees audio and this is its only signal that the model has become audible. An ordinary session owns the audio and knows when it starts playing it, so no provider reports this there.

This is about _playback_, not generation: the provider produces audio faster than it plays it, so this can arrive well after the audio itself was generated.

#### Attributes

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_output\_speech\_start'\] **Default:** `'realtime_output_speech_start'`

### RealtimeOutputSpeechEndEvent

The provider stopped playing the model's audio to the listener.

The counterpart to [`RealtimeOutputSpeechStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeOutputSpeechStartEvent), and the honest end of a spoken turn: because the provider generates audio far ahead of playing it, it is still talking long after [`RealtimeTurnCompleteEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeTurnCompleteEvent) reports the response finished. Drive a "speaking" indicator from this pair rather than from turn completion.

#### Attributes

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_output\_speech\_end'\] **Default:** `'realtime_output_speech_end'`

### RealtimeInputTranscriptionErrorEvent

The provider failed to transcribe a user audio input turn, but the session continues.

This is recoverable; `item_id` and `content_index` locate the affected user turn.

#### Attributes

##### message

Human-readable error message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### type

Provider error category, if any.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### code

Provider error code, if any.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### item\_id

Provider conversation-item ID for the affected user turn, when available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### content\_index

Content index within the affected user turn, when available.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_input\_transcription\_error'\] **Default:** `'realtime_input_transcription_error'`

### RealtimeSessionReconnectEvent

The connection dropped and was automatically re-established; inspect `state_restored` for continuity.

Session configuration (instructions, tools, voice, ...) is restored on every reconnect. Conversation state is restored either by the provider's native session resumption (Gemini Live when enabled, xAI Grok Voice) or by the session replaying its local history into the fresh server-side conversation (OpenAI/Azure OpenAI).

#### Attributes

##### state\_restored

Whether the reconnect carried the conversation through without cutting a turn off, regardless of mechanism -- native provider resumption or a local-history replay.

`True` means nothing in flight was lost: the provider either resumed the in-flight response itself (Gemini Live, xAI Grok Voice) or there was no turn in progress when the connection dropped.

`False` means a turn the drop interrupted was settled before continuing -- its partial reply is recorded as an interrupted response and any running tool calls as cancelled returns -- so [`all_messages()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.all_messages) stays a coherent history. Finalized turns from before the drop survive where the provider restores them (the OpenAI/Azure OpenAI local replay) and are lost where it does not; either way, treat the interrupted turn as over and expect the model to stay quiet until the next input.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_session\_reconnect'\] **Default:** `'realtime_session_reconnect'`

### RealtimeSessionErrorEvent

A provider-reported error occurred in the session.

#### Attributes

##### message

Human-readable error message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### type

Provider error category, e.g. `invalid_request_error` or `server_error`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### code

Provider error code, if any.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### recoverable

Whether the session can continue. A protocol `error` is recoverable; a dropped connection is not.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_session\_error'\] **Default:** `'realtime_session_error'`

### infer\_realtime\_model

```python
def infer_realtime_model(
    model: KnownRealtimeModelName | str,
    provider_factory: Callable[[str], Provider[Any]] | None = None,
) -> RealtimeModel
```

Infer a realtime model from a `provider:model` identifier.

The provider is one of `openai`, `azure`, `xai`, `google` (the Gemini Developer API), or `google-cloud` (Vertex AI) -- e.g. `openai:gpt-realtime` -- or a [Pydantic AI Gateway](https://pydantic.dev/docs/ai/overview/gateway/) route (`gateway/openai:gpt-realtime`, `gateway/google:gemini-live-2.5-flash`), which connects through the gateway's built-in provider -- the provider string is passed to the realtime model as its `provider`, so authentication and the base URL come from [`gateway_provider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.gateway.gateway_provider).

#### Returns

`RealtimeModel`

#### Parameters

**`model`** : `KnownRealtimeModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The realtime model identifier, in the format `provider:model`.

**`provider_factory`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], `Provider`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Function that instantiates the provider, called with the `provider` prefix exactly as written (`'azure'`, `'gateway/google'`, ...) -- the counterpart of the same parameter on [`infer_model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.infer_model), for credentials that don't come from the environment. The provider it returns is used as-is. When omitted, each realtime model resolves the prefix itself (e.g. `azure` through [`AzureProvider.for_realtime()`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.azure.AzureProvider.for_realtime)).

### AudioRetention

How much audio a [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) retains in its history.

Values other than `'transcript_only'` are additive: transcripts are always kept, and the named audio is retained alongside them.

-   `'transcript_only'` (default): keep only transcripts; drop all audio bytes.
-   `'input_audio'`: also retain the user's spoken audio.
-   `'output_audio'`: also retain the model's spoken audio.
-   `'all'`: retain both sides' audio.

Retained audio is stored on the [`SpeechPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart)'s `audio` as WAV [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent). Live audio deltas remain raw PCM. Retained input audio is split only at boundaries the provider reports. OpenAI, Azure, and xAI report the end of each detected speech segment, so each user part normally contains audio sent since the preceding speech-end boundary through the current one. This can include inter-turn microphone input. Gemini does not report speech-end boundaries, so its user part contains everything sent since the preceding response completed through the current response completion, including silence sent while the model is responding. Retention records the microphone stream only; it does not mix the model's output audio into the user's part unless that output is present in the microphone input itself.

**Default:** `TypeAliasType('AudioRetention', Literal['transcript_only', 'input_audio', 'output_audio', 'all'])`

### RealtimeSessionInput

The content types a caller feeds into [`RealtimeSession.send`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send).

Session content only, in the shared message vocabulary: a `str` is a complete text turn, and [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) carries an image frame, WAV audio (unwrapped to raw PCM before it is streamed, matching the history-seeding path), or a raw PCM chunk (`media_type='audio/pcm'`). The session normalizes these before forwarding them to the connection. Turn-control verbs (`CommitAudio`, `ClearAudio`, `CreateResponse`, `CancelResponse`, `TruncateOutput`) are connection-level vocabulary driven through the dedicated `RealtimeSession` methods (`commit_audio()`, `clear_audio()`, `create_response()`, `interrupt()`), and [`ToolResult`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.ToolResult) is sent by the session itself when a tool completes -- neither is accepted by `send()`.

**Default:** `TypeAliasType('RealtimeSessionInput', 'str | BinaryContent')`

### RealtimeEvent

Union of events yielded by [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession).

This is a strict subset of [`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent).

Content is streamed as the shared [`PartStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartStartEvent) / [`PartDeltaEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartDeltaEvent) / [`PartEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartEndEvent) events (carrying [`SpeechPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart)s and [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart)s), tool execution as [`FunctionToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolCallEvent) / [`FunctionToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolResultEvent), inline deferred resolution as [`DeferredToolRequestsEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.DeferredToolRequestsEvent) / [`DeferredToolResultsEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.DeferredToolResultsEvent), and the rest as realtime control-plane events.

**Default:** `TypeAliasType('RealtimeEvent', PartStartEvent | PartDeltaEvent | PartEndEvent | FunctionToolCallEvent | FunctionToolResultEvent | DeferredToolRequestsEvent | DeferredToolResultsEvent | RealtimeTurnCompleteEvent | RealtimeInputSpeechStartEvent | RealtimeResponseInterruptedEvent | RealtimeInputSpeechEndEvent | RealtimeOutputSpeechStartEvent | RealtimeOutputSpeechEndEvent | RealtimeInputTranscriptionErrorEvent | RealtimeSessionReconnectEvent | RealtimeSessionErrorEvent)`

### RealtimeModelProfileSpec

What a user may pass as a realtime model's `profile=`, mirroring [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec).

Either a partial [`RealtimeModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile) merged over the resolved profile, or a callable taking the resolved profile and returning the one to use, for full control.

**Default:** `TypeAliasType('RealtimeModelProfileSpec', 'RealtimeModelProfile | Callable[[RealtimeModelProfile], RealtimeModelProfile]')`

### KnownRealtimeTranscriptionModelName

Known values for the OpenAI-protocol models' `input_transcription_model`, pinned by a provider sync test.

`'auto'` is the sentinel that resolves to the provider's recommended transcription model; the rest are concrete model ids. The values span providers, so an id valid for one provider (e.g. `'grok-transcribe'` for xAI) is rejected by another at connect time. The field also accepts any other `str`, so a newer id not listed here still works -- this is just an autocomplete aid, like [`KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName).

**Default:** `TypeAliasType('KnownRealtimeTranscriptionModelName', Literal['auto', 'whisper-1', 'gpt-4o-transcribe', 'gpt-4o-mini-transcribe', 'gpt-realtime-whisper', 'grok-transcribe', 'azure-speech', 'mai-transcribe'])`

### KnownRealtimeModelName

Known realtime model identifiers, surfaced for autocomplete and pinned to provider aliases by a sync test.

**Default:** `TypeAliasType('KnownRealtimeModelName', Literal['openai:gpt-realtime', 'openai:gpt-realtime-2.1', 'openai:gpt-realtime-2.1-mini', 'azure:gpt-realtime', 'xai:grok-voice-latest', 'xai:grok-voice-think-fast-2.0', 'google:gemini-2.5-flash-native-audio-latest', 'google:gemini-3.1-flash-live-preview'])`

---
