# [Events](https://pydantic.dev/docs/ai/realtime/events/)

# Events

Iterating a [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) yields the session's event stream: content parts, tool activity, turn boundaries, reconnects, and recoverable errors. The high-level [`stream_audio()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_audio) and [`stream_transcripts()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_transcripts) views described in [Audio, images, and transcripts](https://pydantic.dev/docs/ai/realtime/audio/) are derived from this same stream, so most applications iterate the session for control flow and leave media to the views.

## Event reference

Event

Meaning

[`PartStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartStartEvent)

A speech, text, or tool part started.

[`PartDeltaEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartDeltaEvent)

Incremental speech audio/transcript or text content.

[`PartEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartEndEvent)

A finalized part; retained speech audio appears here, not at part start.

[`FunctionToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolCallEvent)

A local function tool began executing.

[`FunctionToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolResultEvent)

A local function tool completed or returned a retry prompt.

[`DeferredToolRequestsEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.DeferredToolRequestsEvent)

An inline capability handler resolved deferred requests.

[`DeferredToolResultsEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.DeferredToolResultsEvent)

Inline deferred results are ready for normal tool processing.

[`RealtimeInputSpeechStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeInputSpeechStartEvent)

The provider detected that the user started speaking, when the profile declares [`emits_input_speech_events`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile.emits_input_speech_events).

[`RealtimeInputSpeechEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeInputSpeechEndEvent)

The provider detected the end of user speech, when the profile declares [`emits_input_speech_events`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile.emits_input_speech_events).

[`RealtimeResponseInterruptedEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeResponseInterruptedEvent)

The provider reported an interrupted model response.

[`RealtimeInputTranscriptionErrorEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeInputTranscriptionErrorEvent)

One user turn could not be transcribed; the session remains usable.

[`RealtimeOutputSpeechStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeOutputSpeechStartEvent) / [`RealtimeOutputSpeechEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeOutputSpeechEndEvent)

The model became, or stopped being, audible. These are emitted on a [WebRTC sideband](https://pydantic.dev/docs/ai/realtime/deployment/#browser-webrtc-server-sideband), where the provider owns audio playback.

[`RealtimeTurnCompleteEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeTurnCompleteEvent)

The model finished replying and no tool remains active.

[`RealtimeSessionReconnectEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSessionReconnectEvent)

The connection was automatically re-established.

[`RealtimeSessionErrorEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSessionErrorEvent)

A recoverable provider error occurred; the session remains usable.

## Shared and realtime-only events

The first seven rows are [`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent) members from [`pydantic_ai.messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages) -- the same events a [standard streamed run](https://pydantic.dev/docs/ai/core-concepts/agent/#streaming-all-events) yields, so event-handling code written for a text agent (rendering parts, logging tool calls) works on a session unchanged. The `Realtime*` rows are [`RealtimeEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeEvent) members that only a session emits: speech detection, interruption, turn completion, reconnection, and recoverable errors have no equivalent in a request-response run.

A capability's [event stream hooks](https://pydantic.dev/docs/ai/core-concepts/hooks/#event-stream-hooks) see both kinds flow through the same stream; see [Capabilities and hooks](https://pydantic.dev/docs/ai/realtime/capabilities/#the-event-stream).

## The turn boundary

Use [`RealtimeTurnCompleteEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeTurnCompleteEvent) as the exchange boundary. A model can speak, call a tool, and speak again, so receiving speech -- or a tool result -- does not imply that the turn is done.

## Reading raw audio events

The audio stream _is_ these events under the hood: [`stream_audio()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_audio) is a bounded view over the speech part deltas, and most applications should use it. As an advanced alternative, play [`SpeechPartDelta.audio_chunk`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPartDelta.audio_chunk) from raw [`PartDeltaEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartDeltaEvent)s. Model audio arrives in full whether or not history retention is enabled. When output audio is retained, the final [`SpeechPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart) contains the whole turn again as a WAV snapshot for [history](https://pydantic.dev/docs/ai/realtime/history/#retaining-audio); do not play both or the turn will play twice.

---
