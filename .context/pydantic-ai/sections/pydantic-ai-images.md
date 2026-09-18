# [pydantic_ai.images](https://pydantic.dev/docs/ai/api/pydantic-ai/images/)

# pydantic\_ai.images

### WrapperImageGenerationModel

**Bases:** [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel)

Base class for image generation models that wrap another model.

Use this as a base class to create custom image generation model wrappers that modify behavior (e.g., caching, logging, rate limiting) while delegating to an underlying model.

By default, all methods are passed through to the wrapped model. Override specific methods to customize behavior.

#### Attributes

##### wrapped

The underlying image generation model being wrapped.

**Type:** [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) **Default:** `infer_image_generation_model(wrapped) if isinstance(wrapped, str) else wrapped`

##### settings

Get the settings from the wrapped image generation model.

**Type:** [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_init\_\_

```python
def __init__(wrapped: ImageGenerationModel | str)
```

Initialize the wrapper with an image generation model.

###### Parameters

**`wrapped`** : [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The model to wrap. Can be an [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) instance or a model name string (e.g., `'openai:gpt-image-1'`).

### GeneratedImage

One generated image with normalized content and provider metadata.

#### Attributes

##### content

The generated image as normalized binary content.

**Type:** [`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage)

##### revised\_prompt

Provider-revised or enhanced prompt, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### output\_format

Generated image output format, derived from the bytes the provider returned.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Provider-specific details for this generated image.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### ImageGenerationModel

**Bases:** `ABC`

Abstract base class for image generation models.

#### Attributes

##### settings

Get the default settings for this model.

**Type:** [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### base\_url

The base URL for the provider API, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### model\_name

The name of the image generation model.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The image generation model provider/system identifier.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(*, settings: ImageGenerationSettings | None = None) -> None
```

Initialize the model with optional settings.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`settings`** : [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

##### generate

`@abstractmethod`

`@async`

```python
def generate(
    prompt: str,
    *,
    images: Sequence[ImageGenerationInput] | None = None,
    settings: ImageGenerationSettings | None = None,
) -> ImageGenerationResult
```

Generate images for the given prompt.

The result always holds at least one image. An implementation with no image to return raises [`ContentFilterError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ContentFilterError) when the provider blocked the output, and [`UnexpectedModelBehavior`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UnexpectedModelBehavior) otherwise, rather than returning an empty result.

###### Returns

[`ImageGenerationResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationResult)

##### prepare\_generate

```python
def prepare_generate(
    prompt: str,
    *,
    images: Sequence[ImageGenerationInput] | None = None,
    settings: ImageGenerationSettings | None = None,
) -> tuple[str, list[ImageGenerationInput], ImageGenerationSettings]
```

Prepare the prompt, reference images, and settings for image generation.

###### Returns

[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ImageGenerationInput`\], [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings)\]

### TestImageGenerationModel

**Bases:** [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel)

A deterministic image generation model for testing.

This model returns a single 1x1 PNG without making any API calls, and records the reference images and settings used in the last call via the `last_images` and `last_settings` attributes.

Example:

```python
from pydantic_ai import ImageGenerator
from pydantic_ai.images import TestImageGenerationModel

test_model = TestImageGenerationModel()
generator = ImageGenerator('openai:gpt-image-2')


async def main():
    with generator.override(model=test_model):
        await generator.generate('A test image', settings={'aspect_ratio': '16:9'})
        print(test_model.last_settings)
        #> {'aspect_ratio': '16:9'}
        print(test_model.last_images)
        #> []
```

#### Attributes

##### last\_images

The reference images passed to the most recent generate call.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ImageGenerationInput`\] **Default:** `[]`

##### last\_settings

The settings used in the most recent generate call.

**Type:** [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### model\_name

The image generation model name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The image generation model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: str = 'test',
    *,
    provider_name: str = 'test',
    settings: ImageGenerationSettings | None = None,
)
```

Initialize the test image generation model.

###### Parameters

**`model_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'test'`

The model name to report in results.

**`provider_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'test'`

The provider name to report in results.

**`settings`** : [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional default settings for the model.

### ImageGenerationResult

The result of an image generation operation.

#### Attributes

##### images

Generated images.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`GeneratedImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.GeneratedImage)\]

##### prompt

The input prompt used for generation.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### model\_name

The name of the model that generated the images.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_name

The name of the provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

When the image generation request was made.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) **Default:** `field(default_factory=_now_utc)`

##### usage

Usage statistics for this request.

**Type:** [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage) **Default:** `field(default_factory=RequestUsage)`

##### provider\_details

Provider-specific details from the response.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_response\_id

Unique identifier for this response from the provider, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_url

Provider API URL, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### image

The first generated image. Use `images` when the request asked for more than one.

A result always holds at least one image: the [`ImageGenerationModel.generate`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel.generate) contract requires an implementation with nothing to return to raise instead of returning an empty result.

**Type:** [`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage)

#### Methods

##### cost

```python
def cost() -> genai_types.PriceCalculation
```

Calculate the cost of the image generation request.

Uses [`genai-prices`](https://github.com/pydantic/genai-prices) for pricing data.

Models priced per token are covered, such as the GPT Image and Gemini image families. The Grok Imagine family raises `LookupError`: it has no entry in the pricing data, and there is no unit that counts generated images to price it with.

###### Returns

`genai_types.PriceCalculation` -- A price calculation object with `total_price`, `input_price`, and other cost details.

###### Raises

-   `LookupError` -- If pricing data is not available for this model/provider.

### InstrumentedImageGenerationModel

**Bases:** `WrapperImageGenerationModel`

Image generation model which wraps another model for OpenTelemetry instrumentation.

#### Attributes

##### instrumentation\_settings

Instrumentation settings for this model.

**Type:** [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) **Default:** `options or InstrumentationSettings()`

### ImageGenerationSettings

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Normalized settings for configuring image generation models.

This type contains only settings with the same semantics across every direct image provider. Provider-specific settings classes extend it with prefixed options for controls that are not portable.

#### Attributes

##### dimensions

The exact output dimensions as `(width, height)` in pixels.

This is mutually exclusive with `aspect_ratio`. The selected provider and model must support the exact dimensions; no rounding or nearest-shape fallback is applied. GPT Image 1.x accepts its three fixed shapes, GPT Image 2 validates a continuous constrained range, and Gemini/Grok Imagine accept their model-specific aspect-ratio and resolution table entries. See the `ImageDimensions` documentation for the full matrix.

**Type:** `ImageDimensions`

##### aspect\_ratio

The requested aspect ratio.

Providers with a native aspect-ratio field receive the ratio as given, and reject an unsupported one themselves. OpenAI has no such field, so Pydantic AI maps the ratio to one of the model family's enumerated sizes and raises `UserError` for a ratio outside that set; xAI takes an enum with no member for some portable values and raises `UserError` for those. See the [Image Generation guide](https://pydantic.dev/docs/ai/guides/image-generation/#canonical-dimensions-for-aspect_ratio) for the per-family shapes.

**Type:** `ImageGenerationAspectRatio`

##### extra\_headers

Extra headers to send to the model.

This follows the existing `ModelSettings` and `EmbeddingSettings` escape-hatch pattern. Prefer provider-prefixed typed settings when a setting is part of the supported public API.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### extra\_body

Extra body to send to the model.

This follows the existing `ModelSettings` and `EmbeddingSettings` escape-hatch pattern. Prefer provider-prefixed typed settings when a setting is part of the supported public API.

**Type:** [`object`](https://docs.python.org/3/glossary.html#term-object)

### ImageGenerator

High-level interface for generating images.

The `ImageGenerator` class provides a convenient way to generate images from a prompt, and to edit or transform reference images, using dedicated image models. It handles model inference, settings management, and optional OpenTelemetry instrumentation.

Example:

```python
from pydantic_ai import ImageGenerator

generator = ImageGenerator('openai:gpt-image-2')


async def main():
    result = await generator.generate('A watercolor map of a floating city.')
    print(result.image.media_type)
    #> image/png
```

#### Attributes

##### instrument

Options to automatically instrument with OpenTelemetry.

Set to `True` to use default instrumentation settings, which will use Logfire if it's configured. Set to an instance of [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) to customize. If this isn't set, then the last value set by [`ImageGenerator.instrument_all()`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerator.instrument_all) will be used, which defaults to False.

**Type:** [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `instrument`

##### model

The image generation model used by this generator.

**Type:** [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) | `KnownImageGenerationModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model: ImageGenerationModel | KnownImageGenerationModelName | str,
    *,
    settings: ImageGenerationSettings | None = None,
    defer_model_check: bool = True,
    instrument: InstrumentationSettings | bool | None = None,
) -> None
```

Initialize an ImageGenerator.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`model`** : [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) | `KnownImageGenerationModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The image generation model to use. Can be specified as:

-   A model name string in the format `'provider:model-name'` (e.g., `'openai:gpt-image-2'`)
-   An [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) instance

**`settings`** : [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) to use as defaults for all generate calls.

**`defer_model_check`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to defer resolving the model name to a model instance, and the provider authentication that resolution requires, until the first generate call. Set to `False` to resolve the model immediately on construction.

**`instrument`** : [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

OpenTelemetry instrumentation settings. Set to `True` to enable with defaults, or pass an [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) instance to customize. If `None`, uses the value from [`ImageGenerator.instrument_all()`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerator.instrument_all).

##### instrument\_all

`@staticmethod`

```python
def instrument_all(instrument: InstrumentationSettings | bool = True) -> None
```

Set the default instrumentation options for all image generators where `instrument` is not explicitly set.

This is useful for enabling instrumentation globally without modifying each generator individually.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`instrument`** : [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Instrumentation settings to use as the default. Set to `True` for default settings, `False` to disable, or pass an [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) instance to customize.

##### override

```python
def override(
    *,
    model: ImageGenerationModel | KnownImageGenerationModelName | str | _utils.Unset = _utils.UNSET,
) -> Generator[None]
```

Context manager to temporarily override the image generation model.

Useful for testing or dynamically switching models.

Example:

```python
from pydantic_ai import ImageGenerator

generator = ImageGenerator('openai:gpt-image-2')


async def main():
    # Temporarily use a different model
    with generator.override(model='google:gemini-3.1-flash-image'):
        result = await generator.generate('A watercolor map of a floating city.')
        print(result.model_name)
        #> gemini-3.1-flash-image
```

###### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

###### Parameters

**`model`** : [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) | `KnownImageGenerationModelName` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `_utils.Unset` _Default:_ `_utils.UNSET`

The image generation model to use within this context.

##### generate

`@async`

```python
def generate(
    prompt: str,
    *,
    images: Sequence[ImageGenerationInput] | None = None,
    settings: ImageGenerationSettings | None = None,
) -> ImageGenerationResult
```

Generate images from a prompt and optional reference images.

###### Returns

[`ImageGenerationResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationResult) -- An [`ImageGenerationResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationResult) containing the [`ImageGenerationResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationResult) -- generated images and metadata about the operation.

###### Parameters

**`prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The text prompt describing the image to generate.

**`images`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`ImageGenerationInput`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional reference images to edit or transform. Passing reference images sends the request to the provider's image-editing path, preserving the order of the images. Each item can be a [`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage), [`ImageUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ImageUrl), or [`UploadedFile`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UploadedFile); see the [Image Generation guide](https://pydantic.dev/docs/ai/guides/image-generation/#editing-images) for the reference-input types each provider accepts.

**`settings`** : [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to override the generator's default settings for this call.

###### Raises

-   `ContentFilterError` -- If the provider blocked the request, or every generated image, for content moderation.
-   `UserError` -- If the prompt is empty, a setting is invalid, or the model cannot produce the requested dimensions.

##### generate\_sync

```python
def generate_sync(
    prompt: str,
    *,
    images: Sequence[ImageGenerationInput] | None = None,
    settings: ImageGenerationSettings | None = None,
) -> ImageGenerationResult
```

Synchronous version of [`generate()`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerator.generate).

###### Returns

[`ImageGenerationResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationResult) -- An [`ImageGenerationResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationResult) containing the [`ImageGenerationResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationResult) -- generated images and metadata about the operation.

###### Parameters

**`prompt`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The text prompt describing the image to generate.

**`images`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`ImageGenerationInput`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional reference images to edit or transform.

**`settings`** : [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional settings to override the generator's default settings for this call.

###### Raises

-   `ContentFilterError` -- If the provider blocked the request, or every generated image, for content moderation.
-   `UserError` -- If the prompt is empty, a setting is invalid, or the model cannot produce the requested dimensions.

### instrument\_image\_generation\_model

```python
def instrument_image_generation_model(
    model: ImageGenerationModel,
    instrument: InstrumentationSettings | bool,
) -> ImageGenerationModel
```

Instrument an image generation model with OpenTelemetry/logfire.

#### Returns

[`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel)

### infer\_image\_generation\_model

```python
def infer_image_generation_model(
    model: ImageGenerationModel | KnownImageGenerationModelName | str,
    *,
    provider_factory: Callable[[str], Provider[Any]] = infer_provider,
) -> ImageGenerationModel
```

Infer the image generation model from the name.

#### Returns

[`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel)

### merge\_image\_generation\_settings

```python
def merge_image_generation_settings(
    base: ImageGenerationSettings | None,
    overrides: ImageGenerationSettings | None,
) -> ImageGenerationSettings | None
```

Merge two sets of image generation settings, with overrides taking precedence.

#### Returns

[`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### ImageDimensions

Exact output image dimensions as `(width, height)` in pixels.

Supported values are model-specific. GPT Image 1.x accepts three fixed shapes; GPT Image 2 accepts any shape satisfying its edge, area, multiple-of-16, and 3:1 limits; Gemini and Grok Imagine accept the documented or verified shapes for their aspect-ratio and resolution tiers. See the [Image Generation guide](https://pydantic.dev/docs/ai/guides/image-generation/#supported-exact-dimensions) for the complete matrix.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `tuple[int, int]`

### ImageGenerationInput

An image input that can be used as a reference for image generation.

**Default:** `TypeAliasType('ImageGenerationInput', ImageUrl | BinaryImage | UploadedFile)`

### ImageGenerationAspectRatio

Portable aspect ratios accepted by at least one direct image model adapter.

The canonical exact shape a ratio produces is model-family specific, and the families name different subsets: GPT Image 1.x three, GPT Image 2 sixteen, Gemini 2.5 Flash and Gemini 3 Pro ten, Gemini 3.1 Flash and Flash Lite fourteen, and Grok Imagine thirteen. A ratio outside a family's set still reaches Gemini, which validates it itself; OpenAI and xAI have no way to carry it and raise `UserError`. See the [Image Generation guide](https://pydantic.dev/docs/ai/guides/image-generation/#canonical-dimensions-for-aspect_ratio) for the ratio-to-dimensions matrix.

This is the direct image API's vocabulary. The native image generation tool takes [`ImageAspectRatio`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.ImageAspectRatio) instead, whose ten values are a subset of these twenty.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['1:1', '1:2', '1:4', '1:8', '2:1', '2:3', '3:2', '3:4', '4:1', '4:3', '4:5', '5:4', '8:1', '9:16', '9:19.5', '9:20', '16:9', '19.5:9', '20:9', '21:9']`

### KnownImageGenerationModelName

Known model names that can be used with the `model` parameter of `ImageGenerator`.

`google:` is the Gemini Developer API (Google AI Studio) and `google-cloud:` is Vertex AI, exactly as in [`KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName). A [Pydantic AI Gateway](https://pydantic.dev/docs/ai/overview/gateway/) route is also accepted for Gemini as `gateway/google:<model>`.

**Default:** `TypeAliasType('KnownImageGenerationModelName', Literal['google-cloud:gemini-2.5-flash-image', 'google-cloud:gemini-3-pro-image', 'google-cloud:gemini-3.1-flash-image', 'google-cloud:gemini-3.1-flash-lite-image', 'google:gemini-2.5-flash-image', 'google:gemini-3-pro-image', 'google:gemini-3.1-flash-image', 'google:gemini-3.1-flash-lite-image', 'openai:gpt-image-1', 'openai:gpt-image-1-mini', 'openai:gpt-image-1.5', 'openai:gpt-image-2', 'xai:grok-imagine-image', 'xai:grok-imagine-image-2.0', 'xai:grok-imagine-image-quality'])`

### ImageGenerationModel

**Bases:** `ABC`

Abstract base class for image generation models.

#### Attributes

##### settings

Get the default settings for this model.

**Type:** [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### base\_url

The base URL for the provider API, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### model\_name

The name of the image generation model.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The image generation model provider/system identifier.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(*, settings: ImageGenerationSettings | None = None) -> None
```

Initialize the model with optional settings.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`settings`** : [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

##### generate

`@abstractmethod`

`@async`

```python
def generate(
    prompt: str,
    *,
    images: Sequence[ImageGenerationInput] | None = None,
    settings: ImageGenerationSettings | None = None,
) -> ImageGenerationResult
```

Generate images for the given prompt.

The result always holds at least one image. An implementation with no image to return raises [`ContentFilterError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ContentFilterError) when the provider blocked the output, and [`UnexpectedModelBehavior`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UnexpectedModelBehavior) otherwise, rather than returning an empty result.

###### Returns

[`ImageGenerationResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationResult)

##### prepare\_generate

```python
def prepare_generate(
    prompt: str,
    *,
    images: Sequence[ImageGenerationInput] | None = None,
    settings: ImageGenerationSettings | None = None,
) -> tuple[str, list[ImageGenerationInput], ImageGenerationSettings]
```

Prepare the prompt, reference images, and settings for image generation.

###### Returns

[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ImageGenerationInput`\], [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings)\]

### ImageGenerationInput

An image input that can be used as a reference for image generation.

**Default:** `TypeAliasType('ImageGenerationInput', ImageUrl | BinaryImage | UploadedFile)`

### GeneratedImage

One generated image with normalized content and provider metadata.

#### Attributes

##### content

The generated image as normalized binary content.

**Type:** [`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage)

##### revised\_prompt

Provider-revised or enhanced prompt, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### output\_format

Generated image output format, derived from the bytes the provider returned.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Provider-specific details for this generated image.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### ImageGenerationResult

The result of an image generation operation.

#### Attributes

##### images

Generated images.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`GeneratedImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.GeneratedImage)\]

##### prompt

The input prompt used for generation.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### model\_name

The name of the model that generated the images.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_name

The name of the provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

When the image generation request was made.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) **Default:** `field(default_factory=_now_utc)`

##### usage

Usage statistics for this request.

**Type:** [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage) **Default:** `field(default_factory=RequestUsage)`

##### provider\_details

Provider-specific details from the response.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_response\_id

Unique identifier for this response from the provider, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_url

Provider API URL, if available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### image

The first generated image. Use `images` when the request asked for more than one.

A result always holds at least one image: the [`ImageGenerationModel.generate`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel.generate) contract requires an implementation with nothing to return to raise instead of returning an empty result.

**Type:** [`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage)

#### Methods

##### cost

```python
def cost() -> genai_types.PriceCalculation
```

Calculate the cost of the image generation request.

Uses [`genai-prices`](https://github.com/pydantic/genai-prices) for pricing data.

Models priced per token are covered, such as the GPT Image and Gemini image families. The Grok Imagine family raises `LookupError`: it has no entry in the pricing data, and there is no unit that counts generated images to price it with.

###### Returns

`genai_types.PriceCalculation` -- A price calculation object with `total_price`, `input_price`, and other cost details.

###### Raises

-   `LookupError` -- If pricing data is not available for this model/provider.

### ImageGenerationSettings

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Normalized settings for configuring image generation models.

This type contains only settings with the same semantics across every direct image provider. Provider-specific settings classes extend it with prefixed options for controls that are not portable.

#### Attributes

##### dimensions

The exact output dimensions as `(width, height)` in pixels.

This is mutually exclusive with `aspect_ratio`. The selected provider and model must support the exact dimensions; no rounding or nearest-shape fallback is applied. GPT Image 1.x accepts its three fixed shapes, GPT Image 2 validates a continuous constrained range, and Gemini/Grok Imagine accept their model-specific aspect-ratio and resolution table entries. See the `ImageDimensions` documentation for the full matrix.

**Type:** `ImageDimensions`

##### aspect\_ratio

The requested aspect ratio.

Providers with a native aspect-ratio field receive the ratio as given, and reject an unsupported one themselves. OpenAI has no such field, so Pydantic AI maps the ratio to one of the model family's enumerated sizes and raises `UserError` for a ratio outside that set; xAI takes an enum with no member for some portable values and raises `UserError` for those. See the [Image Generation guide](https://pydantic.dev/docs/ai/guides/image-generation/#canonical-dimensions-for-aspect_ratio) for the per-family shapes.

**Type:** `ImageGenerationAspectRatio`

##### extra\_headers

Extra headers to send to the model.

This follows the existing `ModelSettings` and `EmbeddingSettings` escape-hatch pattern. Prefer provider-prefixed typed settings when a setting is part of the supported public API.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### extra\_body

Extra body to send to the model.

This follows the existing `ModelSettings` and `EmbeddingSettings` escape-hatch pattern. Prefer provider-prefixed typed settings when a setting is part of the supported public API.

**Type:** [`object`](https://docs.python.org/3/glossary.html#term-object)

### merge\_image\_generation\_settings

```python
def merge_image_generation_settings(
    base: ImageGenerationSettings | None,
    overrides: ImageGenerationSettings | None,
) -> ImageGenerationSettings | None
```

Merge two sets of image generation settings, with overrides taking precedence.

#### Returns

[`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### ImageDimensions

Exact output image dimensions as `(width, height)` in pixels.

Supported values are model-specific. GPT Image 1.x accepts three fixed shapes; GPT Image 2 accepts any shape satisfying its edge, area, multiple-of-16, and 3:1 limits; Gemini and Grok Imagine accept the documented or verified shapes for their aspect-ratio and resolution tiers. See the [Image Generation guide](https://pydantic.dev/docs/ai/guides/image-generation/#supported-exact-dimensions) for the complete matrix.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `tuple[int, int]`

### ImageGenerationAspectRatio

Portable aspect ratios accepted by at least one direct image model adapter.

The canonical exact shape a ratio produces is model-family specific, and the families name different subsets: GPT Image 1.x three, GPT Image 2 sixteen, Gemini 2.5 Flash and Gemini 3 Pro ten, Gemini 3.1 Flash and Flash Lite fourteen, and Grok Imagine thirteen. A ratio outside a family's set still reaches Gemini, which validates it itself; OpenAI and xAI have no way to carry it and raise `UserError`. See the [Image Generation guide](https://pydantic.dev/docs/ai/guides/image-generation/#canonical-dimensions-for-aspect_ratio) for the ratio-to-dimensions matrix.

This is the direct image API's vocabulary. The native image generation tool takes [`ImageAspectRatio`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.ImageAspectRatio) instead, whose ten values are a subset of these twenty.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['1:1', '1:2', '1:4', '1:8', '2:1', '2:3', '3:2', '3:4', '4:1', '4:3', '4:5', '5:4', '8:1', '9:16', '9:19.5', '9:20', '16:9', '19.5:9', '20:9', '21:9']`

### OpenAIImageGenerationSettings

**Bases:** [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings)

Settings used for an OpenAI image generation request.

All fields from [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) are supported, plus OpenAI-specific settings prefixed with `openai_`.

#### Attributes

##### openai\_n

The number of images to generate.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### openai\_output\_format

The generated image format.

**Type:** `OpenAIImageOutputFormat`

##### openai\_size

OpenAI image size setting.

This is provider-specific because OpenAI, Gemini, xAI, and other image APIs use different concepts for pixel sizes, aspect ratios, and resolution tiers.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### openai\_quality

GPT Image quality setting.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['low', 'medium', 'high', 'auto'\]

##### openai\_background

OpenAI image background setting.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['transparent', 'opaque', 'auto'\]

##### openai\_input\_fidelity

OpenAI input fidelity setting for image editing.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['high', 'low'\]

##### openai\_moderation

OpenAI moderation strictness for image generation.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['auto', 'low'\]

##### openai\_output\_compression

OpenAI output compression setting.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### openai\_user

OpenAI end-user identifier.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### OpenAIImageGenerationModel

**Bases:** [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel)

OpenAI image generation model implementation.

This model works with OpenAI's Images API and the GPT Image model family, such as `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1`, and `gpt-image-1-mini`.

The `dall-e-2` and `dall-e-3` models are not supported and raise a [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) on construction, even though they are part of the OpenAI SDK's `ImageModel` type: they diverge from the GPT Image request and response contract in size, quality, image count, and response format. Unrecognized model names are passed through to OpenAI, so newly released GPT Image models work without a Pydantic AI release.

Example:

```python
from pydantic_ai.images.openai import OpenAIImageGenerationModel
from pydantic_ai.providers.openai import OpenAIProvider

# Using OpenAI directly
model = OpenAIImageGenerationModel('gpt-image-2')

# Using a custom base URL or client configuration
model = OpenAIImageGenerationModel(
    'gpt-image-2',
    provider=OpenAIProvider(base_url='https://my-provider.com/v1'),
)
```

#### Attributes

##### model\_name

The image generation model name.

**Type:** `OpenAIImageGenerationModelName`

##### system

The image generation model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: OpenAIImageGenerationModelName,
    *,
    provider: Literal['openai'] | Provider[AsyncOpenAI] = 'openai',
    settings: ImageGenerationSettings | None = None,
)
```

Initialize an OpenAI image generation model.

###### Parameters

**`model_name`** : `OpenAIImageGenerationModelName`

The name of the GPT Image model to use. See [OpenAI's image generation guide](https://developers.openai.com/api/docs/guides/image-generation) for available models.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['openai'\] | `Provider`\[`AsyncOpenAI`\] _Default:_ `'openai'`

The provider to use for authentication and API access. Can be:

-   `'openai'` (default): Uses the standard OpenAI API
-   A [`Provider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.Provider) instance for custom configuration, such as an [`OpenAIProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.openai.OpenAIProvider) with a custom `base_url` or `openai_client`

**`settings`** : [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) to use as defaults for this model.

###### Raises

-   `UserError` -- If `model_name` is a DALL·E model, which this adapter does not support.

### OpenAIImageGenerationModelName

Possible OpenAI image generation model names.

**Default:** `str | LatestOpenAIImageModelNames`

### OpenAIImageOutputFormat

The image formats OpenAI's image endpoints accept as a requested output format.

This types the `openai_output_format` request setting. It does not describe [`GeneratedImage.output_format`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.GeneratedImage), which is a plain `str | None` derived from the media type each adapter resolves for the bytes the provider returned.

**Default:** `Literal['png', 'webp', 'jpeg']`

### GoogleImageGenerationSettings

**Bases:** [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings)

Settings used for a Google image generation request.

All fields from [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) are supported, plus Google-specific settings prefixed with `google_`.

#### Attributes

##### google\_image\_config

Google image generation configuration, including aspect ratio and image size.

**Type:** `ImageConfigDict`

### GoogleImageGenerationModel

**Bases:** [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel)

Google Gemini image generation model implementation.

This model works with the Gemini image models, such as `gemini-3.1-flash-image` and `gemini-3-pro-image`, through the Gemini Developer API (Google AI Studio) or Google Cloud (Vertex AI). It asks Gemini for an image-only response, as [`ImageGenerator`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerator) returns generated images rather than Gemini's optional conversational text.

Example:

```python
from pydantic_ai.images.google import GoogleImageGenerationModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.google_cloud import GoogleCloudProvider

# Using the Gemini API (requires GOOGLE_API_KEY env var)
model = GoogleImageGenerationModel('gemini-3.1-flash-image')

# Or with explicit provider configuration
model = GoogleImageGenerationModel(
    'gemini-3.1-flash-image',
    provider=GoogleProvider(api_key='your-api-key'),
)

# Using Google Cloud (Vertex AI)
model = GoogleImageGenerationModel(
    'gemini-3.1-flash-image',
    provider=GoogleCloudProvider(project='my-project', location='global'),
)
```

#### Attributes

##### model\_name

The image generation model name.

**Type:** `GoogleImageGenerationModelName`

##### system

The image generation model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: GoogleImageGenerationModelName,
    *,
    provider: Literal['google', 'google-cloud'] | Provider[Client] = 'google',
    settings: ImageGenerationSettings | None = None,
)
```

Initialize a Google image generation model.

###### Parameters

**`model_name`** : `GoogleImageGenerationModelName`

The name of the Gemini image model to use. See [Google's image generation documentation](https://ai.google.dev/gemini-api/docs/image-generation) for available models.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['google', 'google-cloud'\] | `Provider`\[`Client`\] _Default:_ `'google'`

The provider to use for authentication and API access. Can be:

-   `'google'` (default): Uses the Gemini Developer API (Google AI Studio)
-   `'google-cloud'`: Uses Google Cloud (formerly known as Vertex AI)
-   A [`GoogleProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.google.GoogleProvider) or [`GoogleCloudProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.google_cloud.GoogleCloudProvider) instance for custom configuration

**`settings`** : [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) to use as defaults for this model.

### LatestGoogleImageGenerationModelNames

Latest Gemini image generation models, served identically by the Gemini API and Google Cloud (Vertex AI).

See the [Gemini image generation documentation](https://ai.google.dev/gemini-api/docs/image-generation) for available models and their capabilities.

**Default:** `Literal['gemini-2.5-flash-image', 'gemini-3-pro-image', 'gemini-3.1-flash-image', 'gemini-3.1-flash-lite-image']`

### GoogleImageGenerationModelName

Possible Google image generation model names.

**Default:** `str | LatestGoogleImageGenerationModelNames`

### XaiImageGenerationSettings

**Bases:** [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings)

Settings used for an xAI image generation request.

All fields from [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) are supported, plus xAI-specific settings prefixed with `xai_`.

#### Attributes

##### xai\_n

The number of images to generate.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### xai\_user

A unique identifier representing your end-user.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### xai\_aspect\_ratio

The aspect ratio of the generated image.

**Type:** `XaiImageAspectRatio`

##### xai\_resolution

The resolution tier of the generated image.

**Type:** `ImageResolution`

### XaiImageGenerationModel

**Bases:** [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel)

xAI image generation model implementation.

This model works with the Grok Imagine models, such as `grok-imagine-image` and `grok-imagine-image-quality`, through the official xAI SDK, which connects over gRPC.

xAI moderates silently: a flagged image in a batch comes back empty rather than as an error, so the clean images are returned and the flagged positions are reported through `provider_details['moderated_image_indices']`. A [`ContentFilterError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ContentFilterError) is raised only when every image was flagged. See the [xAI model page](https://pydantic.dev/docs/ai/models/xai/#image-generation) for details.

Example:

```python
from pydantic_ai.images.xai import XaiImageGenerationModel
from pydantic_ai.providers.xai import XaiProvider

# Using xAI directly (requires XAI_API_KEY env var)
model = XaiImageGenerationModel('grok-imagine-image')

# Or with explicit provider configuration
model = XaiImageGenerationModel(
    'grok-imagine-image',
    provider=XaiProvider(api_key='your-api-key'),
)
```

#### Attributes

##### model\_name

The image generation model name.

**Type:** `XaiImageGenerationModelName`

##### system

The image generation model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: XaiImageGenerationModelName,
    *,
    provider: Literal['xai'] | Provider[AsyncClient] = 'xai',
    settings: ImageGenerationSettings | None = None,
)
```

Initialize an xAI image generation model.

###### Parameters

**`model_name`** : `XaiImageGenerationModelName`

The name of the Grok Imagine model to use. See [xAI's image generation documentation](https://docs.x.ai/developers/model-capabilities/images/generation) for available models.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['xai'\] | `Provider`\[`AsyncClient`\] _Default:_ `'xai'`

The provider to use for authentication and API access. Can be:

-   `'xai'` (default): Uses the standard xAI API
-   An [`XaiProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.xai.XaiProvider) instance for custom configuration, such as a custom `api_host` or `xai_client`

**`settings`** : [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) to use as defaults for this model.

### XaiImageGenerationModelName

Possible xAI image generation model names.

**Default:** `str | LatestXaiImageGenerationModelNames`

### TestImageGenerationModel

**Bases:** [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel)

A deterministic image generation model for testing.

This model returns a single 1x1 PNG without making any API calls, and records the reference images and settings used in the last call via the `last_images` and `last_settings` attributes.

Example:

```python
from pydantic_ai import ImageGenerator
from pydantic_ai.images import TestImageGenerationModel

test_model = TestImageGenerationModel()
generator = ImageGenerator('openai:gpt-image-2')


async def main():
    with generator.override(model=test_model):
        await generator.generate('A test image', settings={'aspect_ratio': '16:9'})
        print(test_model.last_settings)
        #> {'aspect_ratio': '16:9'}
        print(test_model.last_images)
        #> []
```

#### Attributes

##### last\_images

The reference images passed to the most recent generate call.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ImageGenerationInput`\] **Default:** `[]`

##### last\_settings

The settings used in the most recent generate call.

**Type:** [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### model\_name

The image generation model name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### system

The image generation model provider.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: str = 'test',
    *,
    provider_name: str = 'test',
    settings: ImageGenerationSettings | None = None,
)
```

Initialize the test image generation model.

###### Parameters

**`model_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'test'`

The model name to report in results.

**`provider_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'test'`

The provider name to report in results.

**`settings`** : [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional default settings for the model.

### WrapperImageGenerationModel

**Bases:** [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel)

Base class for image generation models that wrap another model.

Use this as a base class to create custom image generation model wrappers that modify behavior (e.g., caching, logging, rate limiting) while delegating to an underlying model.

By default, all methods are passed through to the wrapped model. Override specific methods to customize behavior.

#### Attributes

##### wrapped

The underlying image generation model being wrapped.

**Type:** [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) **Default:** `infer_image_generation_model(wrapped) if isinstance(wrapped, str) else wrapped`

##### settings

Get the settings from the wrapped image generation model.

**Type:** [`ImageGenerationSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_init\_\_

```python
def __init__(wrapped: ImageGenerationModel | str)
```

Initialize the wrapper with an image generation model.

###### Parameters

**`wrapped`** : [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The model to wrap. Can be an [`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel) instance or a model name string (e.g., `'openai:gpt-image-1'`).

### InstrumentedImageGenerationModel

**Bases:** `WrapperImageGenerationModel`

Image generation model which wraps another model for OpenTelemetry instrumentation.

#### Attributes

##### instrumentation\_settings

Instrumentation settings for this model.

**Type:** [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) **Default:** `options or InstrumentationSettings()`

### instrument\_image\_generation\_model

```python
def instrument_image_generation_model(
    model: ImageGenerationModel,
    instrument: InstrumentationSettings | bool,
) -> ImageGenerationModel
```

Instrument an image generation model with OpenTelemetry/logfire.

#### Returns

[`ImageGenerationModel`](https://pydantic.dev/docs/ai/api/pydantic-ai/images/#pydantic_ai.images.ImageGenerationModel)

---
