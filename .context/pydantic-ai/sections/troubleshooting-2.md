# [Troubleshooting](https://pydantic.dev/docs/ai/realtime/troubleshooting/)

# Troubleshooting

Below are suggestions on how to fix some common problems with realtime sessions, each linking to the page that covers the underlying behavior. For issues not listed here or addressed in the documentation, see the general [troubleshooting page](https://pydantic.dev/docs/ai/overview/troubleshooting/), ask in the [Pydantic Slack](https://pydantic.dev/docs/ai/overview/help/), or create an issue on [GitHub](https://github.com/pydantic/pydantic-ai/issues).

## No audio, or no useful speech

Send mono PCM16 at `session.audio_input_sample_rate` and play it at `session.audio_output_sample_rate`. Do not assume the rates match. See the [audio wire contract](https://pydantic.dev/docs/ai/realtime/audio/#audio-wire-contract).

## The model never responds

In push-to-talk mode, call `commit_audio()` and then `create_response()` after sending audio. See [push-to-talk](https://pydantic.dev/docs/ai/realtime/turns/#push-to-talk).

## The model says the same thing twice

`send('...')` already asks the model to reply. Do not follow it with `create_response()`, which asks for a second response. See [text turns](https://pydantic.dev/docs/ai/realtime/turns/#text-turns).

## The model interrupts itself

The microphone is probably hearing speaker output. Add echo cancellation in the device/WebRTC layer and stop local playback on real [barge-in](https://pydantic.dev/docs/ai/realtime/turns/#barge-in).

## The greeting never plays, or the model replies twice when the visitor speaks

Speaker echo or microphone transients probably cancelled the greeting while the audio path opened. Keep the microphone closed until the greeting has played; see [Speaking first](https://pydantic.dev/docs/ai/realtime/turns/#speaking-first). To confirm the cause, iterate the event stream and look for a [`RealtimeResponseInterruptedEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeResponseInterruptedEvent) on the first response and any [`RealtimeSessionErrorEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSessionErrorEvent), or inspect the [Logfire trace](https://pydantic.dev/docs/ai/realtime/observability/#logfire-instrumentation).

## Tools seem to stall

The local tool runs concurrently, but the provider may pause speech while awaiting the result. Show tool lifecycle events and review [concurrent tool execution](https://pydantic.dev/docs/ai/realtime/tools/#concurrent-tool-execution).

## A reconnect lost context

Inspect `RealtimeSessionReconnectEvent.state_restored`. If false, begin a fresh conversation; if true but a current utterance vanished, that in-flight media was outside the restored completed-turn history. See [state restoration](https://pydantic.dev/docs/ai/realtime/lifecycle/#state-restoration).

## Gemini reaches its session limit

Set the `reconnect` setting to a [`ReconnectPolicy`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.ReconnectPolicy); Gemini session resumption is enabled automatically alongside it. Recovery uses the latest in-memory server handle after the drop. See [Gemini session resumption](https://pydantic.dev/docs/ai/realtime/gemini/#session-resumption) and [provider session limits](https://pydantic.dev/docs/ai/realtime/lifecycle/#provider-session-limits).

---
