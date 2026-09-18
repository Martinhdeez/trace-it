# [OpenAI Realtime](https://pydantic.dev/docs/ai/realtime/openai/)

# OpenAI Realtime

[`OpenAIRealtimeModel`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.OpenAIRealtimeModel) connects an agent to OpenAI's native speech-to-speech models. Start with the [realtime quickstart](https://pydantic.dev/docs/ai/realtime/overview/#quickstart) or the [text-to-audio example](https://pydantic.dev/docs/ai/examples/realtime/realtime-text-to-audio/).

## Setup

To use OpenAI realtime models, install `pydantic-ai-slim` with the `openai-realtime` optional group, which bundles the `openai` package together with the realtime WebSocket transport:

-   [pip](#tab-panel-265)
-   [uv](#tab-panel-266)

Terminal

```bash
pip install "pydantic-ai-slim[openai-realtime]"
```

Terminal

```bash
uv add "pydantic-ai-slim[openai-realtime]"
```

Set `OPENAI_API_KEY` as described in the [OpenAI model documentation](https://pydantic.dev/docs/ai/models/openai/#configuration). Authentication and base URL come from `provider`, mirroring [`OpenAIChatModel`](https://pydantic.dev/docs/ai/api/models/openai/#pydantic_ai.models.openai.OpenAIChatModel). The default `provider='openai'` reads the environment; pass an [`OpenAIProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.openai.OpenAIProvider) for a custom key or base URL. The realtime WebSocket opens separately, so a custom provider `httpx` client is not used for it. Sessions run over a server-side WebSocket by default; for browser voice, the browser can exchange media directly over [WebRTC](#browser-webrtc) while your backend runs the agent (see [Connecting a frontend](https://pydantic.dev/docs/ai/realtime/deployment/#browser-webrtc-server-sideband)).

## Model names

Use the provider's realtime model ID with [`OpenAIRealtimeModel`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.OpenAIRealtimeModel), for example `gpt-realtime`, `gpt-realtime-2.1`, or `gpt-realtime-2.1-mini`. Model availability and aliases can change; use the [official OpenAI model documentation](https://platform.openai.com/docs/models) as the canonical model list.

## Settings

[`OpenAIRealtimeModelSettings`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.OpenAIRealtimeModelSettings) -- the realtime counterpart of [model run settings](https://pydantic.dev/docs/ai/core-concepts/agent/#model-run-settings) -- extends the [shared settings](https://pydantic.dev/docs/ai/realtime/overview/#shared-settings) with voice, noise reduction, output speed, exact [turn detection](https://pydantic.dev/docs/ai/realtime/turns/), and truncation:

```python
from pydantic_ai.realtime.openai import (
    OpenAIRealtimeModel,
    OpenAIRealtimeModelSettings,
)

settings = OpenAIRealtimeModelSettings(
    max_tokens=2_000,
    openai_voice='alloy',
    turn_detection={'sensitivity': 'high', 'silence_duration_ms': 400},
    openai_input_noise_reduction='near_field',
    openai_output_speed=1.1,
    openai_turn_detection={'type': 'semantic_vad', 'eagerness': 'high'},
    openai_truncation={'type': 'retention_ratio', 'retention_ratio': 0.8},
)
model = OpenAIRealtimeModel('gpt-realtime', settings=settings)
```

`openai_turn_detection` accepts [`ServerVAD`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.ServerVAD) or [`SemanticVAD`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.SemanticVAD) and overrides shared [`turn_detection`](https://pydantic.dev/docs/ai/realtime/turns/#automatic-turn-detection). `openai_truncation` also accepts `'auto'` or `'disabled'`; retention ratio preserves a stable, cacheable prefix as the session grows. `openai_voice` selects the provider voice. OpenAI realtime does not expose `temperature` through Pydantic AI.

Input transcription defaults to `'auto'`; set a supported transcription model ID to pin it or `None` to disable it. See [Input transcription](https://pydantic.dev/docs/ai/realtime/audio/#input-transcription).

### Reasoning

The shared [`thinking`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings.thinking) setting (see [Thinking](https://pydantic.dev/docs/ai/capabilities/thinking/)) applies to models whose profile reports `supports_thinking`, including the `gpt-realtime-2` family. `True` uses the provider default and an effort string selects a level. `False` omits `reasoning`, because OpenAI realtime does not accept a disabled effort. The GA `gpt-realtime` ignores the setting.

Reasoning traces are not surfaced as [`ThinkingPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ThinkingPart)s; the API exposes effort as input only.

## Browser WebRTC

For browser voice agents, OpenAI recommends WebRTC: the audio flows browser ↔ OpenAI directly, while your backend attaches a control-plane **sideband** to run the agent. [`AgentRealtime`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime) exposes two signaling helpers, both resolving and binding the agent's session configuration (instructions, tools, voice, VAD) server-side:

-   [`answer_webrtc_offer`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.answer_webrtc_offer) -- the **secure** path: relay the browser's SDP offer to `POST /v1/realtime/calls`, returning the SDP answer and a [`WebRTCSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.WebRTCSession) to attach a sideband to with [`agent.realtime(model).session(provider_session=...)`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.session). The browser never sees a token.
-   [`create_client_secret`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AgentRealtime.create_client_secret) -- mint a short-lived [`RealtimeClientSecret`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeClientSecret) (ephemeral token) for a browser that negotiates the WebRTC call itself, when you don't relay the SDP through your backend.

See [Connecting a frontend](https://pydantic.dev/docs/ai/realtime/deployment/#browser-webrtc-server-sideband) for the topology, the secure offer-relay flow, and the sideband trust model, and the [realtime WebRTC example](https://pydantic.dev/docs/ai/examples/realtime/realtime-webrtc/) for a runnable FastAPI and browser app.

## Feature support and limitations

Feature

Support

Notes

Audio format

Full feature support

Mono PCM16, 24 kHz input and output

Text output

Full feature support

Select with `output_modality='text'`

Image input

Full feature support

[Images](https://pydantic.dev/docs/ai/realtime/audio/#images) provide context for the next turn

Manual turns

Full feature support

`turn_detection=False` plus [commit/create verbs](https://pydantic.dev/docs/ai/realtime/turns/#push-to-talk)

Interruption/truncation

Full feature support

[`interrupt(played_ms=...)`](https://pydantic.dev/docs/ai/realtime/turns/#barge-in) records the heard cutoff

Input transcription

Full feature support

[Dedicated model](https://pydantic.dev/docs/ai/realtime/audio/#input-transcription); `'auto'` by default

Native tools

Unsupported

Configure [local fallbacks](https://pydantic.dev/docs/ai/realtime/tools/#native-tools) for web capabilities

Usage

Full feature support

Token, audio, and cache breakdowns

Reconnection

Full feature support

Pydantic AI [replays completed local history](https://pydantic.dev/docs/ai/realtime/lifecycle/#state-restoration); in-flight media is lost

See [Audio, images, and transcripts](https://pydantic.dev/docs/ai/realtime/audio/), [Turns and interruptions](https://pydantic.dev/docs/ai/realtime/turns/), [Tools](https://pydantic.dev/docs/ai/realtime/tools/), and [Connection lifecycle](https://pydantic.dev/docs/ai/realtime/lifecycle/) for the provider-agnostic workflows.

## Gateway

To route through the [Pydantic AI Gateway](https://pydantic.dev/docs/ai/overview/gateway/), use a `gateway/`\-prefixed model string:

```python
from pydantic_ai import Agent

agent = Agent(instructions='You are a helpful voice assistant.')
realtime = agent.realtime('gateway/openai:gpt-realtime')
```

Credentials come from [`gateway_provider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.gateway.gateway_provider). OpenAI-compatible endpoints that expose the realtime protocol can also be supplied through an `OpenAIProvider`. See [Gateway trace propagation](https://pydantic.dev/docs/ai/realtime/observability/#gateway-trace-propagation).

## Provider-specific quirks

-   The provider connection has no resumable server handle. Automatic reconnect restores completed history by [replaying local messages](https://pydantic.dev/docs/ai/realtime/lifecycle/#state-restoration) into a new session.

---
