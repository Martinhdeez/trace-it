# [Connecting a frontend](https://pydantic.dev/docs/ai/realtime/deployment/)

# Connecting a frontend

Keep provider keys, tools, and business logic on the server; connect user devices to your backend, not straight to the provider. How audio travels between the device and the model depends on the client and the provider:

-   **[Browser WebRTC + server sideband](#browser-webrtc-server-sideband)** -- the recommended browser path on OpenAI and Azure OpenAI: the browser exchanges media directly with the provider (lowest latency) while your backend runs the agent over a control-plane sideband.
-   **[Browser → backend WebSocket relay](#browser-backend-websocket-relay)** -- works with every provider, including Gemini Live and xAI: the browser streams audio to your backend, which owns the media bridge.
-   **[SIP / telephony bridge](#siptelephony-bridge)** -- for phone calls, via a telephony provider.

In every setup the session -- with its [tools](https://pydantic.dev/docs/ai/realtime/tools/), [history](https://pydantic.dev/docs/ai/realtime/history/), and [usage limits](https://pydantic.dev/docs/ai/realtime/observability/#usage-and-limits) -- runs on your backend. Wiring a browser straight to the provider with the provider's own SDK instead moves the agent loop into the client and gives up all of that; prefer one of the setups above.

## Browser WebRTC + server sideband

For browser voice agents on OpenAI and Azure OpenAI, the browser carries microphone and speaker audio directly over WebRTC while the backend attaches a control-plane **sideband** to the same call. Media never touches your backend, so latency stays low, while tools, history, dependencies, and provider credentials stay on the server. Gemini Live and xAI do not offer this sideband transport -- use the [WebSocket relay](#browser-backend-websocket-relay) there.

```text
browser ── WebRTC media ── provider
   │                         ▲
   └─ SDP offer → backend ───┘ sideband identified by call_id
```

Relay the browser's offer with [`AgentRealtime.answer_webrtc_offer`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.answer_webrtc_offer), return the SDP answer to the browser, then attach the returned call handle:

```python
import asyncio

from pydantic_ai import Agent

agent = Agent(instructions='You are a concise voice assistant.')
realtime = agent.realtime('openai:gpt-realtime')
sideband_tasks: set[asyncio.Task[None]] = set()


async def handle_offer(sdp_offer: str) -> str:
    answer = await realtime.answer_webrtc_offer(sdp_offer)

    async def run_sideband() -> None:
        async with realtime.session(provider_session=answer.session) as session:
            async for event in session:
                print(event)

    task = asyncio.create_task(run_sideband())
    sideband_tasks.add(task)  # (1)
    task.add_done_callback(sideband_tasks.discard)
    return answer.sdp
```

asyncio keeps only a weak reference to a task, so hold one yourself until the call ends; the done callback also surfaces an error the sideband session raised instead of leaving it as a "never retrieved" warning.

The secure offer-relay flow never gives the browser a token. As an alternative, [`AgentRealtime.create_client_secret`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.create_client_secret) mints a short-lived credential for client-led negotiation. Either way the browser is a peer on the provider session and can send provider-native control events, so authorize every server-side tool against trusted [`deps`](https://pydantic.dev/docs/ai/core-concepts/dependencies/), not session instructions supplied to the model.

The browser can read seeded history

Seeding a sideband session with [`message_history`](https://pydantic.dev/docs/ai/realtime/history/) sends those prior turns into the **shared** provider conversation that the browser is a peer on, so a call participant can read them -- including confidential tool results -- over the data channel (Azure's `webrtcfilter=on` still forwards conversation-item events). Only seed a sideband with history that is safe for the browser to see; keep confidential context in [`deps`](https://pydantic.dev/docs/ai/core-concepts/dependencies/) and tool logic instead.

A sideband does not own the audio transport: its `send_audio()`, `commit_audio()`, `clear_audio()`, and `stream_audio()` methods raise, and `audio_retention` must remain `'transcript_only'`. Enable [input transcription](https://pydantic.dev/docs/ai/realtime/audio/#input-transcription) when user speech must appear in history, and use [`RealtimeOutputSpeechStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeOutputSpeechStartEvent) / [`RealtimeOutputSpeechEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeOutputSpeechEndEvent) for speaking indicators -- [`interrupt()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.interrupt) clears the provider's outbound WebRTC audio buffer so [barge-in](https://pydantic.dev/docs/ai/realtime/turns/#barge-in) stops playback. A dropped sideband follows the same [reconnect](https://pydantic.dev/docs/ai/realtime/lifecycle/#reconnecting) rules, with one wrinkle covered there: a clean close is treated as the browser hanging up.

The [realtime WebRTC example](https://pydantic.dev/docs/ai/examples/realtime/realtime-webrtc/) demonstrates the full FastAPI and browser flow. Provider-specific setup (Azure's Microsoft Entra ID and `webrtcfilter`) lives on the [Azure](https://pydantic.dev/docs/ai/realtime/azure/#browser-webrtc-and-microsoft-entra-id) page.

## Browser → backend WebSocket relay

When the browser can't use WebRTC -- or the provider is Gemini Live or xAI -- build a WebSocket endpoint on your backend that accepts the browser's microphone audio and pumps it into [`send_audio()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send_audio), while relaying [`stream_audio()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.stream_audio) output back for playback. Here the backend owns the media bridge. The [realtime camera example](https://pydantic.dev/docs/ai/examples/realtime/realtime-camera/) demonstrates this setup end to end; a minimal FastAPI relay -- the browser sends raw PCM16 binary frames and plays the frames it receives -- is:

```python
import asyncio

from fastapi import FastAPI, WebSocket

from pydantic_ai import Agent

agent = Agent(instructions='You are a helpful voice assistant.')
app = FastAPI()


@app.websocket('/voice')
async def voice_socket(websocket: WebSocket):
    await websocket.accept()

    async def microphone():
        while True:
            yield await websocket.receive_bytes()

    async with agent.realtime('openai:gpt-realtime').session() as session:

        async def playback():
            async for chunk in session.stream_audio():
                await websocket.send_bytes(chunk)

        playback_task = asyncio.create_task(playback())
        try:
            await session.send_audio(microphone())
        finally:
            playback_task.cancel()
```

[`send_audio()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.send_audio) consumes the async iterator for the whole call, so when the browser disconnects, `receive_bytes()` raises, the `finally` stops playback, and leaving the `async with` block hangs up the provider session. Driving the input from a bare `asyncio.create_task` instead would swallow that error and leave the billed session open with nobody listening.

## SIP/telephony bridge

Terminate the phone call with a telephony provider such as Twilio, then build the service that connects its media stream (e.g. Twilio Media Streams over WebSocket) to the backend session, transcoding between the line's codec and PCM16.

---
