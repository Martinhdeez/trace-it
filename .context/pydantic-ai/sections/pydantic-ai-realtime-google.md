# [pydantic_ai.realtime.google](https://pydantic.dev/docs/ai/api/realtime/google/)

# pydantic\_ai.realtime.google

The Gemini Live API provider. Requires the `google` optional group (`pip install "pydantic-ai-slim[google]"`).

[`GoogleRealtimeModel`](https://pydantic.dev/docs/ai/api/realtime/google/#pydantic_ai.realtime.google.GoogleRealtimeModel) runs over the `google-genai` SDK (which manages the WebSocket transport). Gemini expects **16 kHz** PCM input (output is 24 kHz), produces one response modality per session, and natively accepts live video frames sent as [`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage). It exposes Gemini Live's session and generation configuration through [`GoogleRealtimeModelSettings`](https://pydantic.dev/docs/ai/api/realtime/google/#pydantic_ai.realtime.google.GoogleRealtimeModelSettings) -- shared turn-taking via [`TurnDetection`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.TurnDetection), with finer Gemini-specific control via [`AutomaticVAD`](https://pydantic.dev/docs/ai/api/realtime/google/#pydantic_ai.realtime.google.AutomaticVAD) in `google_vad` plus `google_activity_handling`/`google_turn_coverage`, voice via `google_voice` or a [`MultiSpeaker`](https://pydantic.dev/docs/ai/api/realtime/google/#pydantic_ai.realtime.google.MultiSpeaker) in `google_multi_speaker`, and long-session [`ContextCompression`](https://pydantic.dev/docs/ai/api/realtime/google/#pydantic_ai.realtime.google.ContextCompression) -- with resilience via session resumption + a [`ReconnectPolicy`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.ReconnectPolicy) in the `reconnect` setting.

Gemini Live API provider for realtime speech-to-speech (and live video) sessions.

Built on the `google-genai` SDK, which manages the WebSocket transport for you. Available via the `google` optional group:

pip install "pydantic-ai-slim\[google-realtime\]"

Unlike the OpenAI provider, Gemini wants **16 kHz** PCM input audio (output is 24 kHz), produces a single response modality per session (audio _or_ text), and natively accepts a stream of video frames sent as [`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage).

Use `provider='google'` for the Gemini Developer API, or `provider='google-cloud'` / [`GoogleCloudProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.google_cloud.GoogleCloudProvider) for Google Cloud with Application Default Credentials.

### AutomaticVAD

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Server-side voice activity detection -- the default turn-taking mode for Gemini Live.

#### Attributes

##### disabled

Turn off automatic VAD entirely. Defaults to `False`.

Do not set this through `RealtimeSession`: Pydantic AI does not expose Gemini activity markers or manual turn controls. Use automatic VAD instead; the shared `turn_detection=False` setting is rejected for the same reason.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### start\_sensitivity

How readily speech onset is detected. `high` triggers on quieter audio; `low` is stricter. Defaults to the provider default.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['high', 'low'\]

##### end\_sensitivity

How readily the end of speech is detected. `high` ends turns sooner; `low` waits longer. Defaults to the provider default.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['high', 'low'\]

##### prefix\_padding\_ms

Audio to include before detected speech, in milliseconds. Defaults to the provider default.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### silence\_duration\_ms

Silence required to detect the end of speech, in milliseconds. Defaults to the provider default.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

### MultiSpeaker

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Assign prebuilt voices to named speakers for multi-speaker audio output.

#### Attributes

##### voices

Mapping of speaker label to prebuilt voice name, e.g. `{'Joe': 'Puck', 'Jane': 'Kore'}`. Defaults to an empty mapping.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

### ContextCompression

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Sliding-window context compression so long sessions don't exceed the context window.

#### Attributes

##### trigger\_tokens

Compress once the context passes this many tokens. Defaults to the provider default.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### target\_tokens

Target size (in tokens) of the retained sliding window after compression. Defaults to the provider default.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

### GoogleRealtimeModelSettings

**Bases:** `RealtimeModelSettings`

Settings used for a Gemini Live session.

#### Attributes

##### temperature

Amount of randomness injected into the response.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

##### top\_p

Nucleus sampling probability mass.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

##### top\_k

Only sample from the top K options for each subsequent token.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### seed

The random seed to use for the session.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### google\_thinking\_config

The thinking configuration to use for the model.

**Type:** `genai_types.ThinkingConfigDict`

##### google\_video\_resolution

The video resolution to use for the model.

**Type:** `genai_types.MediaResolution`

##### google\_language\_code

BCP-47 language code for audio output.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### google\_voice

Prebuilt voice used for audio output, e.g. `Puck`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### google\_multi\_speaker

Per-speaker voice assignments; takes precedence over `google_voice`.

**Type:** `MultiSpeaker`

##### google\_affective\_dialog

Whether to enable emotion-aware delivery (native-audio models only).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### google\_proactive\_audio

Whether the model may decide _when_ to respond, including staying silent on input not addressed to it (native-audio models only). Useful for "react to the camera" experiences.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### google\_input\_transcription

Whether to transcribe input audio. Defaults to `True`.

When `False`, user turns are recorded as retained audio when available, or as content-less placeholders otherwise. Takes precedence over the shared [`input_transcription_model`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings.input_transcription_model), whose `None` also turns transcription off here.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### google\_output\_transcription

Whether to transcribe output audio. Defaults to `True`.

When `False`, retain output audio if assistant audio turns need to appear in history. Assistant audio without a transcript cannot be handed off or seeded.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### google\_transcription\_language\_codes

Language hints applied to input and output transcription.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### google\_vad

Gemini-specific server-side voice activity detection settings.

When present, this fully overrides the cross-provider `turn_detection` setting. `google_vad={'disabled': True}` raises a `UserError`, like `turn_detection=False`: Pydantic AI does not expose Gemini activity markers or manual turn controls, so the resulting session could not drive turns.

**Type:** `AutomaticVAD`

##### google\_activity\_handling

Whether detected user activity interrupts the model.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['interrupts', 'no\_interruption'\]

##### google\_turn\_coverage

Which realtime input is attached to a turn -- `'activity_only'`, `'all_input'` (everything between turns too), or `'all_video'` (all video frames plus audio during activity; ideal for live-camera use). Absent uses the provider default.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['activity\_only', 'all\_input', 'all\_video'\]

##### google\_context\_compression

Sliding-window context compression for long-running sessions.

**Type:** `ContextCompression`

##### google\_config\_overrides

Raw values merged last into the Google `LiveConnectConfig`.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### google\_enable\_session\_resumption

Whether to request session-resumption handles, which let a re-dial restore the server-side conversation.

When absent, handles are requested exactly when a [`reconnect`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings.reconnect) policy is set. An explicit `False` cannot be combined with a `reconnect` policy: a re-dial without resumption would lose the conversation, so `connect` raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) rather than silently reconnecting into a model that remembers nothing.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### google\_async\_tool\_calls

Whether tool calls may run without pausing the model's speech. Defaults to `False`.

By default Gemini stops generating while a tool call is outstanding, so the caller hears silence for as long as the tool takes. Enabling this declares tools `NON_BLOCKING` and returns their results with `INTERRUPT` scheduling, so the model keeps talking (typically narrating what it's doing) and the result cuts into that speech when it arrives.

This pays off for tools that take a noticeable moment. It is a poor trade for fast tools: the result interrupts a reply the model has barely started, leaving an extra interrupted turn in history with nothing in it. Verified live against `gemini-2.5-flash-native-audio-latest`.

Supported by Gemini native-audio models (see [`supports_async_tool_calls`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile.supports_async_tool_calls)). Other models silently ignore it.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### GoogleRealtimeModel

**Bases:** `RealtimeModel`

Gemini Live API model.

Session and generation configuration is read from [`GoogleRealtimeModelSettings`](https://pydantic.dev/docs/ai/api/realtime/google/#pydantic_ai.realtime.google.GoogleRealtimeModelSettings), passed through `settings` as model-level defaults or as `model_settings` when opening a session.

Authentication and the underlying `google-genai` client come from a [`Provider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.Provider), mirroring [`GoogleModel`](https://pydantic.dev/docs/ai/api/models/google/#pydantic_ai.models.google.GoogleModel). Pass `provider='google'` (the default) for the Gemini Developer API (reads `GOOGLE_API_KEY` / `GEMINI_API_KEY`), `provider='google-cloud'` for Vertex AI (Application Default Credentials, useful where org policy disallows API keys), or a [`GoogleProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.google.GoogleProvider) / [`GoogleCloudProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.google_cloud.GoogleCloudProvider) instance for a custom key, client, or region. Gemini Live is available on both surfaces.

#### Constructor Parameters

**`model`** : `GoogleRealtimeModelName`

The model name, e.g. `gemini-2.5-flash-native-audio-latest` (an alias that tracks the newest native-audio Live model) or `gemini-3.1-flash-live-preview`.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['google', 'google-cloud', 'gateway'\] | `Provider`\[`Client`\] _Default:_ `'google'`

The provider to use for authentication and API access -- `'google'` (Gemini Developer API, the default) or `'google-cloud'` (Vertex AI), or a `Provider` instance.

**`settings`** : `RealtimeModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-level defaults for session and generation configuration.

**`profile`** : `RealtimeModelProfileSpec` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional override for the [realtime model profile](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile), merged over the provider's -- a partial dict, or a callable taking the resolved profile and returning the one to use. Mirrors `profile=` on a standard [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model), and is the escape hatch when a model name doesn't identify the model (e.g. an Azure deployment named something other than its model).

#### Attributes

##### client

The underlying `google.genai.Client` from the provider.

**Type:** `Client`

### GoogleRealtimeConnection

**Bases:** `RealtimeConnection`

A live connection to the Gemini Live API, backed by a `google-genai` session.

#### Methods

##### send

`@async`

```python
def send(content: RealtimeInput) -> None
```

Send content to the Gemini Live API.

Accepts `BinaryAudio` (raw PCM16, 16kHz, mono), a `str` text turn, `TextContext` (text sent with `turn_complete=False`, so it waits for the next turn), `BinaryImage` (a live video frame), and `ToolResult`. The manual turn-taking verbs are not supported (Gemini uses automatic VAD).

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### INPUT\_SAMPLE\_RATE

Sample rate (Hz) Gemini expects for PCM16 input audio.

**Default:** `16000`

---
