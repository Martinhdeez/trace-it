# [pydantic_ai.embeddings](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/)

# pydantic\_ai.embeddings

### EmbeddingSettings

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Common settings for configuring embedding models.

These settings apply across multiple embedding model providers. Not all settings are supported by all models - check the specific model's documentation for details.

Provider-specific settings classes (e.g., [`OpenAIEmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.openai.OpenAIEmbeddingSettings), [`CohereEmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.cohere.CohereEmbeddingSettings)) extend this with additional provider-prefixed options.

#### Attributes

##### dimensions

The number of dimensions for the output embeddings.

Supported by:

-   OpenAI
-   Cohere
-   Google
-   Sentence Transformers
-   Bedrock
-   VoyageAI

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### truncate

Whether to truncate inputs that exceed the model's context length.

Defaults to `False`. If `True`, inputs that are too long will be truncated. If `False`, an error will be raised for inputs that exceed the context length.

For more control over truncation, you can use [`max_input_tokens()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.max_input_tokens) and [`count_tokens()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.count_tokens) to implement your own truncation logic.

Provider-specific truncation settings (e.g., `cohere_truncate`, `bedrock_cohere_truncate`) take precedence if specified.

Supported by:

-   Cohere
-   Bedrock (Cohere and Nova models)
-   VoyageAI

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### extra\_headers

Extra headers to send to the model.

Supported by:

-   OpenAI
-   Cohere

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### extra\_body

Extra body to send to the model.

Supported by:

-   OpenAI
-   Cohere

**Type:** [`object`](https://docs.python.org/3/glossary.html#term-object)

### EmbeddingModel

**Bases:** `ABC`

Abstract base class for embedding models.

Implement this class to create a custom embedding model. For most use cases, use one of the built-in implementations:

-   [`OpenAIEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.openai.OpenAIEmbeddingModel)
-   [`CohereEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.cohere.CohereEmbeddingModel)
-   [`GoogleEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.google.GoogleEmbeddingModel)
-   [`BedrockEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.bedrock.BedrockEmbeddingModel)
-   [`SentenceTransformerEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.sentence_transformers.SentenceTransformerEmbeddingModel)

#### Attributes

##### settings

Get the default settings for this model.

**Type:** [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### base\_url

The base URL for the provider API, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### model\_name

The name of the embedding model.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The embedding model provider/system identifier (e.g., 'openai', 'cohere').

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(*, settings: EmbeddingSettings | None = None) -> None
```

Initialize the model with optional settings.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

##### embed

`@abstractmethod`

`@async`

```python
def embed(
    inputs: str | Sequence[str],
    *,
    input_type: EmbedInputType,
    settings: EmbeddingSettings | None = None,
) -> EmbeddingResult
```

Generate embeddings for the given inputs.

###### Returns

[`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) -- An [`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) containing [`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) -- the embeddings and metadata.

###### Parameters

**`inputs`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

A single string or sequence of strings to embed.

**`input_type`** : `EmbedInputType`

Whether the inputs are queries or documents.

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to override the model's defaults.

##### prepare\_embed

```python
def prepare_embed(
    inputs: str | Sequence[str],
    settings: EmbeddingSettings | None = None,
) -> tuple[list[str], EmbeddingSettings]
```

Prepare the inputs and settings for embedding.

This method normalizes inputs to a list and merges settings. Subclasses should call this at the start of their `embed()` implementation.

###### Returns

[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings)\] -- A tuple of (normalized inputs list, merged settings).

###### Parameters

**`inputs`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

A single string or sequence of strings.

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to merge with defaults.

##### max\_input\_tokens

`@async`

```python
def max_input_tokens() -> int | None
```

Get the maximum number of tokens that can be input to the model.

###### Returns

[`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- The maximum token count, or `None` if unknown.

##### count\_tokens

`@async`

```python
def count_tokens(text: str) -> int
```

Count the number of tokens in the given text.

###### Returns

[`int`](https://docs.python.org/3/builtins/functions.html#int) -- The number of tokens.

###### Parameters

**`text`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The text to tokenize and count.

###### Raises

-   `NotImplementedError` -- If the model doesn't support token counting.
-   `UserError` -- If the model or tokenizer is not supported.

### WrapperEmbeddingModel

**Bases:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

Base class for embedding models that wrap another model.

Use this as a base class to create custom embedding model wrappers that modify behavior (e.g., caching, logging, rate limiting) while delegating to an underlying model.

By default, all methods are passed through to the wrapped model. Override specific methods to customize behavior.

#### Attributes

##### wrapped

The underlying embedding model being wrapped.

**Type:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel) **Default:** `infer_embedding_model(wrapped) if isinstance(wrapped, str) else wrapped`

##### settings

Get the settings from the wrapped embedding model.

**Type:** [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_init\_\_

```python
def __init__(wrapped: EmbeddingModel | str)
```

Initialize the wrapper with an embedding model.

###### Parameters

**`wrapped`** : [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The model to wrap. Can be an [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel) instance or a model name string (e.g., `'openai:text-embedding-3-small'`).

### EmbeddingResult

The result of an embedding operation.

This class contains the generated embeddings along with metadata about the operation, including the original inputs, model information, usage statistics, and timing.

Example:

```python
from pydantic_ai import Embedder

embedder = Embedder('openai:text-embedding-3-small')


async def main():
    result = await embedder.embed_query('What is AI?')

    # Access embeddings by index
    print(len(result.embeddings[0]))
    #> 1536

    # Access embeddings by original input text
    print(result['What is AI?'] == result.embeddings[0])
    #> True

    # Check usage
    print(f'Tokens used: {result.usage.input_tokens}')
    #> Tokens used: 3
```

#### Attributes

##### embeddings

The computed embedding vectors, one per input text.

Each embedding is a sequence of floats representing the text in vector space.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`float`](https://docs.python.org/3/builtins/functions.html#float)\]\]

##### inputs

The original input texts that were embedded.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### input\_type

Whether the inputs were embedded as queries or documents.

**Type:** `EmbedInputType`

##### model\_name

The name of the model that generated these embeddings.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_name

The name of the provider (e.g., 'openai', 'cohere').

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

When the embedding request was made.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) **Default:** `field(default_factory=_now_utc)`

##### usage

Token usage statistics for this request.

**Type:** [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage) **Default:** `field(default_factory=RequestUsage)`

##### provider\_details

Provider-specific details from the response.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_response\_id

Unique identifier for this response from the provider, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### \_\_getitem\_\_

```python
def __getitem__(item: int | str) -> Sequence[float]
```

Get the embedding for an input by index or by the original input text.

###### Returns

[`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`float`](https://docs.python.org/3/builtins/functions.html#float)\] -- The embedding vector for the specified input.

###### Parameters

**`item`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Either an integer index or the original input string.

###### Raises

-   `IndexError` -- If the index is out of range.
-   `ValueError` -- If the string is not found in the inputs.

##### cost

```python
def cost() -> genai_types.PriceCalculation
```

Calculate the cost of the embedding request.

Uses [`genai-prices`](https://github.com/pydantic/genai-prices) for pricing data.

###### Returns

`genai_types.PriceCalculation` -- A price calculation object with `total_price`, `input_price`, and other cost details.

###### Raises

-   `LookupError` -- If pricing data is not available for this model/provider.

### TestEmbeddingModel

**Bases:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

A mock embedding model for testing.

This model returns deterministic embeddings (all 1.0 values) and tracks the settings used in the last call via the `last_settings` attribute.

Example:

```python
from pydantic_ai import Embedder
from pydantic_ai.embeddings import TestEmbeddingModel

test_model = TestEmbeddingModel()
embedder = Embedder('openai:text-embedding-3-small')


async def main():
    with embedder.override(model=test_model):
        await embedder.embed_query('test')
        assert test_model.last_settings is not None
```

#### Attributes

##### last\_settings

The settings used in the most recent embed call.

**Type:** [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### model\_name

The embedding model name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The embedding model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: str = 'test',
    *,
    provider_name: str = 'test',
    dimensions: int = 8,
    settings: EmbeddingSettings | None = None,
)
```

Initialize the test embedding model.

###### Parameters

**`model_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'test'`

The model name to report in results.

**`provider_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'test'`

The provider name to report in results.

**`dimensions`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) _Default:_ `8`

The number of dimensions for the generated embeddings.

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional default settings for the model.

### InstrumentedEmbeddingModel

**Bases:** `WrapperEmbeddingModel`

Embedding model which wraps another model so that requests are instrumented with OpenTelemetry.

See the [Debugging and Monitoring guide](https://pydantic.dev/docs/ai/integrations/logfire/) for more info.

#### Attributes

##### instrumentation\_settings

Instrumentation settings for this model.

**Type:** [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) **Default:** `options or InstrumentationSettings()`

### Embedder

High-level interface for generating text embeddings.

The `Embedder` class provides a convenient way to generate vector embeddings from text using various embedding model providers. It handles model inference, settings management, and optional OpenTelemetry instrumentation.

Example:

```python
from pydantic_ai import Embedder

embedder = Embedder('openai:text-embedding-3-small')


async def main():
    result = await embedder.embed_query('What is machine learning?')
    print(result.embeddings[0][:5])  # First 5 dimensions
    #> [1.0, 1.0, 1.0, 1.0, 1.0]
```

#### Attributes

##### instrument

Options to automatically instrument with OpenTelemetry.

Set to `True` to use default instrumentation settings, which will use Logfire if it's configured. Set to an instance of [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) to customize. If this isn't set, then the last value set by [`Embedder.instrument_all()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.instrument_all) will be used, which defaults to False. See the [Debugging and Monitoring guide](https://pydantic.dev/docs/ai/integrations/logfire/) for more info.

**Type:** [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `instrument`

##### model

The embedding model used by this embedder.

**Type:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel) | `KnownEmbeddingModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model: EmbeddingModel | KnownEmbeddingModelName | str,
    *,
    settings: EmbeddingSettings | None = None,
    defer_model_check: bool = True,
    instrument: InstrumentationSettings | bool | None = None,
) -> None
```

Initialize an Embedder.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`model`** : [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel) | `KnownEmbeddingModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The embedding model to use. Can be specified as:

-   A model name string in the format `'provider:model-name'` (e.g., `'openai:text-embedding-3-small'`)
-   An [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel) instance

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) to use as defaults for all embed calls.

**`defer_model_check`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to defer model validation until first use. Set to `False` to validate the model immediately on construction.

**`instrument`** : [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

OpenTelemetry instrumentation settings. Set to `True` to enable with defaults, or pass an [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) instance to customize. If `None`, uses the value from [`Embedder.instrument_all()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.instrument_all).

##### instrument\_all

`@staticmethod`

```python
def instrument_all(instrument: InstrumentationSettings | bool = True) -> None
```

Set the default instrumentation options for all embedders where `instrument` is not explicitly set.

This is useful for enabling instrumentation globally without modifying each embedder individually.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`instrument`** : [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Instrumentation settings to use as the default. Set to `True` for default settings, `False` to disable, or pass an [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) instance to customize.

##### override

```python
def override(
    *,
    model: EmbeddingModel | KnownEmbeddingModelName | str | _utils.Unset = _utils.UNSET,
) -> Generator[None]
```

Context manager to temporarily override the embedding model.

Useful for testing or dynamically switching models.

Example:

```python
from pydantic_ai import Embedder

embedder = Embedder('openai:text-embedding-3-small')


async def main():
    # Temporarily use a different model
    with embedder.override(model='openai:text-embedding-3-large'):
        result = await embedder.embed_query('test')
        print(len(result.embeddings[0]))  # 3072 dimensions for large model
        #> 3072
```

###### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

###### Parameters

**`model`** : [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel) | `KnownEmbeddingModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The embedding model to use within this context.

##### embed\_query

`@async`

```python
def embed_query(
    query: str | Sequence[str],
    *,
    settings: EmbeddingSettings | None = None,
) -> EmbeddingResult
```

Embed one or more query texts.

Use this method when embedding search queries that will be compared against document embeddings. Some models optimize embeddings differently based on whether the input is a query or document.

###### Returns

[`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) -- An [`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) containing the embeddings [`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) -- and metadata about the operation.

###### Parameters

**`query`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

A single query string or sequence of query strings to embed.

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to override the embedder's default settings for this call.

##### embed\_documents

`@async`

```python
def embed_documents(
    documents: str | Sequence[str],
    *,
    settings: EmbeddingSettings | None = None,
) -> EmbeddingResult
```

Embed one or more document texts.

Use this method when embedding documents that will be stored and later searched against. Some models optimize embeddings differently based on whether the input is a query or document.

###### Returns

[`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) -- An [`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) containing the embeddings [`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) -- and metadata about the operation.

###### Parameters

**`documents`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

A single document string or sequence of document strings to embed.

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to override the embedder's default settings for this call.

##### embed

`@async`

```python
def embed(
    inputs: str | Sequence[str],
    *,
    input_type: EmbedInputType,
    settings: EmbeddingSettings | None = None,
) -> EmbeddingResult
```

Embed text inputs with explicit input type specification.

This is the low-level embedding method. For most use cases, prefer [`embed_query()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.embed_query) or [`embed_documents()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.embed_documents).

###### Returns

[`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) -- An [`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) containing the embeddings [`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) -- and metadata about the operation.

###### Parameters

**`inputs`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

A single string or sequence of strings to embed.

**`input_type`** : `EmbedInputType`

The type of input, either `'query'` or `'document'`.

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to override the embedder's default settings for this call.

##### max\_input\_tokens

`@async`

```python
def max_input_tokens() -> int | None
```

Get the maximum number of tokens the model can accept as input.

###### Returns

[`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- The maximum token count, or `None` if the limit is unknown for this model.

##### count\_tokens

`@async`

```python
def count_tokens(text: str) -> int
```

Count the number of tokens in the given text.

###### Returns

[`int`](https://docs.python.org/3/builtins/functions.html#int) -- The number of tokens in the text.

###### Parameters

**`text`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The text to tokenize and count.

###### Raises

-   `NotImplementedError` -- If the model doesn't support token counting.
-   `UserError` -- If the model or tokenizer is not supported.

##### embed\_query\_sync

```python
def embed_query_sync(
    query: str | Sequence[str],
    *,
    settings: EmbeddingSettings | None = None,
) -> EmbeddingResult
```

Synchronous version of [`embed_query()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.embed_query).

###### Returns

[`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult)

##### embed\_documents\_sync

```python
def embed_documents_sync(
    documents: str | Sequence[str],
    *,
    settings: EmbeddingSettings | None = None,
) -> EmbeddingResult
```

Synchronous version of [`embed_documents()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.embed_documents).

###### Returns

[`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult)

##### embed\_sync

```python
def embed_sync(
    inputs: str | Sequence[str],
    *,
    input_type: EmbedInputType,
    settings: EmbeddingSettings | None = None,
) -> EmbeddingResult
```

Synchronous version of [`embed()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.embed).

###### Returns

[`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult)

##### max\_input\_tokens\_sync

```python
def max_input_tokens_sync() -> int | None
```

Synchronous version of [`max_input_tokens()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.max_input_tokens).

###### Returns

[`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### count\_tokens\_sync

```python
def count_tokens_sync(text: str) -> int
```

Synchronous version of [`count_tokens()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.count_tokens).

###### Returns

[`int`](https://docs.python.org/3/builtins/functions.html#int)

### instrument\_embedding\_model

```python
def instrument_embedding_model(
    model: EmbeddingModel,
    instrument: InstrumentationSettings | bool,
) -> EmbeddingModel
```

Instrument an embedding model with OpenTelemetry/logfire.

#### Returns

[`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

### merge\_embedding\_settings

```python
def merge_embedding_settings(
    base: EmbeddingSettings | None,
    overrides: EmbeddingSettings | None,
) -> EmbeddingSettings | None
```

Merge two sets of embedding settings, with overrides taking precedence.

#### Returns

[`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- Merged settings, or `None` if both inputs are `None`.

#### Parameters

**`base`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

Base settings (typically from the embedder or model).

**`overrides`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

Settings that should override the base (typically per-call settings).

### infer\_embedding\_model

```python
def infer_embedding_model(
    model: EmbeddingModel | KnownEmbeddingModelName | str,
    *,
    provider_factory: Callable[[str], Provider[Any]] = infer_provider,
) -> EmbeddingModel
```

Infer the model from the name.

#### Returns

[`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

### KnownEmbeddingModelName

Known model names that can be used with the `model` parameter of [`Embedder`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder).

`KnownEmbeddingModelName` is provided as a concise way to specify an embedding model.

**Default:** `TypeAliasType('KnownEmbeddingModelName', Literal['google-cloud:gemini-embedding-001', 'google-cloud:gemini-embedding-2-preview', 'google-cloud:gemini-embedding-2', 'google-cloud:text-embedding-005', 'google-cloud:text-multilingual-embedding-002', 'google:gemini-embedding-001', 'google:gemini-embedding-2-preview', 'google:gemini-embedding-2', 'openai:text-embedding-ada-002', 'openai:text-embedding-3-small', 'openai:text-embedding-3-large', 'cohere:embed-v4.0', 'cohere:embed-english-v3.0', 'cohere:embed-english-light-v3.0', 'cohere:embed-multilingual-v3.0', 'cohere:embed-multilingual-light-v3.0', 'voyageai:voyage-4-large', 'voyageai:voyage-4', 'voyageai:voyage-4-lite', 'voyageai:voyage-3-large', 'voyageai:voyage-3.5', 'voyageai:voyage-3.5-lite', 'voyageai:voyage-code-3', 'voyageai:voyage-finance-2', 'voyageai:voyage-law-2', 'voyageai:voyage-code-2', 'bedrock:amazon.titan-embed-text-v1', 'bedrock:amazon.titan-embed-text-v2:0', 'bedrock:cohere.embed-english-v3', 'bedrock:cohere.embed-multilingual-v3', 'bedrock:cohere.embed-v4:0', 'bedrock:amazon.nova-2-multimodal-embeddings-v1:0'])`

### EmbeddingModel

**Bases:** `ABC`

Abstract base class for embedding models.

Implement this class to create a custom embedding model. For most use cases, use one of the built-in implementations:

-   [`OpenAIEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.openai.OpenAIEmbeddingModel)
-   [`CohereEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.cohere.CohereEmbeddingModel)
-   [`GoogleEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.google.GoogleEmbeddingModel)
-   [`BedrockEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.bedrock.BedrockEmbeddingModel)
-   [`SentenceTransformerEmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.sentence_transformers.SentenceTransformerEmbeddingModel)

#### Attributes

##### settings

Get the default settings for this model.

**Type:** [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### base\_url

The base URL for the provider API, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### model\_name

The name of the embedding model.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The embedding model provider/system identifier (e.g., 'openai', 'cohere').

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(*, settings: EmbeddingSettings | None = None) -> None
```

Initialize the model with optional settings.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

##### embed

`@abstractmethod`

`@async`

```python
def embed(
    inputs: str | Sequence[str],
    *,
    input_type: EmbedInputType,
    settings: EmbeddingSettings | None = None,
) -> EmbeddingResult
```

Generate embeddings for the given inputs.

###### Returns

[`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) -- An [`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) containing [`EmbeddingResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingResult) -- the embeddings and metadata.

###### Parameters

**`inputs`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

A single string or sequence of strings to embed.

**`input_type`** : `EmbedInputType`

Whether the inputs are queries or documents.

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to override the model's defaults.

##### prepare\_embed

```python
def prepare_embed(
    inputs: str | Sequence[str],
    settings: EmbeddingSettings | None = None,
) -> tuple[list[str], EmbeddingSettings]
```

Prepare the inputs and settings for embedding.

This method normalizes inputs to a list and merges settings. Subclasses should call this at the start of their `embed()` implementation.

###### Returns

[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings)\] -- A tuple of (normalized inputs list, merged settings).

###### Parameters

**`inputs`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

A single string or sequence of strings.

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to merge with defaults.

##### max\_input\_tokens

`@async`

```python
def max_input_tokens() -> int | None
```

Get the maximum number of tokens that can be input to the model.

###### Returns

[`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- The maximum token count, or `None` if unknown.

##### count\_tokens

`@async`

```python
def count_tokens(text: str) -> int
```

Count the number of tokens in the given text.

###### Returns

[`int`](https://docs.python.org/3/builtins/functions.html#int) -- The number of tokens.

###### Parameters

**`text`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The text to tokenize and count.

###### Raises

-   `NotImplementedError` -- If the model doesn't support token counting.
-   `UserError` -- If the model or tokenizer is not supported.

### EmbeddingResult

The result of an embedding operation.

This class contains the generated embeddings along with metadata about the operation, including the original inputs, model information, usage statistics, and timing.

Example:

```python
from pydantic_ai import Embedder

embedder = Embedder('openai:text-embedding-3-small')


async def main():
    result = await embedder.embed_query('What is AI?')

    # Access embeddings by index
    print(len(result.embeddings[0]))
    #> 1536

    # Access embeddings by original input text
    print(result['What is AI?'] == result.embeddings[0])
    #> True

    # Check usage
    print(f'Tokens used: {result.usage.input_tokens}')
    #> Tokens used: 3
```

#### Attributes

##### embeddings

The computed embedding vectors, one per input text.

Each embedding is a sequence of floats representing the text in vector space.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`float`](https://docs.python.org/3/builtins/functions.html#float)\]\]

##### inputs

The original input texts that were embedded.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### input\_type

Whether the inputs were embedded as queries or documents.

**Type:** `EmbedInputType`

##### model\_name

The name of the model that generated these embeddings.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_name

The name of the provider (e.g., 'openai', 'cohere').

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

When the embedding request was made.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) **Default:** `field(default_factory=_now_utc)`

##### usage

Token usage statistics for this request.

**Type:** [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage) **Default:** `field(default_factory=RequestUsage)`

##### provider\_details

Provider-specific details from the response.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_response\_id

Unique identifier for this response from the provider, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### \_\_getitem\_\_

```python
def __getitem__(item: int | str) -> Sequence[float]
```

Get the embedding for an input by index or by the original input text.

###### Returns

[`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`float`](https://docs.python.org/3/builtins/functions.html#float)\] -- The embedding vector for the specified input.

###### Parameters

**`item`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Either an integer index or the original input string.

###### Raises

-   `IndexError` -- If the index is out of range.
-   `ValueError` -- If the string is not found in the inputs.

##### cost

```python
def cost() -> genai_types.PriceCalculation
```

Calculate the cost of the embedding request.

Uses [`genai-prices`](https://github.com/pydantic/genai-prices) for pricing data.

###### Returns

`genai_types.PriceCalculation` -- A price calculation object with `total_price`, `input_price`, and other cost details.

###### Raises

-   `LookupError` -- If pricing data is not available for this model/provider.

### EmbedInputType

The type of input to the embedding model.

-   `'query'`: Text that will be used as a search query
-   `'document'`: Text that will be stored and searched against

Some embedding models optimize differently for queries vs documents.

**Default:** `Literal['query', 'document']`

### EmbeddingSettings

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Common settings for configuring embedding models.

These settings apply across multiple embedding model providers. Not all settings are supported by all models - check the specific model's documentation for details.

Provider-specific settings classes (e.g., [`OpenAIEmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.openai.OpenAIEmbeddingSettings), [`CohereEmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.cohere.CohereEmbeddingSettings)) extend this with additional provider-prefixed options.

#### Attributes

##### dimensions

The number of dimensions for the output embeddings.

Supported by:

-   OpenAI
-   Cohere
-   Google
-   Sentence Transformers
-   Bedrock
-   VoyageAI

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### truncate

Whether to truncate inputs that exceed the model's context length.

Defaults to `False`. If `True`, inputs that are too long will be truncated. If `False`, an error will be raised for inputs that exceed the context length.

For more control over truncation, you can use [`max_input_tokens()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.max_input_tokens) and [`count_tokens()`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.Embedder.count_tokens) to implement your own truncation logic.

Provider-specific truncation settings (e.g., `cohere_truncate`, `bedrock_cohere_truncate`) take precedence if specified.

Supported by:

-   Cohere
-   Bedrock (Cohere and Nova models)
-   VoyageAI

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### extra\_headers

Extra headers to send to the model.

Supported by:

-   OpenAI
-   Cohere

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### extra\_body

Extra body to send to the model.

Supported by:

-   OpenAI
-   Cohere

**Type:** [`object`](https://docs.python.org/3/glossary.html#term-object)

### merge\_embedding\_settings

```python
def merge_embedding_settings(
    base: EmbeddingSettings | None,
    overrides: EmbeddingSettings | None,
) -> EmbeddingSettings | None
```

Merge two sets of embedding settings, with overrides taking precedence.

#### Returns

[`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- Merged settings, or `None` if both inputs are `None`.

#### Parameters

**`base`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

Base settings (typically from the embedder or model).

**`overrides`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

Settings that should override the base (typically per-call settings).

### OpenAIEmbeddingSettings

**Bases:** [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings)

Settings used for an OpenAI embedding model request.

All fields from [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) are supported.

### OpenAIEmbeddingModel

**Bases:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

OpenAI embedding model implementation.

This model works with OpenAI's embeddings API and any [OpenAI-compatible providers](https://pydantic.dev/docs/ai/models/openai/#openai-compatible-models).

Example:

```python
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
from pydantic_ai.providers.openai import OpenAIProvider

# Using OpenAI directly
model = OpenAIEmbeddingModel('text-embedding-3-small')

# Using an OpenAI-compatible provider
model = OpenAIEmbeddingModel(
    'text-embedding-3-small',
    provider=OpenAIProvider(base_url='https://my-provider.com/v1'),
)
```

#### Attributes

##### model\_name

The embedding model name.

**Type:** `OpenAIEmbeddingModelName`

##### system

The embedding model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: OpenAIEmbeddingModelName,
    *,
    provider: OpenAIEmbeddingsCompatibleProvider | Literal['openai'] | Provider[AsyncOpenAI] = 'openai',
    settings: EmbeddingSettings | None = None,
)
```

Initialize an OpenAI embedding model.

###### Parameters

**`model_name`** : `OpenAIEmbeddingModelName`

The name of the OpenAI model to use. See [OpenAI's embedding models](https://platform.openai.com/docs/guides/embeddings) for available options.

**`provider`** : `OpenAIEmbeddingsCompatibleProvider` | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['openai'\] | `Provider`\[`AsyncOpenAI`\] _Default:_ `'openai'`

The provider to use for authentication and API access. Can be:

-   `'openai'` (default): Uses the standard OpenAI API
-   A provider name string (e.g., `'azure'`, `'deepseek'`)
-   A [`Provider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.Provider) instance for custom configuration

See [OpenAI-compatible providers](https://pydantic.dev/docs/ai/models/openai/#openai-compatible-models) for a list of supported providers.

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) to use as defaults for this model.

### OpenAIEmbeddingModelName

Possible OpenAI embeddings model names.

See the [OpenAI embeddings documentation](https://platform.openai.com/docs/guides/embeddings) for available models.

**Default:** `str | LatestOpenAIEmbeddingModelNames`

### CohereEmbeddingSettings

**Bases:** [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings)

Settings used for a Cohere embedding model request.

All fields from [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) are supported, plus Cohere-specific settings prefixed with `cohere_`.

#### Attributes

##### cohere\_max\_tokens

The maximum number of tokens to embed.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### cohere\_input\_type

The Cohere-specific input type for the embedding.

Overrides the standard `input_type` argument. Options include: `'search_query'`, `'search_document'`, `'classification'`, `'clustering'`, and `'image'`.

**Type:** `CohereEmbedInputType`

##### cohere\_truncate

The truncation strategy to use:

-   `'NONE'` (default): Raise an error if input exceeds max tokens.
-   `'END'`: Truncate the end of the input text.
-   `'START'`: Truncate the start of the input text.

Note: This setting overrides the standard `truncate` boolean setting when specified.

**Type:** `V2EmbedRequestTruncate`

### CohereEmbeddingModel

**Bases:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

Cohere embedding model implementation.

This model works with Cohere's embeddings API, which offers multilingual support and various model sizes.

Example:

```python
from pydantic_ai.embeddings.cohere import CohereEmbeddingModel

model = CohereEmbeddingModel('embed-v4.0')
```

#### Attributes

##### base\_url

The base URL for the provider API, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### model\_name

The embedding model name.

**Type:** `CohereEmbeddingModelName`

##### system

The embedding model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: CohereEmbeddingModelName,
    *,
    provider: Literal['cohere'] | Provider[AsyncClientV2] = 'cohere',
    settings: EmbeddingSettings | None = None,
)
```

Initialize a Cohere embedding model.

###### Parameters

**`model_name`** : `CohereEmbeddingModelName`

The name of the Cohere model to use. See [Cohere Embed documentation](https://docs.cohere.com/docs/cohere-embed) for available models.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['cohere'\] | `Provider`\[`AsyncClientV2`\] _Default:_ `'cohere'`

The provider to use for authentication and API access. Can be:

-   `'cohere'` (default): Uses the standard Cohere API
-   A [`CohereProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.cohere.CohereProvider) instance for custom configuration

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) to use as defaults for this model.

### LatestCohereEmbeddingModelNames

Latest Cohere embeddings models.

See the [Cohere Embed documentation](https://docs.cohere.com/docs/cohere-embed) for available models and their capabilities.

**Default:** `Literal['embed-v4.0', 'embed-english-v3.0', 'embed-english-light-v3.0', 'embed-multilingual-v3.0', 'embed-multilingual-light-v3.0']`

### CohereEmbeddingModelName

Possible Cohere embeddings model names.

**Default:** `str | LatestCohereEmbeddingModelNames`

### GoogleEmbeddingSettings

**Bases:** [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings)

Settings used for a Google embedding model request.

All fields from [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) are supported, plus Google-specific settings prefixed with `google_`.

#### Attributes

##### google\_task

Task to condition `gemini-embedding-2` on, applied as a text prefix.

Only supported by `gemini-embedding-2`; on other models it is ignored with a warning (they use [`google_task_type`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.google.GoogleEmbeddingSettings.google_task_type) instead). When unset on `gemini-embedding-2`, defaults to `'search result'`.

For asymmetric tasks the prefix depends on `input_type`: a `'query'` becomes `task: {task} | query: {text}`, while a `'document'` becomes `title: {title} | text: {text}`, using [`google_title`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.google.GoogleEmbeddingSettings.google_title) (or `none` when no title is set). Symmetric tasks use the `task: {task} | query: {text}` form for both. `'raw'` embeds the text verbatim. See [`GoogleEmbeddingTask`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.google.GoogleEmbeddingTask) for the per-task semantics.

**Type:** `GoogleEmbeddingTask`

##### google\_task\_type

The task type for the embedding.

Overrides the automatic task type selection based on `input_type`. See [Google's task type documentation](https://ai.google.dev/gemini-api/docs/embeddings#task-types) for available options.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### google\_title

Optional title for the content being embedded.

Only applicable when task\_type is `RETRIEVAL_DOCUMENT`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### GoogleEmbeddingModel

**Bases:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

Google embedding model implementation.

This model works with Google's embeddings API via the `google-genai` SDK, supporting both the Gemini API (Google AI Studio) and Google Cloud (formerly known as Vertex AI).

Example:

```python
from pydantic_ai.embeddings.google import GoogleEmbeddingModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.google_cloud import GoogleCloudProvider

# Using the Gemini API (requires GOOGLE_API_KEY env var)
model = GoogleEmbeddingModel('gemini-embedding-001', provider=GoogleProvider())

# Using Google Cloud
model = GoogleEmbeddingModel(
    'gemini-embedding-001',
    provider=GoogleCloudProvider(project='my-project', location='us-central1'),
)
```

#### Attributes

##### model\_name

The embedding model name.

**Type:** `GoogleEmbeddingModelName`

##### system

The embedding model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: GoogleEmbeddingModelName,
    *,
    provider: Literal['google', 'google-cloud'] | Provider[Client] = 'google',
    settings: EmbeddingSettings | None = None,
)
```

Initialize a Google embedding model.

###### Parameters

**`model_name`** : `GoogleEmbeddingModelName`

The name of the Google model to use. See [Google Embeddings documentation](https://ai.google.dev/gemini-api/docs/embeddings) for available models.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['google', 'google-cloud'\] | `Provider`\[`Client`\] _Default:_ `'google'`

The provider to use for authentication and API access. Can be:

-   `'google'` (default): Uses the Gemini API (Google AI Studio)
-   `'google-cloud'`: Uses Google Cloud (formerly known as Vertex AI)
-   A [`GoogleProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.google.GoogleProvider) or [`GoogleCloudProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.google_cloud.GoogleCloudProvider) instance for custom configuration

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) to use as defaults for this model.

### LatestGoogleGLAEmbeddingModelNames

Latest Gemini API embedding models.

See the [Google Embeddings documentation](https://ai.google.dev/gemini-api/docs/embeddings) for available models and their capabilities.

**Default:** `Literal['gemini-embedding-001', 'gemini-embedding-2-preview', 'gemini-embedding-2']`

### LatestGoogleVertexEmbeddingModelNames

Latest Google Cloud (formerly known as Vertex AI) embedding models.

See the [Google Cloud Embeddings documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings) for available models and their capabilities.

**Default:** `Literal['gemini-embedding-001', 'gemini-embedding-2-preview', 'gemini-embedding-2', 'text-embedding-005', 'text-multilingual-embedding-002']`

### LatestGoogleEmbeddingModelNames

All latest Google embedding models (union of Gemini API and Google Cloud models).

**Default:** `LatestGoogleGLAEmbeddingModelNames | LatestGoogleVertexEmbeddingModelNames`

### GoogleEmbeddingModelName

Possible Google embeddings model names.

**Default:** `str | LatestGoogleEmbeddingModelNames`

### GoogleEmbeddingTask

Task the embedding is optimized for, applied as a text prefix by `gemini-embedding-2`.

Unlike other Google embedding models (which condition on the [`google_task_type`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.google.GoogleEmbeddingSettings.google_task_type) field), `gemini-embedding-2` is conditioned by prepending a task instruction to the input text.

Asymmetric tasks prefix queries and documents differently, so the same task can be used for both sides of a retrieval pair:

-   `'search result'`: retrieval; find documents relevant to a search query (the default).
-   `'question answering'`: retrieval; find passages that answer a question.
-   `'fact checking'`: retrieval; find evidence that supports or refutes a claim.
-   `'code retrieval'`: retrieval; find code relevant to a natural-language query.

Symmetric tasks prefix both inputs the same way, since both sides play the same role:

-   `'classification'`: assign inputs to predefined categories.
    
-   `'clustering'`: group inputs by similarity.
    
-   `'sentence similarity'`: measure semantic similarity between inputs.
    
-   `'raw'`: embed the text verbatim, without any prefix.
    

**Default:** `Literal['search result', 'question answering', 'fact checking', 'code retrieval', 'classification', 'clustering', 'sentence similarity', 'raw']`

### BedrockEmbeddingSettings

**Bases:** [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings)

Settings used for a Bedrock embedding model request.

All fields from [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) are supported, plus Bedrock-specific settings prefixed with `bedrock_`.

All settings are optional - if not specified, model defaults are used.

**Note on `dimensions` parameter support:**

-   **Titan v1** (`amazon.titan-embed-text-v1`): Not supported (fixed: 1536)
-   **Titan v2** (`amazon.titan-embed-text-v2:0`): Supported (default: 1024, accepts 256/384/1024)
-   **Cohere v3** (`cohere.embed-english-v3`, `cohere.embed-multilingual-v3`): Not supported (fixed: 1024)
-   **Cohere v4** (`cohere.embed-v4:0`): Supported (default: 1536, accepts 256/512/1024/1536)
-   **Nova** (`amazon.nova-2-multimodal-embeddings-v1:0`): Supported (default: 3072, accepts 256/384/1024/3072)

Unsupported settings are silently ignored.

**Note on `truncate` parameter support:**

-   **Titan models** (`amazon.titan-embed-text-v1`, `amazon.titan-embed-text-v2:0`): Not supported
-   **Cohere models** (all versions): Supported (default: `False`, maps to `'END'` when `True`)
-   **Nova** (`amazon.nova-2-multimodal-embeddings-v1:0`): Supported (default: `False`, maps to `'END'` when `True`)

For fine-grained truncation control, use model-specific settings: `bedrock_cohere_truncate` or `bedrock_nova_truncate`.

#### Attributes

##### bedrock\_titan\_normalize

Whether to normalize embedding vectors for Titan models.

**Supported by:** `amazon.titan-embed-text-v2:0` (default: `True`)

**Not supported by:** `amazon.titan-embed-text-v1` (silently ignored)

When enabled, vectors are normalized for direct cosine similarity calculations.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### bedrock\_cohere\_max\_tokens

The maximum number of tokens to embed for Cohere models.

**Supported by:** `cohere.embed-v4:0` (default: 128000)

**Not supported by:** `cohere.embed-english-v3`, `cohere.embed-multilingual-v3` (silently ignored)

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### bedrock\_cohere\_input\_type

The input type for Cohere models.

**Supported by:** All Cohere models (`cohere.embed-english-v3`, `cohere.embed-multilingual-v3`, `cohere.embed-v4:0`)

By default, `embed_query()` uses `'search_query'` and `embed_documents()` uses `'search_document'`. Also accepts `'classification'` or `'clustering'`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['search\_document', 'search\_query', 'classification', 'clustering'\]

##### bedrock\_cohere\_truncate

The truncation strategy for Cohere models. Overrides base `truncate` setting.

**Supported by:** All Cohere models (`cohere.embed-english-v3`, `cohere.embed-multilingual-v3`, `cohere.embed-v4:0`)

Default: `'NONE'`

-   `'NONE'`: Raise an error if input exceeds max tokens.
-   `'START'`: Truncate the start of the input.
-   `'END'`: Truncate the end of the input.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['NONE', 'START', 'END'\]

##### bedrock\_nova\_truncate

The truncation strategy for Nova models. Overrides base `truncate` setting.

**Supported by:** `amazon.nova-2-multimodal-embeddings-v1:0`

Default: `'NONE'`

-   `'NONE'`: Raise an error if input exceeds max tokens.
-   `'START'`: Truncate the start of the input.
-   `'END'`: Truncate the end of the input.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['NONE', 'START', 'END'\]

##### bedrock\_nova\_embedding\_purpose

The embedding purpose for Nova models.

**Supported by:** `amazon.nova-2-multimodal-embeddings-v1:0`

By default, `embed_query()` uses `'GENERIC_RETRIEVAL'` and `embed_documents()` uses `'GENERIC_INDEX'`. Also accepts `'TEXT_RETRIEVAL'`, `'CLASSIFICATION'`, or `'CLUSTERING'`.

Note: Multimodal-specific purposes (`'IMAGE_RETRIEVAL'`, `'VIDEO_RETRIEVAL'`, `'DOCUMENT_RETRIEVAL'`, `'AUDIO_RETRIEVAL'`) are not supported as this embedding client only accepts text input.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['GENERIC\_INDEX', 'GENERIC\_RETRIEVAL', 'TEXT\_RETRIEVAL', 'CLASSIFICATION', 'CLUSTERING'\]

##### bedrock\_inference\_profile

An [inference profile](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles.html) ARN to use as the `modelId` in API requests.

When set, this value is used as the `modelId` in `invoke_model` API calls instead of the base `model_name`. This allows you to pass the base model name (e.g. `'amazon.titan-embed-text-v2:0'`) as `model_name` for detecting model capabilities, while routing requests through an inference profile for cost tracking or cross-region inference.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### bedrock\_max\_concurrency

Maximum number of concurrent requests for models that don't support batch embedding.

**Applies to:** `amazon.titan-embed-text-v1`, `amazon.titan-embed-text-v2:0`, `amazon.nova-2-multimodal-embeddings-v1:0`

When embedding multiple texts with models that only support single-text requests, this controls how many requests run in parallel. Defaults to 5 and must be at least 1.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

### BedrockEmbeddingModel

**Bases:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

Bedrock embedding model implementation.

This model works with AWS Bedrock's embedding models including Amazon Titan Embeddings and Cohere Embed models.

Example:

```python
from pydantic_ai.embeddings.bedrock import BedrockEmbeddingModel
from pydantic_ai.providers.bedrock import BedrockProvider

# Using default AWS credentials
model = BedrockEmbeddingModel('amazon.titan-embed-text-v2:0')

# Using explicit credentials
model = BedrockEmbeddingModel(
    'cohere.embed-english-v3',
    provider=BedrockProvider(
        region_name='us-east-1',
        aws_access_key_id='...',
        aws_secret_access_key='...',
    ),
)
```

#### Attributes

##### base\_url

The base URL for the provider API.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### model\_name

The embedding model name.

**Type:** `BedrockEmbeddingModelName`

##### system

The embedding model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: BedrockEmbeddingModelName,
    *,
    provider: Literal['bedrock'] | Provider[BaseClient] = 'bedrock',
    settings: EmbeddingSettings | None = None,
)
```

Initialize a Bedrock embedding model.

###### Parameters

**`model_name`** : `BedrockEmbeddingModelName`

The name of the Bedrock embedding model to use. See [Bedrock embedding models](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html) for available options.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['bedrock'\] | `Provider`\[`BaseClient`\] _Default:_ `'bedrock'`

The provider to use for authentication and API access. Can be:

-   `'bedrock'` (default): Uses default AWS credentials
-   A [`BedrockProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.bedrock.BedrockProvider) instance for custom configuration

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) to use as defaults for this model.

##### max\_input\_tokens

`@async`

```python
def max_input_tokens() -> int | None
```

Get the maximum number of tokens that can be input to the model.

###### Returns

[`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### LatestBedrockEmbeddingModelNames

Latest Bedrock embedding model names.

See [the Bedrock docs](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html) for available embedding models.

**Default:** `Literal['amazon.titan-embed-text-v1', 'amazon.titan-embed-text-v2:0', 'cohere.embed-english-v3', 'cohere.embed-multilingual-v3', 'cohere.embed-v4:0', 'amazon.nova-2-multimodal-embeddings-v1:0']`

### BedrockEmbeddingModelName

Possible Bedrock embedding model names.

**Default:** `str | LatestBedrockEmbeddingModelNames`

### VoyageAIEmbeddingSettings

**Bases:** [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings)

Settings used for a VoyageAI embedding model request.

All fields from [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) are supported, plus VoyageAI-specific settings prefixed with `voyageai_`.

#### Attributes

##### voyageai\_input\_type

The VoyageAI-specific input type for the embedding.

Overrides the standard `input_type` argument. Options include: `'query'`, `'document'`, or `'none'` for direct embedding without prefix.

**Type:** `VoyageAIEmbedInputType`

### VoyageAIEmbeddingModel

**Bases:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

VoyageAI embedding model implementation.

VoyageAI provides state-of-the-art embedding models optimized for retrieval, with specialized models for code, finance, and legal domains.

Example:

```python
from pydantic_ai.embeddings.voyageai import VoyageAIEmbeddingModel

model = VoyageAIEmbeddingModel('voyage-3.5')
```

#### Attributes

##### base\_url

The base URL for the provider API.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### model\_name

The embedding model name.

**Type:** `VoyageAIEmbeddingModelName`

##### system

The embedding model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: VoyageAIEmbeddingModelName,
    *,
    provider: Literal['voyageai'] | Provider[AsyncClient] = 'voyageai',
    settings: EmbeddingSettings | None = None,
)
```

Initialize a VoyageAI embedding model.

###### Parameters

**`model_name`** : `VoyageAIEmbeddingModelName`

The name of the VoyageAI model to use. See [VoyageAI models](https://docs.voyageai.com/docs/embeddings) for available options.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['voyageai'\] | `Provider`\[`AsyncClient`\] _Default:_ `'voyageai'`

The provider to use for authentication and API access. Can be:

-   `'voyageai'` (default): Uses the standard VoyageAI API
-   A [`VoyageAIProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.voyageai.VoyageAIProvider) instance for custom configuration

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) to use as defaults for this model.

### LatestVoyageAIEmbeddingModelNames

Latest VoyageAI embedding models.

See [VoyageAI Embeddings](https://docs.voyageai.com/docs/embeddings) for available models and their capabilities.

**Default:** `Literal['voyage-4-large', 'voyage-4', 'voyage-4-lite', 'voyage-3-large', 'voyage-3.5', 'voyage-3.5-lite', 'voyage-code-3', 'voyage-finance-2', 'voyage-law-2', 'voyage-code-2']`

### VoyageAIEmbeddingModelName

Possible VoyageAI embedding model names.

**Default:** `str | LatestVoyageAIEmbeddingModelNames`

### VoyageAIEmbedInputType

VoyageAI embedding input types.

-   `'query'`: For search queries; prepends retrieval-optimized prefix.
-   `'document'`: For documents; prepends document retrieval prefix.
-   `'none'`: Direct embedding without any prefix.

**Default:** `Literal['query', 'document', 'none']`

### SentenceTransformersEmbeddingSettings

**Bases:** [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings)

Settings used for a Sentence-Transformers embedding model request.

All fields from [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) are supported, plus Sentence-Transformers-specific settings prefixed with `sentence_transformers_`.

#### Attributes

##### sentence\_transformers\_device

Device to run inference on.

Examples: `'cpu'`, `'cuda'`, `'cuda:0'`, `'mps'` (Apple Silicon).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### sentence\_transformers\_normalize\_embeddings

Whether to L2-normalize embeddings.

When `True`, all embeddings will have unit length, which is useful for cosine similarity calculations.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### sentence\_transformers\_batch\_size

Batch size to use during encoding.

Larger batches may be faster but require more memory.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

### SentenceTransformerEmbeddingModel

**Bases:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

Local embedding model using the `sentence-transformers` library.

This model runs embeddings locally on your machine, which is useful for:

-   Privacy-sensitive applications where data shouldn't leave your infrastructure
-   Reducing API costs for high-volume embedding workloads
-   Offline or air-gapped environments

Models are downloaded from Hugging Face on first use. See the [Sentence-Transformers documentation](https://www.sbert.net/docs/sentence_transformer/pretrained_models.html) for available models.

Example:

```python
from sentence_transformers import SentenceTransformer

from pydantic_ai.embeddings.sentence_transformers import (
    SentenceTransformerEmbeddingModel,
)

# Using a model name (downloads from Hugging Face)
model = SentenceTransformerEmbeddingModel('sentence-transformers/all-MiniLM-L6-v2')

# Using an existing SentenceTransformer instance
st_model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')
model = SentenceTransformerEmbeddingModel(st_model)
```

#### Attributes

##### base\_url

No base URL -- runs locally.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### model\_name

The embedding model name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The embedding model provider/system identifier.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model: SentenceTransformer | str,
    *,
    settings: EmbeddingSettings | None = None,
) -> None
```

Initialize a Sentence-Transformers embedding model.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`model`** : `SentenceTransformer` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The model to use. Can be:

-   A model name from Hugging Face (e.g., `'sentence-transformers/all-MiniLM-L6-v2'`)
-   A local path to a saved model
-   An existing `SentenceTransformer` instance

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific [`SentenceTransformersEmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.sentence_transformers.SentenceTransformersEmbeddingSettings) to use as defaults for this model.

### TestEmbeddingModel

**Bases:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

A mock embedding model for testing.

This model returns deterministic embeddings (all 1.0 values) and tracks the settings used in the last call via the `last_settings` attribute.

Example:

```python
from pydantic_ai import Embedder
from pydantic_ai.embeddings import TestEmbeddingModel

test_model = TestEmbeddingModel()
embedder = Embedder('openai:text-embedding-3-small')


async def main():
    with embedder.override(model=test_model):
        await embedder.embed_query('test')
        assert test_model.last_settings is not None
```

#### Attributes

##### last\_settings

The settings used in the most recent embed call.

**Type:** [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### model\_name

The embedding model name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The embedding model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: str = 'test',
    *,
    provider_name: str = 'test',
    dimensions: int = 8,
    settings: EmbeddingSettings | None = None,
)
```

Initialize the test embedding model.

###### Parameters

**`model_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'test'`

The model name to report in results.

**`provider_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'test'`

The provider name to report in results.

**`dimensions`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) _Default:_ `8`

The number of dimensions for the generated embeddings.

**`settings`** : [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional default settings for the model.

### WrapperEmbeddingModel

**Bases:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

Base class for embedding models that wrap another model.

Use this as a base class to create custom embedding model wrappers that modify behavior (e.g., caching, logging, rate limiting) while delegating to an underlying model.

By default, all methods are passed through to the wrapped model. Override specific methods to customize behavior.

#### Attributes

##### wrapped

The underlying embedding model being wrapped.

**Type:** [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel) **Default:** `infer_embedding_model(wrapped) if isinstance(wrapped, str) else wrapped`

##### settings

Get the settings from the wrapped embedding model.

**Type:** [`EmbeddingSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_init\_\_

```python
def __init__(wrapped: EmbeddingModel | str)
```

Initialize the wrapper with an embedding model.

###### Parameters

**`wrapped`** : [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The model to wrap. Can be an [`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel) instance or a model name string (e.g., `'openai:text-embedding-3-small'`).

### InstrumentedEmbeddingModel

**Bases:** `WrapperEmbeddingModel`

Embedding model which wraps another model so that requests are instrumented with OpenTelemetry.

See the [Debugging and Monitoring guide](https://pydantic.dev/docs/ai/integrations/logfire/) for more info.

#### Attributes

##### instrumentation\_settings

Instrumentation settings for this model.

**Type:** [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) **Default:** `options or InstrumentationSettings()`

### instrument\_embedding\_model

```python
def instrument_embedding_model(
    model: EmbeddingModel,
    instrument: InstrumentationSettings | bool,
) -> EmbeddingModel
```

Instrument an embedding model with OpenTelemetry/logfire.

#### Returns

[`EmbeddingModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/embeddings/#pydantic_ai.embeddings.EmbeddingModel)

---
