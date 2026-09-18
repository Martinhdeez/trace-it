# [pydantic_ai.providers](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/)

# pydantic\_ai.providers

### Provider

**Bases:** `ABC`, `Generic[InterfaceClient]`

Abstract class for a provider.

The provider is in charge of providing an authenticated client to the API.

Each provider only supports a specific interface. An interface can be supported by multiple providers.

For example, the `OpenAIChatModel` interface can be supported by the `OpenAIProvider` and the `DeepSeekProvider`.

When used as an async context manager, providers that create their own HTTP client will close it on exit. This is handled automatically when using [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent) as a context manager.

#### Attributes

##### name

The provider name.

The returned value flows into [`ModelMessage.provider_name`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage) on every part. Thinking-tag detection and native-tool detection check this value when the model class loads history, so silently renaming a concrete `name` value breaks replay of any message history captured against the old name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### model\_id\_namespace

The namespace used to fully qualify model IDs routed through this provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### base\_url

The base URL for the provider API.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### client

The client for the provider.

**Type:** `InterfaceClient`

#### Methods

##### model\_profile

`@staticmethod`

```python
def model_profile(model_name: str) -> ModelProfile | None
```

The model profile for the named model, if available.

###### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### realtime\_model\_profile

`@staticmethod`

```python
def realtime_model_profile(model_name: str) -> RealtimeModelProfile | None
```

The realtime model profile for the named model, if available.

###### Returns

`RealtimeModelProfile` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### infer\_provider

```python
def infer_provider(provider: str) -> Provider[Any]
```

Infer the provider from the provider name.

#### Returns

`Provider`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

### infer\_provider\_class

```python
def infer_provider_class(provider: str) -> type[Provider[Any]]
```

Infers the provider class from the provider name.

#### Returns

[`type`](https://docs.python.org/3/glossary.html#term-type)\[`Provider`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]

### gateway\_provider

```python
def gateway_provider(
    upstream_provider: Literal['openai', 'openai-chat', 'openai-responses', 'chat', 'responses'],
    /,
    *,
    route: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    http_client: AsyncHTTPClient | None = None,
) -> Provider[AsyncOpenAI]
def gateway_provider(
    upstream_provider: Literal['groq'],
    /,
    *,
    route: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> Provider[AsyncGroq]
def gateway_provider(
    upstream_provider: Literal['anthropic'],
    /,
    *,
    route: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    http_client: httpx2.AsyncClient | None = None,
) -> Provider[AsyncAnthropicClient]
def gateway_provider(
    upstream_provider: Literal['bedrock', 'converse'],
    /,
    *,
    route: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> Provider[BaseClient]
def gateway_provider(
    upstream_provider: Literal['google', 'google-cloud'],
    /,
    *,
    route: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    http_client: AsyncHTTPClient | None = None,
) -> Provider[GoogleClient]
def gateway_provider(
    upstream_provider: str,
    /,
    *,
    route: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> Provider[Any]
```

Create a new Gateway provider.

#### Returns

`Provider`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

#### Parameters

**`upstream_provider`** : `UpstreamProvider` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The upstream provider to use.

**`route`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The name of the provider or gateway endpoint to use to handle the request. If not provided, the default gateway endpoint for the API format will be used.

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication. If not provided, the `PYDANTIC_AI_GATEWAY_API_KEY` environment variable will be used if available.

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base URL to use for the Gateway. If not provided, the `PYDANTIC_AI_GATEWAY_BASE_URL` environment variable will be used if available. Otherwise, it is inferred from the API key's region, e.g. `https://gateway-us.pydantic.dev/proxy`.

**`http_client`** : `AsyncHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The HTTP client to use for the Gateway.

### AnthropicProvider

**Bases:** `Provider[AsyncAnthropicClient]`

Provider for Anthropic API.

#### Methods

##### \_\_init\_\_

```python
def __init__(*, anthropic_client: AsyncAnthropicClient | None = None) -> None
def __init__(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    http_client: httpx2.AsyncClient | None = None,
) -> None
```

Create a new Anthropic provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `ANTHROPIC_API_KEY` environment variable will be used if available.

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base URL to use for the Anthropic API.

**`anthropic_client`** : `AsyncAnthropicClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing Anthropic client to use. Accepts [`AsyncAnthropic`](https://github.com/anthropics/anthropic-sdk-python), [`AsyncAnthropicBedrock`](https://platform.claude.com/docs/en/build-with-claude/claude-on-amazon-bedrock-legacy), [`AsyncAnthropicBedrockMantle`](https://platform.claude.com/docs/en/build-with-claude/claude-in-amazon-bedrock), [`AsyncAnthropicFoundry`](https://platform.claude.com/docs/en/build-with-claude/claude-in-microsoft-foundry), or [`AsyncAnthropicVertex`](https://docs.anthropic.com/en/api/claude-on-vertex-ai). If provided, the `api_key` and `http_client` arguments will be ignored.

**`http_client`** : `httpx2.AsyncClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` to use for making HTTP requests.

### BaseGoogleProvider

**Bases:** `Provider[Client]`, `ABC`

Common base for the Gemini API and Google Cloud providers.

Abstract -- instantiate [`GoogleProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.google.GoogleProvider) for the Gemini API or [`GoogleCloudProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.google_cloud.GoogleCloudProvider) for Google Cloud. Subclasses share `base_url`, `client`, `_set_http_client`, and model-profile lookup; each subclass owns its own `Client` construction.

### GoogleProvider

**Bases:** `BaseGoogleProvider`

Provider for the Gemini API (formerly Google AI Studio / Google GLA).

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    api_key: str | None = None,
    http_client: AsyncHTTPClient | None = None,
    base_url: str | None = None,
    retry_options: HttpRetryOptions | None = None,
) -> None
def __init__(*, client: Client) -> None
```

Create a new Google provider for the Gemini API.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The [API key](https://ai.google.dev/gemini-api/docs/api-key) to use for authentication. It can also be set via the `GOOGLE_API_KEY` environment variable, or the legacy `GEMINI_API_KEY` environment variable (`GOOGLE_API_KEY` takes precedence).

**`client`** : `Client` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A pre-initialized client to use. Stored as-is, so a client built for Google Cloud (`Client(vertexai=True, ...)`, or its current spelling `Client(enterprise=True, ...)`) is used on that transport even though `name` stays `'google'`. `GoogleModel` reads the transport off the client rather than the provider name, so it routes correctly either way.

**`http_client`** : `AsyncHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to use for making HTTP requests.

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base URL for the Gemini API.

**`retry_options`** : `HttpRetryOptions` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

HTTP retry options for transient errors (429, 5xx, etc.). See `google.genai.types.HttpRetryOptions` for available fields.

### GoogleCloudLocation

Regions available for Google Cloud. More details [here](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations#genai-locations).

This lists single-region values only. `GoogleCloudProvider` also accepts the `'global'` location and the `'us'`/`'eu'` multi-regions (routed to the `aiplatform.{us,eu}.rep.googleapis.com` data-residency endpoints) as separate union members on its `location` parameter.

**Default:** `Literal['asia-east1', 'asia-east2', 'asia-northeast1', 'asia-northeast3', 'asia-south1', 'asia-southeast1', 'australia-southeast1', 'europe-central2', 'europe-north1', 'europe-southwest1', 'europe-west1', 'europe-west2', 'europe-west3', 'europe-west4', 'europe-west6', 'europe-west8', 'europe-west9', 'me-central1', 'me-central2', 'me-west1', 'northamerica-northeast1', 'southamerica-east1', 'us-central1', 'us-east1', 'us-east4', 'us-east5', 'us-south1', 'us-west1', 'us-west4']`

### GoogleCloudProvider

**Bases:** `BaseGoogleProvider`

Provider for Google Cloud (formerly known as Vertex AI).

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    api_key: str | None = None,
    credentials: Credentials | None = None,
    project: str | None = None,
    location: GoogleCloudLocation | Literal['global', 'us', 'eu'] | str | None = None,
    client: Client | None = None,
    http_client: AsyncHTTPClient | None = None,
    base_url: str | None = None,
    retry_options: HttpRetryOptions | None = None,
) -> None
```

Create a new Google Cloud provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The [Vertex AI Express Mode API key](https://cloud.google.com/vertex-ai/generative-ai/docs/start/api-keys?usertype=expressmode) to use for authentication. It can also be set via the `GOOGLE_API_KEY` environment variable, or the legacy `GEMINI_API_KEY` environment variable (`GOOGLE_API_KEY` takes precedence). Explicit `credentials` use credential-based authentication instead. Explicit `project`/`location` use Application Default Credentials. `GOOGLE_APPLICATION_CREDENTIALS` takes precedence over an API key from the environment.

**`credentials`** : `Credentials` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The credentials to use for authentication when calling the Google Cloud APIs. Credentials can be obtained from environment variables and default credentials. For more information, see [Set up Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials). Credentials that require scopes are automatically scoped with `https://www.googleapis.com/auth/cloud-platform`.

**`project`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Google Cloud project ID to use for quota. Can be obtained from environment variables (for example, `GOOGLE_CLOUD_PROJECT`).

**`location`** : `GoogleCloudLocation` | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['global', 'us', 'eu'\] | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The location to send API requests to, for example `us-central1` (a single region) or `global`. `'us'` and `'eu'` are multi-region values routed to the `aiplatform.{us,eu}.rep.googleapis.com` data-residency endpoints. Model availability differs between single regions, multi-regions, and `global` -- see the [Vertex AI locations docs](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations#available-regions). Can be obtained from the `GOOGLE_CLOUD_LOCATION` environment variable.

**`client`** : `Client` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A pre-initialized client to use. Stored as-is without forcing `vertexai=True`, so a client built for the Gemini Developer API is used on that transport even though `name` stays `'google-cloud'`. `GoogleModel` reads the transport off the client rather than the provider name, so it routes correctly either way.

**`http_client`** : `AsyncHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to use for making HTTP requests.

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base URL for the Google Cloud API.

**`retry_options`** : `HttpRetryOptions` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

HTTP retry options for transient errors (429, 5xx, etc.). See `google.genai.types.HttpRetryOptions` for available fields.

### OpenAIProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for OpenAI API.

#### Methods

##### \_\_init\_\_

```python
def __init__(*, openai_client: AsyncOpenAI) -> None
def __init__(
    base_url: str | None = None,
    api_key: str | None = None,
    openai_client: None = None,
    http_client: _OpenAIHTTPClient | None = None,
) -> None
```

Create a new OpenAI provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base url for the OpenAI requests. If not provided, the `OPENAI_BASE_URL` environment variable will be used if available. Otherwise, defaults to OpenAI's base url.

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `OPENAI_API_KEY` environment variable will be used if available.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing [`AsyncOpenAI`](https://github.com/openai/openai-python?tab=readme-ov-file#async-usage) client to use. If provided, `base_url`, `api_key`, and `http_client` must be `None`.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to use for making HTTP requests.

OpenAI Codex subscription-auth provider: OAuth flow primitives, credential refresh, wire dialect.

Core owns the protocol primitives (PKCE context, authorization URL, code exchange, refresh) and, because the pinned redirect URI makes every login a localhost callback, the one-shot callback catcher (`exchange_code_from_callback()`); browser opening and persistent credential storage belong to applications and harnesses.

The authorization-code + PKCE redirect flow is the only login flow the public Codex client supports: its registration pins the redirect URI to `http://localhost:1455/auth/callback` (exact-match, probed live 2026-08-25), and the auth service serves no device-authorization endpoint. `exchange_code_from_callback()` serves this exact redirect URI and exchanges the authorization code.

### CredentialsRefreshError

**Bases:** `_CredentialsError`

Refreshing Codex credentials against the token endpoint failed.

When the underlying error is `invalid_grant`, the stored grant is no longer usable and a fresh authorization is required (locally: rerun `codex login`; in an app: rerun your connect flow).

#### Attributes

##### message

The error message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

##### model\_name

The name of the model associated with the error.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `model_name`

### CredentialsPersistenceError

**Bases:** `_CredentialsError`, `OpenAIError`

Rotated credentials were updated in memory but the persistence callback raised.

The in-memory credentials are current and were handed to the callback before it failed; the error surfaces so callers do not mistake a failed save for durability.

#### Attributes

##### message

The error message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `message`

##### model\_name

The name of the model associated with the error.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `model_name`

### OpenAICodexCredentials

Codex subscription credentials.

The tokens are excluded from `repr` so a logged or traceback-embedded instance does not leak them.

#### Methods

##### from\_codex\_cli\_auth

`@classmethod`

```python
def from_codex_cli_auth(cls, data: Mapping[str, Any]) -> Self
```

Parse the Codex CLI `~/.codex/auth.json` shape (`{'tokens': {...}}`).

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self)

### OpenAICodexCredentialSource

**Bases:** [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Application-owned storage for the credentials, so refreshed tokens outlive the process.

The provider owns the credential lifecycle (expiry checks, refresh, single-flight) and calls this only to read and write the stored set: `load()` on first use, and `save()` after tokens are refreshed.

Refresh tokens are single-use, so before refreshing, the provider re-reads storage with `load()` and adopts newer credentials if another process using the same store already refreshed them. That is best-effort, not mutual exclusion: two processes can still race between `load()` and `save()`.

Conformance is structural, but implementations are encouraged to subclass the protocol explicitly so type checkers verify the method signatures.

#### Methods

##### load

`@async`

```python
def load() -> OpenAICodexCredentials
```

Return the currently stored credentials.

###### Returns

`OpenAICodexCredentials`

##### save

`@async`

```python
def save(credentials: OpenAICodexCredentials) -> None
```

Durably replace the stored credentials with a freshly rotated set.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### OpenAICodexOAuthFlow

**Bases:** `OAuthFlow[OpenAICodexCredentials]`

Pure authorization-code + PKCE context for the OpenAI Codex public client.

This is the only login flow the public client supports (no device flow; redirect URI pinned to `localhost:1455`, probed exact-match). Construction does no I/O: build the context anywhere, send the user to `authorization_url()`, then let `exchange_code_from_callback()` receive the redirect on localhost and exchange its code. The browser and credential storage stay caller-owned.

#### Attributes

##### code\_challenge

The S256 PKCE challenge derived from `code_verifier`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### exchange\_code\_from\_callback

`@async`

```python
def exchange_code_from_callback() -> CredentialsT
```

Serve `redirect_uri` for one authorization callback, then exchange the received code.

Binds the host and port from `redirect_uri` with a one-shot local HTTP server, ignores requests that don't carry this flow's `state`, and raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) when the provider reports an authorization error instead of a code (e.g. the user clicked Deny). Callers wanting a time limit can wrap the call in [`anyio.fail_after`](https://anyio.readthedocs.io/en/stable/cancellation.html).

###### Returns

`CredentialsT`

##### \_\_init\_\_

```python
def __init__(*, redirect_uri: str = _REDIRECT_URI, state: str | None = None) -> None
```

Create a new flow context. Construction does no I/O.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`redirect_uri`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `_REDIRECT_URI`

Where the authorization code is delivered. The public client's registration pins this to `http://localhost:1455/auth/callback` (exact-match), so leave the default unchanged when using the public client.

**`state`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The CSRF token bound to the callback; auto-generated when `None`.

##### authorization\_url

```python
def authorization_url(
    *,
    scope: str | None = None,
    extra_params: Mapping[str, str] | None = None,
) -> str
```

The URL to send the user to. Note the public client pins redirects to localhost.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

###### Parameters

**`scope`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The OAuth scopes to request; `None` means the standard Codex login scopes.

**`extra_params`** : [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Additional query parameters, merged over the defaults (so they can also override them), except `client_id` and `redirect_uri`: `exchange_code()` always posts the public client id and the flow's `redirect_uri`, so overriding either here would make the authorization code unusable. The production Codex login's `id_token_add_organizations=true` and `codex_cli_simplified_flow=true` are sent by default: without the former, the `id_token` can omit the account id for multi-org accounts (live-verified 2026-08-25).

##### exchange\_code

`@async`

```python
def exchange_code(code: str) -> OpenAICodexCredentials
```

Exchange an authorization code for credentials (call this in your callback handler).

###### Returns

`OpenAICodexCredentials`

### OpenAICodexProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for OpenAI Codex subscription authentication.

Wraps the standard `OpenAIProvider` machinery pointed at the Codex backend, injecting Codex OAuth credentials instead of API keys. One provider instance carries one set of credentials (there is no process-global cache). The instance binds its refresh lock to the first event loop that awaits a request, so do not reuse it across loops.

```python
provider = OpenAICodexProvider(credential_source=YourCredentialStore())
agent = Agent('openai-codex:gpt-5.6-luna', provider=provider)
```

#### Attributes

##### model\_id\_namespace

The namespace used to fully qualify model IDs routed through this provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### credentials

The credentials currently held in memory, rotated in place by refreshes.

**Type:** `OpenAICodexCredentials`

#### Methods

##### realtime\_model\_profile

`@staticmethod`

```python
def realtime_model_profile(model_name: str) -> RealtimeModelProfile | None
```

The realtime model profile for the named model, if available.

###### Returns

`RealtimeModelProfile` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### \_\_init\_\_

```python
def __init__(
    credentials: OpenAICodexCredentials | None = None,
    *,
    credential_source: OpenAICodexCredentialSource | None = None,
    openai_client: AsyncOpenAI | None = None,
    http_client: _OpenAIHTTPClient | None = None,
) -> None
```

Create a new OpenAI Codex provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`credentials`** : `OpenAICodexCredentials` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The subscription credentials to inject. If both this and `credential_source` are omitted, they are loaded **read-only** from the Codex CLI's `auth.json` (honors `CODEX_HOME`), which never writes the file: refreshed tokens then live in memory only. Pydantic AI never falls back to `OPENAI_API_KEY`.

**`credential_source`** : `OpenAICodexCredentialSource` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Application-owned storage for the credentials, so refreshed tokens are persisted between runs; see [`OpenAICodexCredentialSource`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.openai_codex.OpenAICodexCredentialSource). Mutually exclusive with `credentials`.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `AsyncOpenAI` client to use as-is. Opts out of credential injection entirely; `credentials`, `credential_source`, and `http_client` must be `None`.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` to use. Must be dedicated to this provider (no auth of its own): the provider attaches its credential-injecting auth to it, and sharing a client between providers would mix their credentials. The auth only injects credentials on HTTPS requests to the Codex host, so the client can safely be reused for other destinations.

### XaiProvider

**Bases:** `Provider[AsyncClient]`

Provider for xAI API (native xAI SDK).

#### Attributes

##### api\_key

The resolved API key, or `None` when the provider was built from a pre-configured `xai_client`.

The gRPC `AsyncClient` doesn't expose its key, so this returns the one resolved from the `api_key` argument or `XAI_API_KEY`. Used by transports that authenticate outside the SDK, e.g. [`XaiRealtimeModel`](https://pydantic.dev/docs/ai/api/realtime/xai/#pydantic_ai.realtime.xai.XaiRealtimeModel)'s WebSocket `Authorization` header.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### api\_host

The custom `api_host` this provider was configured with, or `None`.

Read by [`XaiRealtimeModel`](https://pydantic.dev/docs/ai/api/realtime/xai/#pydantic_ai.realtime.xai.XaiRealtimeModel) to reject a custom host it can't yet honor: the realtime WebSocket derives its URL from `base_url`, not the gRPC channel target that `api_host` sets.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    api_key: str | None = None,
    api_host: str | None = None,
    timeout: float | None = None,
    metadata: tuple[tuple[str, str], ...] | None = None,
) -> None
def __init__(*, xai_client: AsyncClient) -> None
```

Create a new xAI provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `XAI_API_KEY` environment variable will be used if available.

**`api_host`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API host to use for the xAI SDK client.

**`timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The client-level default timeout for the xAI SDK client, in seconds, applied to all requests made through it. The xAI SDK does not support per-request timeouts, so `ModelSettings.timeout` is not supported and has no effect.

**`metadata`** : [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], ...\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

gRPC metadata to attach to every request the xAI SDK client makes, forwarded to `xai_sdk.AsyncClient`. This is client-scoped, not per-request, so it applies to every request made through the provider. The canonical use is xAI prompt-cache sticky routing via `metadata=(('x-grok-conv-id', '<conversation-id>'),)`; see the [xAI prompt-caching docs](https://docs.x.ai/developers/advanced-api-usage/prompt-caching/maximizing-cache-hits). Because it is client-scoped, a provider configured with conversation-specific metadata (e.g. a fixed `x-grok-conv-id`) must not be shared between unrelated conversations. Ignored when `xai_client` is passed.

**`xai_client`** : `AsyncClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `xai_sdk.AsyncClient` to use. This takes precedence over `api_key`, `api_host`, `timeout`, and `metadata`.

### DeepSeekProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for DeepSeek API.

### BedrockJsonSchemaTransformer

**Bases:** [`JsonSchemaTransformer`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.JsonSchemaTransformer)

Transforms schemas to the subset supported by Bedrock structured outputs.

The transformer is applied to Bedrock tool and output schemas during request customization. Strict-mode rewrites are applied when:

-   `NativeOutput` is used as the `output_type` of the Agent. `BedrockConverseModel` forces native output schemas to `strict=True` before request customization.
-   `strict=True` is set explicitly on a Tool.

Like `AnthropicJsonSchemaTransformer`, Bedrock does not infer strict tool mode from `strict=None`. Strict tool definitions are opt-in: callers must set `strict=True` explicitly. This avoids silently changing large toolsets into strict toolsets, which can exceed Anthropic/Bedrock's 20 strict-tools-per-request limit, and avoids applying potentially lossy strict-mode schema rewrites unless requested.

When `strict=True`, `additionalProperties: false` is injected on objects and keys Bedrock rejects are removed from the schema and re-emitted into the field's `description` so the model still has the hint.

### BedrockModelProfile

**Bases:** [`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

Profile for models used with BedrockModel.

ALL FIELDS MUST BE `bedrock_` PREFIXED SO YOU CAN MERGE THEM WITH OTHER MODELS.

#### Attributes

##### bedrock\_supports\_tool\_choice

Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### bedrock\_tool\_result\_format

Default: `'text'`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['text', 'json'\]

##### bedrock\_send\_back\_thinking\_parts

Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### bedrock\_supports\_prompt\_caching

Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### bedrock\_supports\_tool\_caching

Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### bedrock\_supported\_media\_kinds\_in\_tool\_returns

Default: `frozenset({'image'})`.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['image', 'document', 'video'\]\]

##### bedrock\_tool\_result\_colocatable\_content

Content-block kinds that this model accepts in the same user message as a `toolResult` block.

pydantic-ai merges consecutive user turns into one Bedrock message, which can place a `toolResult` alongside a following turn's text/attachment. Some models reject that: Anthropic rejects documents and video next to a `toolResult`, while Llama and Mistral reject _any_ content sharing the turn (the `toolResult` must be alone). When a merge would co-locate a `toolResult` with a kind not listed here, the adapter splits the turns and separates them with a synthetic assistant message (Bedrock re-merges consecutive same-role turns, so a bare split doesn't suffice). See [https://github.com/pydantic/pydantic-ai/issues/6081](https://github.com/pydantic/pydantic-ai/issues/6081).

Default: all kinds (no restriction); the model receives merged turns unchanged.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['text', 'image', 'document', 'video'\]\]

##### bedrock\_supports\_leading\_assistant\_message

Whether this model accepts a conversation that starts with an assistant message.

Bedrock's Converse API requires that a conversation start with a user message for most model families (Amazon Nova, Meta Llama, Mistral, Cohere, AI21, Writer, ...), which reject a leading assistant turn with `"A conversation must start with a user message..."`. Anthropic and Qwen models accept a leading assistant turn, so for them we don't need to synthesize a placeholder user message when `message_history` starts with a `ModelResponse`.

Verified against Bedrock `us-east-1` on 2026-07-03.

Default: `False` (strict -- synthesize a leading user message when history starts with an assistant turn).

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### bedrock\_supports\_tool\_result\_status

Whether this model accepts the `status` field on a `toolResult` block in Bedrock's Converse API.

Most families accept (and pydantic-ai emits) `status: 'success'`/`'error'` on `toolResult` blocks, but Writer Palmyra rejects it (`"This model doesn't support the status field. Remove status and try again."`), so the field is omitted for it. Verified against Bedrock `us-east-1`.

Default: `True`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### bedrock\_supports\_strict\_tool\_definition

Whether this model accepts `strict: true` on `toolSpec` in Bedrock's Converse API.

Tracked separately from `supports_json_schema_output` (which gates `NativeOutput` / `outputConfig`) because AWS could in principle ship a model that supports one without the other; today both features track the same per-model allowlist per the Bedrock structured-output docs: [https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html).

Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### bedrock\_thinking\_variant

Which thinking API shape to use for unified thinking translation.

-   `'anthropic'`: Uses `{'thinking': {'type': 'adaptive'}}` for 4.6+ models, or `{'thinking': {'type': 'enabled', 'budget_tokens': N}}` for older models.
-   `'openai'`: Uses `{'reasoning_effort': 'low'|'medium'|'high'}`
-   `'qwen'`: Uses `{'reasoning_config': 'low'|'high'}`
-   `None`: No unified thinking support.

Default: `None`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['anthropic', 'openai', 'qwen'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### bedrock\_supports\_adaptive\_thinking

Whether this model accepts `{'thinking': {'type': 'adaptive'}}` (Sonnet 4.6+, Opus 4.6+).

Only meaningful for the `'anthropic'` variant. When False, the variant falls back to `{'type': 'enabled', 'budget_tokens': N}` for pre-4.6 models.

Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### bedrock\_supports\_effort

Whether this model emits `output_config.effort` on Bedrock Converse (Sonnet 4.6+, Opus 4.6+).

Only meaningful for the `'anthropic'` variant AND only honored alongside `bedrock_supports_adaptive_thinking=True`. Bedrock has not been verified to accept `output_config.effort` on the legacy `{'type': 'enabled', 'budget_tokens': N}` path (e.g. Opus 4.5), so the translator skips it there even though the direct Anthropic API accepts it. Effort lives at `additionalModelRequestFields.output_config.effort` (a sibling of `thinking`, not inside it).

Default: `False`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### bedrock\_top\_k\_variant

How the unified `top_k` setting is placed in `additionalModelRequestFields`.

Bedrock's Converse `inferenceConfig` has no `topK` field, so `top_k` must travel in the model-specific `additionalModelRequestFields` blob, where the shape differs per family (and Bedrock 400s on an unrecognized key rather than ignoring it):

-   `'anthropic'`: flat `{'top_k': N}`
-   `'nova'`: nested `{'inferenceConfig': {'topK': N}}`
-   `None`: `top_k` is silently dropped (Llama/Mistral/DeepSeek/Jamba don't accept it on Converse; Cohere's `k` and Qwen's key are unverified on Converse, so they stay here too).

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['anthropic', 'nova'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### bedrock\_supported\_on\_converse

Whether this model is served by the Bedrock Converse API. Default: `True`.

Set to `False` for models that Bedrock serves only through the Mantle OpenAI-compatible API (today, the proprietary OpenAI GPT models); `BedrockConverseModel` raises at construction so the user gets an actionable pointer to `BedrockMantleProvider` instead of an opaque Converse error at request time.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### BedrockProvider

**Bases:** `Provider[BaseClient]`

Provider for AWS Bedrock.

#### Attributes

##### client

The boto3 client used to make requests to the Bedrock API.

**Type:** `BaseClient`

#### Methods

##### \_\_init\_\_

```python
def __init__(*, bedrock_client: BaseClient) -> None
def __init__(
    *,
    api_key: str,
    base_url: str | None = None,
    region_name: str | None = None,
    profile_name: str | None = None,
    aws_read_timeout: float | None = None,
    aws_connect_timeout: float | None = None,
) -> None
def __init__(
    *,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    aws_session_token: str | None = None,
    base_url: str | None = None,
    region_name: str | None = None,
    profile_name: str | None = None,
    aws_read_timeout: float | None = None,
    aws_connect_timeout: float | None = None,
) -> None
```

Initialize the Bedrock provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`bedrock_client`** : `BaseClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A boto3 client for Bedrock Runtime. If provided, other arguments are ignored.

**`aws_access_key_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The AWS access key ID. If not set, the `AWS_ACCESS_KEY_ID` environment variable will be used if available.

**`aws_secret_access_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The AWS secret access key. If not set, the `AWS_SECRET_ACCESS_KEY` environment variable will be used if available.

**`aws_session_token`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The AWS session token. If not set, the `AWS_SESSION_TOKEN` environment variable will be used if available.

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key for Bedrock client. Can be used instead of `aws_access_key_id`, `aws_secret_access_key`, and `aws_session_token`. If not set, the `AWS_BEARER_TOKEN_BEDROCK` environment variable will be used if available.

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base URL for the Bedrock client.

**`region_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The AWS region name. If not set, the `AWS_DEFAULT_REGION` environment variable will be used if available.

**`profile_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The AWS profile name.

**`aws_read_timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The read timeout for Bedrock client.

**`aws_connect_timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The connect timeout for Bedrock client.

### bedrock\_anthropic\_model\_profile

```python
def bedrock_anthropic_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for an Anthropic model used via Bedrock.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### bedrock\_amazon\_model\_profile

```python
def bedrock_amazon_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for an Amazon model used via Bedrock.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### bedrock\_deepseek\_model\_profile

```python
def bedrock_deepseek_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a DeepSeek model used via Bedrock.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### bedrock\_meta\_model\_profile

```python
def bedrock_meta_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Meta Llama model used via Bedrock.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### bedrock\_mistral\_model\_profile

```python
def bedrock_mistral_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Mistral model used via Bedrock.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### bedrock\_qwen\_model\_profile

```python
def bedrock_qwen_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Qwen model used via Bedrock.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### bedrock\_google\_model\_profile

```python
def bedrock_google_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Google model used via Bedrock.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### bedrock\_zai\_model\_profile

```python
def bedrock_zai_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Z.AI (Zhipu) GLM model used via Bedrock.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### bedrock\_moonshotai\_model\_profile

```python
def bedrock_moonshotai_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Moonshot AI Kimi model used via Bedrock.

Registered for both the `moonshot.` and `moonshotai.` Bedrock provider prefixes.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### bedrock\_writer\_model\_profile

```python
def bedrock_writer_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Writer Palmyra model used via Bedrock.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### bedrock\_minimax\_model\_profile

```python
def bedrock_minimax_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a MiniMax model used via Bedrock.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### bedrock\_nvidia\_model\_profile

```python
def bedrock_nvidia_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for an NVIDIA model used via Bedrock.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### bedrock\_openai\_model\_profile

```python
def bedrock_openai_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for an OpenAI model used via Bedrock Converse.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### BedrockMantleModelProfile

**Bases:** `OpenAIModelProfile`

Profile for OpenAI models served through Amazon Bedrock Mantle.

#### Attributes

##### bedrock\_mantle\_interface

Which Mantle endpoint family serves this model, selecting the model class and base URL.

**Type:** `BedrockMantleInterface`

### BedrockMantleProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for the Amazon Bedrock Mantle OpenAI-compatible API.

#### Methods

##### \_\_init\_\_

```python
def __init__(*, openai_client: AsyncOpenAI) -> None
def __init__(
    *,
    region_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    aws_session_token: str | None = None,
    profile_name: str | None = None,
    http_client: _OpenAIHTTPClient | None = None,
) -> None
```

Create a Bedrock Mantle provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`region_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The AWS region used to construct the default `bedrock-mantle.{region}.api.aws` origin. If not set, the `AWS_DEFAULT_REGION` or `AWS_REGION` environment variable is used.

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A Mantle base URL. Its origin (scheme + host, with any `/openai/v1` or `/v1` suffix stripped) is used to route between `/v1` and `/openai/v1` per model, the same as `region_name`.

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A Bedrock API key. If omitted, `AWS_BEARER_TOKEN_BEDROCK` is used. Use this or the `aws_*` credentials, not both.

**`aws_access_key_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The AWS access key ID for SigV4 authentication.

**`aws_secret_access_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The AWS secret access key for SigV4 authentication.

**`aws_session_token`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The AWS session token for SigV4 authentication.

**`profile_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The AWS profile name for SigV4 authentication.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing OpenAI client. If provided, no other argument may be set; its base URL's origin is used to derive both the `/v1` and `/openai/v1` endpoints (preserving its auth and transport) so every interface routes correctly.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` used to make requests.

### bedrock\_mantle\_model\_profile

```python
def bedrock_mantle_model_profile(model_name: str) -> ModelProfile
```

Resolve the profile for an OpenAI model served through Bedrock Mantle.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile)

### BedrockMantleInterface

The OpenAI-compatible endpoint family a Bedrock Mantle model is served on.

-   `'chat'`: Chat Completions at `/v1/chat/completions` (GPT-OSS Safeguard).
-   `'responses'`: Responses at `/v1/responses` (GPT-OSS).
-   `'openai-responses'`: Responses at `/openai/v1/responses`, the OpenAI-model-specific path (GPT-5.4+).

**Default:** `Literal['chat', 'responses', 'openai-responses']`

### GroqProvider

**Bases:** `Provider[AsyncGroq]`

Provider for Groq API.

#### Methods

##### \_\_init\_\_

```python
def __init__(*, groq_client: AsyncGroq | None = None) -> None
def __init__(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> None
```

Create a new Groq provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `GROQ_API_KEY` environment variable will be used if available.

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base url for the Groq requests. If not provided, the `GROQ_BASE_URL` environment variable will be used if available. Otherwise, defaults to Groq's base url.

**`groq_client`** : `AsyncGroq` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing [`AsyncGroq`](https://github.com/groq/groq-python?tab=readme-ov-file#async-usage) client to use. If provided, `api_key` and `http_client` must be `None`.

**`http_client`** : `httpx.AsyncClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `AsyncClient` to use for making HTTP requests.

### groq\_moonshotai\_model\_profile

```python
def groq_moonshotai_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for an MoonshotAI model used with the Groq provider.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### meta\_groq\_model\_profile

```python
def meta_groq_model_profile(model_name: str) -> ModelProfile | None
```

Get the model profile for a Meta model used with the Groq provider.

#### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### AzureProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for Azure OpenAI API.

See [https://azure.microsoft.com/en-us/products/ai-foundry](https://azure.microsoft.com/en-us/products/ai-foundry) for more information.

#### Attributes

##### azure\_endpoint

The Azure resource endpoint used to derive service-specific URLs.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### api\_key

The Azure resource key, for transports that authenticate with one.

Raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) when the provider has no key, i.e. it was built from a Microsoft Entra ID client (`azure_ad_token` / `azure_ad_token_provider`).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### voice\_live\_endpoint

The Azure AI Voice Live endpoint (`AZURE_VOICELIVE_ENDPOINT`, else the Azure OpenAI endpoint).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### voice\_live\_api\_key

The Azure AI Voice Live key (`AZURE_VOICELIVE_API_KEY`, else the Azure OpenAI key).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### voice\_live\_api\_version

The Azure AI Voice Live API version (`AZURE_VOICELIVE_API_VERSION`, else a supported default).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### for\_realtime

`@classmethod`

```python
def for_realtime(
    cls,
    *,
    azure_endpoint: str | None = None,
    api_version: str | None = None,
    api_key: str | None = None,
    entra_authenticated: bool = False,
    http_client: _OpenAIHTTPClient | None = None,
) -> Self
```

Create an Azure provider for the GA realtime API.

The realtime transport always uses Azure's `/openai/v1` protocol and does not send an `api_version`. When neither `api_version` nor `OPENAI_API_VERSION` is set, a bare resource endpoint is therefore normalized to its `/openai/v1` form before constructing the provider. Explicit arguments otherwise follow the same environment fallbacks and validation as the standard constructor.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self)

###### Parameters

**`azure_endpoint`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Azure resource endpoint. Falls back to `AZURE_OPENAI_ENDPOINT`.

**`api_version`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API version for endpoints that require one. Falls back to `OPENAI_API_VERSION`.

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Azure resource key. Falls back to `AZURE_OPENAI_API_KEY`.

**`entra_authenticated`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Set when every request is authenticated with a Microsoft Entra ID credential instead of the resource key (see [`AzureRealtimeModel(credential=...)`](https://pydantic.dev/docs/ai/api/realtime/azure/#pydantic_ai.realtime.azure.AzureRealtimeModel)). The key is then neither required nor sent, and `api_key` raises its usual explanatory error if anything asks -- the same state a provider built from an Entra-authenticated `openai_client` lands in.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` used to construct the provider client.

##### \_\_init\_\_

```python
def __init__(*, openai_client: AsyncAzureOpenAI) -> None
def __init__(
    *,
    azure_endpoint: str | None = None,
    api_version: str | None = None,
    api_key: str | None = None,
    voice_live_endpoint: str | None = None,
    voice_live_api_key: str | None = None,
    voice_live_api_version: str | None = None,
    http_client: _OpenAIHTTPClient | None = None,
) -> None
```

Create a new Azure provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`azure_endpoint`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Azure endpoint to use for authentication, if not provided, the `AZURE_OPENAI_ENDPOINT` environment variable will be used if available.

**`api_version`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API version to use for authentication, if not provided, the `OPENAI_API_VERSION` environment variable will be used if available. Not required (and not sent) when `azure_endpoint` targets the [Azure OpenAI v1 GA API](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/api-version-lifecycle) (i.e. a path ending in `/v1`, such as `https://<resource>.openai.azure.com/openai/v1/`) or an Azure AI Foundry serverless model endpoint (`*.models.ai.azure.com`), both of which reject the `api-version` query parameter.

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `AZURE_OPENAI_API_KEY` environment variable will be used if available.

**`voice_live_endpoint`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The [Azure AI Voice Live](https://learn.microsoft.com/azure/ai-services/speech-service/voice-live) endpoint, used only by [`AzureRealtimeModel`](https://pydantic.dev/docs/ai/api/realtime/azure/#pydantic_ai.realtime.azure.AzureRealtimeModel) with `azure_voice_live=True`. Voice Live is a distinct Azure resource, so when this is not provided the `AZURE_VOICELIVE_ENDPOINT` environment variable is used, and finally `azure_endpoint` as a fallback.

**`voice_live_api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Voice Live API key; falls back to `AZURE_VOICELIVE_API_KEY`, then `api_key`.

**`voice_live_api_version`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Voice Live API version; falls back to `AZURE_VOICELIVE_API_VERSION`, then a supported default. Deliberately _not_ derived from `api_version`, which versions the Azure OpenAI data plane on an unrelated schedule.

**`openai_client`** : `AsyncAzureOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing [`AsyncAzureOpenAI`](https://github.com/openai/openai-python#microsoft-azure-openai) client to use. If provided, `base_url`, `api_key`, and `http_client` must be `None`.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to use for making HTTP requests.

### CohereProvider

**Bases:** `Provider[AsyncClientV2]`

Provider for Cohere API.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    api_key: str | None = None,
    cohere_client: AsyncClientV2 | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> None
```

Create a new Cohere provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `CO_API_KEY` environment variable will be used if available.

**`cohere_client`** : `AsyncClientV2` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing [AsyncClientV2](https://github.com/cohere-ai/cohere-python) client to use. If provided, `api_key` and `http_client` must be `None`.

**`http_client`** : `httpx.AsyncClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx.AsyncClient` to use for making HTTP requests.

### VoyageAIProvider

**Bases:** `Provider[AsyncClient]`

Provider for VoyageAI API.

#### Methods

##### \_\_init\_\_

```python
def __init__(*, voyageai_client: AsyncClient) -> None
def __init__(*, api_key: str | None = None) -> None
```

Create a new VoyageAI provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `VOYAGE_API_KEY` environment variable will be used if available.

**`voyageai_client`** : `AsyncClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing [AsyncClient](https://github.com/voyage-ai/voyageai-python) client to use. If provided, `api_key` must be `None`.

### SentenceTransformersProvider

**Bases:** `Provider[Any]`

Provider for Sentence Transformers API.

#### Attributes

##### name

The provider name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### base\_url

The base URL for the provider API.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### client

The client for the provider.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### CerebrasProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for Cerebras API.

#### Methods

##### \_\_init\_\_

```python
def __init__() -> None
def __init__(*, api_key: str) -> None
def __init__(*, api_key: str, http_client: _OpenAIHTTPClient) -> None
def __init__(*, http_client: _OpenAIHTTPClient) -> None
def __init__(*, openai_client: AsyncOpenAI | None = None) -> None
```

Create a new Cerebras provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `CEREBRAS_API_KEY` environment variable will be used if available.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `AsyncOpenAI` client to use. If provided, `api_key` and `http_client` must be `None`.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to use for making HTTP requests.

### MistralProvider

**Bases:** `Provider[Mistral]`

Provider for Mistral API.

#### Methods

##### \_\_init\_\_

```python
def __init__(*, mistral_client: Mistral | None = None) -> None
def __init__(
    *,
    api_key: str | None = None,
    http_client: AsyncHTTPClient | None = None,
) -> None
```

Create a new Mistral provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `MISTRAL_API_KEY` environment variable will be used if available.

**`mistral_client`** : `Mistral` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `Mistral` client to use, if provided, `api_key` and `http_client` must be `None`.

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base url for the Mistral requests.

**`http_client`** : `AsyncHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to use for making HTTP requests.

### FireworksProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for Fireworks AI API.

### TogetherProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for Together AI API.

### HerokuProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for Heroku API.

### GitHubProvider

**Bases:** `Provider[AsyncOpenAI]`

Provider for the retired GitHub Models API.

GitHub Models was [retired on 2026-07-30](https://docs.github.com/en/github-models); the inference API is no longer available, so this provider is deprecated and will be removed in v3.

#### Methods

##### \_\_init\_\_

```python
def __init__() -> None
def __init__(*, api_key: str) -> None
def __init__(*, api_key: str, http_client: httpx.AsyncClient) -> None
def __init__(*, openai_client: AsyncOpenAI | None = None) -> None
```

Create a new GitHub Models provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The GitHub token to use for authentication. If not provided, the `GITHUB_API_KEY` environment variable will be used if available.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `AsyncOpenAI` client to use. If provided, `api_key` and `http_client` must be `None`.

**`http_client`** : `httpx.AsyncClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx.AsyncClient` to use for making HTTP requests.

### GitHubCopilotProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for [GitHub Copilot](https://docs.github.com/en/copilot).

Routes requests through Copilot's OpenAI-compatible Chat Completions API at `https://api.githubcopilot.com/chat/completions`. Copilot serves Anthropic, OpenAI, Google, xAI and MoonshotAI models under a subscription, but only the ids whose catalog entry lists `/chat/completions` under `supported_endpoints` are reachable here; xAI's Grok ids, for one, are served on the Responses API alone. Which ids you can reach also depends on your plan; list yours with `GET https://api.githubcopilot.com/models`.

This is not [`GitHubProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.github.GitHubProvider), which served the retired GitHub Models API.

#### Methods

##### \_\_init\_\_

```python
def __init__(*, openai_client: AsyncOpenAI) -> None
def __init__(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    openai_client: None = None,
    http_client: _OpenAIHTTPClient | None = None,
) -> None
```

Create a new GitHub Copilot provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The Copilot token to authenticate with. Defaults to the `GITHUB_COPILOT_API_KEY` environment variable, then to `GITHUB_COPILOT_API_TOKEN` and `COPILOT_GITHUB_TOKEN`, the names GitHub's own tooling uses. The general-purpose `GITHUB_TOKEN`, `GH_TOKEN` and `GITHUB_API_KEY` variables are deliberately not read, so a token meant for the GitHub API is never sent to Copilot.

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base URL of the Copilot inference API, e.g. for an enterprise host or a local proxy. Defaults to the `GITHUB_COPILOT_BASE_URL`, `COPILOT_API_URL` or `GITHUB_COPILOT_API_BASE` environment variable, then to `https://api.githubcopilot.com`.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `AsyncOpenAI` client to use. Its `base_url` must already point at the Copilot inference API, and it is used as-is, without the Copilot client headers. If provided, `api_key`, `base_url` and `http_client` must be `None`.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to use for making HTTP requests.

### OpenRouterProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for OpenRouter API.

#### Methods

##### \_\_init\_\_

```python
def __init__(*, openai_client: AsyncOpenAI) -> None
def __init__(
    *,
    api_key: str | None = None,
    app_url: str | None = None,
    app_title: str | None = None,
    openai_client: None = None,
    http_client: _OpenAIHTTPClient | None = None,
) -> None
```

Configure the provider with either an API key or prebuilt client.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

OpenRouter API key. Falls back to `OPENROUTER_API_KEY` when omitted and required unless `openai_client` is provided.

**`app_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional url for app attribution. Falls back to `OPENROUTER_APP_URL` when omitted.

**`app_title`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional title for app attribution. Falls back to `OPENROUTER_APP_TITLE` when omitted.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Existing `AsyncOpenAI` client to reuse instead of creating one internally.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to pass into the `AsyncOpenAI` constructor when building a client.

###### Raises

-   `UserError` -- If no API key is available and no `openai_client` is provided.

### VercelProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for Vercel AI Gateway API.

### HuggingFaceProvider

**Bases:** `Provider[AsyncInferenceClient]`

Provider for Hugging Face.

#### Methods

##### \_\_init\_\_

```python
def __init__(*, base_url: str, api_key: str | None = None) -> None
def __init__(*, provider_name: str, api_key: str | None = None) -> None
def __init__(*, hf_client: AsyncInferenceClient, api_key: str | None = None) -> None
def __init__(
    *,
    hf_client: AsyncInferenceClient,
    base_url: str,
    api_key: str | None = None,
) -> None
def __init__(
    *,
    hf_client: AsyncInferenceClient,
    provider_name: str,
    api_key: str | None = None,
) -> None
def __init__(*, api_key: str | None = None) -> None
```

Create a new Hugging Face provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base url for the Hugging Face requests.

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `HF_TOKEN` environment variable will be used if available.

**`hf_client`** : `AsyncInferenceClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing [`AsyncInferenceClient`](https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client#huggingface_hub.AsyncInferenceClient) client to use. If not provided, a new instance will be created.

**`http_client`** : `AsyncClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

(currently ignored) An existing `httpx.AsyncClient` to use for making HTTP requests.

**`provider_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Name of the provider to use for inference. available providers can be found in the [HF Inference Providers documentation](https://huggingface.co/docs/inference-providers/index#partners). defaults to "auto", which will select the first available provider for the model, the first of the providers available for the model, sorted by the user's order in [https://hf.co/settings/inference-providers](https://hf.co/settings/inference-providers). If `base_url` is passed, then `provider_name` is not used.

### MoonshotAIProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for MoonshotAI platform (Kimi models).

### OllamaProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for local or remote Ollama API.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    base_url: str | None = None,
    api_key: str | None = None,
    openai_client: AsyncOpenAI | None = None,
    http_client: _OpenAIHTTPClient | None = None,
) -> None
```

Create a new Ollama provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base url for the Ollama requests. If not provided, the `OLLAMA_BASE_URL` environment variable will be used if available.

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `OLLAMA_API_KEY` environment variable will be used if available.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing [`AsyncOpenAI`](https://github.com/openai/openai-python?tab=readme-ov-file#async-usage) client to use. If provided, `base_url`, `api_key`, and `http_client` must be `None`.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to use for making HTTP requests.

### LiteLLMProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for LiteLLM API.

#### Methods

##### \_\_init\_\_

```python
def __init__(*, api_key: str | None = None, api_base: str | None = None) -> None
def __init__(
    *,
    api_key: str | None = None,
    api_base: str | None = None,
    http_client: _OpenAIHTTPClient,
) -> None
def __init__(*, openai_client: AsyncOpenAI) -> None
```

Initialize a LiteLLM provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

API key for the model provider. If None, LiteLLM will try to get it from environment variables.

**`api_base`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Base URL for the model provider. Use this for custom endpoints or self-hosted models.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Pre-configured OpenAI client. If provided, other parameters are ignored.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom HTTP client to use.

### VLLMProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for local or remote vLLM API.

#### Methods

##### \_\_init\_\_

```python
def __init__(*, openai_client: AsyncOpenAI) -> None
def __init__(
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    openai_client: None = None,
    http_client: _OpenAIHTTPClient | None = None,
) -> None
```

Create a new vLLM provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base url for the vLLM requests. If not provided, the `VLLM_BASE_URL` environment variable will be used if available.

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `VLLM_API_KEY` environment variable will be used if available.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing [`AsyncOpenAI`](https://github.com/openai/openai-python?tab=readme-ov-file#async-usage) client to use. If provided, `base_url`, `api_key`, and `http_client` must be `None`.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to use for making HTTP requests.

### NebiusProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for Nebius AI Studio API.

### OVHcloudProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for OVHcloud AI Endpoints.

### CrusoeProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for Crusoe Serverless Inference API.

#### Methods

##### \_\_init\_\_

```python
def __init__() -> None
def __init__(*, api_key: str) -> None
def __init__(*, api_key: str, http_client: _OpenAIHTTPClient) -> None
def __init__(*, http_client: _OpenAIHTTPClient) -> None
def __init__(*, openai_client: AsyncOpenAI | None = None) -> None
```

Create a new Crusoe provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `CRUSOE_API_KEY` environment variable will be used if available.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `AsyncOpenAI` client to use. If provided, `api_key` and `http_client` must be `None`.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to use for making HTTP requests.

### AlibabaProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for Alibaba Cloud Model Studio (DashScope) OpenAI-compatible API.

### SambaNovaProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for SambaNova AI models.

SambaNova uses an OpenAI-compatible API.

#### Attributes

##### name

Return the provider name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### base\_url

Return the base URL.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### client

Return the AsyncOpenAI client.

**Type:** `AsyncOpenAI`

#### Methods

##### model\_profile

`@staticmethod`

```python
def model_profile(model_name: str) -> ModelProfile | None
```

Get model profile for SambaNova models.

SambaNova serves models from multiple families including Meta Llama, DeepSeek, Qwen, and Mistral. Model profiles are matched based on model name prefixes.

###### Returns

[`ModelProfile`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfile) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### \_\_init\_\_

```python
def __init__(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    openai_client: AsyncOpenAI | None = None,
    http_client: _OpenAIHTTPClient | None = None,
) -> None
```

Initialize SambaNova provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

SambaNova API key. If not provided, reads from SAMBANOVA\_API\_KEY env var.

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Custom API base URL. Defaults to [https://api.sambanova.ai/v1](https://api.sambanova.ai/v1)

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional pre-configured OpenAI client

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional custom `httpx2.AsyncClient` or legacy `httpx.AsyncClient` for making HTTP requests.

###### Raises

-   `UserError` -- If API key is not provided and SAMBANOVA\_API\_KEY env var is not set

### SnowflakeProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for [Snowflake Cortex](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-rest-api).

Routes requests through Snowflake's OpenAI-compatible Chat Completions API at `https://<account>.snowflakecomputing.com/api/v2/cortex/v1/chat/completions`, which serves Claude, GPT, Llama, Mistral, DeepSeek, and Snowflake's own models. All inference runs inside the customer's Snowflake account, so data never leaves the Snowflake security perimeter.

#### Methods

##### \_\_init\_\_

```python
def __init__(*, openai_client: AsyncOpenAI) -> None
def __init__(
    *,
    account: str | None = None,
    token: str | None = None,
    base_url: str | None = None,
    openai_client: None = None,
    http_client: _OpenAIHTTPClient | None = None,
) -> None
```

Create a new Snowflake provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`account`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The [Snowflake account identifier](https://docs.snowflake.com/en/user-guide/admin-account-identifier), e.g. `myorg-myaccount`. Defaults to the `SNOWFLAKE_ACCOUNT` environment variable.

**`token`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

A Snowflake [programmatic access token](https://docs.snowflake.com/en/user-guide/programmatic-access-tokens), OAuth token, or key-pair JWT, sent as `Authorization: Bearer <token>`. Defaults to the `SNOWFLAKE_TOKEN` environment variable.

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The base URL of the Cortex REST API, e.g. when connecting through [private connectivity](https://docs.snowflake.com/en/user-guide/private-snowflake-service). Defaults to `https://<account>.snowflakecomputing.com/api/v2/cortex/v1`.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `AsyncOpenAI` client to use. Its `base_url` must already point at the Cortex REST API. If provided, `account`, `token`, `base_url`, and `http_client` must be `None`.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to use for making HTTP requests.

### ZaiProvider

**Bases:** `_OpenAICompatibleProvider`

Provider for Z.AI (Zhipu AI) API.

Z.AI provides GLM models with support for thinking/reasoning mode and preserved thinking across turns.

#### Methods

##### \_\_init\_\_

```python
def __init__() -> None
def __init__(*, api_key: str) -> None
def __init__(*, api_key: str, http_client: _OpenAIHTTPClient) -> None
def __init__(*, http_client: _OpenAIHTTPClient) -> None
def __init__(*, openai_client: AsyncOpenAI | None = None) -> None
```

Create a new Z.AI provider.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The API key to use for authentication, if not provided, the `ZAI_API_KEY` environment variable will be used if available.

**`openai_client`** : `AsyncOpenAI` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `AsyncOpenAI` client to use. If provided, `api_key` and `http_client` must be `None`.

**`http_client`** : `_OpenAIHTTPClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An existing `httpx2.AsyncClient` or legacy `httpx.AsyncClient` to use for making HTTP requests.

---
