# [pydantic_ai.usage](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/)

# pydantic\_ai.usage

### UsageBase

#### Attributes

##### input\_tokens

Total number of input/prompt tokens, across all modalities.

Token counts form inclusive parent/child buckets, not disjoint ones: this total includes cached tokens (`cache_read_tokens`, `cache_write_tokens`) and audio tokens (`input_audio_tokens`). Usage extraction normalizes providers that report these separately (e.g. Anthropic and Bedrock, whose raw `input_tokens` exclude cache reads/writes) so the convention holds everywhere.

**Type:** [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated)\[[`int`](https://docs.python.org/3/builtins/functions.html#int), `Field`(`validation_alias`\=(`AliasChoices`(`input_tokens`, `request_tokens`)))\] **Default:** `0`

##### cache\_write\_tokens

Number of tokens written to the cache. Included in `input_tokens`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### cache\_read\_tokens

Number of tokens read from the cache, across all modalities (includes `cache_audio_read_tokens`).

Included in `input_tokens`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### output\_tokens

Number of output/completion tokens.

**Type:** [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated)\[[`int`](https://docs.python.org/3/builtins/functions.html#int), `Field`(`validation_alias`\=(`AliasChoices`(`output_tokens`, `response_tokens`)))\] **Default:** `0`

##### input\_audio\_tokens

Number of audio input tokens. Included in `input_tokens`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### cache\_audio\_read\_tokens

Number of audio tokens read from the cache. Included in `cache_read_tokens` and `input_audio_tokens`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### output\_audio\_tokens

Number of audio output tokens. Included in `output_tokens`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### cost

Best-effort cost in USD, or `None` if no cost could be determined.

Calculated with [genai-prices](https://github.com/pydantic/genai-prices). `None` (rather than zero) when the model or provider can't be priced, so "unknown" stays distinguishable from a genuine zero cost. Models released after your install can be priced by calling [`update_in_background()`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.prices.update_in_background).

**Type:** `Decimal` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### details

Any extra details returned by the model.

**Type:** [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated)\[[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`int`](https://docs.python.org/3/builtins/functions.html#int)\], `BeforeValidator`([`lambda`](https://docs.python.org/3/glossary.html#term-lambda) `d`: `d` [`or`](https://docs.python.org/3/reference/expressions.html#or) {})\] **Default:** `details or {}`

##### total\_tokens

Sum of `input_tokens + output_tokens`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### cache\_hit\_ratio

Fraction of input tokens that were read from the provider's prompt cache.

Computed as `cache_read_tokens / input_tokens`. Both counts span all modalities -- cached audio tokens are included in `cache_read_tokens` just as audio input tokens are included in `input_tokens` -- and `input_tokens` includes cached reads for every provider, so the ratio is comparable across providers: `0.0` means no prompt-cache hits, while values approaching `1.0` mean nearly the entire prompt was served from cache. Returns `0.0` when there are no input tokens.

On [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage) this is the hit ratio of a single request; on [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage) it aggregates all requests in the run.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

#### Methods

##### \_\_get\_pydantic\_core\_schema\_\_

`@classmethod`

```python
def __get_pydantic_core_schema__(
    cls,
    source_type: Any,
    handler: GetCoreSchemaHandler,
) -> core_schema.CoreSchema
```

Preserve arbitrary usage fields across Pydantic serialization.

###### Returns

`core_schema.CoreSchema`

##### \_\_copy\_\_

```python
def __copy__() -> UsageBase
```

Shallow copy that also copies mutable fields like `details`.

###### Returns

`UsageBase`

##### opentelemetry\_attributes

```python
def opentelemetry_attributes() -> dict[str, int]
```

Get the token usage values as OpenTelemetry attributes.

###### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`int`](https://docs.python.org/3/builtins/functions.html#int)\]

##### has\_values

```python
def has_values() -> bool
```

Whether any values are set and non-zero.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### RequestUsage

**Bases:** `UsageBase`

LLM usage associated with a single request.

This is an implementation of `genai_prices.types.AbstractUsage` so it can be used to calculate the price of the request using [genai-prices](https://github.com/pydantic/genai-prices).

#### Methods

##### incr

```python
def incr(incr_usage: RequestUsage) -> None
```

Increment the usage in place.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`incr_usage`** : [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage)

The usage to increment by.

##### \_\_add\_\_

```python
def __add__(other: RequestUsage) -> RequestUsage
```

Add two RequestUsages together.

This is provided so it's trivial to sum usage information from multiple parts of a response.

**WARNING:** this CANNOT be used to sum multiple requests without breaking some pricing calculations.

###### Returns

[`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage)

##### extract

`@classmethod`

```python
def extract(
    cls,
    data: Any,
    *,
    provider: str,
    provider_url: str,
    provider_fallback: str,
    api_flavor: str = 'default',
    details: dict[str, Any] | None = None,
) -> RequestUsage
```

Extract usage information from the response data using genai-prices.

###### Returns

[`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage)

###### Parameters

**`data`** : [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

The response data from the model API.

**`provider`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The actual provider ID

**`provider_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The provider base\_url

**`provider_fallback`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The fallback provider ID to use if the actual provider is not found in genai-prices. For example, an OpenAI model should set this to "openai" in case it has an obscure provider ID.

**`api_flavor`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'default'`

The API flavor to use when extracting usage information, e.g. 'chat' or 'responses' for OpenAI.

**`details`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Becomes the `details` field on the returned `RequestUsage` for convenience.

### RunUsage

**Bases:** `UsageBase`

LLM usage associated with an agent run.

Responsibility for calculating request usage is on the model; Pydantic AI simply sums the usage information across requests.

#### Attributes

##### requests

Number of requests made to the LLM API.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### tool\_calls

Number of successful tool calls executed during the run.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### input\_tokens

Total number of input/prompt tokens.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### cache\_write\_tokens

Total number of tokens written to the cache.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### cache\_read\_tokens

Total number of tokens read from the cache.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### input\_audio\_tokens

Total number of audio input tokens.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### cache\_audio\_read\_tokens

Total number of audio tokens read from the cache.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### output\_tokens

Total number of output/completion tokens.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### details

Any extra details returned by the model.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`int`](https://docs.python.org/3/builtins/functions.html#int)\] **Default:** `dataclasses.field(default_factory=(dict[str, int]))`

#### Methods

##### incr

```python
def incr(incr_usage: RunUsage | RequestUsage) -> None
```

Increment the usage in place.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`incr_usage`** : [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage) | [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage)

The usage to increment by.

##### \_\_add\_\_

```python
def __add__(other: RunUsage | RequestUsage) -> RunUsage
```

Add two RunUsages together.

This is provided so it's trivial to sum usage information from multiple runs.

###### Returns

[`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage)

##### \_\_sub\_\_

```python
def __sub__(other: RunUsage) -> RunUsage
```

Return the field-by-field usage accumulated since `other`.

This is useful when a nested operation shares a run's mutable usage object and needs to report only the requests, tool calls, tokens, details, and cost added by that operation. Unknown costs remain `None`; an unchanged known cost also produces `None`.

###### Returns

[`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage)

### UsageLimits

Limits on model usage.

The request count is tracked by pydantic\_ai, and the request limit is checked before each request to the model. Token counts are provided in responses from the model, and the token limits are checked after each response.

Each of the limits can be set to `None` to disable that limit.

#### Attributes

##### cost\_limit

The maximum cost allowed in USD.

**Type:** `Decimal` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### request\_limit

The maximum number of requests allowed to the model.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `50`

##### tool\_calls\_limit

The maximum number of successful tool calls allowed to be executed.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### input\_tokens\_limit

The maximum number of input/prompt tokens allowed.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### output\_tokens\_limit

The maximum number of output/response tokens allowed.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### total\_tokens\_limit

The maximum number of tokens allowed in requests and responses combined.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### per\_request\_input\_tokens\_limit

The maximum number of input/prompt tokens allowed per individual request.

Unlike `input_tokens_limit` which is cumulative across the entire run, this limit is checked against each request's input token count independently -- ahead of the request when `count_tokens_before_request=True`, otherwise against the provider-reported `input_tokens` of the response.

This provides a guard against oversized contexts (which hurt model performance and incur high costs on cache misses), complementing the runaway-loop protection that cumulative limits provide.

Note that `input_tokens` (and therefore this limit) includes cached-prefix tokens, normalized consistently across providers: a request served largely from cache still counts its full context size toward this limit. This caps context size, not cache-miss cost.

Set `count_tokens_before_request=True` to enforce this preemptively; otherwise the request is sent before the limit is checked, so the oversized request is still billed (matching `input_tokens_limit`).

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### count\_tokens\_before\_request

If True, perform a token counting pass before sending the request to the model, to enforce `input_tokens_limit` and `per_request_input_tokens_limit` ahead of time.

This may incur additional overhead (from calling the model's `count_tokens` API before making the actual request) and is disabled by default.

Supported by:

-   Anthropic
-   Google
-   Bedrock Converse
-   OpenAI Responses

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

#### Methods

##### has\_token\_limits

```python
def has_token_limits() -> bool
```

Returns `True` if this instance places any limits on token counts.

If this returns `False`, the `check_tokens` and `check_per_request_input_tokens` methods will never raise an error.

This is useful because if we have token limits, we need to check them after receiving each streamed message. If there are no limits, we can skip that processing in the streaming response iterator.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### check\_before\_request

```python
def check_before_request(usage: RunUsage) -> None
```

Raises a `UsageLimitExceeded` exception if the next request would exceed any of the limits.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### check\_cost

```python
def check_cost(usage: RunUsage, *, warn_if_cost_unavailable: bool = True) -> None
```

Check whether usage exceeds the cost limit.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`usage`** : [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage)

The accumulated run usage to check.

**`warn_if_cost_unavailable`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to warn when a `cost_limit` is set but no cost was calculated.

##### check\_tokens

```python
def check_tokens(usage: RunUsage) -> None
```

Raises a `UsageLimitExceeded` exception if the usage exceeds any of the token limits.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### check\_before\_tool\_call

```python
def check_before_tool_call(projected_usage: RunUsage) -> None
```

Raises a `UsageLimitExceeded` exception if the next tool call(s) would exceed the tool call limit.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### check\_per\_request\_input\_tokens

```python
def check_per_request_input_tokens(request_input_tokens: int) -> None
```

Raises a `UsageLimitExceeded` if the per-request input tokens exceed the limit.

This checks a single request's input token count -- not the cumulative `RunUsage.input_tokens` -- against `per_request_input_tokens_limit`.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

## `pydantic_ai.prices`

Keep model prices up to date by downloading the latest price list in the background.

### update\_in\_background

```python
def update_in_background() -> UpdatePrices
```

Download the latest model prices now, and again every hour, in the background.

Pydantic AI bundles model prices at release time. Call this when your app starts to estimate costs for models released after you installed it.

Downloads never block your code. If one fails, the last good price list stays in use and the failure is logged to the `genai-prices` logger.

Returns the updater. Call `stop()` when your app shuts down.

To download from your own URL or on a different schedule, use [`genai_prices.UpdatePrices`](https://github.com/pydantic/genai-prices/blob/main/packages/python/README.md#updateprices) directly. It shares one background download with this function.

#### Returns

`UpdatePrices`

---
