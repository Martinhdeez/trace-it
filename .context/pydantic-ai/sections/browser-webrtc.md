# [Browser WebRTC](https://pydantic.dev/docs/ai/examples/realtime/realtime-webrtc/)

# Browser WebRTC

This example is a browser voice agent where the **browser exchanges audio with the provider (OpenAI or Azure OpenAI) directly over WebRTC** (lowest latency), while a [Pydantic AI sideband](https://pydantic.dev/docs/ai/realtime/deployment/#browser-webrtc-server-sideband) on the server runs the agent's tools, builds message history, and keeps the API key off the client.

It's the recommended topology for browser voice agents: the server never sits in the audio path -- it is the control plane.

```text
   browser ──mic/speaker audio (WebRTC media)──▶  OpenAI / Azure OpenAI Realtime
          ◀─────────────────────────────────────
      │  SDP offer (POST /offer)                    ▲ control WebSocket (call_id)
      ▼                                             │
   FastAPI backend ──answer_webrtc_offer()──▶ provider ──session(provider_session=...)──┘
                   (relays the SDP, gets a call_id)     (runs tools, builds history)
```

Demonstrates:

-   [browser WebRTC + server sideband](https://pydantic.dev/docs/ai/realtime/deployment/#browser-webrtc-server-sideband) with the [OpenAI](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.OpenAIRealtimeModel) and [Azure OpenAI](https://pydantic.dev/docs/ai/api/realtime/azure/#pydantic_ai.realtime.azure.AzureRealtimeModel) providers
-   [`AgentRealtime.answer_webrtc_offer`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.answer_webrtc_offer) -- relaying the browser's SDP offer server-side, with the agent's instructions and tools baked in, so the API key never reaches the client
-   [`agent.realtime(model).session(provider_session=...)`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.session) -- running the agent's [tools](https://pydantic.dev/docs/ai/realtime/tools/) over the call's control plane while the browser owns the audio

## Running the Example

You'll need an `OPENAI_API_KEY` with realtime access, in a `.env` file at the repo root:

```dotenv
OPENAI_API_KEY=...
```

To run against **Azure OpenAI** instead, point `WEBRTC_REALTIME_MODEL` at your realtime deployment:

```dotenv
WEBRTC_REALTIME_MODEL=azure:gpt-realtime
AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com
AZURE_OPENAI_API_KEY=...
```

Azure needs an input-transcription deployment

Azure resolves models against your resource's **deployments**: the resource needs a realtime deployment (the `azure:<deployment-name>` segment above) _and_ an input-transcription deployment, because a [sideband session](https://pydantic.dev/docs/ai/realtime/deployment/#browser-webrtc-server-sideband) records the user's turns as transcripts. The default is `gpt-realtime-whisper`; if your transcription deployment is named differently, set `WEBRTC_TRANSCRIPTION_MODEL` to its name.

With [dependencies installed and your key set](https://pydantic.dev/docs/ai/examples/setup/#usage), start the server:

Terminal

```bash
uv run --all-packages uvicorn pydantic_ai_examples.realtime_webrtc.app:app
```

Open [http://localhost:8000](http://localhost:8000/), click **Start call**, allow microphone access, and ask "What time is it in Tokyo?" or "What's your refund policy?" to trigger a server-side tool.

Overrides: `WEBRTC_REALTIME_MODEL` (default `openai:gpt-realtime`), `WEBRTC_REALTIME_VOICE` (default `marin`), `WEBRTC_TRANSCRIPTION_MODEL` (default: the provider's `'auto'` choice).

The microphone needs a secure context

Browsers grant microphone access on `localhost` or over HTTPS. To open the example from another device, expose the local server over HTTPS with a [Cloudflare quick tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/):

Terminal

```bash
cloudflared tunnel --url http://localhost:8000
```

## Example Code

The server -- it relays the SDP offer to OpenAI, attaches the sideband session, and runs the tools:

app.py

```py
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import logfire
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from pydantic_ai import Agent
from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent
from pydantic_ai.realtime import (
    RealtimeTurnCompleteEvent,
    WebRTCSession,
    infer_realtime_model,
)
from pydantic_ai.realtime.openai import OpenAIRealtimeModelSettings

load_dotenv()

logfire.configure(send_to_logfire='if-token-present', service_name='realtime-webrtc')
logfire.instrument_pydantic_ai()

VOICE = os.getenv('WEBRTC_REALTIME_VOICE', 'marin')
INSTRUCTIONS = (
    'You are Roberto, a concise and friendly voice support assistant. '
    'Use `lookup_time` for time questions and `lookup_support_policy` for account or refund questions. '
    'Keep answers short and natural for speech.'
)

INDEX_HTML = (Path(__file__).parent / 'index.html').read_text(encoding='utf-8')

agent = Agent(instructions=INSTRUCTIONS)


@agent.tool_plain
def lookup_time(city: str) -> str:
    """Look up the current local time for a city."""
    timezones = {
        'london': 'Europe/London',
        'new york': 'America/New_York',
        'tokyo': 'Asia/Tokyo',
        'sydney': 'Australia/Sydney',
        'san francisco': 'America/Los_Angeles',
    }
    zone = timezones.get(city.lower())
    if zone is None:
        return f'I only know these example cities: {", ".join(sorted(timezones))}.'
    try:
        now = datetime.now(ZoneInfo(zone))
    except ZoneInfoNotFoundError:  # pragma: no cover - depends on the host tz database
        return f'I could not load timezone data for {city}.'
    return now.strftime(f'It is %A, %I:%M %p in {city}.')


@agent.tool_plain
def lookup_support_policy(topic: str) -> str:
    """Return a short canned support policy answer."""
    policies = {
        'refund': 'Refunds are available within 30 days for billing errors or duplicate charges.',
        'return': 'Physical returns can be started within 14 days of the delivery date.',
        'password': 'Reset your password from the sign-in page using the email verification flow.',
    }
    return policies.get(
        topic.lower(), 'I only have example policies for refund, return, and password.'
    )


model = infer_realtime_model(os.getenv('WEBRTC_REALTIME_MODEL', 'openai:gpt-realtime'))
settings = OpenAIRealtimeModelSettings(openai_voice=VOICE)
if transcription_model := os.getenv('WEBRTC_TRANSCRIPTION_MODEL'):
    settings['input_transcription_model'] = transcription_model
realtime = agent.realtime(model, model_settings=settings)


@dataclass
class Call:
    """One live WebRTC call and its server-side sideband task."""

    answer_sdp: str
    provider_session: WebRTCSession
    task: asyncio.Task[None] | None = None
    # Set once the sideband has either attached or failed to; `attach_error` distinguishes the two so
    # `/offer` doesn't return a successful answer for a session that never came up.
    attached: asyncio.Event = field(default_factory=asyncio.Event)
    attach_error: BaseException | None = None


CALLS: dict[str, Call] = {}


async def run_sideband(call: Call) -> None:
    """Attach the sideband session to the WebRTC call and run the agent's tool loop over its events."""
    call_id = call.provider_session.call_id
    try:
        async with realtime.session(provider_session=call.provider_session) as session:
            call.attached.set()
            async for event in session:
                if isinstance(event, FunctionToolCallEvent):
                    logfire.info(
                        'tool call', tool=event.part.tool_name, args=event.part.args
                    )
                elif isinstance(event, FunctionToolResultEvent):
                    logfire.info(
                        'tool result',
                        tool=event.part.tool_name,
                        content=event.part.content,
                    )
                elif isinstance(event, RealtimeTurnCompleteEvent):
                    logfire.info('turn complete', messages=len(session.all_messages()))
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logfire.exception('sideband session for {call_id} failed', call_id=call_id)
        # Record the failure so `/offer` can surface it instead of returning a dead call.
        call.attach_error = exc
        call.attached.set()
    finally:
        CALLS.pop(call_id, None)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        yield
    finally:
        for call in list(CALLS.values()):
            if call.task is not None:
                call.task.cancel()
                with suppress(asyncio.CancelledError):
                    await call.task


app = FastAPI(lifespan=lifespan)


@app.get('/')
async def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.post('/offer')
async def offer(request: Request) -> JSONResponse:
    """Relay the browser's SDP offer to the provider, start the sideband, and return the SDP answer."""
    try:
        sdp_offer = (await request.body()).decode('utf-8')
    except UnicodeDecodeError:
        # The SDP offer is untrusted signaling input; reject malformed bytes as a client error, not a 500.
        raise HTTPException(
            status_code=400, detail='Expected a UTF-8 SDP offer in the request body.'
        ) from None
    if not sdp_offer.strip():
        raise HTTPException(
            status_code=400, detail='Expected an SDP offer in the request body.'
        )

    answer = await realtime.answer_webrtc_offer(sdp_offer)
    call = Call(answer_sdp=answer.sdp, provider_session=answer.session)
    CALLS[answer.session.call_id] = call

    # Attach the sideband before returning the answer, so the tools are live before the browser (which
    # only starts sending audio once it has the answer) can speak.
    call.task = asyncio.create_task(run_sideband(call))
    try:
        await asyncio.wait_for(call.attached.wait(), timeout=10)
    except asyncio.TimeoutError:
        call.task.cancel()
        CALLS.pop(answer.session.call_id, None)
        raise HTTPException(
            status_code=504, detail='Timed out attaching the server-side session.'
        )
    except asyncio.CancelledError:
        # The client disconnected before receiving the answer, so it never got the `call_id` and can't
        # call `/hangup`. Cancel the sideband and drop the call here to avoid leaking the provider
        # connection and the background agent task.
        call.task.cancel()
        CALLS.pop(answer.session.call_id, None)
        raise
    if call.attach_error is not None:
        raise HTTPException(
            status_code=502, detail='The server-side session failed to attach.'
        )

    return JSONResponse({'sdp': call.answer_sdp, 'call_id': answer.session.call_id})


@app.post('/hangup/{call_id}')
async def hangup(call_id: str) -> JSONResponse:
    call = CALLS.get(call_id)
    if call is not None and call.task is not None:
        call.task.cancel()
        with suppress(asyncio.CancelledError):
            await call.task
    return JSONResponse({'stopped': call is not None})


def main() -> None:  # pragma: no cover - manual entrypoint
    import uvicorn

    uvicorn.run(app, host='127.0.0.1', port=8000)


if __name__ == '__main__':  # pragma: no cover
    main()
```

The browser -- it captures the microphone, negotiates WebRTC through the backend, and plays the audio back. Plain HTML and JavaScript, no build step:

index.html

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Pydantic AI -- Realtime WebRTC voice agent</title>
    <style>
      body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem auto; max-width: 46rem; padding: 0 1rem; color: #111827; }
      h1 { font-size: 1.4rem; }
      button { padding: .55rem 1.1rem; margin-right: .5rem; border-radius: .5rem; border: 1px solid #d1d5db; cursor: pointer; }
      button[disabled] { opacity: .5; cursor: default; }
      #status { margin: 1rem 0; font-weight: 600; }
      #log { white-space: pre-wrap; background: #0f172a; color: #e2e8f0; padding: 1rem; border-radius: .6rem; min-height: 12rem; font-size: .85rem; }
      .hint { color: #6b7280; }
    </style>
  </head>
  <body>
    <h1>Realtime WebRTC voice agent</h1>
    <p>
      The browser exchanges audio with the provider directly over WebRTC. The Python backend negotiates
      the call, attaches a Pydantic AI sideband session, and runs the tools server-side.
    </p>
    <p class="hint">Try: "What time is it in Tokyo?" or "What's your refund policy?"</p>
    <button id="start">Start call</button>
    <button id="stop" disabled>Stop call</button>
    <div id="status">Idle</div>
    <audio id="audio" autoplay></audio>
    <div id="log"></div>

    <script>
      const startBtn = document.getElementById('start');
      const stopBtn = document.getElementById('stop');
      const statusEl = document.getElementById('status');
      const logEl = document.getElementById('log');
      const audioEl = document.getElementById('audio');

      let pc = null;
      let stream = null;
      let callId = null;

      function log(line) {
        logEl.textContent += line + '\n';
        logEl.scrollTop = logEl.scrollHeight;
      }

      function describe(event) {
        if (event.type === 'conversation.item.input_audio_transcription.completed' && event.transcript)
          return 'You: ' + event.transcript;
        if (event.type === 'response.output_audio_transcript.done' && event.transcript)
          return 'Assistant: ' + event.transcript;
        if (event.type === 'response.function_call_arguments.done')
          return 'Model tool call: ' + event.name + ' ' + event.arguments;
        return null;
      }

      async function start() {
        startBtn.disabled = true;
        statusEl.textContent = 'Requesting microphone...';
        logEl.textContent = '';

        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        pc = new RTCPeerConnection();
        pc.ontrack = (e) => { audioEl.srcObject = e.streams[0]; };
        for (const track of stream.getTracks()) pc.addTrack(track, stream);

        // The data channel carries the provider's (filtered) event stream for display only.
        const dc = pc.createDataChannel('oai-events');
        dc.onmessage = (m) => {
          try { const line = describe(JSON.parse(m.data)); if (line) log(line); } catch {}
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        statusEl.textContent = 'Negotiating...';
        const res = await fetch('/offer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/sdp' },
          body: offer.sdp,
        });
        if (!res.ok) throw new Error(await res.text());

        const { sdp, call_id } = await res.json();
        callId = call_id;
        await pc.setRemoteDescription({ type: 'answer', sdp });

        statusEl.textContent = 'Live -- start talking';
        stopBtn.disabled = false;
      }

      async function stop() {
        stopBtn.disabled = true;
        const hangupId = callId;
        callId = null;
        try {
          // Server hangup is best effort: if the backend is unreachable, local cleanup must still run
          // so the WebRTC connection closes and the microphone is released.
          if (hangupId) await fetch('/hangup/' + hangupId, { method: 'POST' });
        } catch (e) {
          // Ignore: the finally block releases local resources regardless.
        } finally {
          if (pc) { pc.close(); pc = null; }
          if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
          audioEl.srcObject = null;
          statusEl.textContent = 'Idle';
          startBtn.disabled = false;
        }
      }

      startBtn.onclick = () => start().catch((e) => { statusEl.textContent = 'Failed: ' + e; stop(); });
      stopBtn.onclick = stop;
      window.addEventListener('beforeunload', () => { if (callId) navigator.sendBeacon('/hangup/' + callId); });
    </script>
  </body>
</html>
```

---
