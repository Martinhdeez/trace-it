# [Camera Agent](https://pydantic.dev/docs/ai/examples/realtime/realtime-camera/)

# Camera Agent

This camera agent streams microphone audio and one camera frame per second into a [realtime session](https://pydantic.dev/docs/ai/realtime/overview/), then plays and captions the spoken response. Point it at objects to ask about them, enable _Watch_ for proactive narration, or show it a sketch to redraw.

The example demonstrates:

-   provider-agnostic [realtime sessions](https://pydantic.dev/docs/ai/realtime/overview/) with profile-derived PCM sample rates
-   [image input](https://pydantic.dev/docs/ai/realtime/audio/#images) using [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent)
-   live vision with `turn_coverage='all_input'` and a _Watch_ toggle
-   a regular function tool that delegates diagram rendering to a second [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent)
-   [web search](https://pydantic.dev/docs/ai/realtime/tools/#native-tools) with [`WebSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebSearch) and clickable citations
-   a model picker and provider-aware voice, modality, VAD, and Gemini settings

## Running the Example

Add credentials for a picker model to the repository-root `.env`, for example:

```dotenv
GOOGLE_API_KEY=your-google-api-key
```

The sketch-redraw tool delegates to a separate drawing agent -- `google:gemini-3.5-flash` by default, which reuses the same `GOOGLE_API_KEY`. Set `CAMERA_DRAW_MODEL` to any other `provider:model` your credentials cover, or `CAMERA_DRAW=false` to disable drawing; the rest of the assistant works either way.

With [dependencies installed and environment variables set](https://pydantic.dev/docs/ai/examples/setup/#usage), start the local server:

-   [pip](#tab-panel-50)
-   [uv](#tab-panel-51)

Terminal

```bash
python -m pydantic_ai_examples.realtime_camera.app
```

Terminal

```bash
uv run -m pydantic_ai_examples.realtime_camera.app
```

Open [http://localhost:8000](http://localhost:8000/), select **Start**, and allow camera and microphone access.

The model defaults to `google:gemini-3.1-flash-live-preview`; set `CAMERA_REALTIME_MODEL` to change it, or use the picker to switch to any Google, OpenAI, or Azure OpenAI `provider:model` per session (xAI realtime doesn't support camera image input). The selected model's realtime profile supplies the browser's PCM input and output sample rates: Gemini input uses 16 kHz, while OpenAI and Azure input uses 24 kHz.

Keep the example local

The WebSocket uses provider credentials from the server and has no user authentication. The example checks that the browser's origin matches the host it's served from, but that is a development safeguard rather than production access control.

Do not expose the server through a Cloudflare quick tunnel, ngrok, or a public reverse proxy. For another device, deploy behind authentication and TLS on a network you control, with user-level quotas and rate limits appropriate to your environment.

## Watch mode

Camera frames add visual context but do not start a model turn. _Watch_ periodically sends a short text turn while the model is idle, prompting it to report a visual change without interrupting speech already in progress. Set `CAMERA_WATCH_PROMPT` to customize that instruction.

Gemini native-audio models can decide that nothing needs saying:

Terminal

```bash
export CAMERA_PROACTIVE=true
export CAMERA_AFFECTIVE=true
```

`CAMERA_TURN_COVERAGE` defaults to `all_input`, which works with both the Gemini Developer API and Vertex AI. Watch mode consumes tokens while enabled.

## Search and citations

With `CAMERA_WEB_SEARCH=true` (the default), the example adds [`WebSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.WebSearch) when the selected model profile supports native search. Native-tool return events are converted into citation chips; the browser accepts only HTTP(S) source URLs.

## Redraw a diagram

With `CAMERA_DRAW=true` (the default), the realtime agent can call `redraw_diagram`. It gives a detailed textual description of the visible sketch to a separate [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent), which produces self-contained HTML. The browser displays that HTML in an opaque-origin iframe that blocks scripts and network access, and retains the PNG export action.

The default is a fast small model because the user is waiting on a live call: the redraw's latency is dominated by HTML output tokens, so a larger model mostly adds thinking time, not quality. Configure the drawing model independently:

Terminal

```bash
export CAMERA_DRAW_MODEL=anthropic:claude-haiku-4-5
```

Drawing and web search remain enabled together when the selected realtime model supports both. Tools [run concurrently](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.session), so drawing does not replace the voice conversation.

## Vertex AI

Use Application Default Credentials when your organization does not allow Gemini API keys:

Terminal

```bash
gcloud auth application-default login
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT=your-project
export GOOGLE_CLOUD_LOCATION=us-central1
```

## How the bridge works

The browser and provider are connected by two small concurrent pumps in `_run_session`:

```text
browser ── PCM16 + JPEG/text ──▶ FastAPI /ws ──▶ RealtimeSession
browser ◀── PCM16 + JSON events ──────────────── RealtimeSession
```

Before microphone capture begins, the server sends `session_config` over the JSON channel with the profile-derived audio rates. The inbound pump then forwards PCM, image, text, and Watch messages. The event pump returns audio, transcripts, barge-in notifications, grounding citations, drawing updates, and turn completion. Either side ending cancels the other pump and closes the session cleanly.

## Example Code

The server contains the realtime bridge and the subordinate Watch, grounding, and drawing helpers:

app.py

```py
from __future__ import annotations

import base64
import json
import os
import re
from collections.abc import Awaitable, Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

import anyio
import logfire
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from pydantic_ai import (
    Agent,
    BinaryContent,
    PartDeltaEvent,
    PartEndEvent,
    RunContext,
    SpeechPartDelta,
)
from pydantic_ai.capabilities import WebSearch
from pydantic_ai.exceptions import ModelAPIError, UserError
from pydantic_ai.messages import NativeToolReturnPart, TextPartDelta
from pydantic_ai.native_tools import WebSearchTool
from pydantic_ai.realtime import (
    RealtimeError,
    RealtimeEvent,
    RealtimeInputSpeechStartEvent,
    RealtimeModel,
    RealtimeModelSettings,
    RealtimeResponseInterruptedEvent,
    RealtimeSession,
    RealtimeTurnCompleteEvent,
    ReconnectPolicy,
    TurnDetection,
    infer_realtime_model,
)
from pydantic_ai.realtime.google import (
    AutomaticVAD,
    GoogleRealtimeModel,
    GoogleRealtimeModelSettings,
)
from pydantic_ai.realtime.openai import (
    OpenAIRealtimeModel,
    OpenAIRealtimeModelSettings,
)

load_dotenv()

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured.
# Configure after `load_dotenv()` so a `LOGFIRE_TOKEN` in `.env` is picked up.
logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_pydantic_ai()


def _truthy(value: str | None) -> bool:
    """Parse an env/query flag: `'1'`, `'true'`, `'yes'`, or `'on'` (any case) mean enabled."""
    return (value or '').lower() in ('1', 'true', 'yes', 'on')


MODEL = os.environ.get('CAMERA_REALTIME_MODEL', 'google:gemini-3.1-flash-live-preview')
# Empty by default so each provider picks its own default voice -- no need to change it when switching
# between Gemini and OpenAI, whose voice names differ (Gemini rejects `alloy`, OpenAI rejects `Puck`).
VOICE = os.environ.get('CAMERA_REALTIME_VOICE', '')
# Use Vertex AI (Application Default Credentials) instead of a Gemini API key -- handy where org
# policy disallows API keys. Needs `gcloud auth application-default login` + `GOOGLE_CLOUD_PROJECT`.
USE_VERTEX = _truthy(os.environ.get('GOOGLE_GENAI_USE_VERTEXAI'))
# `all_input` keeps every camera frame in the model's context -- the live scene the assistant reasons
# about -- and works on both the Gemini Developer API and Vertex AI (the newer `all_video` doesn't yet).
TURN_COVERAGE = os.environ.get('CAMERA_TURN_COVERAGE', 'all_input')
# Gemini native-audio-only knobs, off by default so the default model still connects: proactive audio
# lets the model stay silent when a Watch nudge finds nothing new; affective dialog adapts delivery
# to emotion in the conversation.
PROACTIVE = _truthy(os.environ.get('CAMERA_PROACTIVE'))
AFFECTIVE = _truthy(os.environ.get('CAMERA_AFFECTIVE'))
# Sketch-to-diagram: the `redraw_diagram` tool passes the realtime model's text description of a
# sketch to a separate drawing agent that renders it as clean HTML. The default drawing model reuses
# the `GOOGLE_API_KEY` the default realtime model already needs, and is a fast small model because
# the user is waiting on a live call: output tokens dominate the redraw's latency, and a larger
# model mostly adds thinking time. `CAMERA_DRAW_MODEL` takes any `provider:model` string.
DRAW = _truthy(os.environ.get('CAMERA_DRAW', 'true'))
DRAW_MODEL = os.environ.get('CAMERA_DRAW_MODEL', 'google:gemini-3.5-flash')
# Web search (the `WebSearch` capability) -- on by default, but only enabled for a session when the
# selected model supports web search natively (see `_web_search_supported`), so switching models
# drops the capability instead of failing the session.
WEB_SEARCH = _truthy(os.environ.get('CAMERA_WEB_SEARCH', 'true'))
WATCH_PROMPT = os.environ.get(
    'CAMERA_WATCH_PROMPT',
    "Look at the current camera view. In a few words, say what's changed since you last spoke; "
    'if nothing notable changed, stay silent.',
)
_INDEX_PATH = Path(__file__).parent / 'index.html'


def _same_origin(socket: WebSocket) -> bool:
    """Accept browser WebSockets only from the origin serving this development example.

    Any web page can open a WebSocket to this server (which spends your API credits), so the
    browser-reported `Origin` must match the host the request was addressed to. Three ways in: a
    loopback origin matching `Host` (direct local use); an origin matching `X-Forwarded-Host` (a
    reverse proxy such as Codespaces or a dev tunnel -- trustworthy because the browser WebSocket API
    cannot send custom headers, so its presence proves a real proxy hop); or an origin listed in
    `CAMERA_ALLOWED_ORIGINS` (comma-separated `scheme://host[:port]`, for proxies that forward
    neither).
    """
    origin = socket.headers.get('origin')
    if not origin:
        return False
    allowed = os.environ.get('CAMERA_ALLOWED_ORIGINS', '')
    if origin in {value.strip() for value in allowed.split(',') if value.strip()}:
        return True
    parsed = urlsplit(origin)
    if parsed.scheme not in ('http', 'https'):
        return False
    if parsed.netloc == socket.headers.get('x-forwarded-host'):
        return True
    return parsed.hostname in (
        'localhost',
        '127.0.0.1',
        '::1',
    ) and parsed.netloc == socket.headers.get('host')


def _instructions(*, web_search: bool) -> str:
    """The assistant's instructions, built per connection.

    The web-search guidance is included only when web search is actually enabled for the selected
    model (see `_web_search_supported`), so the model isn't told about a tool it doesn't have.
    """
    return (
        'You are a friendly, concise voice assistant. The user is talking to you and may show you things '
        'through their camera -- when relevant, describe and reason about what you can see. Keep replies '
        'short and natural, like a conversation.'
        + (
            ' Search the web when a question needs current or external facts.'
            if web_search
            else ''
        )
        + (
            ' You can redraw a hand-drawn sketch the user shows you -- a diagram, system design, flow '
            'chart, or wireframe -- into a clean version with the `redraw_diagram` tool. Do NOT call it '
            'the moment you see a drawing. First make sure you understand what they actually want: if '
            "they haven't said, ask one short question -- keep it faithful but tidier, turn it into a "
            'flowchart, restructure it, add or label something? Once their intent is clear, FIRST tell '
            "them out loud that you're about to redraw it and that it takes a few moments (around ten"
            "seconds) -- don't leave them waiting in silence -- THEN call the tool. The drawing tool "
            'cannot see the camera, so pass it a thorough text description as `instructions`: every box '
            'and its label, every arrow and what it connects, groupings, and the overall layout, plus '
            'what the user asked you to change. Be specific -- it can only draw what you describe. '
            'After calling the tool, stop talking until its result arrives -- never say the redraw is '
            'done in the same breath as calling it, because the drawing takes several seconds. Once '
            'the result arrives, briefly describe what you drew.'
            if DRAW
            else ''
        )
    )


@dataclass
class CameraDeps:
    """Per-connection hooks the `redraw_diagram` tool needs.

    `emit` pushes a JSON message back to this connection's browser -- the tool uses it to show and
    then clear the drawing overlay while the diagram is being generated.
    """

    emit: Callable[[dict[str, object]], Awaitable[None]]


app = FastAPI()
logfire.instrument_fastapi(app)

DRAW_INSTRUCTIONS = (
    'You turn a text description of a hand-drawn sketch -- a diagram, system design, flow chart, or '
    'wireframe -- into a clean, modern, self-contained HTML page that recreates and tidies up the '
    'drawing. Faithfully render every box, label, arrow, and connection the description mentions, '
    'and lay everything out neatly with clear typography, generous spacing, and restrained color on '
    'a light background. '
    'Design it to fit comfortably on a phone screen in portrait: prefer a vertical flow over very '
    'wide horizontal layouts, let content wrap, and use relative widths so nothing is cut off. '
    # The user is waiting on a live call while this generates, so latency is part of the spec:
    # output tokens dominate the wall-clock time, and a compact page halves it.
    'Keep the page LEAN so it generates fast: one short `<style>` block with a few shared classes, '
    'simple semantic markup (plain divs, or one inline SVG for connector-heavy layouts), and no '
    'decorative gradients, shadows, animations, or per-element styling. Do not restate the '
    'description in comments or prose. '
    'Respond with a SINGLE complete HTML document and nothing else: inline all CSS in a `<style>` '
    'tag, use no external resources (no images, web fonts, or scripts), and no markdown fences.'
)
DRAW_PROMPT = 'Recreate this diagram as a self-contained HTML page:\n\n{instructions}'
_FENCE_RE = re.compile(r'^```[a-zA-Z]*\n(.*)\n```$', re.DOTALL)


@lru_cache(maxsize=1)
def _draw_agent() -> Agent[None, str]:
    """Build the drawing agent that redraws sketches, lazily so it only needs credentials when used.

    A full HTML page for a busy diagram can outgrow a provider's default `max_tokens` (Anthropic's
    default is low enough to cut off mid-page), so the limit is raised explicitly.
    """
    return Agent(
        DRAW_MODEL,
        name='diagram_drawer',
        instructions=DRAW_INSTRUCTIONS,
        model_settings={'max_tokens': 16_384},
    )


def _extract_html(text: str) -> str:
    """Strip a Markdown HTML fence if the model wrapped its output in one."""
    text = text.strip()
    match = _FENCE_RE.match(text)
    return (match.group(1) if match else text).strip()


async def redraw_diagram(ctx: RunContext[CameraDeps], instructions: str) -> str:
    """Redraw a sketch the user is showing the camera as a clean diagram on their screen.

    Use this for a hand-drawn diagram, system design, flow chart, or wireframe when the user asks
    to clean it up, redraw, digitize, or "make a proper version" of what they're holding up.

    The drawing tool cannot see the camera, so describe the sketch in full here -- it draws only
    what you describe.

    Args:
        ctx: The context.
        instructions: A thorough text description of the diagram to draw: every box and its
            label, every arrow and what it connects, groupings, overall layout, and any changes
            the user asked for (e.g. "clean up this microservices diagram and label the queues").
    """
    await ctx.deps.emit({'type': 'drawing_started', 'request': instructions})
    try:
        result = await _draw_agent().run(DRAW_PROMPT.format(instructions=instructions))
    except anyio.get_cancelled_exc_class():
        # The realtime model cancelled this call mid-draw -- e.g. the user barged in, so the provider
        # abandoned the turn (a `ToolCallCancelled`, which the session maps to task cancellation).
        # Cancellation is a `BaseException`, so it skips the `except Exception` below; clear the
        # browser's loading overlay (shielded, since we're unwinding a cancellation) before re-raising.
        with anyio.CancelScope(shield=True):
            await ctx.deps.emit({'type': 'drawing_error'})
        raise
    except Exception as exc:
        await ctx.deps.emit({'type': 'drawing_error'})
        return f'The redraw failed: {exc}'
    await ctx.deps.emit({'type': 'drawing', 'html': _extract_html(result.output)})
    return 'Done -- the cleaned-up diagram is on their screen now. Briefly tell them what you drew.'


def _web_search_supported(model: RealtimeModel) -> bool:
    """Whether `model` supports web search natively, read from its realtime profile."""
    return WebSearchTool in model.profile.get('supported_native_tools', frozenset())


def _build_agent(*, web_search: bool) -> Agent[CameraDeps, str]:
    """Build the camera assistant for one connection.

    The agent is per connection because whether web search is available depends on the selected
    model, so its capabilities and instructions vary. The `redraw_diagram` tool is registered
    whenever drawing is enabled, independently of web search -- the two can be active at once.
    """
    agent = Agent(
        # Named so Logfire tells this run apart from the drawing agent's.
        name='camera_assistant',
        instructions=_instructions(web_search=web_search),
        deps_type=CameraDeps,
        capabilities=[WebSearch()] if web_search else [],
    )
    if DRAW:
        agent.tool(redraw_diagram)
    return agent


@app.get('/')
async def index() -> HTMLResponse:
    # Seed the settings panel with the server's env-configured defaults so the UI mirrors them.
    # Angle brackets are JSON-escaped so env-supplied values can't break out of the script tag.
    defaults = (
        json.dumps(
            {
                'model': MODEL,
                'voice': VOICE,
                'turn_coverage': TURN_COVERAGE,
                'proactive': PROACTIVE,
                'affective': AFFECTIVE,
            }
        )
        .replace('<', '\\u003c')
        .replace('>', '\\u003e')
    )
    return HTMLResponse(
        _INDEX_PATH.read_text(encoding='utf-8').replace('__DEFAULTS__', defaults)
    )


def _build_model(params: Mapping[str, str]) -> RealtimeModel:
    """Build the selected realtime model with provider-appropriate UI settings."""
    model_id = params.get('model') or MODEL
    if USE_VERTEX and model_id.startswith('google:'):
        model = GoogleRealtimeModel(
            model_id.removeprefix('google:'), provider='google-cloud'
        )
    else:
        model = infer_realtime_model(model_id)

    modality = params.get('modality', 'audio')
    if modality not in ('audio', 'text'):
        raise ValueError(f'Output modality {modality!r} must be "audio" or "text"')
    common_settings = RealtimeModelSettings(
        output_modality=modality, reconnect=ReconnectPolicy(max_attempts=5)
    )
    voice = params.get('voice') or VOICE
    start, end = params.get('start_sensitivity'), params.get('end_sensitivity')
    if isinstance(model, GoogleRealtimeModel):
        settings = GoogleRealtimeModelSettings(
            **common_settings,
            google_proactive_audio=_truthy(params['proactive'])
            if 'proactive' in params
            else PROACTIVE,
            google_affective_dialog=_truthy(params['affective'])
            if 'affective' in params
            else AFFECTIVE,
            google_enable_session_resumption=True,
        )
        if voice:
            settings['google_voice'] = voice
        if language_code := params.get('language'):
            settings['google_language_code'] = language_code
        coverage = params.get('turn_coverage') or TURN_COVERAGE
        if coverage in ('activity_only', 'all_input', 'all_video'):
            settings['google_turn_coverage'] = coverage
        if start in ('high', 'low') or end in ('high', 'low'):
            vad: AutomaticVAD = {}
            if start in ('high', 'low'):
                vad['start_sensitivity'] = start
            if end in ('high', 'low'):
                vad['end_sensitivity'] = end
            settings['google_vad'] = vad
        model.settings = settings
    elif isinstance(model, OpenAIRealtimeModel):
        settings = OpenAIRealtimeModelSettings(**common_settings)
        if voice:
            settings['openai_voice'] = voice
        # OpenAI has one shared turn-detection sensitivity, so either UI VAD control maps onto it.
        if (sensitivity := start or end) in ('high', 'low'):
            settings['turn_detection'] = TurnDetection(sensitivity=sensitivity)
        model.settings = settings
    else:
        raise ValueError(
            f'Realtime model {model_id!r} does not support camera image input'
        )
    return model


def _grounding_sources(content: object) -> list[dict[str, object]]:
    """Extract `{url, title}` source chips from a grounding `NativeToolReturnPart.content`.

    Google Search grounding returns cited pages as a list of provider-shaped chunks; keep the ones
    with a usable URL, and degrade to no chips on an unexpected shape rather than an error.
    """
    if not isinstance(content, list):
        return []
    sources: list[dict[str, object]] = []
    for raw in cast('list[object]', content):
        if not isinstance(raw, dict):
            continue
        chunk = cast('dict[str, object]', raw)
        if isinstance(url := chunk.get('uri'), str):
            sources.append({'url': url, 'title': chunk.get('title')})
    return sources


def _json_message(event: RealtimeEvent) -> dict[str, object] | None:
    """Translate a session event into a JSON message for the browser.

    Audio and the incrementally streamed transcript are handled directly in `pump_events`; this
    covers the remaining one-shot events (barge-in, grounding sources, end of turn).
    """
    match event:
        case RealtimeInputSpeechStartEvent() | RealtimeResponseInterruptedEvent():
            # A barge-in: the user started talking over the model, or the provider reported the
            # response interrupted -- Gemini signals only the latter, without an
            # `RealtimeInputSpeechStartEvent`. The browser flushes buffered audio either way.
            return {'type': 'speech_started'}
        case PartEndEvent(part=NativeToolReturnPart(content=content)):
            # Google Search grounding finished; surface its cited sources as chips.
            return {
                'type': 'sources',
                'queries': [],
                'sources': _grounding_sources(content),
            }
        case RealtimeTurnCompleteEvent():
            return {'type': 'turn_complete'}
        case _:
            return None


async def _dispatch_text(session: RealtimeSession, text: str) -> None:
    """Route a JSON text frame from the browser.

    Handles a streamed camera frame (`image`), a typed turn (`text`), or a watch `nudge`.
    """
    try:
        # Decode and validate the message. A malformed frame is ignored here, but a genuine send
        # failure must surface, so `session.send()` stays outside this guard.
        raw: object = json.loads(text)
        if not isinstance(raw, dict):
            return
        # JSON object keys are strings.
        data = cast('dict[str, object]', raw)
        match data.get('type'):
            case 'image':
                image_data = data.get('data')
                media_type = data.get('mime', 'image/jpeg')
                if not isinstance(image_data, str) or not isinstance(media_type, str):
                    return
                content: str | BinaryContent = BinaryContent(
                    data=base64.b64decode(image_data),
                    media_type=media_type,
                )
            case 'text':
                text_content = data.get('text')
                if not isinstance(text_content, str):
                    return
                content = text_content
            case 'nudge':
                # Watch mode: trigger a turn so the model reports visual changes.
                content = WATCH_PROMPT
            case _:
                return
    except ValueError:
        logfire.exception('Ignoring malformed browser message')
        return
    await session.send(content)


async def _run_session(
    session: RealtimeSession,
    socket: WebSocket,
    emit: Callable[[dict[str, object]], Awaitable[None]],
    send_lock: anyio.Lock,
) -> None:
    """The realtime bridge: model output goes out while browser input goes in.

    Two concurrent pumps run until either side ends; when one stops (a disconnect or a provider drop)
    it cancels the task group so the other unwinds and the session closes.
    """
    async with anyio.create_task_group() as tg:

        async def pump_events() -> None:
            try:
                async for event in session:
                    match event:
                        case PartDeltaEvent(
                            delta=SpeechPartDelta(audio_chunk=chunk)
                        ) if chunk is not None:
                            # Model audio goes back as raw binary frames.
                            async with send_lock:
                                await socket.send_bytes(chunk)
                        case PartDeltaEvent(
                            delta=SpeechPartDelta(
                                speaker=speaker, transcript_delta=delta
                            )
                        ) if delta:
                            # Stream the transcript into the browser bubble as it arrives. Both
                            # speakers' transcripts stream at once, so each delta names its own
                            # speaker rather than needing to be tied back to a `PartStartEvent`.
                            await emit(
                                {
                                    'type': 'transcript',
                                    'speaker': speaker or 'assistant',
                                    'delta': delta,
                                }
                            )
                        case PartDeltaEvent(
                            delta=TextPartDelta(content_delta=delta)
                        ) if delta:
                            # With `output_modality='text'` the assistant's reply arrives as text
                            # part deltas rather than speech; stream it into the same bubble.
                            await emit(
                                {
                                    'type': 'transcript',
                                    'speaker': 'assistant',
                                    'delta': delta,
                                }
                            )
                        case _:
                            if (message := _json_message(event)) is not None:
                                await emit(message)
            except Exception as exc:
                logfire.exception('Realtime event pump failed')
                # Best effort: the socket itself may be what failed.
                with suppress(Exception):
                    await emit(
                        {'type': 'error', 'message': f'Realtime provider failed: {exc}'}
                    )
            finally:
                tg.cancel_scope.cancel()

        async def pump_inbound() -> None:
            try:
                while True:
                    message: Mapping[str, object] = await socket.receive()
                    if message.get('type') == 'websocket.disconnect':
                        break
                    if isinstance(chunk := message.get('bytes'), bytes):
                        await session.send_audio(chunk)
                    elif isinstance(text := message.get('text'), str):
                        await _dispatch_text(session, text)
            except WebSocketDisconnect:
                pass
            except RealtimeError as exc:
                # Send-side recovery is not reconnect-aware yet; a provider drop ends this session and
                # lets the browser reconnect. See https://github.com/pydantic/pydantic-ai/issues/6703.
                logfire.exception('Realtime inbound pump failed')
                with suppress(Exception):
                    await emit(
                        {'type': 'error', 'message': f'Realtime provider failed: {exc}'}
                    )
            finally:
                tg.cancel_scope.cancel()

        tg.start_soon(pump_events)
        tg.start_soon(pump_inbound)


@app.websocket('/ws')
async def ws(socket: WebSocket) -> None:
    if not _same_origin(socket):
        logfire.warn(
            'Rejected WebSocket: origin {origin!r} does not match host {host!r} or forwarded host '
            '{forwarded_host!r}. Behind a proxy that rewrites Host, set CAMERA_ALLOWED_ORIGINS to '
            "the browser-facing origin (e.g. 'https://myapp.example.com').",
            origin=socket.headers.get('origin'),
            host=socket.headers.get('host'),
            forwarded_host=socket.headers.get('x-forwarded-host'),
        )
        await socket.close(code=1008, reason='WebSocket origin does not match Host')
        return
    await socket.accept()

    # A lock serializes WebSocket sends, since a tool's `emit` can race the event pump.
    send_lock = anyio.Lock()

    async def emit(message: dict[str, object]) -> None:
        async with send_lock:
            await socket.send_json(message)

    try:
        model = _build_model(socket.query_params)
    except (UserError, ValueError) as exc:
        logfire.exception('Could not build realtime model')
        await emit({'type': 'error', 'message': str(exc)})
        return

    # This handshake must precede mic capture: raw PCM does not carry its sample rate.
    await emit(
        {
            'type': 'session_config',
            'input_sample_rate': model.audio_input_sample_rate,
            'output_sample_rate': model.audio_output_sample_rate,
        }
    )

    agent = _build_agent(web_search=WEB_SEARCH and _web_search_supported(model))
    try:
        async with agent.realtime(
            model, deps=CameraDeps(emit=emit)
        ).session() as session:
            await _run_session(session, socket, emit, send_lock)
    except ModelAPIError as exc:
        logfire.exception('Realtime session failed to connect')
        await emit({'type': 'error', 'message': str(exc)})


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='127.0.0.1', port=8000)
```

The build-free browser captures media, waits for session configuration, and renders every demo feature:

index.html

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover" />
    <title>Lens -- Camera Assistant</title>
    <style>
      :root {
        --g1: #4285f4; --g2: #9b6bff; --g3: #ff5c8a; --g4: #36c5f0;
        --ink: #fff; --dim: rgba(255, 255, 255, 0.66);
        --glass: rgba(255, 255, 255, 0.08); --line: rgba(255, 255, 255, 0.16);
        --level: 0; --mic: 0;
      }
      * { box-sizing: border-box; }
      html, body { height: 100%; margin: 0; }
      body {
        background: #05060a; color: var(--ink); overflow: hidden;
        font-family: ui-sans-serif, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
      }
      button { font-family: inherit; }

      .stage { position: fixed; inset: 0; }
      .cam { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; background: #05060a;
        opacity: 0; transition: opacity 0.6s ease; }
      .stage[data-cam='on'] .cam { opacity: 1; }

      .aura { position: absolute; inset: 0; pointer-events: none; transition: background 0.12s linear; z-index: 1;
        background: radial-gradient(130% 90% at 50% 118%,
          rgba(155, 107, 255, calc(0.10 + var(--level) * 0.55)) 0%,
          rgba(66, 133, 244, calc(0.05 + var(--level) * 0.28)) 32%, transparent 62%); }
      .scrim-top, .scrim-bot { position: absolute; left: 0; right: 0; pointer-events: none; z-index: 2; }
      .scrim-top { top: 0; height: 150px; background: linear-gradient(to bottom, rgba(0, 0, 0, 0.5), transparent); }
      .scrim-bot { bottom: 0; height: 320px; background: linear-gradient(to top, rgba(0, 0, 0, 0.62), transparent); }

      .hud { position: absolute; left: 0; right: 0; display: flex; align-items: center; gap: 12px;
        padding: max(16px, env(safe-area-inset-top)) 18px 16px; z-index: 6; }
      .hud.top { top: 0; }
      .hud.dock { bottom: 0; padding: 16px 18px max(20px, env(safe-area-inset-bottom)); }
      .dock-inner { margin: 0 auto; display: flex; align-items: center; justify-content: center; gap: 12px;
        flex-wrap: wrap; width: 100%; max-width: 680px; }

      .brand { display: flex; align-items: center; gap: 10px; font-weight: 650; letter-spacing: -0.01em; }
      .brand small { color: var(--dim); font-weight: 500; }
      .logo { width: 26px; height: 26px; border-radius: 50%;
        background: conic-gradient(from 0deg, var(--g1), var(--g2), var(--g3), var(--g4), var(--g1));
        box-shadow: 0 0 14px rgba(124, 107, 255, 0.6); animation: spin 7s linear infinite; }
      .spacer { margin-left: auto; }
      .status { display: flex; align-items: center; gap: 7px; font-size: 13px; color: var(--dim);
        background: rgba(0, 0, 0, 0.32); border: 1px solid var(--line); border-radius: 999px; padding: 5px 11px;
        -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px); }
      .pip { width: 8px; height: 8px; border-radius: 50%; background: #8a8f9a; transition: all 0.25s; }
      [data-state='connecting'] .pip { background: #f5a623; }
      [data-state='listening'] .pip { background: var(--g4); box-shadow: 0 0 0 4px rgba(54, 197, 240, 0.18); }
      [data-state='thinking'] .pip { background: var(--g2); animation: blink 1s ease-in-out infinite; }
      [data-state='speaking'] .pip { background: var(--g2); box-shadow: 0 0 0 5px rgba(155, 107, 255, 0.22); }
      [data-state='error'] .pip { background: var(--g3); }
      @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

      .ico { width: 48px; height: 48px; border-radius: 50%; border: 1px solid var(--line); background: var(--glass);
        color: var(--ink); font-size: 18px; cursor: pointer; display: grid; place-items: center; transition: all 0.15s;
        -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); }
      .ico:hover:not(:disabled) { background: rgba(255, 255, 255, 0.16); transform: translateY(-1px); }
      .ico:disabled { opacity: 0.4; cursor: not-allowed; }
      .ico svg { width: 21px; height: 21px; display: block; }
      .ico.sm { width: 38px; height: 38px; }
      .ico.sm svg { width: 17px; height: 17px; }
      .ico.watch.on { background: linear-gradient(135deg, var(--g4), var(--g1)); border-color: transparent;
        box-shadow: 0 0 20px rgba(54, 197, 240, 0.6); animation: glowPulse 1.6s ease-in-out infinite; }
      @keyframes glowPulse { 0%, 100% { box-shadow: 0 0 16px rgba(54, 197, 240, 0.5); } 50% { box-shadow: 0 0 28px rgba(54, 197, 240, 0.85); } }

      .cta { height: 52px; padding: 0 30px; border: 0; border-radius: 999px; font-weight: 650; font-size: 15px;
        color: #fff; cursor: pointer; transition: transform 0.12s, box-shadow 0.2s, filter 0.2s;
        background: linear-gradient(135deg, var(--g1), var(--g2) 55%, var(--g3));
        box-shadow: 0 10px 32px rgba(124, 107, 255, 0.45); }
      .cta:hover { transform: translateY(-1px); filter: brightness(1.06); }
      .cta.stop { background: linear-gradient(135deg, var(--g3), #d6455f); box-shadow: 0 10px 32px rgba(214, 69, 95, 0.45); }

      .composer { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 200px; max-width: 320px;
        background: var(--glass); border: 1px solid var(--line); border-radius: 999px; padding: 5px 6px 5px 16px;
        -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); }
      .composer input { flex: 1; min-width: 40px; border: 0; outline: none; background: transparent; color: #fff;
        font: inherit; font-size: 14px; }
      .composer input::placeholder { color: rgba(255, 255, 255, 0.5); }

      .center { position: absolute; left: 0; right: 0; bottom: 150px; z-index: 4; pointer-events: none;
        display: flex; flex-direction: column; align-items: center; gap: 20px; padding: 0 24px; }
      .orb-wrap { position: relative; width: 132px; height: 132px; }
      .orb { position: absolute; inset: 0; border-radius: 50%; transition: transform 0.08s ease-out;
        transform: scale(calc(1 + var(--level) * 0.34));
        box-shadow: 0 0 calc(30px + var(--level) * 95px) rgba(124, 107, 255, calc(0.22 + var(--level) * 0.55)); }
      .orb::before { content: ''; position: absolute; inset: -7px; border-radius: 50%; filter: blur(7px); opacity: 0.92;
        background: conic-gradient(from 0deg, var(--g1), var(--g2), var(--g3), var(--g4), var(--g1));
        animation: spin 6s linear infinite; }
      .orb::after { content: ''; position: absolute; inset: 7px; border-radius: 50%;
        background: radial-gradient(circle at 50% 34%, rgba(255, 255, 255, 0.22), rgba(8, 8, 14, 0.88) 72%); }
      .mic-ring { position: absolute; inset: -14px; border-radius: 50%; border: 2px solid rgba(54, 197, 240, 0.85);
        opacity: calc(var(--mic) * 1.3); transform: scale(calc(1 + var(--mic) * 0.16)); pointer-events: none; }
      [data-state='idle'] .orb, [data-state='listening'] .orb { animation: breathe 3.6s ease-in-out infinite; }
      [data-state='thinking'] .orb::before { animation: spin 1.6s linear infinite; }
      @keyframes breathe {
        0%, 100% { box-shadow: 0 0 28px rgba(124, 107, 255, 0.22); }
        50% { box-shadow: 0 0 52px rgba(124, 107, 255, 0.4); }
      }
      @keyframes spin { to { transform: rotate(360deg); } }

      .caption { max-width: 720px; text-align: center; font-size: clamp(18px, 2.4vw, 24px); line-height: 1.34;
        font-weight: 500; text-shadow: 0 2px 18px rgba(0, 0, 0, 0.75); opacity: 0; transform: translateY(10px);
        transition: opacity 0.35s, transform 0.35s; }
      .caption.show { opacity: 1; transform: none; }
      .userline { font-size: 14px; color: var(--dim); text-shadow: 0 1px 10px rgba(0, 0, 0, 0.8);
        opacity: 0; transition: opacity 0.3s; }
      .userline.show { opacity: 1; }

      .sources { pointer-events: auto; display: flex; flex-wrap: wrap; justify-content: center; gap: 7px;
        max-width: 640px; opacity: 0; transform: translateY(8px); transition: opacity 0.35s, transform 0.35s; }
      .sources[hidden] { display: none; }
      .sources.show { opacity: 1; transform: none; }
      .sources .src-label { width: 100%; text-align: center; font-size: 10.5px; font-weight: 700;
        letter-spacing: 0.08em; text-transform: uppercase; color: rgba(255, 255, 255, 0.5); margin-bottom: 2px; }
      .sources a { display: inline-flex; align-items: center; gap: 6px; max-width: 240px; text-decoration: none;
        color: #fff; font-size: 12.5px; font-weight: 500; padding: 6px 11px; border-radius: 999px;
        border: 1px solid var(--line); background: rgba(255, 255, 255, 0.08); text-shadow: 0 1px 8px rgba(0, 0, 0, 0.7);
        -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px); transition: background 0.18s, border-color 0.18s; }
      .sources a:hover { background: rgba(255, 255, 255, 0.16); border-color: var(--g2); }
      .sources a .favi { width: 14px; height: 14px; border-radius: 3px; flex: 0 0 auto; }
      .sources a .label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

      .idle-hint { display: none; max-width: 360px; text-align: center; color: var(--dim); font-size: 14.5px;
        line-height: 1.5; }
      [data-state='idle'] .idle-hint { display: block; }
      [data-state='idle'] .caption, [data-state='idle'] .userline, [data-state='idle'] .sources { display: none; }

      .sheet { position: absolute; left: 0; right: 0; bottom: 0; z-index: 12; color: #fff;
        background: rgba(14, 14, 20, 0.82); border-top: 1px solid var(--line); border-radius: 22px 22px 0 0;
        padding: 16px 18px max(22px, env(safe-area-inset-bottom)); -webkit-backdrop-filter: blur(22px);
        backdrop-filter: blur(22px); box-shadow: 0 -20px 60px rgba(0, 0, 0, 0.5); animation: rise 0.28s ease; }
      .sheet[hidden] { display: none; }
      @keyframes rise { from { transform: translateY(20px); opacity: 0; } to { transform: none; opacity: 1; } }
      .sheet .head { display: flex; align-items: center; margin-bottom: 14px; }
      .sheet .head h3 { margin: 0; font-size: 14px; font-weight: 650; letter-spacing: -0.01em; }
      .sheet .head .logo { margin-right: 9px; }
      .sheet .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px 16px; }
      .sheet .group { display: contents; }
      .sheet .group-title { grid-column: 1 / -1; margin: 2px 0 -3px; font-size: 11px; font-weight: 700;
        color: rgba(255, 255, 255, 0.72); text-transform: uppercase; letter-spacing: 0.08em; }
      .sheet .hint { text-transform: none; letter-spacing: 0; font-weight: 400; }
      .sheet label { display: flex; flex-direction: column; gap: 5px; font-size: 11px; font-weight: 600;
        color: rgba(255, 255, 255, 0.6); text-transform: uppercase; letter-spacing: 0.05em; }
      .sheet .in { font: inherit; font-size: 14px; font-weight: 400; text-transform: none; letter-spacing: 0; color: #fff;
        background: rgba(255, 255, 255, 0.06); border: 1px solid var(--line); border-radius: 10px; padding: 9px 11px; }
      .sheet .in:focus { outline: none; border-color: var(--g2); }
      .sheet option { color: #111; }
      .sheet .ck { flex-direction: row; align-items: center; gap: 8px; text-transform: none; letter-spacing: 0;
        font-size: 13px; color: #fff; }
      .sheet .ck input { width: 16px; height: 16px; accent-color: var(--g2); }
      .sheet-foot { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }

      .board { position: absolute; inset: 0; z-index: 20; display: flex; align-items: center; justify-content: center;
        padding: max(18px, env(safe-area-inset-top)) 16px max(18px, env(safe-area-inset-bottom)); color: var(--ink);
        background: radial-gradient(120% 80% at 50% 0%, rgba(155, 107, 255, 0.16), transparent 60%), rgba(5, 6, 10, 0.74);
        -webkit-backdrop-filter: blur(22px); backdrop-filter: blur(22px); animation: fade 0.25s ease; }
      .board[hidden] { display: none; }
      @keyframes fade { from { opacity: 0; } to { opacity: 1; } }
      .board-card { display: flex; flex-direction: column; width: 100%; max-width: 920px; height: min(860px, 100%);
        border-radius: 24px; border: 1.5px solid transparent; overflow: hidden;
        background: linear-gradient(#0c0d14, #0c0d14) padding-box,
          linear-gradient(135deg, var(--g1), var(--g2) 55%, var(--g3)) border-box;
        box-shadow: 0 30px 80px rgba(0, 0, 0, 0.6); animation: pop 0.32s cubic-bezier(0.2, 0.9, 0.3, 1); }
      @keyframes pop { from { opacity: 0; transform: scale(0.96) translateY(12px); } to { opacity: 1; transform: none; } }
      .board-head { display: flex; align-items: center; gap: 11px; padding: 13px 14px 13px 16px;
        border-bottom: 1px solid var(--line); }
      .board-title { display: flex; flex-direction: column; line-height: 1.25; }
      .board-title b { font-size: 14px; font-weight: 650; letter-spacing: -0.01em; }
      .board-title small { font-size: 11px; color: var(--dim); font-weight: 500; }
      .board-save { display: inline-flex; align-items: center; gap: 7px; height: 38px; padding: 0 15px; border: 0;
        border-radius: 999px; font: inherit; font-size: 13px; font-weight: 600; color: #fff; cursor: pointer;
        background: linear-gradient(135deg, var(--g1), var(--g2) 60%, var(--g3)); box-shadow: 0 8px 22px rgba(124, 107, 255, 0.4);
        transition: transform 0.12s, filter 0.2s; }
      .board-save:hover { transform: translateY(-1px); filter: brightness(1.06); }
      .board-save svg { width: 16px; height: 16px; }
      .board-body { position: relative; flex: 1; min-height: 0; margin: 14px; border-radius: 14px; overflow: hidden;
        background: #fff; box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.06); }
      .board-frame { width: 100%; height: 100%; border: 0; background: #fff; }
      .board-loading { position: absolute; inset: 0; display: none; flex-direction: column; align-items: center;
        justify-content: center; gap: 16px; background: #0c0d14; color: var(--dim); font-size: 13px; font-weight: 500; }
      .board.loading .board-loading { display: flex; }
      .board-spin { width: 46px; height: 46px; border-radius: 50%;
        background: conic-gradient(from 0deg, var(--g1), var(--g2), var(--g3), var(--g4), var(--g1));
        -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 4px), #000 0);
        mask: radial-gradient(farthest-side, transparent calc(100% - 4px), #000 0);
        animation: spin 0.9s linear infinite; }
    </style>
  </head>
  <body>
    <div class="stage" id="app" data-state="idle" data-cam="off">
      <video id="video" class="cam" autoplay playsinline muted></video>
      <div class="aura"></div>
      <div class="scrim-top"></div>
      <div class="scrim-bot"></div>

      <header class="hud top">
        <div class="brand"><span class="logo"></span> Lens <small>Camera Assistant</small></div>
        <span class="spacer"></span>
        <span class="status" id="status"><span class="pip"></span><span id="statusText">tap start</span></span>
        <button class="ico sm" id="gear" title="Settings" aria-label="Settings">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/></svg>
        </button>
      </header>

      <div class="center">
        <div class="orb-wrap"><div class="orb"></div><div class="mic-ring"></div></div>
        <div class="caption" id="caption"></div>
        <div class="userline" id="userline"></div>
        <div class="sources" id="sources" hidden></div>
        <div class="idle-hint">Tap <b>Start</b>, then talk and point your camera at things to ask about them. Show it a hand-drawn sketch and ask it to <b>redraw</b> it as a clean diagram. The model sees your camera the whole time; toggle <b>Watch</b> to have it speak up on its own when the scene changes, instead of only when you ask.</div>
      </div>

      <footer class="hud dock">
        <div class="dock-inner">
          <button class="ico watch" id="watch" title="Watch -- the model always sees your camera; turn this on to have it speak up on its own when the scene changes, not just when you ask" aria-label="Watch" disabled>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
          <button class="cta" id="toggle">Start</button>
          <form class="composer" id="composer">
            <input id="text" type="text" placeholder="...or type a message" autocomplete="off" />
            <button class="ico sm" id="send" type="submit" title="Send" aria-label="Send">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/><path d="m22 2-7 20-4-9-9-4Z"/></svg>
            </button>
          </form>
        </div>
      </footer>

      <div class="sheet" id="panel" hidden>
        <div class="head"><span class="logo"></span><h3>Voice settings</h3><span class="spacer"></span><button class="ico sm" id="close" title="Close" aria-label="Close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button></div>
        <div class="grid">
          <label>Model<input id="model" class="in" list="models" value="google:gemini-3.1-flash-live-preview" placeholder="provider:model" autocomplete="off" /></label>
          <!-- The two recommended models lead; xAI is omitted because it has no image input for the camera.
               For Azure, replace the deployment name with your own. -->
          <datalist id="models">
            <option value="google:gemini-3.1-flash-live-preview"></option>
            <option value="openai:gpt-realtime-2.1"></option>
            <option value="openai:gpt-realtime-2.1-mini"></option>
            <option value="openai:gpt-realtime"></option>
            <option value="azure:gpt-realtime"></option>
            <option value="google:gemini-2.5-flash-native-audio-latest"></option>
          </datalist>
          <label>Voice <span class="hint">Suggestions are Gemini voices; OpenAI also supports names such as marin and alloy.</span><input id="voice" class="in" list="voices" placeholder="default" autocomplete="off" /></label>
          <label>Output modality<select id="modality" class="in"><option value="audio">audio</option><option value="text">text</option></select></label>
          <datalist id="voices">
            <option value="Puck"></option><option value="Charon"></option><option value="Kore"></option>
            <option value="Fenrir"></option><option value="Aoede"></option><option value="Leda"></option>
            <option value="Orus"></option><option value="Zephyr"></option>
          </datalist>
          <div class="group-title">Gemini-only settings</div>
          <div class="group">
            <label>Language code<input id="language" class="in" placeholder="e.g. en-US" autocomplete="off" /></label>
            <label>Turn coverage<select id="turn_coverage" class="in"><option value="">server default</option><option value="activity_only">activity only</option><option value="all_input">all input</option><option value="all_video">all video</option></select></label>
            <label>Start sensitivity <span class="hint">Also sets shared sensitivity on OpenAI/Azure.</span><select id="start_sensitivity" class="in"><option value="">default</option><option value="high">high</option><option value="low">low</option></select></label>
            <label>End sensitivity <span class="hint">Also sets shared sensitivity on OpenAI/Azure.</span><select id="end_sensitivity" class="in"><option value="">default</option><option value="high">high</option><option value="low">low</option></select></label>
            <label class="ck" title="The model decides when to speak and can stay silent."><input id="proactive" type="checkbox" />Proactive audio -- model can stay silent (native audio)</label>
            <label class="ck" title="The model adapts delivery to emotion in the conversation."><input id="affective" type="checkbox" />Affective dialog -- emotion-aware delivery (native audio)</label>
          </div>
        </div>
        <div class="sheet-foot"><button class="cta" id="apply">Apply &amp; restart</button></div>
      </div>

      <div class="board" id="board" hidden>
        <div class="board-card">
          <div class="board-head">
            <span class="logo"></span>
            <div class="board-title"><b>Redrawn diagram</b><small id="boardSubtitle">from your sketch</small></div>
            <span class="spacer"></span>
            <button class="board-save" id="boardSave" title="Save as PNG">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
              PNG
            </button>
            <button class="ico sm" id="boardClose" title="Close" aria-label="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </div>
          <div class="board-body">
            <iframe id="boardFrame" class="board-frame" sandbox title="Redrawn diagram"></iframe>
            <div class="board-loading"><div class="board-spin"></div><div>Redrawing your diagram...</div></div>
          </div>
        </div>
      </div>
    </div>

    <script>
      const FRAME_MS = 1000; // ~1 camera frame per second
      const FRAME_W = 512; // downscale streamed frames to keep bandwidth/cost low
      const WATCH_MS = 3500; // in Watch mode, check this often whether to nudge the model to report changes

      const $ = (id) => document.getElementById(id);
      const app = $('app'), video = $('video'), statusText = $('statusText');
      const caption = $('caption'), userline = $('userline');
      const toggleBtn = $('toggle'), watchBtn = $('watch'), panel = $('panel');

      const STATUS = { idle: 'tap start', connecting: 'connecting...', listening: 'listening', thinking: 'thinking...', speaking: 'speaking' };
      function setState(state, text) {
        app.dataset.state = state;
        statusText.textContent = text || STATUS[state] || state;
      }

      const DEFAULTS = __DEFAULTS__;
      let inputRate = null, outputRate = null;
      $('model').value = DEFAULTS.model || '';
      $('voice').value = DEFAULTS.voice || '';
      $('turn_coverage').value = DEFAULTS.turn_coverage || '';
      $('proactive').checked = !!DEFAULTS.proactive;
      $('affective').checked = !!DEFAULTS.affective;
      function settings() {
        return {
          model: $('model').value, voice: $('voice').value, language: $('language').value,
          modality: $('modality').value,
          turn_coverage: $('turn_coverage').value,
          start_sensitivity: $('start_sensitivity').value, end_sensitivity: $('end_sensitivity').value,
          proactive: $('proactive').checked ? '1' : '0', affective: $('affective').checked ? '1' : '0',
        };
      }
      function query() {
        const params = new URLSearchParams();
        for (const [k, v] of Object.entries(settings())) if (v !== '' && v != null) params.set(k, v);
        return params.toString();
      }
      $('gear').onclick = () => { panel.hidden = !panel.hidden; };
      $('close').onclick = () => { panel.hidden = true; };
      $('apply').onclick = async () => {
        panel.hidden = true;
        if (running) { stop(); try { await start(); } catch (err) { setState('error', 'error: ' + err.message); } }
      };

      let capTimer = null, userTimer = null;
      function showCaption(text) {
        caption.textContent = text; caption.classList.add('show');
        clearTimeout(capTimer); capTimer = setTimeout(() => caption.classList.remove('show'), 7000);
      }
      function showUser(text) {
        userline.textContent = text; userline.classList.add('show');
        clearTimeout(userTimer); userTimer = setTimeout(() => userline.classList.remove('show'), 3500);
      }

      // The transcript streams in as {speaker, delta} chunks. Accumulate into the current speaker's
      // bubble, starting a fresh one whenever the speaker changes or the previous turn ended.
      let streamSpeaker = null, streamText = '';
      function appendTranscript(speaker, delta) {
        if (speaker !== streamSpeaker) { streamSpeaker = speaker; streamText = ''; }
        streamText += delta;
        if (speaker === 'assistant') showCaption(streamText); else showUser(streamText);
      }
      function endTranscript() { streamSpeaker = null; streamText = ''; }

      const sourcesEl = $('sources');
      let srcTimer = null;
      const GLOBE = 'M2 12h20 M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z';
      function chipLabel(src) {
        if (src.title) return src.title;
        try { return new URL(src.url).hostname.replace(/^www\./, ''); } catch (e) { return src.url; }
      }
      function showSources(sources) {
        sourcesEl.replaceChildren();
        if (!sources || !sources.length) { sourcesEl.hidden = true; sourcesEl.classList.remove('show'); return; }
        const label = document.createElement('span');
        label.className = 'src-label'; label.textContent = 'Sources'; sourcesEl.appendChild(label);
        for (const src of sources.slice(0, 6)) {
          if (!src.url) continue;
          let url;
          try {
            url = new URL(src.url);
            if (url.protocol !== 'https:' && url.protocol !== 'http:') continue;
          } catch (e) { continue; }
          const a = document.createElement('a');
          a.href = url.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.title = url.href;
          const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
          svg.setAttribute('class', 'favi'); svg.setAttribute('viewBox', '0 0 24 24');
          svg.setAttribute('fill', 'none'); svg.setAttribute('stroke', 'currentColor'); svg.setAttribute('stroke-width', '2');
          const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
          circle.setAttribute('cx', '12'); circle.setAttribute('cy', '12'); circle.setAttribute('r', '10');
          const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
          path.setAttribute('d', GLOBE);
          svg.append(circle, path);
          const span = document.createElement('span'); span.className = 'label'; span.textContent = chipLabel(src);
          a.append(svg, span); sourcesEl.appendChild(a);
        }
        sourcesEl.hidden = false; sourcesEl.classList.add('show');
        clearTimeout(srcTimer); srcTimer = setTimeout(() => sourcesEl.classList.remove('show'), 15000);
      }

      // Redrawn-diagram board: the server sends self-contained HTML, we render it in a sandboxed
      // iframe and let the user export it to PNG client-side (no extra dependencies).
      const board = $('board'), boardFrame = $('boardFrame'), boardSubtitle = $('boardSubtitle');
      let lastHtml = '';
      const DRAWING_CSP = "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; img-src data:\">";
      function showDrawingLoading(request) {
        // The opaque loading overlay hides the frame, so the previous drawing (if any) can stay in
        // the iframe: one srcdoc navigation per drawing, not a blank-then-content pair.
        boardSubtitle.textContent = request ? '"' + request + '"' : 'from your sketch';
        board.hidden = false; board.classList.add('loading');
      }
      function showDrawing(html) {
        // The opaque iframe sandbox blocks scripts and same-origin access; CSP also blocks network loads.
        // Reveal only once the new document has loaded: dropping the overlay before the navigation
        // commits can expose a not-yet-painted (white) frame on the sandbox's first composite.
        lastHtml = DRAWING_CSP + html;
        board.hidden = false;
        boardFrame.onload = () => { boardFrame.onload = null; board.classList.remove('loading'); };
        boardFrame.srcdoc = lastHtml;
      }
      $('boardClose').onclick = () => {
        board.hidden = true; board.classList.remove('loading');
        boardFrame.onload = null; boardFrame.srcdoc = ''; lastHtml = '';
      };
      function downloadBlob(blob, name) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = name; a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
      // Rasterize the rendered HTML via an SVG <foreignObject>; fall back to saving the raw HTML if
      // the browser taints the canvas (e.g. it embedded a cross-origin resource we didn't expect).
      async function saveDrawingPng() {
        if (!lastHtml) return;
        try {
          const w = boardFrame.clientWidth, h = boardFrame.clientHeight, scale = 2;
          const doc = new DOMParser().parseFromString(lastHtml, 'text/html');
          const xml = new XMLSerializer().serializeToString(doc.documentElement);
          const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><foreignObject x="0" y="0" width="100%" height="100%">${xml}</foreignObject></svg>`;
          const img = new Image();
          await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg); });
          const canvas = document.createElement('canvas');
          canvas.width = w * scale; canvas.height = h * scale;
          const ctx = canvas.getContext('2d');
          ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.scale(scale, scale); ctx.drawImage(img, 0, 0);
          canvas.toBlob((blob) => blob ? downloadBlob(blob, 'diagram.png') : downloadBlob(new Blob([lastHtml], { type: 'text/html' }), 'diagram.html'));
        } catch (e) {
          downloadBlob(new Blob([lastHtml], { type: 'text/html' }), 'diagram.html');
        }
      }
      $('boardSave').onclick = saveDrawingPng;

      let playCtx = null, playHead = 0, scheduled = [], outAnalyser = null;
      function ensurePlayback() {
        if (!outputRate) return;
        if (!playCtx) {
          playCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: outputRate });
          outAnalyser = playCtx.createAnalyser(); outAnalyser.fftSize = 256; outAnalyser.smoothingTimeConstant = 0.8;
          outAnalyser.connect(playCtx.destination);
        }
        if (playCtx.state === 'suspended') playCtx.resume();
      }
      function playPCM(ab) {
        ensurePlayback();
        const i16 = new Int16Array(ab); if (!i16.length) return;
        const f32 = new Float32Array(i16.length);
        for (let i = 0; i < i16.length; i++) f32[i] = i16[i] / 0x8000;
        const buf = playCtx.createBuffer(1, f32.length, outputRate); buf.getChannelData(0).set(f32);
        const node = playCtx.createBufferSource(); node.buffer = buf; node.connect(outAnalyser);
        const t = Math.max(playCtx.currentTime, playHead); node.start(t); playHead = t + buf.duration;
        scheduled.push(node); node.onended = () => { scheduled = scheduled.filter((n) => n !== node); };
      }
      function flushPlayback() {
        for (const n of scheduled) { try { n.stop(); } catch (e) {} }
        scheduled = []; if (playCtx) playHead = playCtx.currentTime;
      }

      let micAnalyser = null, raf = null, outLvl = 0, micLvl = 0;
      const td = new Uint8Array(256);
      function rms(an) {
        if (!an) return 0;
        an.getByteTimeDomainData(td);
        let s = 0;
        for (let i = 0; i < td.length; i++) { const v = (td[i] - 128) / 128; s += v * v; }
        return Math.sqrt(s / td.length);
      }
      function loop() {
        raf = requestAnimationFrame(loop);
        outLvl += (Math.min(1, rms(outAnalyser) * 3.4) - outLvl) * 0.28;
        micLvl += (Math.min(1, rms(micAnalyser) * 3.4) - micLvl) * 0.28;
        app.style.setProperty('--level', outLvl.toFixed(3));
        app.style.setProperty('--mic', micLvl.toFixed(3));
      }
      function startLoop() { if (!raf) loop(); }
      function stopLoop() {
        if (raf) { cancelAnimationFrame(raf); raf = null; }
        outLvl = micLvl = 0; app.style.setProperty('--level', '0'); app.style.setProperty('--mic', '0');
      }

      let sock = null, speakTimer = null;
      function send(obj) {
        if (!sock || sock.readyState !== 1) return false;
        sock.send(JSON.stringify(obj)); return true;
      }
      function onSpeaking() {
        setState('speaking');
        clearTimeout(speakTimer);
        // Packets arrive in bursts, so seconds of audio may still be scheduled when the last one
        // lands; stay in `speaking` until playback actually drains, or Watch mode's nudge could
        // truncate audio that is still playing.
        const settle = () => {
          if (!running) return;
          if (playCtx && playHead > playCtx.currentTime + 0.05) {
            speakTimer = setTimeout(settle, 250);
            return;
          }
          setState('listening');
        };
        speakTimer = setTimeout(settle, 380);
      }

      function connect() {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        setState('connecting');
        return new Promise((resolve, reject) => {
          const connection = new WebSocket(`${proto}://${location.host}/ws?${query()}`);
          sock = connection;
          connection.binaryType = 'arraybuffer';
          connection.onclose = () => {
            if (sock !== connection) return;
            if (running) setState('idle', 'disconnected');
            reject(new Error('disconnected'));
          };
          connection.onerror = () => {
            if (sock !== connection) return;
            setState('error', 'connection error'); reject(new Error('connection error'));
          };
          connection.onmessage = (ev) => {
          if (sock !== connection) return;
          if (ev.data instanceof ArrayBuffer) { onSpeaking(); playPCM(ev.data); return; }
          const m = JSON.parse(ev.data);
          if (m.type === 'session_config') {
            inputRate = m.input_sample_rate; outputRate = m.output_sample_rate;
            setState('listening'); resolve(); return;
          }
          if (m.type === 'speech_started') { flushPlayback(); endTranscript(); setState('listening'); }
          else if (m.type === 'transcript') { appendTranscript(m.speaker, m.delta); }
          else if (m.type === 'sources') { showSources(m.sources); }
          else if (m.type === 'drawing_started') { showDrawingLoading(m.request); }
          else if (m.type === 'drawing') { showDrawing(m.html); }
          else if (m.type === 'drawing_error') { board.hidden = true; board.classList.remove('loading'); showCaption('Sorry, I could not redraw that.'); }
          else if (m.type === 'error') {
            const message = m.message || 'the model rejected the session';
            stop(); setState('error', message); reject(new Error(message));
          }
          else if (m.type === 'turn_complete') { endTranscript(); if (running && app.dataset.state === 'thinking') setState('listening'); }
          };
        });
      }

      let watching = false, watchTimer = null;
      function setWatch(on) {
        watching = on && running;
        watchBtn.classList.toggle('on', watching);
        if (watchTimer) { clearInterval(watchTimer); watchTimer = null; }
        // Only nudge when the model is idle: nudging while it's thinking or speaking interrupts the
        // in-flight response (a barge-in), which chops up the audio. Waiting for 'listening' means each
        // nudge lands between turns, so Watch narrates changes without cutting off what it's saying.
        if (watching) watchTimer = setInterval(() => {
          if (app.dataset.state === 'listening') send({ type: 'nudge' });
        }, WATCH_MS);
      }
      watchBtn.onclick = () => { if (running) setWatch(!watching); };

      let micCtx = null, mediaStream = null, micNode = null, frameTimer = null, canvas = null, running = false, starting = false;

      async function start() {
        if (starting) return;
        starting = true; toggleBtn.disabled = true;
        try {
          mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
            // Prefer the rear camera; frames are downscaled to FRAME_W before streaming to keep the
            // live session cheap.
            video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
          });
          video.srcObject = mediaStream;
          app.dataset.cam = 'on';
          await connect();
          ensurePlayback();
          startMic();
          startFrames();
          startLoop();
          running = true; toggleBtn.textContent = 'Stop'; toggleBtn.classList.add('stop'); watchBtn.disabled = false;
        } catch (err) {
          stop();
          throw err;
        } finally {
          starting = false; toggleBtn.disabled = false;
        }
      }

      function startMic() {
        micCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: inputRate });
        const src = micCtx.createMediaStreamSource(mediaStream);
        micAnalyser = micCtx.createAnalyser(); micAnalyser.fftSize = 256; micAnalyser.smoothingTimeConstant = 0.75;
        src.connect(micAnalyser);
        micNode = micCtx.createScriptProcessor(4096, 1, 1);
        const mute = micCtx.createGain(); mute.gain.value = 0;
        src.connect(micNode); micNode.connect(mute); mute.connect(micCtx.destination);
        micNode.onaudioprocess = (e) => {
          if (!sock || sock.readyState !== 1) return;
          const f32 = e.inputBuffer.getChannelData(0); const i16 = new Int16Array(f32.length);
          for (let i = 0; i < f32.length; i++) { const s = Math.max(-1, Math.min(1, f32[i])); i16[i] = s < 0 ? s * 0x8000 : s * 0x7fff; }
          sock.send(i16.buffer);
        };
      }

      function startFrames() {
        canvas = document.createElement('canvas');
        frameTimer = setInterval(() => {
          if (!sock || sock.readyState !== 1 || !video.videoWidth) return;
          const scale = FRAME_W / video.videoWidth;
          canvas.width = FRAME_W; canvas.height = Math.round(video.videoHeight * scale);
          canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
          canvas.toBlob((blob) => {
            if (!blob) return;
            const reader = new FileReader();
            reader.onload = () => send({ type: 'image', data: String(reader.result).split(',')[1], mime: 'image/jpeg' });
            reader.readAsDataURL(blob);
          }, 'image/jpeg', 0.6);
        }, FRAME_MS);
      }

      function stop() {
        running = false; toggleBtn.textContent = 'Start'; toggleBtn.classList.remove('stop');
        setWatch(false); watchBtn.disabled = true;
        if (frameTimer) { clearInterval(frameTimer); frameTimer = null; }
        if (micNode) { micNode.disconnect(); micNode.onaudioprocess = null; micNode = null; }
        if (micCtx) { micCtx.close(); micCtx = null; } micAnalyser = null;
        if (mediaStream) { mediaStream.getTracks().forEach((t) => t.stop()); mediaStream = null; }
        video.srcObject = null; app.dataset.cam = 'off';
        if (sock) { try { sock.close(); } catch (e) {} sock = null; }
        flushPlayback(); stopLoop(); setState('idle');
      }

      toggleBtn.onclick = async () => {
        if (running) { stop(); return; }
        try { await start(); } catch (err) { setState('error', 'error: ' + err.message); }
      };

      $('composer').addEventListener('submit', (e) => {
        e.preventDefault();
        const q = $('text').value.trim(); if (!q) return;
        if (!send({ type: 'text', text: q })) { setState('error', 'not connected'); return; }
        ensurePlayback(); showUser(q);
        if (running) setState('thinking');
        $('text').value = '';
      });
    </script>
  </body>
</html>
```

---
