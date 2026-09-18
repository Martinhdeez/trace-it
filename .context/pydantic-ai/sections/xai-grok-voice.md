# [xAI Grok Voice](https://pydantic.dev/docs/ai/realtime/xai/)

# xAI Grok Voice

[`XaiRealtimeModel`](https://pydantic.dev/docs/ai/api/realtime/xai/#pydantic_ai.realtime.xai.XaiRealtimeModel) brings Grok Voice into the typed, server-side realtime agent loop. Start with the [realtime quickstart](https://pydantic.dev/docs/ai/realtime/overview/#quickstart) or the [text-to-audio example](https://pydantic.dev/docs/ai/examples/realtime/realtime-text-to-audio/).

## Setup

To use Grok Voice, install `pydantic-ai-slim` with the `xai-realtime` optional group. Alongside `xai-sdk`, the bundle includes the `openai` package, because Grok Voice's realtime API reuses the OpenAI Realtime protocol's event types:

-   [pip](#tab-panel-269)
-   [uv](#tab-panel-270)

Terminal

```bash
pip install "pydantic-ai-slim[xai-realtime]"
```

Terminal

```bash
uv add "pydantic-ai-slim[xai-realtime]"
```

Set `XAI_API_KEY` as described in the [xAI model documentation](https://pydantic.dev/docs/ai/models/xai/#configuration). Use `provider='xai'` or pass an [`XaiProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.xai.XaiProvider) with `api_key=`. Custom `api_host` is unsupported, and a provider constructed with only `xai_client=` cannot open the WebSocket because the connection requires the API key.

## Model names

Use a Grok Voice ID such as `grok-voice-latest` or a pinned `grok-voice-think-*` model. `grok-voice-latest` follows xAI's current flagship and can change underneath an application; pin a version when behavior must remain stable. Use the [official xAI voice documentation](https://docs.x.ai/developers/model-capabilities/audio/voice-agent) for the canonical model list.

## Settings

[`XaiRealtimeModelSettings`](https://pydantic.dev/docs/ai/api/realtime/xai/#pydantic_ai.realtime.xai.XaiRealtimeModelSettings) -- the realtime counterpart of [model run settings](https://pydantic.dev/docs/ai/core-concepts/agent/#model-run-settings) -- extends the [shared settings](https://pydantic.dev/docs/ai/realtime/overview/#shared-settings):

```python
from pydantic_ai.realtime.xai import XaiRealtimeModel, XaiRealtimeModelSettings

settings = XaiRealtimeModelSettings(
    xai_voice='eve',
    turn_detection={'sensitivity': 'low'},
    input_transcription_model='auto',
)
model = XaiRealtimeModel('grok-voice-latest', settings=settings)
```

`xai_voice` selects the provider voice; when unset, xAI picks its own server-side default (currently `eve`). For exact server-VAD threshold or automatic-response behavior, set `xai_turn_detection=` with [`ServerVAD`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.ServerVAD); it fully overrides shared [`turn_detection`](https://pydantic.dev/docs/ai/realtime/turns/#automatic-turn-detection). Set `turn_detection=False` for [push-to-talk](https://pydantic.dev/docs/ai/realtime/turns/#push-to-talk).

[Input transcription](https://pydantic.dev/docs/ai/realtime/audio/#input-transcription) defaults to `'auto'`. Unlike the incremental deltas described in [live captions](https://pydantic.dev/docs/ai/realtime/audio/#live-captions), xAI sends cumulative transcript snapshots that can revise earlier words, so caption UIs should render the full [`TranscriptUpdate.transcript`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.TranscriptUpdate.transcript) rather than append deltas.

### Reasoning

`grok-voice-latest` and `grok-voice-think-*` models support the shared [`thinking`](https://pydantic.dev/docs/ai/capabilities/thinking/) setting. The provider exposes only `'high'` and `'none'`: every enabled effort maps to `'high'`, while `False` maps to `'none'`. Other Grok Voice models ignore the setting.

## Feature support and limitations

Feature

Support

Notes

Audio format

Full feature support

Mono PCM16, 24 kHz input and output

Text output

Unsupported

Grok Voice always produces audio

Image input

Unsupported

Audio/text input only

Manual turns

Full feature support

`turn_detection=False` plus [commit/create verbs](https://pydantic.dev/docs/ai/realtime/turns/#push-to-talk)

Interruption

Limited parameter support

[`interrupt()`](https://pydantic.dev/docs/ai/realtime/turns/#barge-in) works; output truncation with `played_ms` does not

Input transcription

Full feature support

[Dedicated provider path](https://pydantic.dev/docs/ai/realtime/audio/#input-transcription); `'auto'` by default

Native tools

Unsupported

Configure [local fallbacks](https://pydantic.dev/docs/ai/realtime/tools/#native-tools) for web capabilities

Usage

Full feature support

Audio-token buckets and `billable_audio_seconds` in `RunUsage.details`

State-restoring reconnect

Full feature support

Native [resumption](#session-resumption) is automatic with a reconnect policy

See [Audio, images, and transcripts](https://pydantic.dev/docs/ai/realtime/audio/), [Turns and interruptions](https://pydantic.dev/docs/ai/realtime/turns/), [Tools](https://pydantic.dev/docs/ai/realtime/tools/), and [Connection lifecycle](https://pydantic.dev/docs/ai/realtime/lifecycle/) for the provider-agnostic workflows.

## Gateway

Grok Voice is not currently available through the [Pydantic AI Gateway](https://pydantic.dev/docs/ai/overview/gateway/). Connect through `provider='xai'` or an `XaiProvider`.

## Session resumption

With a [`ReconnectPolicy`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.ReconnectPolicy), xAI automatically enables native resumption for [state-restoring reconnects](https://pydantic.dev/docs/ai/realtime/lifecycle/#state-restoration): it restores prior turns and suppresses the provider's replay burst from the local event stream. The handle stays in memory and cannot resume in another process.

## Provider-specific quirks

-   Grok Voice always speaks: its profile reports `supports_text_output=False`, so `output_modality='text'` raises a `UserError` before connecting. Read the answer from the transcript on the `SpeechPart`.
-   xAI supports cancellation but not output truncation. Flush local playback and call `interrupt()` without `played_ms`.
-   The protocol resembles OpenAI Realtime, but feature support comes from the xAI model profile; avoid assuming every OpenAI behavior is available.

---
