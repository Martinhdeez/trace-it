# [pydantic_ai.realtime.openai](https://pydantic.dev/docs/ai/api/realtime/openai/)

# pydantic\_ai.realtime.openai

The OpenAI Realtime API provider. Requires the `realtime` and `openai` optional groups (`pip install "pydantic-ai-slim[realtime,openai]"`).

[`OpenAIRealtimeModelSettings`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.OpenAIRealtimeModelSettings) configures the session, including shared turn-taking via [`TurnDetection`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.TurnDetection) (or `False` for push-to-talk). For finer control, `openai_turn_detection` accepts [`ServerVAD`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.ServerVAD) or [`SemanticVAD`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.SemanticVAD) and fully overrides the shared setting. Resilience comes from the `reconnect` setting: a [`ReconnectPolicy`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.ReconnectPolicy) in [`RealtimeModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings).

OpenAI Realtime API provider for speech-to-speech sessions.

Connects to `wss://api.openai.com/v1/realtime` over a WebSocket and maps the OpenAI event protocol to the shared realtime event types.

Requires the `websockets` and `openai` packages, available via the `realtime` and `openai` optional groups:

pip install "pydantic-ai-slim\[openai-realtime\]"

### OpenAIRealtimeModelSettings

**Bases:** `RealtimeModelSettings`

Settings specific to OpenAI realtime models.

#### Attributes

##### openai\_voice

Voice used for audio output, e.g. `alloy` or `VoiceID(id='voice_1234')`.

The known prebuilt names provide autocomplete, while any string and the OpenAI SDK's custom `VoiceID` form (`openai.types.realtime.realtime_audio_config_output.VoiceID`) are also accepted.

**Type:** `KnownOpenAIRealtimeVoiceName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `VoiceID`

##### openai\_input\_noise\_reduction

Noise reduction tuned for `near_field` (headset) or `far_field` (laptop/conference) microphones.

Absent disables it.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['near\_field', 'far\_field'\]

##### openai\_output\_speed

Playback speed multiplier for generated audio (0.25-1.5).

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

##### openai\_turn\_detection

OpenAI-specific server or semantic VAD configuration.

When present, this fully overrides the cross-provider `turn_detection` setting.

**Type:** `ServerVAD` | `SemanticVAD`

##### openai\_truncation

How the session truncates conversation context once it exceeds the model's window.

`'auto'` (the server default) drops the oldest turns; `'disabled'` keeps everything (and errors when the window is full); a `retention_ratio` truncation (`\{'type': 'retention_ratio', 'retention_ratio': 0.8\}`) keeps a fixed fraction, holding the prompt-cached prefix stable across turns (cached audio is far cheaper). This is the OpenAI SDK's `truncation` shape, forwarded as-is.

**Type:** `RealtimeTruncationParam`

### ServerVAD

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Server-side voice activity detection -- the default turn-taking mode.

The server detects when the user starts and stops speaking and (by default) commits the audio and triggers a response automatically. Unset fields fall back to the provider defaults.

#### Attributes

##### type

The turn-detection type. Must be `'server_vad'`.

**Type:** [`Required`](https://docs.python.org/3/library/typing.html#typing.Required)\[[`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['server\_vad'\]\]

##### threshold

Activation threshold (0.0-1.0). Higher requires louder audio; better in noisy environments. Defaults to the provider default.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

##### prefix\_padding\_ms

Audio to include before detected speech, in milliseconds. Defaults to the provider default.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### silence\_duration\_ms

Silence required to detect the end of speech, in milliseconds. Defaults to the provider default.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### create\_response

Whether to automatically generate a response when the user stops speaking. Defaults to `True`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### interrupt\_response

Whether to interrupt an in-progress response when the user starts speaking. Defaults to `True`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### idle\_timeout\_ms

If set, auto-trigger a response after this much idle time with no detected speech. Defaults to the provider default.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

### SemanticVAD

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Model-based semantic turn detection -- uses a model to decide when the user is done speaking.

#### Attributes

##### type

The turn-detection type. Must be `'semantic_vad'`.

**Type:** [`Required`](https://docs.python.org/3/library/typing.html#typing.Required)\[[`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['semantic\_vad'\]\]

##### eagerness

How eagerly the model responds. Defaults to `'auto'`; `low` waits longer and `high` responds sooner.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['low', 'medium', 'high', 'auto'\]

##### create\_response

Whether to automatically generate a response when a turn ends. Defaults to `True`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### interrupt\_response

Whether to interrupt an in-progress response when the user starts speaking. Defaults to `True`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### OpenAIRealtimeConnection

**Bases:** `RealtimeConnection`

A live WebSocket connection to the OpenAI Realtime API.

#### Attributes

##### message\_history

The call so far, when a session has offered it for replay on reconnect.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[\], [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### send

`@async`

```python
def send(content: RealtimeInput) -> None
```

Send content to the OpenAI Realtime API.

Accepts `BinaryAudio` (raw PCM16, 24kHz, mono), a `str` text turn, `TextContext` (text added without soliciting a reply), `BinaryImage`, `ToolResult`, and the control verbs `CommitAudio`, `ClearAudio`, `CreateResponse`, `CancelResponse`, and `TruncateOutput`.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### OpenAIRealtimeModel

**Bases:** `RealtimeModel`

OpenAI Realtime API model.

Authentication and the base URL come from a [`Provider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.Provider), mirroring [`OpenAIChatModel`](https://pydantic.dev/docs/ai/api/models/openai/#pydantic_ai.models.openai.OpenAIChatModel). Pass `provider='openai'` (the default) to read `OPENAI_API_KEY` / `OPENAI_BASE_URL` from the environment, or an [`OpenAIProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.openai.OpenAIProvider) instance for a custom key or base URL. The realtime transport is opened separately with `websockets`, so the provider's `httpx` client is not used for the WebSocket connection. The realtime WebSocket URL is derived from the provider's base URL (e.g. `https://api.openai.com/v1/` → `wss://api.openai.com/v1/realtime`), so OpenAI-compatible endpoints that expose a realtime API work too.

#### Constructor Parameters

**`model`** : `OpenAIRealtimeModelName`

The model name, e.g. `gpt-realtime` or `gpt-realtime-2.1-mini`.

**`provider`** : `Provider`\[`AsyncOpenAI`\] | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'openai'`

The provider to use for authentication and the base URL. Defaults to `'openai'`. Azure OpenAI is not supported (its realtime endpoint uses a different URL and auth scheme).

**`settings`** : `RealtimeModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

[Model settings](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings) used as defaults for realtime sessions.

**`profile`** : `RealtimeModelProfileSpec` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional override for the [realtime model profile](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile), merged over the provider's -- a partial dict, or a callable taking the resolved profile and returning the one to use. Mirrors `profile=` on a standard [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model), and is the escape hatch when a model name doesn't identify the model (e.g. an Azure deployment named something other than its model).

#### Attributes

##### client

The underlying [`AsyncOpenAI`](https://github.com/openai/openai-python) client from the provider.

**Type:** `AsyncOpenAI`

### map\_event

```python
def map_event(data: dict[str, Any]) -> RealtimeCodecEvent | None
```

Map a raw OpenAI Realtime event to a [`RealtimeCodecEvent`](https://pydantic.dev/docs/ai/api/realtime/codec/#pydantic_ai.realtime.codec.RealtimeCodecEvent).

Returns `None` for events that carry no session-relevant content (e.g. `session.created`).

#### Returns

`RealtimeCodecEvent` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### KnownOpenAIRealtimeVoiceName

The prebuilt voices OpenAI's realtime API ships, mirroring the `openai` SDK's own `Voice` union.

The [`openai_voice`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.OpenAIRealtimeModelSettings.openai_voice) setting also accepts any other string, so a voice OpenAI adds later works before this list catches up; a test pins the list against the SDK so it doesn't silently fall behind.

**Default:** `TypeAliasType('KnownOpenAIRealtimeVoiceName', Literal['alloy', 'ash', 'ballad', 'cedar', 'coral', 'echo', 'marin', 'sage', 'shimmer', 'verse'])`

---
