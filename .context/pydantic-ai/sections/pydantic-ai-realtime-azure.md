# [pydantic_ai.realtime.azure](https://pydantic.dev/docs/ai/api/realtime/azure/)

# pydantic\_ai.realtime.azure

The Azure OpenAI realtime model reuses the OpenAI Realtime codec and connection, authenticates with [`AzureProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.azure.AzureProvider), and so needs the `realtime` and `openai` optional groups (`pip install "pydantic-ai-slim[realtime,openai]"`).

Azure realtime support using the OpenAI GA or Azure AI Voice Live protocol.

### AzureRealtimeModelProfile

**Bases:** `RealtimeModelProfile`

A [`RealtimeModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile) with the Azure-specific facts.

Read via [`AzureRealtimeModel.profile`](https://pydantic.dev/docs/ai/api/realtime/azure/#pydantic_ai.realtime.azure.AzureRealtimeModel). Pass a partial one as `profile=` to correct what's inferred from a deployment name that doesn't match its model.

#### Attributes

##### azure\_realtime\_apis

Which Azure realtime APIs serve this model, when only one does -- the constraint that routes it.

A model served only by Voice Live carries `{'voice_live'}` and routes there automatically; a GA-only model carries `{'azure_openai'}` and rejects [`azure_voice_live=True`](https://pydantic.dev/docs/ai/api/realtime/azure/#pydantic_ai.realtime.azure.AzureRealtimeModelSettings.azure_voice_live). Absent for a model served by _both_ (e.g. `gpt-realtime`) or a name the table below doesn't recognize (e.g. a future `gpt-realtime-3`): either way it defaults to GA and reaches Voice Live only when `azure_voice_live=True` is set. Pass a `profile=` override to constrain a deployment named after something the table can't place.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[`AzureRealtimeApi`\]

### AzureRealtimeConnection

**Bases:** `OpenAIRealtimeConnection`

A live WebSocket connection to Azure OpenAI's realtime API.

Reuses [`OpenAIRealtimeConnection`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.OpenAIRealtimeConnection) for the shared GA wire protocol, naming Azure as the vendor so a connection that drops or rejects content doesn't send someone debugging an Azure session to OpenAI's status page.

### AzureTokenCredential

**Bases:** [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Structural type for a synchronous Microsoft Entra ID token credential.

### AzureRealtimeModelSettings

**Bases:** `OpenAIRealtimeModelSettings`

Settings specific to Azure realtime models.

This inherits every [`OpenAIRealtimeModelSettings`](https://pydantic.dev/docs/ai/api/realtime/openai/#pydantic_ai.realtime.openai.OpenAIRealtimeModelSettings) field, but when [`azure_voice_live`](https://pydantic.dev/docs/ai/api/realtime/azure/#pydantic_ai.realtime.azure.AzureRealtimeModelSettings.azure_voice_live) is set the Voice Live session config is built from only the cross-protocol fields -- `instructions`, `openai_voice` (by name), `turn_detection` (or `azure_voice_live_turn_detection`), `input_transcription_model`, `output_modality`, `max_tokens`, `tool_choice`, and tools. The inherited `openai_*` fields, plus `thinking` and `parallel_tool_calls`, are **silently ignored** under Voice Live; they still apply on the GA path.

They fall into two groups, and only the first is settled:

-   `openai_output_speed`, `openai_turn_detection`, `thinking`, and `parallel_tool_calls` have no counterpart in Voice Live's beta session object (see the recorded `session.created` payload in `tests/realtime/cassettes/test_azure_voice_live_ws/`), so there is nothing to map them to. Voice Live's own turn detection is configured with `azure_voice_live_turn_detection`.
-   `openai_input_noise_reduction` and `openai_truncation` _do_ have counterparts -- `input_audio_noise_reduction` and `truncation_strategy` -- but under Azure's own vocabulary, which the recording pins as `null` and so does not evidence. Mapping OpenAI's values onto them would be guessing at the accepted shape, so they stay unmapped until a recording proves it; a dedicated `azure_voice_live_*` setting is the natural home when it does.

#### Attributes

##### azure\_voice\_live

Use the Azure AI Voice Live endpoint and beta session protocol instead of the GA endpoint.

Voice Live is a distinct Azure resource; [`AzureProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.azure.AzureProvider) reads its `AZURE_VOICELIVE_ENDPOINT` / `AZURE_VOICELIVE_API_KEY` / `AZURE_VOICELIVE_API_VERSION` credentials as a fallback to the `AZURE_OPENAI_*` variables.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### azure\_voice\_live\_turn\_detection

Voice Live server or semantic VAD config; only applies when `azure_voice_live=True`.

**Type:** `ServerVAD` | `SemanticVAD`

### AzureRealtimeModel

**Bases:** `OpenAIRealtimeModel`

Azure realtime model using the OpenAI GA protocol or Azure AI Voice Live.

The existing [`AzureProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.azure.AzureProvider) supplies the Azure resource endpoint and API key. The WebSocket transport does not use its OpenAI SDK client or `api_version`. By default it connects to the GA `/openai/v1/realtime` endpoint; set [`azure_voice_live`](https://pydantic.dev/docs/ai/api/realtime/azure/#pydantic_ai.realtime.azure.AzureRealtimeModelSettings.azure_voice_live) to connect to `/voice-live/realtime` with the Voice Live beta session protocol. Both use an `api-key` header.

Pass a Microsoft Entra ID `credential` (e.g. `azure.identity.DefaultAzureCredential()`) to authenticate every request to the resource -- the realtime WebSocket session _and_ the browser WebRTC signaling calls -- with a bearer token instead of the `api-key` (needed when the resource is locked to managed identity). For browser WebRTC the browser still only ever receives the short-lived ephemeral secret, never the Entra token or the API key.

A model served only by Voice Live (e.g. the cascade chat models like `gpt-5`, or `phi4-mm-realtime`) routes there automatically; a model served by both defaults to GA and needs `azure_voice_live=True` for Voice Live; a GA-only model rejects the setting. See [`AzureRealtimeModelProfile.azure_realtime_apis`](https://pydantic.dev/docs/ai/api/realtime/azure/#pydantic_ai.realtime.azure.AzureRealtimeModelProfile.azure_realtime_apis).

#### Attributes

##### profile

The Azure realtime profile, with the model's serving APIs and minus what Voice Live can't do.

Stamps [`azure_realtime_apis`](https://pydantic.dev/docs/ai/api/realtime/azure/#pydantic_ai.realtime.azure.AzureRealtimeModelProfile.azure_realtime_apis) for a recognized model (a `profile=` override wins), which routes between the GA API and Voice Live. And because Voice Live negotiates WebRTC over its own WebSocket control channel rather than the GA signaling endpoints this model inherits, a model configured for Voice Live reports no WebRTC support and the signaling methods refuse. Voice Live selected per session instead can't be seen from here, so those calls still refuse at the point of use.

**Type:** `RealtimeModelProfile`

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model: AzureRealtimeModelName,
    *,
    provider: Provider[AsyncOpenAI] | str = 'azure',
    settings: RealtimeModelSettings | None = None,
    profile: RealtimeModelProfileSpec | None = None,
    credential: AzureTokenCredential | None = None,
) -> None
```

Create an Azure OpenAI realtime model.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`model`** : `AzureRealtimeModelName`

The Azure _deployment_ name, which is what the realtime URL and the profile lookup use. Azure deployments are conventionally named after their model; when yours isn't, `profile` is how to correct the facts inferred from the name.

**`provider`** : `Provider`\[`AsyncOpenAI`\] | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'azure'`

The provider supplying the resource endpoint and API key. Defaults to `'azure'`.

**`settings`** : `RealtimeModelSettings` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

[Model settings](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings) used as defaults for realtime sessions.

**`profile`** : `RealtimeModelProfileSpec` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional override for the [realtime model profile](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelProfile), merged over the provider's -- a partial dict, or a callable taking the resolved profile and returning the one to use.

**`credential`** : `AzureTokenCredential` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional Microsoft Entra ID credential. When set, realtime requests use its bearer tokens instead of the resource API key.

### AzureRealtimeApi

An Azure realtime speech-to-speech API a model can be reached through: the Azure OpenAI GA realtime API (`/openai/v1/realtime`) or [Azure AI Voice Live](https://learn.microsoft.com/azure/ai-services/speech-service/voice-live) (`/voice-live/realtime`, selected with [`azure_voice_live=True`](https://pydantic.dev/docs/ai/api/realtime/azure/#pydantic_ai.realtime.azure.AzureRealtimeModelSettings.azure_voice_live)).

**Default:** `Literal['azure_openai', 'voice_live']`

---
