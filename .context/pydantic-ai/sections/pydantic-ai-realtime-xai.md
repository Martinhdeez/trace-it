# [pydantic_ai.realtime.xai](https://pydantic.dev/docs/ai/api/realtime/xai/)

# pydantic\_ai.realtime.xai

The xAI Grok Voice realtime API provider. Requires the `realtime`, `xai`, and `openai` optional groups (`pip install "pydantic-ai-slim[realtime,xai,openai]"`) -- `openai` because the model reuses the OpenAI Realtime codec, whose event types come from the OpenAI SDK.

xAI's realtime API is a clone of the OpenAI Realtime protocol, so [`XaiRealtimeModel`](https://pydantic.dev/docs/ai/api/realtime/xai/#pydantic_ai.realtime.xai.XaiRealtimeModel) reuses the OpenAI codec (event mapping, seeding, the WebSocket connection). Turn-taking uses the shared [`TurnDetection`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.TurnDetection) (or `False` for push-to-talk); for exact server-VAD control, `xai_turn_detection` accepts [`ServerVAD`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.ServerVAD) and fully overrides the shared setting. It diverges only where xAI does: it supports cancellation-based interruption but not output truncation, has no image input, and streams input transcription as cumulative snapshots that may revise earlier text, rather than as incremental deltas. Authentication comes from an [`XaiProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.xai.XaiProvider), mirroring [`XaiModel`](https://pydantic.dev/docs/ai/api/models/xai/#pydantic_ai.models.xai.XaiModel).

xAI Grok Voice realtime API provider for speech-to-speech sessions.

Connects to `wss://api.x.ai/v1/realtime` over a WebSocket. xAI's realtime API is a deliberate clone of the OpenAI Realtime protocol, so this provider reuses the OpenAI codec from [`pydantic_ai.realtime.openai`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai) -- event mapping, session seeding, tool conversion, server-VAD config, and the WebSocket connection itself -- and diverges only where xAI does:

-   the `session.update` shape (`voice`/`turn_detection` sit at the session top level, not nested under `audio` as on OpenAI's GA surface);
-   input audio transcription, delivered as cumulative `conversation.item.input_audio_transcription.updated` snapshots plus a final `.completed`, rather than OpenAI's incremental `.delta` events (see [`map_event`](https://pydantic.dev/docs/ai/api/realtime/xai/#pydantic_ai.realtime.xai.map_event));
-   native conversation resumption when a reconnect policy is configured: the provider-assigned `conversation.id` is reused and its replay burst is suppressed from local history;
-   no output truncation (`conversation.item.truncate` is unsupported), so [`RealtimeModelProfile.supports_output_truncation`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile.supports_output_truncation) is `False` while cancellation-based interruption still works;
-   no text output -- the API has no response-modality control and always speaks -- so [`RealtimeModelProfile.supports_text_output`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile.supports_text_output) is `False` and `output_modality='text'` raises rather than silently coming back as audio.

Requires the `websockets` package (the `realtime` optional group), `xai-sdk` (the `xai` group, for [`XaiProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.xai.XaiProvider)), and `openai` (the `openai` group, whose SDK supplies the event types the shared OpenAI codec is built on):

pip install "pydantic-ai-slim\[xai-realtime\]"

### XaiRealtimeModelSettings

**Bases:** `RealtimeModelSettings`

Settings specific to xAI realtime models.

Grok Voice always produces audio, so its profile reports [`supports_text_output=False`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile.supports_text_output) and the inherited `output_modality='text'` is rejected up front rather than quietly ignored.

#### Attributes

##### xai\_voice

Voice used for audio output, e.g. `eve`, or a custom voice ID.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### xai\_turn\_detection

xAI-specific server-VAD configuration.

When present, this fully overrides the cross-provider `turn_detection` setting.

**Type:** `ServerVAD`

### XaiRealtimeConnection

**Bases:** `OpenAIRealtimeConnection`

A live WebSocket connection to the xAI Grok Voice realtime API.

Reuses [`OpenAIRealtimeConnection`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.OpenAIRealtimeConnection) for the shared wire protocol, while mapping xAI's cumulative input transcription and conversation lifecycle events and emitting the resumption replay controls captured during reconnect handshakes.

#### Attributes

##### conversation\_id

The xAI conversation ID used for native session resumption.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### set\_message\_history

```python
def set_message_history(message_history: Callable[[], Sequence[ModelMessage]]) -> None
```

Ignored: xAI restores the conversation itself, so replaying it would say everything twice.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### XaiRealtimeModel

**Bases:** `RealtimeModel`

xAI Grok Voice realtime API model.

Pass `provider='xai'` (the default, which reads `XAI_API_KEY`) or an [`XaiProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.xai.XaiProvider) constructed with `api_key=`. A custom `api_host` is not supported, and a provider constructed only with `xai_client=` cannot be used because the WebSocket connection needs access to the API key. The realtime WebSocket URL is `wss://api.x.ai/v1/realtime`.

#### Constructor Parameters

**`model`** : `XaiRealtimeModelName`

The model name, e.g. `grok-voice-latest` (which tracks the current model) or a pinned version like `grok-voice-think-fast-1.0`. The `model` query parameter is required by the server, which otherwise falls back to a default silently.

**`provider`** : `Provider`\[`AsyncClient`\] | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'xai'`

The provider to use for authentication and the base URL. Defaults to `'xai'`.

**`settings`** : `RealtimeModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

[Model settings](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings) used as defaults for realtime sessions. A [`reconnect`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings.reconnect) policy enables xAI's native session resumption: prior turns are restored when reconnecting within xAI's resumption window (reportedly ~30 minutes).

**`profile`** : `RealtimeModelProfileSpec` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional override for the [realtime model profile](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile), merged over the provider's -- a partial dict, or a callable taking the resolved profile and returning the one to use. Mirrors `profile=` on a standard [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model), and is the escape hatch when a model name doesn't identify the model (e.g. an Azure deployment named something other than its model).

### map\_conversation\_event

```python
def map_conversation_event(
    data: dict[str, Any],
    *,
    replayed: bool | None = None,
) -> ConversationCreated | ConversationItemCreated | None
```

Map xAI's conversation handshake and item lifecycle events to codec control events.

#### Returns

`ConversationCreated` | `ConversationItemCreated` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### map\_event

```python
def map_event(data: dict[str, Any]) -> RealtimeCodecEvent | None
```

Map a raw xAI Grok Voice realtime event to a [`RealtimeCodecEvent`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeCodecEvent).

xAI clones the OpenAI Realtime protocol, so most events map identically via the OpenAI codec. The first exception is input audio transcription: xAI emits cumulative `conversation.item.input_audio_transcription.updated` snapshots (which may retroactively _correct_ earlier text -- `'Hello?'` becomes `'Hello, my name is'`) plus cumulative `.completed` snapshots, rather than OpenAI's incremental `.delta`. The partials are surfaced as cumulative [`InputTranscript`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.InputTranscript)s so a live transcript can render the user's words as they are spoken; the session adopts each snapshot wholesale, appending when it merely extends and replacing when xAI revises itself. The shared codec still drops interim `.completed` snapshots. The other exception is xAI's conversation lifecycle events, which are surfaced as codec control events so the connection can capture `conversation.id` and the session can suppress resume replay.

#### Returns

`RealtimeCodecEvent` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

---
