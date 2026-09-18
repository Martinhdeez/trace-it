# [pydantic_ai.messages](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/)

# pydantic\_ai.messages

The structure of [`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage) can be shown as a graph:

```mermaid
graph RL
    SystemPromptPart(SystemPromptPart) --- ModelRequestPart
    UserPromptPart(UserPromptPart) --- ModelRequestPart
    ToolReturnPart(ToolReturnPart) --- ModelRequestPart
    RetryPromptPart(RetryPromptPart) --- ModelRequestPart
    ToolAvailabilityDeltaPart(ToolAvailabilityDeltaPart) --- ModelRequestPart
    TextPart(TextPart) --- ModelResponsePart
    ToolCallPart(ToolCallPart) --- ModelResponsePart
    ThinkingPart(ThinkingPart) --- ModelResponsePart
    ModelRequestPart("ModelRequestPart<br>(Union)") --- ModelRequest
    ModelRequest("ModelRequest(parts=list[...])") --- ModelMessage
    ModelResponsePart("ModelResponsePart<br>(Union)") --- ModelResponse
    ModelResponse("ModelResponse(parts=list[...])") --- ModelMessage("ModelMessage<br>(Union)")
```

### SystemPromptPart

A system prompt, generally written by the application developer.

This gives the model context and guidance on how to respond.

#### Attributes

##### content

The content of the prompt.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

The timestamp of the prompt.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) **Default:** `field(default_factory=_now_utc)`

##### dynamic\_ref

The ref of the dynamic system prompt function that generated this part.

Only set if system prompt is dynamic, see [`system_prompt`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.system_prompt) for more information.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['system-prompt'\] **Default:** `'system-prompt'`

### FileUrl

**Bases:** `ABC`

Abstract base class for any URL-based file.

#### Attributes

##### url

The URL of the file.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### force\_download

Controls whether the file is downloaded and how SSRF protection is applied:

-   If `False`, the URL is sent directly to providers that support it. For providers that don't, the file is downloaded with SSRF protection (blocks private IPs and cloud metadata).
-   If `True`, the file is always downloaded with SSRF protection (blocks private IPs and cloud metadata).
-   If `'allow-local'`, the file is always downloaded, allowing private IPs but still blocking cloud metadata.

**Type:** `ForceDownloadMode` **Default:** `False`

##### vendor\_metadata

Vendor-specific metadata for the file.

Supported by:

-   `GoogleModel`: `VideoUrl.vendor_metadata` is used as `video_metadata`: [https://ai.google.dev/gemini-api/docs/video-understanding#customize-video-processing](https://ai.google.dev/gemini-api/docs/video-understanding#customize-video-processing), and `vendor_metadata['media_resolution']` is forwarded as the per-Part `media_resolution` field for any file type: [https://ai.google.dev/gemini-api/docs/media-resolution](https://ai.google.dev/gemini-api/docs/media-resolution)
-   `OpenAIChatModel`, `OpenAIResponsesModel`: `ImageUrl.vendor_metadata['detail']` is used as `detail` setting for images
-   `XaiModel`: `ImageUrl.vendor_metadata['detail']` is used as `detail` setting for images
-   `GroqModel`: `ImageUrl.vendor_metadata['detail']` is used as `detail` setting for images
-   `MistralModel`: `ImageUrl.vendor_metadata['detail']` is used as `detail` setting for images

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### media\_type

Return the media type of the file, based on the URL or the provided `media_type`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### identifier

The identifier of the file, such as a unique ID.

This identifier can be provided to the model in a message to allow it to refer to this file in a tool call argument, and the tool can look up the file in question by iterating over the message history and finding the matching `FileUrl`.

This identifier is only automatically passed to the model when the `FileUrl` is returned by a tool. If you're passing the `FileUrl` as a user message, it's up to you to include a separate text part with the identifier, e.g. "This is file <identifier>:" preceding the `FileUrl`.

It's also included in inline-text delimiters for providers that require inlining text documents, so the model can distinguish multiple files.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### format

The file format.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### VideoUrl

**Bases:** [`FileUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl)

A URL to a video.

#### Attributes

##### url

The URL of the video.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### kind

Type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['video-url'\] **Default:** `'video-url'`

##### is\_youtube

True if the URL is on a YouTube host that models can resolve directly.

This is a specific set of hosts rather than every YouTube-owned domain, so `music.youtube.com` is deliberately not one of them.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### format

The file format of the video.

The choice of supported formats were based on the Bedrock Converse API. Other APIs don't require to use a format.

**Type:** `VideoFormat`

### AudioUrl

**Bases:** [`FileUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl)

A URL to an audio file.

#### Attributes

##### url

The URL of the audio file.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### kind

Type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['audio-url'\] **Default:** `'audio-url'`

##### format

The file format of the audio file.

**Type:** `AudioFormat`

### ImageUrl

**Bases:** [`FileUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl)

A URL to an image.

#### Attributes

##### url

The URL of the image.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### kind

Type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['image-url'\] **Default:** `'image-url'`

##### format

The file format of the image.

The choice of supported formats were based on the Bedrock Converse API. Other APIs don't require to use a format.

**Type:** `ImageFormat`

### DocumentUrl

**Bases:** [`FileUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl)

The URL of the document.

#### Attributes

##### url

The URL of the document.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### kind

Type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['document-url'\] **Default:** `'document-url'`

##### format

The file format of the document.

The choice of supported formats were based on the Bedrock Converse API. Other APIs don't require to use a format.

**Type:** `DocumentFormat`

### TextContent

String content that is tagged with additional metadata.

This is useful for including metadata that can be accessed programmatically by the application, but is not sent to the LLM.

#### Attributes

##### content

The content that is sent to the LLM.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### metadata

Additional data that can be accessed programmatically by the application but is not sent to the LLM.

`ModelMessagesTypeAdapter` preserves this field, but as application-only data it is not guaranteed to survive a round-trip through the UI adapters; see [Storing and loading messages](https://pydantic.dev/docs/ai/core-concepts/message-history/#storing-and-loading-messages-to-json).

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) **Default:** `None`

##### kind

Type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['text-content'\] **Default:** `'text-content'`

### BinaryContent

Binary content, e.g. an audio or image file.

#### Attributes

##### data

The binary file data.

Use `.base64` to get the base64-encoded string.

**Type:** [`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes)

##### media\_type

The media type of the binary data.

**Type:** `AudioMediaType` | `ImageMediaType` | `DocumentMediaType` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### vendor\_metadata

Vendor-specific metadata for the file.

Supported by:

-   `GoogleModel`: `BinaryContent.vendor_metadata` is used as `video_metadata`: [https://ai.google.dev/gemini-api/docs/video-understanding#customize-video-processing](https://ai.google.dev/gemini-api/docs/video-understanding#customize-video-processing), and `BinaryContent.vendor_metadata['media_resolution']` is forwarded as the per-Part `media_resolution` field: [https://ai.google.dev/gemini-api/docs/media-resolution](https://ai.google.dev/gemini-api/docs/media-resolution)
-   `OpenAIChatModel`, `OpenAIResponsesModel`: `BinaryContent.vendor_metadata['detail']` is used as `detail` setting for images
-   `XaiModel`: `BinaryContent.vendor_metadata['detail']` is used as `detail` setting for images
-   `GroqModel`: `BinaryContent.vendor_metadata['detail']` is used as `detail` setting for images
-   `MistralModel`: `BinaryContent.vendor_metadata['detail']` is used as `detail` setting for images

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### kind

Type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['binary'\] **Default:** `'binary'`

##### identifier

Identifier for the binary content, such as a unique ID.

This identifier can be provided to the model in a message to allow it to refer to this file in a tool call argument, and the tool can look up the file in question by iterating over the message history and finding the matching `BinaryContent`.

This identifier is only automatically passed to the model when the `BinaryContent` is returned by a tool. If you're passing the `BinaryContent` as a user message, it's up to you to include a separate text part with the identifier, e.g. "This is file <identifier>:" preceding the `BinaryContent`.

It's also included in inline-text delimiters for providers that require inlining text documents, so the model can distinguish multiple files.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### data\_uri

Convert the `BinaryContent` to a data URI.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### base64

Return the binary data as a base64-encoded string. Default encoding is UTF-8.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### is\_audio

Return `True` if the media type is an audio type.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### is\_image

Return `True` if the media type is an image type.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### is\_video

Return `True` if the media type is a video type.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### is\_document

Return `True` if the media type is a document type.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### format

The file format of the binary content.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### narrow\_type

`@staticmethod`

```python
def narrow_type(bc: BinaryContent) -> BinaryContent | BinaryImage
```

Narrow the type of the `BinaryContent` to `BinaryImage` if it's an image.

###### Returns

[`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) | [`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage)

##### from\_data\_uri

`@classmethod`

```python
def from_data_uri(cls, data_uri: str) -> BinaryContent
```

Create a `BinaryContent` from a data URI.

###### Returns

[`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent)

##### from\_path

`@classmethod`

```python
def from_path(cls, path: PathLike[str]) -> BinaryContent
```

Create a `BinaryContent` from a path.

Defaults to 'application/octet-stream' if the media type cannot be inferred.

###### Returns

[`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent)

###### Raises

-   `FileNotFoundError` -- if the file does not exist.
-   `PermissionError` -- if the file cannot be read.

### BinaryImage

**Bases:** [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent)

Binary content that's guaranteed to be an image.

### BinaryAudio

**Bases:** [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent)

Binary content that's guaranteed to be audio.

### CachePoint

A cache point marker for prompt caching.

Can be inserted into UserPromptPart.content to mark cache boundaries. Models that don't support caching will filter these out.

Supported by:

-   Anthropic
-   Amazon Bedrock (Converse API)
-   OpenAI (GPT-5.6 models)
-   OpenRouter (Anthropic and Gemini models via `OpenRouterModel`, plus OpenAI GPT-5.6 models when using `OpenAIChatModel` or `OpenAIResponsesModel` with `OpenRouterProvider`)

#### Attributes

##### kind

Type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['cache-point'\] **Default:** `'cache-point'`

##### ttl

The cache time-to-live, either "5m" (5 minutes) or "1h" (1 hour).

Supported by:

-   Anthropic -- see [https://docs.claude.com/en/docs/build-with-claude/prompt-caching#1-hour-cache-duration](https://docs.claude.com/en/docs/build-with-claude/prompt-caching#1-hour-cache-duration) for more information.
-   Amazon Bedrock (Converse API) -- see [https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html) for more information.
-   OpenAI ignores this per-marker value and uses the request-wide `openai_prompt_cache_options['ttl']` setting instead.
-   OpenRouter with Anthropic models (automatically omitted for Gemini models, which do not support explicit TTL).

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['5m', '1h'\] **Default:** `'5m'`

### UploadedFile

A reference to a file uploaded to a provider's file storage by ID.

This allows referencing files that have been uploaded via provider-specific file APIs rather than providing the file content directly.

Supported by:

-   [`AnthropicModel`](https://pydantic.dev/docs/ai/api/models/anthropic/#pydantic_ai.models.anthropic.AnthropicModel)
-   [`OpenAIChatModel`](https://pydantic.dev/docs/ai/api/models/openai/#pydantic_ai.models.openai.OpenAIChatModel)
-   [`OpenAIResponsesModel`](https://pydantic.dev/docs/ai/api/models/openai/#pydantic_ai.models.openai.OpenAIResponsesModel)
-   [`BedrockConverseModel`](https://pydantic.dev/docs/ai/api/models/bedrock/#pydantic_ai.models.bedrock.BedrockConverseModel)
-   [`GoogleModel`](https://pydantic.dev/docs/ai/api/models/google/#pydantic_ai.models.google.GoogleModel) (Gemini API: [Files API](https://ai.google.dev/gemini-api/docs/files) URIs, Google Cloud: GCS `gs://` URIs)
-   [`XaiModel`](https://pydantic.dev/docs/ai/api/models/xai/#pydantic_ai.models.xai.XaiModel)

#### Attributes

##### file\_id

The provider-specific file identifier.

For most providers, this is the file ID returned by the provider's upload API. For GoogleModel (Google Cloud), this must be a GCS URI (`gs://bucket/path`). For GoogleModel (Gemini API), this must be a Google Files API URI (`https://generativelanguage.googleapis.com/...`). For BedrockConverseModel, this must be an S3 URI (`s3://bucket/key`).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_name

The provider this file belongs to.

This is required because file IDs are not portable across providers, and using a file ID with the wrong provider will always result in an error.

Tip: Use `model.system` to get the provider name dynamically.

**Type:** `UploadedFileProviderName`

##### vendor\_metadata

Vendor-specific metadata for the file.

The expected shape of this dictionary depends on the provider:

Supported by:

-   `GoogleModel`: used as `video_metadata` for video files, and `UploadedFile.vendor_metadata['media_resolution']` is forwarded as the per-Part `media_resolution` field: [https://ai.google.dev/gemini-api/docs/media-resolution](https://ai.google.dev/gemini-api/docs/media-resolution)
-   `OpenAIResponsesModel`: `UploadedFile.vendor_metadata['detail']` is used as `detail` setting for image files

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### kind

Type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['uploaded-file'\] **Default:** `'uploaded-file'`

##### media\_type

Return the media type of the file, inferred from `file_id` if not explicitly provided.

Note: Inference relies on the file extension in `file_id`. For opaque file IDs (e.g., `'file-abc123'`), the media type will default to `'application/octet-stream'`. Inference relies on Python's `mimetypes` module, whose results may vary across platforms.

Required by some providers (e.g., Bedrock) for certain file types.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### identifier

The identifier of the file, such as a unique ID.

This identifier can be provided to the model in a message to allow it to refer to this file in a tool call argument, and the tool can look up the file in question by iterating over the message history and finding the matching `UploadedFile`.

This identifier is only automatically passed to the model when the `UploadedFile` is returned by a tool. If you're passing the `UploadedFile` as a user message, it's up to you to include a separate text part with the identifier, e.g. "This is file <identifier>:" preceding the `UploadedFile`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### format

A general-purpose media-type-to-format mapping.

Maps media types to format strings (e.g. `'image/png'` -> `'png'`). Covers image, video, audio, and document types. Currently used by Bedrock, which requires explicit format strings.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### ToolReturn

**Bases:** `Generic[_ToolReturnValueT]`

A structured tool return that separates the tool result from additional content sent to the model.

Can be parameterized with a type to enable return schema generation:

-   `ToolReturn[User]` -- generates a return schema for `User`
-   `ToolReturn` (bare) -- no return schema generated

#### Attributes

##### return\_value

The return value to be used in the tool response.

**Type:** `ToolReturnContent`

##### content

Content sent to the model as a separate `UserPromptPart`.

Use this when you want content to appear outside the tool result message. For multimodal content that should be sent natively in the tool result, return it directly from the tool function or include it in `return_value`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`UserContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserContent)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### metadata

Additional data accessible by the application but not sent to the LLM.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) **Default:** `None`

##### tools

Names of deferred tools made available by this tool call.

The names are recorded verbatim in message history in a sibling [`ToolAvailabilityDeltaPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolAvailabilityDeltaPart), then filtered against the currently served tool definitions at render time. A name that matches no deferred tool, such as a typo or an always-visible tool, is a silent no-op by design.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### UserPromptPart

A user prompt, generally written by the end user.

Content comes from the `user_prompt` parameter of [`Agent.run`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run), [`Agent.run_sync`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run_sync), and [`Agent.run_stream`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run_stream).

#### Attributes

##### content

The content of the prompt.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`UserContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserContent)\]

##### timestamp

The timestamp of the prompt.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) **Default:** `field(default_factory=_now_utc)`

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['user-prompt'\] **Default:** `'user-prompt'`

### BaseToolReturnPart

Base class for tool return parts.

#### Attributes

##### tool\_name

The name of the tool that was called.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### content

The tool return content, which may include multimodal files.

**Type:** `ToolReturnContent`

##### tool\_call\_id

The tool call identifier, this is used by some models including OpenAI.

In case the tool call id is not provided by the model, Pydantic AI will generate a random one.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `field(default_factory=_generate_tool_call_id)`

##### tool\_kind

Discriminator for the typed subclass of this part (e.g. `'tool-search'`).

`None` for any part without a typed subclass -- including all user-defined tools and all native tools without a dedicated typed call/return shape. Subclasses that pin this to a [`ToolPartKind`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolPartKind) literal:

-   [`ToolSearchCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchCallPart) / [`ToolSearchReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchReturnPart) -- `'tool-search'`
-   [`NativeToolSearchCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolSearchCallPart) / [`NativeToolSearchReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolSearchReturnPart) -- `'tool-search'`

**Type:** `ToolPartKind` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### metadata

Additional data accessible by the application but not sent to the LLM.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) **Default:** `None`

##### timestamp

The timestamp, when the tool returned.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) **Default:** `field(default_factory=_now_utc)`

##### outcome

The outcome of the tool call.

-   `'success'`: The tool executed successfully.
-   `'failed'`: The tool call failed -- the tool raised an error during execution (the common case), or an args validator or tool hook reported a failure via [`ToolFailed`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ToolFailed).
-   `'denied'`: The tool call was denied -- either by the approval mechanism or by a [`HandleDeferredToolCalls`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.HandleDeferredToolCalls) handler returning [`ToolDenied`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDenied).
-   `'interrupted'`: The tool call did not produce a result because the run was interrupted (e.g. a cancelled stream or a crash mid-execution); synthesized during message-history repair.

Only `'failed'` is mapped to a provider's native error channel (e.g. Anthropic `is_error`, Bedrock `status='error'`). A denial is a deliberate policy decision rather than a runtime error, while an interruption means no result was produced. Both are sent as ordinary results; their content tells the model what happened without suggesting a transient tool failure.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['success', 'failed', 'denied', 'interrupted'\] **Default:** `'success'`

##### files

The multimodal file parts from `content` (`ImageUrl`, `AudioUrl`, `DocumentUrl`, `VideoUrl`, `BinaryContent`).

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`MultiModalContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.MultiModalContent)\]

#### Methods

##### content\_items

```python
def content_items(*, mode: Literal['raw'] = 'raw') -> list[ToolReturnContent]
def content_items(
    *,
    mode: Literal['str'],
    wrap_if_error: bool = True,
) -> list[str | MultiModalContent]
def content_items(
    *,
    mode: Literal['jsonable'],
    wrap_if_error: bool = True,
) -> list[Any | MultiModalContent]
```

Return content as a flat list for iteration, with optional serialization.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`ToolReturnContent`\] | [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`MultiModalContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.MultiModalContent)\] | [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any) | [`MultiModalContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.MultiModalContent)\]

###### Parameters

**`mode`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['raw', 'str', 'jsonable'\] _Default:_ `'raw'`

Controls serialization of non-file items:

-   `'raw'`: No serialization. Returns items as-is.
-   `'str'`: Non-file items are serialized to strings via `tool_return_ta`. File items (`MultiModalContent`) pass through unchanged.
-   `'jsonable'`: Non-file items are serialized to JSON-compatible Python objects via `tool_return_ta`. File items pass through unchanged.

**`wrap_if_error`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to wrap failed tool returns in an `{"error": ...}` object (ignored in `'raw'` mode). When `True` (the default), a failed return's non-file data collapses into a single wrapped error item so providers without a native error channel still see the failure explicitly; files pass through unchanged. Set this to `False` when the provider has a native error channel (e.g. Anthropic `is_error`) and should receive the content unwrapped.

##### model\_response\_str

```python
def model_response_str(*, wrap_if_error: bool = True) -> str
```

Return a string representation of the data content for the model.

This excludes multimodal files - use `.files` to get those separately.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

###### Parameters

**`wrap_if_error`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to wrap failed tool returns in an `{"error": ...}` object. Set this to `False` when the provider has a native error channel.

##### model\_response\_object

```python
def model_response_object(*, wrap_if_error: bool = True) -> dict[str, Any]
```

Return a dictionary representation of the data content, wrapping non-dict types appropriately.

This excludes multimodal files - use `.files` to get those separately. Gemini supports JSON dict return values, but no other JSON types, hence we wrap anything else in a dict.

###### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

###### Parameters

**`wrap_if_error`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to wrap failed tool returns in an `{"error": ...}` object. Set this to `False` when the provider has a native error channel.

##### structured\_content

```python
def structured_content() -> dict[str, Any] | list[Any] | None
```

Return `content` as structured JSON data (a `dict` or `list`), or `None` if it has none.

A JSON string is parsed; already-structured content is returned as-is; a plain/non-JSON string, scalar, or multimodal content yields `None` (there is no structured payload). A read-side companion to [`files`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BaseToolReturnPart.files) and [`model_response_object`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BaseToolReturnPart.model_response_object); some UI wire formats (e.g. AG-UI) transmit tool results as JSON strings, so [`narrow_type`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturnPart.narrow_type) uses it to recover the structured payload a typed return subclass expects.

###### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### model\_response\_str\_and\_user\_content

```python
def model_response_str_and_user_content(
    *,
    wrap_if_error: bool = True,
) -> tuple[str, list[UserContent]]
```

Build a text-only tool result with multimodal files extracted for a trailing user message.

For providers whose tool result API only accepts text. Multimodal files are referenced by identifier in the tool result text ('See file {id}.') and included in full in the returned file content list.

Each file is framed by `_tool_result_provenance_tags` so the model can tell it from the user's own uploads, which travel on the same channel.

###### Returns

[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`UserContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserContent)\]\]

###### Parameters

**`wrap_if_error`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to wrap failed tool returns in an `{"error": ...}` object. Set this to `False` when the provider has a native error channel.

##### has\_content

```python
def has_content() -> bool
```

Return `True` if the tool return has content.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### ToolReturnPart

**Bases:** [`BaseToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BaseToolReturnPart)

A tool return message, this encodes the result of running a tool.

#### Attributes

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool-return'\] **Default:** `'tool-return'`

#### Methods

##### narrow\_type

`@staticmethod`

```python
def narrow_type(
    part: ToolReturnPart,
    *,
    tool_kind: ToolPartKind | None = None,
) -> ToolReturnPart
```

Promote a base `ToolReturnPart` to its typed subclass when its `tool_kind` is registered.

Best-effort: returns the part unchanged when the `tool_kind` (kwarg or on the part) resolves to no registered subclass, and strips an unsubstantiated `tool_kind` when the part's data doesn't validate against that subclass -- keeping it on a base part would break a [`ModelMessagesTypeAdapter`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessagesTypeAdapter) round-trip. For direct construction; Pydantic deserialization promotes automatically via the discriminated union.

###### Returns

[`ToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturnPart)

### NativeToolReturnPart

**Bases:** [`BaseToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BaseToolReturnPart)

A tool return message from a native tool.

For native tools with a stable cross-provider shape (currently `tool_search`), a `NativeToolReturnPart` may be promoted to a typed subclass like [`NativeToolSearchReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolSearchReturnPart) with a narrowed `content` `TypedDict`. See `NativeToolCallPart` for the pattern.

#### Attributes

##### provider\_name

The name of the provider that generated the response.

Required to be set when `provider_details` is set.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Additional data returned by the provider that can't be mapped to standard fields.

This is used for data that is required to be sent back to APIs, as well as data users may want to access programmatically. When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['builtin-tool-return'\] **Default:** `'builtin-tool-return'`

#### Methods

##### narrow\_type

`@staticmethod`

```python
def narrow_type(
    part: NativeToolReturnPart,
    *,
    tool_kind: ToolPartKind | None = None,
) -> NativeToolReturnPart
```

Promote a base `NativeToolReturnPart` to its typed subclass when its `tool_kind` is registered.

Best-effort: returns the part unchanged when the `tool_kind` (kwarg or on the part) resolves to no registered subclass, and strips an unsubstantiated `tool_kind` when the part's data doesn't validate against that subclass -- keeping it on a base part would break a [`ModelMessagesTypeAdapter`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessagesTypeAdapter) round-trip. For direct construction; Pydantic deserialization promotes automatically via the discriminated union.

###### Returns

[`NativeToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolReturnPart)

### RetryPromptPart

A message back to a model asking it to try again.

This can be sent for a number of reasons:

-   Pydantic validation of tool arguments failed, here content is derived from a Pydantic [`ValidationError`](https://docs.pydantic.dev/latest/api/pydantic-core/pydantic_core/#pydantic_core.ValidationError)
-   a tool raised a [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) exception
-   no tool was found for the tool name
-   the model returned plain text when a structured response was expected
-   Pydantic validation of a structured response failed, here content is derived from a Pydantic [`ValidationError`](https://docs.pydantic.dev/latest/api/pydantic-core/pydantic_core/#pydantic_core.ValidationError)
-   an output validator raised a [`ModelRetry`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.ModelRetry) exception

#### Attributes

##### content

Details of why and how the model should retry.

If the retry was triggered by a [`ValidationError`](https://docs.pydantic.dev/latest/api/pydantic-core/pydantic_core/#pydantic_core.ValidationError), this will be a list of error details.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`pydantic_core.ErrorDetails`](https://docs.pydantic.dev/latest/api/pydantic-core/pydantic_core/#pydantic_core.ErrorDetails)\] | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### tool\_name

The name of the tool that was called, if any.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_call\_id

The tool call identifier, this is used by some models including OpenAI.

In case the tool call id is not provided by the model, Pydantic AI will generate a random one.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `field(default_factory=_generate_tool_call_id)`

##### timestamp

The timestamp, when the retry was triggered.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) **Default:** `field(default_factory=_now_utc)`

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['retry-prompt'\] **Default:** `'retry-prompt'`

#### Methods

##### from\_error

`@classmethod`

```python
def from_error(
    cls,
    error: pydantic_core.ValidationError | ModelRetry,
    *,
    tool_name: str | None = None,
    tool_call_id: str | None = None,
) -> RetryPromptPart
```

Build the retry prompt for a failed tool call or output validation.

This is the exact message the model receives when the error is handled by the agent loop, so anything else presenting the failure (e.g. instrumentation spans) must build it the same way.

###### Returns

[`RetryPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.RetryPromptPart)

##### model\_response

```python
def model_response() -> str
```

Return a string message describing why the retry is requested.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### AgentInstructionSource

The agent's own instructions.

There is exactly one agent in scope, so it carries no id.

### ToolsetInstructionSource

A toolset with an `id`.

### CapabilityInstructionSource

A capability with an `id`.

### InstructionId

The key an instruction part is addressed by: who contributed it, and which of their parts it is.

#### Attributes

##### source

Who contributed the part: the agent, a toolset with an `id`, or a capability with an `id`.

**Type:** [`InstructionSource`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionSource)

##### name

Which of that source's parts this is, or `None` to address everything the source contributes.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### InstructionPart

A single instruction part with metadata about its origin.

Instructions are composed of one or more parts, each of which can be static (from a literal string) or dynamic (from a function, template, or toolset). This distinction allows model implementations to make intelligent caching decisions -- e.g. Anthropic's prompt caching can cache the static prefix while leaving dynamic instructions uncached.

#### Attributes

##### content

The text content of this instruction part.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### dynamic

Whether this instruction came from a dynamic source (function, template, or toolset).

Static instructions (`dynamic=False`) come from literal strings passed to `Agent(instructions=...)`. Dynamic instructions (`dynamic=True`) come from `@agent.instructions` functions, `TemplateStr`, or toolset `get_instructions()` methods.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### name

What the author calls this part, relative to whatever contributes it.

Name a part relative to what you own -- `'limits'`, not `'toolset:weather:limits'` -- and the source you contribute through qualifies it into an [`id`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart.id). A name cannot contain `:`, which delimits the segments of an id, and cannot be `'agent'`, which is the key of the agent's own instructions.

Naming a part whose source has no identity of its own leaves `id` as `None`: there is no source key to qualify the name against, so it says what the part is without making it addressable.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### id

The stable key this part is addressed by, or `None` if nothing addresses it.

The framework issues this while collecting instructions, from the author's [`name`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart.name) and the identity of the source that contributed the part -- declare a `name` rather than setting this yourself. A consumer reading [`ModelRequestParameters.instruction_parts`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestParameters.instruction_parts) can persist configuration against an id, because it survives the reordering and rewording that a part's position and text do not.

[`InstructionId.source`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionId.source) is who contributed the part:

-   [`AgentInstructionSource`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentInstructionSource) -- the agent's literal instructions
-   [`ToolsetInstructionSource`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolsetInstructionSource) -- a toolset with an `id`
-   [`CapabilityInstructionSource`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityInstructionSource) -- a capability with an `id`

An id renders and serializes as its segments joined by `:` -- `'agent'`, `'toolset:weather'`, or `'capability:budget:remaining'`.

**Type:** `SerializedInstructionId` **Default:** `None`

##### part\_kind

Part type identifier, used as a discriminator for deserialization.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['instruction'\] **Default:** `'instruction'`

#### Methods

##### join

`@staticmethod`

```python
def join(parts: Sequence[InstructionPart]) -> str | None
```

Join instruction parts into a single string, separated by double newlines.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### sorted

`@staticmethod`

```python
def sorted(parts: Sequence[InstructionPart]) -> list[InstructionPart]
```

Sort instruction parts with static (`dynamic=False`) before dynamic, preserving relative order.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`InstructionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionPart)\]

### ToolAvailabilityDeltaPart

Records that the set of tools available to the model changed at this point.

Additions only. Withdrawing a tool is not supported yet, because no provider can be told about one without also invalidating the prompt cache this part exists to protect: Anthropic rejects a reference to a tool the request doesn't declare, so a withdrawn tool has to leave the `tools` array, and that is itself the invalidation. The name says _availability_ rather than _addition_ so removals can join once they can be done cache-safely -- see [https://github.com/pydantic/pydantic-ai/issues/6985](https://github.com/pydantic/pydantic-ai/issues/6985).

#### Attributes

##### tools\_added

Names of tools this point in history reveals.

A reveal is what the model has been _shown_; whether the tool is callable is the broader availability question, which for a capability-owned tool also asks whether its owning capability is loaded.

**Type:** [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated)\[[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], [`pydantic.Field`](https://docs.pydantic.dev/latest/api/pydantic/fields/#pydantic.fields.Field)(`validation_alias`\=([`pydantic.AliasChoices`](https://docs.pydantic.dev/latest/api/pydantic/aliases/#pydantic.aliases.AliasChoices)(`tools_added`, `added`)))\] **Default:** `field(default_factory=(lambda: []))`

##### tool\_call\_id

The tool call associated with the change, if any.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool-availability-delta'\] **Default:** `'tool-availability-delta'`

#### Methods

##### otel\_message\_parts

```python
def otel_message_parts(
    settings: InstrumentationSettings,
) -> list[_otel_messages.MessagePart]
```

Render the change as trace content.

Tool names are recorded regardless of `include_content`: they aren't user content, they're already visible in the request's tool definitions, and a run where the model suddenly can call something is unreadable without them.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_otel_messages.MessagePart`\]

### ModelRequest

A request generated by Pydantic AI and sent to a model, e.g. a message from the Pydantic AI app to the model.

#### Attributes

##### parts

The parts of the user message.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`ModelRequestPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequestPart)\]

##### timestamp

The timestamp when the request was sent to the model.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### instructions

The instructions string for this request, rendered from structured instruction parts.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### kind

Message type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['request'\] **Default:** `'request'`

##### run\_id

The unique identifier of the agent run in which this message originated.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### conversation\_id

The unique identifier of the conversation this message belongs to.

A conversation spans potentially multiple agent runs that share message history. Emitted as the `gen_ai.conversation.id` OpenTelemetry span attribute on the agent run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### metadata

Additional data that can be accessed programmatically by the application but is not sent to the LLM.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### state

Lifecycle state of the request.

Set to `'interrupted'` when the request was being assembled (e.g. collecting tool returns) and the run was abnormally terminated by an exception or cancellation before the request was sent to the model. In that case `parts` holds only the tool returns that were collected, and is empty if none were. Appears in [`capture_run_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.capture_run_messages) output so consumers can detect partial state.

**Type:** [`ModelRequestState`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequestState) **Default:** `'complete'`

#### Methods

##### user\_text\_prompt

`@classmethod`

```python
def user_text_prompt(
    cls,
    user_prompt: str,
    *,
    instructions: str | None = None,
) -> ModelRequest
```

Create a `ModelRequest` with a single user prompt as text.

###### Returns

[`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest)

### TextPart

A plain text response from a model.

#### Attributes

##### content

The text content of the response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### id

An optional identifier of the text part.

When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_name

The name of the provider that generated the response.

Required to be set when `provider_details` or `id` is set.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Additional data returned by the provider that can't be mapped to standard fields.

This is used for data that is required to be sent back to APIs, as well as data users may want to access programmatically. When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['text'\] **Default:** `'text'`

#### Methods

##### has\_content

```python
def has_content() -> bool
```

Return `True` if the text content is non-empty.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### ThinkingPart

A thinking response from a model.

#### Attributes

##### content

The thinking content of the response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### id

The identifier of the thinking part.

When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### signature

The signature of the thinking.

Supported by:

-   Anthropic (corresponds to the `signature` field)
-   Bedrock (corresponds to the `signature` field)
-   Google (corresponds to the `thought_signature` field)
-   OpenAI (corresponds to the `encrypted_content` field)

When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_name

The name of the provider that generated the response.

Signatures are only sent back to the same provider. Required to be set when `provider_details`, `id` or `signature` is set.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Additional data returned by the provider that can't be mapped to standard fields.

This is used for data that is required to be sent back to APIs, as well as data users may want to access programmatically. When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['thinking'\] **Default:** `'thinking'`

#### Methods

##### has\_content

```python
def has_content() -> bool
```

Return `True` if the thinking content is non-empty.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### CompactionPart

A compaction part that summarizes previous conversation history.

Compaction parts contain an opaque or readable summary of prior messages, produced by provider-specific compaction mechanisms. They must be round-tripped back to the same provider in subsequent requests.

For Anthropic, `content` contains a readable text summary. For OpenAI, `content` is `None` and the encrypted data is stored in `provider_details`.

#### Attributes

##### content

The compaction summary text, if available.

For Anthropic: a readable text summary of compacted messages. For OpenAI: `None` (the compacted content is encrypted and stored in `provider_details`).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### id

The identifier of the compaction part.

When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_name

The name of the provider that generated the compaction.

Compaction data is only sent back to the same provider. Required to be set when `provider_details` or `id` is set.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Additional data returned by the provider that can't be mapped to standard fields.

For OpenAI: contains `encrypted_content` and other fields from `ResponseCompactionItem`. When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['compaction'\] **Default:** `'compaction'`

#### Methods

##### has\_content

```python
def has_content() -> bool
```

Return `True` if the compaction content is non-empty.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### FilePart

A file response from a model.

#### Attributes

##### content

The file content of the response.

**Type:** [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated)\[[`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent), [`pydantic.AfterValidator`](https://docs.pydantic.dev/latest/api/pydantic/functional_validators/#pydantic.functional_validators.AfterValidator)([`BinaryContent.narrow_type`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent.narrow_type))\]

##### id

The identifier of the file part.

When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_name

The name of the provider that generated the response.

Required to be set when `provider_details` or `id` is set.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Additional data returned by the provider that can't be mapped to standard fields.

This is used for data that is required to be sent back to APIs, as well as data users may want to access programmatically. When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['file'\] **Default:** `'file'`

#### Methods

##### has\_content

```python
def has_content() -> bool
```

Return `True` if the file content is non-empty.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### SpeechPart

Spoken audio exchanged during a realtime session, paired with its transcript.

This part is a member of both [`ModelRequestPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequestPart) and [`ModelResponsePart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponsePart), distinguished by `speaker`: in `ModelRequest.parts` the speaker is always `'user'`; in `ModelResponse.parts` it is always `'assistant'`. This invariant is enforced at runtime when a message is constructed.

Standard (non-realtime) models can't consume this part directly; when history containing it is used in an agent run, [`Model.prepare_messages`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model.prepare_messages) converts user-speaker parts to [`UserPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserPromptPart)s and assistant-speaker parts to [`TextPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.TextPart)s.

#### Attributes

##### speaker

Whether the audio was spoken by the end user or by the model.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['user', 'assistant'\]

##### transcript

The transcript of the audio. `None` if transcription was unavailable.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### audio

The audio data, if retained.

Audio is only retained when the realtime session is configured to do so (see the `audio_retention` setting), so this is usually `None`.

**Type:** [`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### interrupted\_at\_ms

The offset into this part's audio where playback was interrupted, in milliseconds.

`None` when the part was not interrupted. It may also be `None` for an interrupted turn when the provider reported the interruption without an offset. This is relative to this part's audio, not wall-clock or session-relative time.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### id

The provider item ID, used to correlate the part with provider-side conversation items.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_name

The name of the provider that generated or transcribed the audio.

Required to be set when `provider_details` or `id` is set.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Additional data returned by the provider that can't be mapped to standard fields.

This is used for data that is required to be sent back to APIs, as well as data users may want to access programmatically. When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['speech'\] **Default:** `'speech'`

##### content

The transcript, or an empty string if transcription was unavailable.

Mirrors [`TextPart.content`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.TextPart.content) so code that renders message parts generically can treat spoken content like text.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### has\_content

```python
def has_content() -> bool
```

Return `True` if the part has a transcript or retained audio.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### BaseToolCallPart

A tool call from a model.

#### Attributes

##### tool\_name

The name of the tool to call.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### args

The arguments to pass to the tool.

This is stored either as a JSON string or a Python dictionary depending on how data was received.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_call\_id

The tool call identifier, this is used by some models including OpenAI.

In case the tool call id is not provided by the model, Pydantic AI will generate a random one.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `field(default_factory=_generate_tool_call_id)`

##### tool\_kind

Discriminator for the typed subclass of this part (e.g. `'tool-search'`).

See [`BaseToolReturnPart.tool_kind`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BaseToolReturnPart.tool_kind) for the full semantics.

**Type:** `ToolPartKind` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### id

An optional identifier of the tool call part, separate from the tool call ID.

This is used by some APIs like OpenAI Responses. When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_name

The name of the provider that generated the response.

Native tool calls are only sent back to the same provider. Required to be set when `provider_details` or `id` is set.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Additional data returned by the provider that can't be mapped to standard fields.

This is used for data that is required to be sent back to APIs, as well as data users may want to access programmatically. When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### args\_as\_dict

```python
def args_as_dict(*, raise_if_invalid: bool = False) -> dict[str, Any]
```

Return the arguments as a Python dictionary.

This is just for convenience with models that require dicts as input.

###### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

###### Parameters

**`raise_if_invalid`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

If `True`, a `ValueError` or `AssertionError` caused by malformed or non-object JSON in `args` will be re-raised. When `False` (the default), such JSON is handled gracefully by returning `{'INVALID_JSON': '<raw args>'}` so that the value can still be sent to a model API (e.g. during a retry flow) without crashing.

##### args\_as\_json\_str

```python
def args_as_json_str() -> str
```

Return the arguments as a JSON string.

This is just for convenience with models that require JSON strings as input.

JSON that's malformed or doesn't represent an object is handled gracefully by returning `'{"INVALID_JSON":"<raw args>"}'`, matching [`args_as_dict`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BaseToolCallPart.args_as_dict), so that the value can still be sent to a model API (e.g. during a retry flow) instead of being rejected by one that requires an object.

Because of that, this is not the way to render args that are still streaming in: a partial fragment that only becomes valid JSON once the following deltas are concatenated would be degraded to the wrapper. Emit those verbatim instead, as the UI event streams do.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### has\_content

```python
def has_content() -> bool
```

Return `True` if the tool call has content.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### ToolCallPart

**Bases:** [`BaseToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BaseToolCallPart)

A tool call from a model.

#### Attributes

##### part\_kind

Part type identifier, this is available on all parts as a discriminator. Note that this is different from `ToolCallPartDelta.part_delta_kind`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool-call'\] **Default:** `'tool-call'`

#### Methods

##### narrow\_type

`@staticmethod`

```python
def narrow_type(
    part: ToolCallPart,
    *,
    tool_kind: ToolPartKind | None = None,
) -> ToolCallPart
```

Promote a base `ToolCallPart` to its typed subclass when its `tool_kind` is registered.

Best-effort: returns the part unchanged when the `tool_kind` (kwarg or on the part) resolves to no registered subclass, and strips an unsubstantiated `tool_kind` when the part's data doesn't validate against that subclass -- keeping it on a base part would break a [`ModelMessagesTypeAdapter`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessagesTypeAdapter) round-trip. For direct construction; Pydantic deserialization promotes automatically via the discriminated union.

###### Returns

[`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart)

### NativeToolCallPart

**Bases:** [`BaseToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BaseToolCallPart)

A tool call to a native tool.

For native tools with a stable cross-provider shape (currently `tool_search`), this base class can be promoted to a typed subclass with a narrowed `args` `TypedDict`. See [`NativeToolSearchCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolSearchCallPart) for the canonical example.

Adding a typed subclass for a future native tool (see `pydantic_ai._tool_search` for a worked example):

1.  Add a sibling `pydantic_ai/_<name>.py` module that defines the cross-provider `TypedDict`s, the `NativeToolCallPart` / `NativeToolReturnPart` subclasses, and registers their narrowers into `_NATIVE_CALL_NARROWERS` / `_NATIVE_RETURN_NARROWERS` keyed by `tool_kind`. Subclass overrides `tool_kind: Literal['<emitter>']` to match the emitting [`AbstractNativeTool.kind`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.AbstractNativeTool.kind), and shadows `args` / `content` with a narrower type.
2.  Late-import the new module from this file (alongside the existing tool-search import) so registration runs whenever `pydantic_ai.messages` is imported.
3.  Add the subclass to `ModelResponsePart`'s discriminated union and to `_model_response_part_discriminator` so Pydantic deserialization auto-promotes on `model_validate` / `model_validate_json`.

Dispatch is by `tool_kind`, not `tool_name`. This protects users whose tools happen to share a name with one of ours from accidentally getting their parts promoted (and failing shape validation against the typed `args`/`content`).

The `provider_details` field carries genuinely non-portable provider extras (e.g. Anthropic's `strategy: 'bm25' | 'regex'` for tool search). Promote a field to a typed slot in `args` / `content` only when at least two of OpenAI, Anthropic, and Google support it (cf. [issue #3885](https://github.com/pydantic/pydantic-ai/issues/3885)).

MCP server tools land here with `tool_kind='mcp_server'` (label stays in `tool_name='mcp_server:<label>'`); typed-subclass work for MCP is tracked by [issue #3561](https://github.com/pydantic/pydantic-ai/issues/3561).

#### Attributes

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['builtin-tool-call'\] **Default:** `'builtin-tool-call'`

#### Methods

##### narrow\_type

`@staticmethod`

```python
def narrow_type(
    part: NativeToolCallPart,
    *,
    tool_kind: ToolPartKind | None = None,
) -> NativeToolCallPart
```

Promote a base `NativeToolCallPart` to its typed subclass when its `tool_kind` is registered.

Best-effort: returns the part unchanged when the `tool_kind` (kwarg or on the part) resolves to no registered subclass, and strips an unsubstantiated `tool_kind` when the part's data doesn't validate against that subclass -- keeping it on a base part would break a [`ModelMessagesTypeAdapter`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessagesTypeAdapter) round-trip. For direct construction; Pydantic deserialization promotes automatically via the discriminated union.

###### Returns

[`NativeToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolCallPart)

### ModelResponse

A response from a model, e.g. a message from the model to the Pydantic AI app.

#### Attributes

##### parts

The parts of the model message.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`ModelResponsePart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponsePart)\]

##### usage

Usage information for this single request, as a [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage).

Run-level usage accumulated across all requests in a run (e.g. `requests`, `tool_calls`) lives on the run's [`RunUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RunUsage), accessible via `result.usage()`; a `RunUsage` should not be assigned to this field.

This has a default to make tests easier, and to support loading old messages where usage will be missing.

**Type:** [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage) **Default:** `field(default_factory=RequestUsage)`

##### model\_name

The name of the model that generated the response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### timestamp

The timestamp when the response was received locally.

This is always a high-precision local datetime. Provider-specific timestamps (if available) are stored in `provider_details['timestamp']`.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime) **Default:** `field(default_factory=_now_utc)`

##### kind

Message type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['response'\] **Default:** `'response'`

##### provider\_name

The name of the LLM provider that generated the response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_url

The base URL of the LLM provider that generated the response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Additional data returned by the provider that can't be mapped to standard fields.

**Type:** [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated)\[[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None), [`pydantic.Field`](https://docs.pydantic.dev/latest/api/pydantic/fields/#pydantic.fields.Field)(`validation_alias`\=([`pydantic.AliasChoices`](https://docs.pydantic.dev/latest/api/pydantic/aliases/#pydantic.aliases.AliasChoices)(`provider_details`, `vendor_details`)))\] **Default:** `None`

##### provider\_response\_id

request ID as specified by the model provider. This can be used to track the specific request to the model.

**Type:** [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None), [`pydantic.Field`](https://docs.pydantic.dev/latest/api/pydantic/fields/#pydantic.fields.Field)(`validation_alias`\=([`pydantic.AliasChoices`](https://docs.pydantic.dev/latest/api/pydantic/aliases/#pydantic.aliases.AliasChoices)(`provider_response_id`, `vendor_id`)))\] **Default:** `None`

##### finish\_reason

Reason the model finished generating the response, normalized to OpenTelemetry values.

**Type:** [`FinishReason`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FinishReason) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### run\_id

The unique identifier of the agent run in which this message originated.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### conversation\_id

The unique identifier of the conversation this message belongs to.

A conversation spans potentially multiple agent runs that share message history. Emitted as the `gen_ai.conversation.id` OpenTelemetry span attribute on the agent run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### metadata

Additional data that can be accessed programmatically by the application but is not sent to the LLM.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### state

The state of this response, indicating whether it is final or requires further action.

-   `'complete'` -- The response is done. This is the default.
-   `'incomplete'` -- A streamed response is still in flight or was stopped before completion.
-   `'suspended'` -- The model paused mid-turn and expects a continuation request. The agent graph will automatically send a continuation request. Set by providers that pause mid-turn (e.g. Anthropic `pause_turn`) or return background/async responses (e.g. OpenAI background mode).
-   `'interrupted'` -- Generation was explicitly stopped before the model finished. Set when a streaming response is cancelled via `StreamedResponse.cancel()`, and when a realtime turn is cut off by a barge-in or `RealtimeSession.interrupt()` -- in which case the cut-off point is recorded on the last [`SpeechPart.interrupted_at_ms`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart.interrupted_at_ms).

**Type:** [`ModelResponseState`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponseState) **Default:** `'complete'`

##### text

Get the text in the response, including the transcript of anything spoken.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### thinking

Get the thinking in the response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### files

Get the files in the response.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`BinaryContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryContent)\]

##### images

Get the images in the response.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`BinaryImage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BinaryImage)\]

##### tool\_calls

Get the tool calls in the response.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart)\]

##### native\_tool\_calls

Get the native tool calls and results in the response.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`NativeToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolCallPart), [`NativeToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolReturnPart)\]\]

#### Methods

##### cost

```python
def cost() -> genai_types.PriceCalculation
```

Calculate the cost of the usage.

Uses [`genai-prices`](https://github.com/pydantic/genai-prices).

###### Returns

`genai_types.PriceCalculation`

### TextPartDelta

A partial update (delta) for a `TextPart` to append new text content.

#### Attributes

##### content\_delta

The incremental text content to add to the existing `TextPart` content.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### provider\_name

The name of the provider that generated the response.

This is required to be set when `provider_details` is set and the initial TextPart does not have a `provider_name` or it has changed.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Additional data returned by the provider that can't be mapped to standard fields.

This is used for data that is required to be sent back to APIs, as well as data users may want to access programmatically.

When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### part\_delta\_kind

Part delta type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['text'\] **Default:** `'text'`

#### Methods

##### apply

```python
def apply(part: ModelResponsePart) -> TextPart
```

Apply this text delta to an existing `TextPart`.

###### Returns

[`TextPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.TextPart) -- A new `TextPart` with updated text content.

###### Parameters

**`part`** : [`ModelResponsePart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponsePart)

The existing model response part, which must be a `TextPart`.

###### Raises

-   `ValueError` -- If `part` is not a `TextPart`.

### ThinkingPartDelta

A partial update (delta) for a `ThinkingPart` to append new thinking content.

#### Attributes

##### content\_delta

The incremental thinking content to add to the existing `ThinkingPart` content.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### signature\_delta

Optional signature delta.

Note this is never treated as a delta -- it can replace None.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_name

Optional provider name for the thinking part.

Signatures are only sent back to the same provider. Required to be set when `provider_details` is set and the initial ThinkingPart does not have a `provider_name` or it has changed.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Additional data returned by the provider that can't be mapped to standard fields.

Can be a dict to merge with existing details, or a callable that takes the existing details and returns updated details. A callable is a transient merge callback and does not survive JSON serialization (it is emitted as `null`); it is resolved to a concrete dict once the delta is applied to a `ThinkingPart`.

This is used for data that is required to be sent back to APIs, as well as data users may want to access programmatically.

When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** `ProviderDetailsDelta` **Default:** `None`

##### part\_delta\_kind

Part delta type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['thinking'\] **Default:** `'thinking'`

#### Methods

##### apply

```python
def apply(part: ModelResponsePart) -> ThinkingPart
def apply(
    part: ModelResponsePart | ThinkingPartDelta,
) -> ThinkingPart | ThinkingPartDelta
```

Apply this thinking delta to an existing `ThinkingPart`.

###### Returns

[`ThinkingPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ThinkingPart) | [`ThinkingPartDelta`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ThinkingPartDelta) -- A new `ThinkingPart` with updated thinking content.

###### Parameters

**`part`** : [`ModelResponsePart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponsePart) | [`ThinkingPartDelta`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ThinkingPartDelta)

The existing model response part, which must be a `ThinkingPart`.

###### Raises

-   `ValueError` -- If `part` is not a `ThinkingPart`.

### ToolCallPartDelta

A partial update (delta) for a `ToolCallPart` to modify tool name, arguments, or tool call ID.

#### Attributes

##### tool\_name\_delta

Incremental text to add to the existing tool name, if any.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### args\_delta

Incremental data to add to the tool arguments.

If this is a string, it will be appended to existing JSON arguments. If this is a dict, it will be merged with existing dict arguments.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_call\_id

Optional tool call identifier, this is used by some models including OpenAI.

Note this is never treated as a delta -- it can replace None, but otherwise if a non-matching value is provided an error will be raised.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_name

The name of the provider that generated the response.

This is required to be set when `provider_details` is set and the initial ToolCallPart does not have a `provider_name` or it has changed.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### provider\_details

Additional data returned by the provider that can't be mapped to standard fields.

This is used for data that is required to be sent back to APIs, as well as data users may want to access programmatically.

When this field is set, `provider_name` is required to identify the provider that generated this data.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### part\_delta\_kind

Part delta type identifier, used as a discriminator. Note that this is different from `ToolCallPart.part_kind`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool\_call'\] **Default:** `'tool_call'`

#### Methods

##### as\_part

```python
def as_part() -> ToolCallPart | None
```

Convert this delta to a fully formed `ToolCallPart` if possible, otherwise return `None`.

###### Returns

[`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- A `ToolCallPart` if `tool_name_delta` is set, otherwise `None`.

##### apply

```python
def apply(part: ModelResponsePart) -> ToolCallPart | NativeToolCallPart
def apply(
    part: ModelResponsePart | ToolCallPartDelta,
) -> ToolCallPart | NativeToolCallPart | ToolCallPartDelta
```

Apply this delta to a part or delta, returning a new part or delta with the changes applied.

###### Returns

[`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart) | [`NativeToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolCallPart) | [`ToolCallPartDelta`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPartDelta) -- Either a new `ToolCallPart` or `NativeToolCallPart`, or an updated `ToolCallPartDelta`.

###### Parameters

**`part`** : [`ModelResponsePart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponsePart) | [`ToolCallPartDelta`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPartDelta)

The existing model response part or delta to update.

###### Raises

-   `ValueError` -- If `part` is neither a `ToolCallPart`, `NativeToolCallPart`, nor a `ToolCallPartDelta`.
-   `UnexpectedModelBehavior` -- If applying JSON deltas to dict arguments or vice versa.

### SpeechPartDelta

A partial update (delta) for a `SpeechPart` to append transcript text and/or audio data.

#### Attributes

##### speaker

Who is speaking, matching the [`SpeechPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart) this delta belongs to.

Realtime sessions are duplex: the user's transcript and the model's can stream at the same time, interleaved delta by delta. Carrying the speaker here means rendering a live transcript needs nothing but the delta itself -- no correlating back to an earlier [`PartStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.PartStartEvent).

`None` only when a delta wasn't produced by a realtime session.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['user', 'assistant'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### transcript\_delta

Transcript text this delta added, if any.

Not every transcript delta has one

This is empty whenever the provider _revised_ what it had already transcribed instead of adding to it, because there is no addition to report. How often that happens is up to the provider -- xAI Grok Voice does it routinely, OpenAI and Gemini not at all today -- so appending this field means a live transcript that is right on some providers and stale on others.

Render [`transcript`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPartDelta.transcript) instead, which is always the turn's full text. Reach for this one only when you specifically want what changed.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### transcript

The whole transcript of this turn so far, when this delta carries transcript text.

Render this and a live transcript is correct on every provider, with no accumulating of your own. Speech recognition is revisable -- later audio changes how earlier audio is read -- so some providers correct words they already transcribed rather than only adding to them, which an appended `transcript_delta` cannot express. Reading this field means never having to know which providers do that. It also recovers a consumer that missed an earlier delta.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### audio\_chunk

A raw audio chunk (e.g. PCM data), if any.

Suitable for live playback; only accumulated on the part if it is retaining audio (see [`SpeechPartDelta.apply`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPartDelta.apply)).

**Type:** [`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### part\_delta\_kind

Part delta type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['speech'\] **Default:** `'speech'`

#### Methods

##### apply

```python
def apply(part: ModelResponsePart) -> SpeechPart
```

Apply this delta to an existing `SpeechPart`.

`transcript` replaces the part's transcript when set, which is how a provider's revision of what it already transcribed is applied; otherwise `transcript_delta` is appended (a part with `transcript=None` gets `transcript=transcript_delta`). `audio_chunk` is appended to the part's retained audio data, but only if the part already has `audio` set: a part with `audio=None` is not retaining audio, so the chunk is intentionally not stored -- it remains available on the delta itself for live playback.

###### Returns

[`SpeechPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart) -- A new `SpeechPart` with the delta applied.

###### Parameters

**`part`** : [`ModelResponsePart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponsePart)

The existing model response part, which must be a `SpeechPart`.

###### Raises

-   `ValueError` -- If `part` is not a `SpeechPart`.

### PartStartEvent

An event indicating that a new part has started.

If multiple `PartStartEvent`s are received with the same index, the new one should fully replace the old one.

#### Attributes

##### index

The index of the part within the overall response parts list.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### part

The newly started `ModelResponsePart`.

**Type:** [`ModelResponsePart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponsePart)

##### previous\_part\_kind

The kind of the previous part, if any.

This is useful for UI event streams to know whether to group parts of the same kind together when emitting events.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['text', 'thinking', 'tool-call', 'builtin-tool-call', 'builtin-tool-return', 'compaction', 'file', 'speech'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['part\_start'\] **Default:** `'part_start'`

### PartDeltaEvent

An event indicating a delta update for an existing part.

#### Attributes

##### index

The index of the part within the overall response parts list.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### delta

The delta to apply to the specified part.

**Type:** [`ModelResponsePartDelta`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponsePartDelta)

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['part\_delta'\] **Default:** `'part_delta'`

### PartEndEvent

An event indicating that a part is complete.

#### Attributes

##### index

The index of the part within the overall response parts list.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### part

The complete `ModelResponsePart`.

**Type:** [`ModelResponsePart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponsePart)

##### next\_part\_kind

The kind of the next part, if any.

This is useful for UI event streams to know whether to group parts of the same kind together when emitting events.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['text', 'thinking', 'tool-call', 'builtin-tool-call', 'builtin-tool-return', 'compaction', 'file', 'speech'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['part\_end'\] **Default:** `'part_end'`

### FinalResultEvent

An event indicating the response to the current model request matches the output schema and will produce a result.

#### Attributes

##### tool\_name

The name of the output tool that was called. `None` if the result is from text content and not from a tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### tool\_call\_id

The tool call ID, if any, that this result is associated with.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['final\_result'\] **Default:** `'final_result'`

### EnqueuedMessagesEvent

An event indicating that messages enqueued via [`enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue) were delivered into the run's message history.

Emitted at delivery time, carrying the delivered message objects themselves -- the same objects held in the run's message history, exactly as they landed there (with `timestamp` / `run_id` / `conversation_id` stamped). A history processor that replaces history with new message objects does not affect the event, but in-place mutation of a delivered message will be visible through it.

#### Attributes

##### enqueue\_id

The ID of the [`enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue) call that produced these messages.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### messages

The messages delivered into the run's message history.

**Type:** [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage), ...\]

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['enqueued\_messages'\] **Default:** `'enqueued_messages'`

### ToolCallEvent

Base class for events emitted when a tool call is about to be invoked.

Match against this in a `case` to handle [`FunctionToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolCallEvent) and [`OutputToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.OutputToolCallEvent) together.

#### Attributes

##### part

The tool call to make.

**Type:** [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart)

##### args\_valid

Whether the tool arguments passed validation. See the [custom validation docs](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#args-validator) for more info.

-   `True`: Schema validation and custom validation (if configured) both passed; args are guaranteed valid.
-   `False`: Validation was performed and failed.
-   `None`: Validation was not performed.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_call\_id

An ID used for matching details about the call to its result.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### FunctionToolCallEvent

**Bases:** [`ToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallEvent)

An event indicating the start to a call to a function tool.

#### Attributes

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['function\_tool\_call'\] **Default:** `'function_tool_call'`

### OutputToolCallEvent

**Bases:** [`ToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallEvent)

An event indicating the start of a call to an output tool (the model's "submit final answer" call).

#### Attributes

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['output\_tool\_call'\] **Default:** `'output_tool_call'`

### ToolResultEvent

Base class for events emitted when a tool call has been completed.

Match against this in a `case` to handle [`FunctionToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolResultEvent) and [`OutputToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.OutputToolResultEvent) together.

#### Attributes

##### part

The tool result part that will be sent back to the model.

**Type:** [`ToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturnPart) | [`RetryPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.RetryPromptPart)

##### tool\_call\_id

An ID used to match the result to its original call.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### FunctionToolResultEvent

**Bases:** [`ToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolResultEvent)

An event indicating the result of a function tool call.

#### Attributes

##### content

The content that will be sent to the model as a UserPromptPart following the result.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`UserContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserContent)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['function\_tool\_result'\] **Default:** `'function_tool_result'`

### ToolAvailabilityDeltaEvent

An event indicating tools were made available mid-run, carrying the recorded delta part.

This is request-side because the delta is created while executing a tool, after response-part streaming has finished. It records the post-dedup change, while `ToolReturnPart.tools` preserves the caller's pre-dedup intent, and is emitted for capability loads as well as tool returns.

#### Attributes

##### part

The tool availability delta part that will be recorded in message history.

**Type:** [`ToolAvailabilityDeltaPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolAvailabilityDeltaPart)

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool\_availability\_delta'\] **Default:** `'tool_availability_delta'`

### OutputToolResultEvent

**Bases:** [`ToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolResultEvent)

An event indicating the result of an output tool call.

#### Attributes

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['output\_tool\_result'\] **Default:** `'output_tool_result'`

### DeferredToolRequestsEvent

An event indicating that tool calls require approval or external execution before the run can continue.

Each deferred call also emits its own [`FunctionToolCallEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolCallEvent); this event additionally carries the batched [`DeferredToolRequests`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolRequests) so stream consumers can tell which calls are paused waiting for interaction, e.g. to notify a frontend.

It is emitted before any [`HandleDeferredToolCalls`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.HandleDeferredToolCalls) handler runs. If no handler resolves all of the requests, the run ends with the pending requests as its [`DeferredToolRequests`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolRequests) output.

See [deferred tools docs](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/) for more information.

#### Attributes

##### requests

The batch of tool calls that require external execution or approval.

**Type:** [`DeferredToolRequests`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolRequests)

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['deferred\_tool\_requests'\] **Default:** `'deferred_tool_requests'`

### DeferredToolResultsEvent

An event indicating that deferred tool calls were resolved by a [`HandleDeferredToolCalls`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.HandleDeferredToolCalls) handler.

The resolved calls are then executed through the regular tool-execution pipeline, emitting a [`FunctionToolResultEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FunctionToolResultEvent) for each result.

This event is not emitted when results are instead provided to a new run via `deferred_tool_results`, as in that case the caller already knows them.

See [deferred tools docs](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/) for more information.

#### Attributes

##### results

The results for the deferred tool calls, keyed by tool call ID.

**Type:** [`DeferredToolResults`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.DeferredToolResults)

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['deferred\_tool\_results'\] **Default:** `'deferred_tool_results'`

### RealtimeTurnCompleteEvent

The model exchange is over: generation and tool work are complete.

It is synthesized by the session once no tool calls are still running and no further response is in flight. Input transcription can finish after this event. On WebRTC sidebands, provider playback can also continue until [`RealtimeOutputSpeechEndEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeOutputSpeechEndEvent).

#### Attributes

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_turn\_complete'\] **Default:** `'realtime_turn_complete'`

### RealtimeInputSpeechStartEvent

The provider detected that the user started speaking.

Useful for barge-in: stop playing any buffered model audio when this arrives, since the model's in-progress turn is being interrupted.

Reported by OpenAI, Azure OpenAI, and xAI. Gemini Live does not report speech onset.

#### Attributes

##### item\_id

Provider id of the user input item this speech segment belongs to, when reported.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_input\_speech\_start'\] **Default:** `'realtime_input_speech_start'`

### RealtimeResponseInterruptedEvent

The provider cut the model's in-progress response short.

Arrives as soon as the provider interrupts, ahead of its response terminal, so it's the point at which to flush buffered model audio.

Reported by Gemini Live, which interrupts server-side when it hears the user speak. The other providers report the user's speech onset as [`RealtimeInputSpeechStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeInputSpeechStartEvent) and leave the cancellation to [`interrupt`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.interrupt), so they never report this.

#### Attributes

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_response\_interrupted'\] **Default:** `'realtime_response_interrupted'`

### RealtimeInputSpeechEndEvent

The provider detected that the user stopped speaking.

Useful as a 'processing' indicator: the user's turn has ended and the model is about to respond.

#### Attributes

##### item\_id

Provider id of the user input item this speech segment belongs to, when reported.

Used to attach retained input audio (`audio_retention='input_audio'`/`'all'`) to the right user turn when turns overlap, since transcripts for different items can finalize out of order.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_input\_speech\_end'\] **Default:** `'realtime_input_speech_end'`

### RealtimeOutputSpeechStartEvent

The provider started playing the model's audio to the listener.

Only reported where the provider, rather than your code, holds the audio on its way to the listener: on a [WebRTC sideband](https://pydantic.dev/docs/ai/realtime/deployment/#browser-webrtc-server-sideband) the media flows browser ↔ provider, so the session never sees audio and this is its only signal that the model has become audible. An ordinary session owns the audio and knows when it starts playing it, so no provider reports this there.

This is about _playback_, not generation: the provider produces audio faster than it plays it, so this can arrive well after the audio itself was generated.

#### Attributes

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_output\_speech\_start'\] **Default:** `'realtime_output_speech_start'`

### RealtimeOutputSpeechEndEvent

The provider stopped playing the model's audio to the listener.

The counterpart to [`RealtimeOutputSpeechStartEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeOutputSpeechStartEvent), and the honest end of a spoken turn: because the provider generates audio far ahead of playing it, it is still talking long after [`RealtimeTurnCompleteEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeTurnCompleteEvent) reports the response finished. Drive a "speaking" indicator from this pair rather than from turn completion.

#### Attributes

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_output\_speech\_end'\] **Default:** `'realtime_output_speech_end'`

### RealtimeInputTranscriptionErrorEvent

The provider failed to transcribe a user audio input turn, but the session continues.

This is recoverable; `item_id` and `content_index` locate the affected user turn.

#### Attributes

##### message

Human-readable error message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### type

Provider error category, if any.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### code

Provider error code, if any.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### item\_id

Provider conversation-item ID for the affected user turn, when available.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### content\_index

Content index within the affected user turn, when available.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_input\_transcription\_error'\] **Default:** `'realtime_input_transcription_error'`

### RealtimeSessionReconnectEvent

The connection dropped and was automatically re-established; inspect `state_restored` for continuity.

Session configuration (instructions, tools, voice, ...) is restored on every reconnect. Conversation state is restored either by the provider's native session resumption (Gemini Live when enabled, xAI Grok Voice) or by the session replaying its local history into the fresh server-side conversation (OpenAI/Azure OpenAI).

#### Attributes

##### state\_restored

Whether the reconnect carried the conversation through without cutting a turn off, regardless of mechanism -- native provider resumption or a local-history replay.

`True` means nothing in flight was lost: the provider either resumed the in-flight response itself (Gemini Live, xAI Grok Voice) or there was no turn in progress when the connection dropped.

`False` means a turn the drop interrupted was settled before continuing -- its partial reply is recorded as an interrupted response and any running tool calls as cancelled returns -- so [`all_messages()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.all_messages) stays a coherent history. Finalized turns from before the drop survive where the provider restores them (the OpenAI/Azure OpenAI local replay) and are lost where it does not; either way, treat the interrupted turn as over and expect the model to stay quiet until the next input.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_session\_reconnect'\] **Default:** `'realtime_session_reconnect'`

### RealtimeSessionErrorEvent

A provider-reported error occurred in the session.

#### Attributes

##### message

Human-readable error message.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### type

Provider error category, e.g. `invalid_request_error` or `server_error`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### code

Provider error code, if any.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### recoverable

Whether the session can continue. A protocol `error` is recoverable; a dropped connection is not.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['realtime\_session\_error'\] **Default:** `'realtime_session_error'`

### CustomEvent

An application-defined event emitted into the agent's event stream.

Emit these from tools or code driving [`Agent.iter`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.iter) via [`RunContext.emit`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.emit) or [`AgentRun.emit`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.emit) to surface progress updates, intermediate results, or status information to consumers of the stream without adding to the model's context.

Define an event by subclassing this class with typed fields carrying the payload:

```python
from dataclasses import dataclass

from pydantic_ai import CustomEvent


@dataclass(kw_only=True)
class OperationProgressEvent(CustomEvent):
    done: int
    total: int
```

Subclasses must be dataclasses. Each subclass registers itself under its `name` -- derived from the class name (`OperationProgressEvent` -> `'operation_progress'`) unless overridden with a `name` class argument -- so instances round-trip through serialization back to the subclass, and consumers can use `isinstance` checks instead of matching name strings. Deserializing an event whose name isn't registered in the current process yields an [`UnknownCustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UnknownCustomEvent).

#### Attributes

##### name

The application-defined name of the event.

On registered subclasses it defaults to the registered event name, so it never needs to be passed.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `''`

##### tool\_call\_id

The tool call this event is associated with, if any.

Automatically stamped from [`RunContext.tool_call_id`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.tool_call_id) when the event is emitted from within a tool call and doesn't already set one, so consumers can attribute the event to the originating tool call.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_name

The name of the tool this event is associated with, if any; stamped like `tool_call_id`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['custom'\] **Default:** `'custom'`

##### ui

Whether [UI event streams](https://pydantic.dev/docs/ai/integrations/ui/overview/) forward this event class to the frontend.

Custom events are application-owned, so they are forwarded by default: the application decided both to emit the event and to serve that frontend. Set `ui=False` as a class argument on an event that exists only for server-side consumers -- metrics, audit logs, an `event_stream_handler` of your own:

```python
from dataclasses import dataclass

from pydantic_ai import CustomEvent


@dataclass(kw_only=True)
class IndexProgressEvent(CustomEvent, ui=False):
    done: int
    total: int
```

It still reaches every in-process consumer; only the UI adapters skip it. Subclasses inherit the setting, and because the check happens before the protocol-specific handler, third-party adapters honor it too. An event that needs a different payload for the frontend rather than no payload at all should override [`to_payload()`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent.to_payload) instead.

The flag lives on the class rather than on the wire, so an event deserialized in a process that hasn't imported its defining module arrives as an [`UnknownCustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UnknownCustomEvent), whose `ui` says nothing about what the application declared. Those are not forwarded either, so an event that crosses a process boundary can't leak a payload its class had opted out of. Import the modules that define your events in the process that serves the frontend, or its custom events won't reach the frontend at all.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

#### Methods

##### to\_payload

```python
def to_payload() -> Any
```

The event's payload: the subclass's own typed fields.

This is what the UI adapters send to the frontend (AG-UI `CustomEvent.value`, Vercel AI `data-{name}` chunk data), with the same shape whether or not the event was emitted from inside a tool call. Override to customize the payload shape -- e.g. to include `self.tool_call_id` when the frontend needs to attribute the event to a tool call.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### \_\_get\_pydantic\_core\_schema\_\_

`@classmethod`

```python
def __get_pydantic_core_schema__(
    cls,
    source: Any,
    handler: pydantic.GetCoreSchemaHandler,
) -> pydantic_core.core_schema.CoreSchema
```

Build this family's tagged union, instead of the plain dataclass schema pydantic would infer.

The set of event classes isn't known when this module is imported -- applications and capabilities register their own by defining them -- so the union can't be written down as a static `Annotated[... , Field(discriminator=...)]` the way the closed event types are. This override builds it from the registry each time a schema is generated, and routes a tag no class has registered to [`UnknownCustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UnknownCustomEvent), so an event from a process that imported a module this one didn't still round-trips instead of failing validation.

Only the family base builds the union; a subclass gets its own dataclass schema, so annotating a concrete event type validates just that event.

###### Returns

`pydantic_core.core_schema.CoreSchema`

### UnknownCustomEvent

**Bases:** [`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent)

A typed custom event whose `name` isn't registered in this process.

Produced when deserializing an event emitted by a process that had the defining module imported (e.g. across a durable execution boundary). The payload fields ride in `data`, and serialization re-flattens them, so a downstream consumer that does have the defining module imported recovers the typed event.

#### Attributes

##### data

The original event's payload fields, or `None` if it had none.

Only the family's validator fills this, and it always gathers the wire dict's unrecognized keys, so the mapping is exactly the payload the defining process serialized.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### to\_payload

```python
def to_payload() -> dict[str, Any] | None
```

The event's payload: the original event's fields, preserved in `data`.

###### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### CapabilityEvent

A typed event emitted by a capability into the agent's event stream.

Capability authors define dataclass subclasses with a namespace shared by their event family. The emitting capability's run id is stamped by [`RunContext.emit`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.emit).

Events dispatch at their stream position by default. Decision events can instead pass `dispatch='immediate'` as a class argument so listeners run before [`RunContext.emit`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.emit) returns:

```python
from dataclasses import dataclass

from pydantic_ai import CapabilityEvent


@dataclass(kw_only=True)
class CheckpointStartEvent(CapabilityEvent, namespace='checkpoint', dispatch='immediate'):
    cancelled: bool = False
    cancel_reason: str | None = None

    def cancel(self, reason: str | None = None) -> None:
        self.cancelled = True
        self.cancel_reason = reason
```

The dispatch mode is inherited by subclasses of a concrete event class.

#### Attributes

##### event\_dispatch

When capability and application listeners receive the event.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['stream', 'immediate'\] **Default:** `'stream'`

##### kind

The namespaced event kind, injected as the default on registered subclasses.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `''`

##### capability\_id

The run id of the capability that emitted this event.

Stamped at emission when unset; a pre-set value is preserved, so a capability re-emitting an event on behalf of another instance can keep the original attribution.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_call\_id

The associated tool call id, when emitted by a capability-contributed tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_name

The associated tool name, when emitted by a capability-contributed tool.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['capability'\] **Default:** `'capability'`

#### Methods

##### \_\_get\_pydantic\_core\_schema\_\_

`@classmethod`

```python
def __get_pydantic_core_schema__(
    cls,
    source: Any,
    handler: pydantic.GetCoreSchemaHandler,
) -> pydantic_core.core_schema.CoreSchema
```

Build this family's tagged union, instead of the plain dataclass schema pydantic would infer.

The set of event classes isn't known when this module is imported -- applications and capabilities register their own by defining them -- so the union can't be written down as a static `Annotated[... , Field(discriminator=...)]` the way the closed event types are. This override builds it from the registry each time a schema is generated, and routes a tag no class has registered to [`UnknownCapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UnknownCapabilityEvent), so an event from a process that imported a module this one didn't still round-trips instead of failing validation.

Only the family base builds the union; a subclass gets its own dataclass schema, so annotating a concrete event type validates just that event.

###### Returns

`pydantic_core.core_schema.CoreSchema`

### UnknownCapabilityEvent

**Bases:** [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent)

A typed capability event whose `kind` isn't registered in this process.

Produced when deserializing an event emitted by a process that had the defining module imported. The payload fields ride in `data`, and serialization re-flattens them, so a downstream consumer that does have the defining module imported recovers the typed event.

#### Attributes

##### data

The original event's payload fields, or `None` if it had none.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### is\_multi\_modal\_content

```python
def is_multi_modal_content(obj: Any) -> TypeGuard[MultiModalContent]
```

Check if obj is a MultiModalContent type, enabling type narrowing.

#### Returns

[`TypeGuard`](https://docs.python.org/3/library/typing.html#typing.TypeGuard)\[[`MultiModalContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.MultiModalContent)\]

### parse\_tool\_kind

```python
def parse_tool_kind(value: str) -> ToolPartKind | None
```

Return `value` if it's a known [`ToolPartKind`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolPartKind), else `None`.

UI adapters call this at the wire boundary to validate an untrusted client-supplied `tool_kind` string before setting it on a part, so an unknown value degrades to `None` rather than asserting a bogus discriminator.

#### Returns

`ToolPartKind` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### post\_compaction\_window

```python
def post_compaction_window(messages: Sequence[ModelMessage]) -> list[ModelMessage]
```

The messages from the latest [`CompactionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CompactionPart) onward.

After compaction, the summary replaces everything before it, so this window is what the model effectively works from -- at part-level precision: within the response that carries the compaction part, parts before it are excluded and parts after it are kept. With no compaction part in the history, the whole history is returned (as a new list).

This is the boundary rule Pydantic AI itself uses when deriving model-visible state from history (discovered tools, loaded capabilities). Capability and toolset authors should apply the same rule to their own derived state -- anything the model needs to have _seen_ (announcements, disclosures, catalogs) should be recomputed from this window rather than remembered in instance attributes, so it self-heals when compaction replaces the history that carried it.

Deliberately provider-agnostic, unlike the wire-level trim, which is provider-specific because it must be exact for the one request it renders. This window feeds run-level state (`RunContext.discovered_tool_names`, loaded capabilities) that must stay valid across [`FallbackModel`](https://pydantic.dev/docs/ai/api/models/fallback/#pydantic_ai.models.fallback.FallbackModel) failover and mid-run model switches -- at parse time there is no "current" provider to resolve against, so the boundary has to be the conservative intersection: a compaction part another provider would skip on the wire still counts.

The execution-availability gate separately anchors its evidence to the provider that served the response being dispatched. Re-disclosure, instruction building, search ranking, and catalogs continue to use this conservative provider-agnostic window because they feed a future request whose provider may differ.

#### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

### narrow\_message\_parts

```python
def narrow_message_parts(messages: Sequence[ModelMessage]) -> list[ModelMessage]
```

Promote each tool call/return part across `messages` to its typed subclass via its `tool_kind`.

Best-effort and idempotent: a part whose `tool_kind` resolves to a registered typed subclass and whose data validates against it is promoted; a part with no `tool_kind`, an unregistered one, or shape-invalid data is left a base part (an unsubstantiated `tool_kind` is stripped -- see [`ToolCallPart.narrow_type`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart.narrow_type)).

UI adapters reconstruct base parts from the wire format with `tool_kind` set from client-echoed metadata, then call this once instead of narrowing each part inline. Pydantic deserialization of a `ModelMessage` performs the same promotion via its discriminated-union dispatch; this is the direct-construction equivalent for callers that build parts by hand.

#### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

### sanitize\_messages

```python
def sanitize_messages(
    messages: Sequence[ModelMessage],
    *,
    strip_system_prompts: bool = True,
    strip_compaction_parts: bool = False,
    allowed_file_url_schemes: Collection[str] = ('http', 'https'),
    allowed_file_url_force_download: Collection[ForceDownloadMode] = (),
    allow_uploaded_files: bool = False,
    resolved_tool_call_ids: Collection[str] = (),
) -> list[ModelMessage]
```

Strip message parts that aren't safe to honor from untrusted input.

This is the same default sanitization the [UI adapters](https://pydantic.dev/docs/ai/integrations/ui/overview/) apply to client-submitted messages before they're passed to an agent. Use it when loading `message_history` from a source the application does not fully trust, such as a browser request.

By default it strips:

-   [`SystemPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SystemPromptPart)s (disable with `strip_system_prompts=False`). The system prompt is the server's to own; a client that can inject one can override the agent's behavior. If stripping leaves a `ModelRequest` with no parts, the request is dropped from history entirely.
-   [`FileUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl) parts whose URL scheme is not in `allowed_file_url_schemes` (default `http`/`https`). Non-HTTP schemes like `s3://` or `gs://` cause the model provider to fetch the object using the server-side IAM role, so they should only be accepted from trusted clients.
-   [`FileUrl.force_download`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl.force_download) values other than `False` that aren't in `allowed_file_url_force_download`, resetting them to `False`. Both `True` and `'allow-local'` are reset by default. Applies to file URLs in user content and those nested in tool return parts.
-   [`UploadedFile`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UploadedFile) items unless `allow_uploaded_files=True`. Like a non-HTTP `FileUrl`, an `UploadedFile` references an object the model provider fetches using the server-side IAM role. Applies to uploaded files in user content and those nested in tool return parts.
-   [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart)s at the end of the history that aren't in `resolved_tool_call_ids`. An unresolved tool call at the end of client-supplied history doesn't correspond to a paused agent run and shouldn't be executed. [`NativeToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolCallPart)s are left in place: the provider executes them server-side and pairs each with a [`NativeToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolReturnPart) in the same response, and the agent loop never dispatches them, so they aren't a client-injection risk. If stripping leaves the final response with no parts, the response is dropped from history entirely.
-   The compaction provenance stamp from [`CompactionPart.provider_details`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CompactionPart.provider_details). This ensures a client-supplied OpenAI Responses compaction item is never trusted to already carry the leading [`SystemPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SystemPromptPart)s: they are re-sent to the model even where the provider's own compaction state would normally let them be skipped.
-   [`CompactionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CompactionPart)s, when `strip_compaction_parts=True` (off by default). Everything before a compaction part is hidden from the model, so pass `True` whenever you combine the sanitized history with trusted server-side `message_history` -- a client-supplied compaction part would hide that server-side history. The [UI adapters](https://pydantic.dev/docs/ai/integrations/ui/overview/) apply this rule automatically when a run combines server-side `message_history` with client-submitted messages.

#### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

#### Parameters

**`messages`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

Messages to sanitize.

**`strip_system_prompts`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to strip [`SystemPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SystemPromptPart)s.

**`strip_compaction_parts`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether to drop [`CompactionPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CompactionPart)s entirely. Off by default, for when the untrusted input is the entire conversation; pass `True` when the sanitized history is combined with trusted server-side history.

**`allowed_file_url_schemes`** : [`Collection`](https://docs.python.org/3/library/typing.html#typing.Collection)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] _Default:_ `('http', 'https')`

URL schemes allowed for [`FileUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl) parts. Defaults to `http` and `https`.

**`allowed_file_url_force_download`** : [`Collection`](https://docs.python.org/3/library/typing.html#typing.Collection)\[`ForceDownloadMode`\] _Default:_ `()`

Additional [`FileUrl.force_download`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.FileUrl.force_download) values to allow. `False` is always allowed. Defaults to no additional values.

**`allow_uploaded_files`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether to honor [`UploadedFile`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UploadedFile) items from the untrusted input. Off by default, since an uploaded file references an object the model provider fetches using the server-side IAM role.

**`resolved_tool_call_ids`** : [`Collection`](https://docs.python.org/3/library/typing.html#typing.Collection)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] _Default:_ `()`

Tool call IDs to preserve when the final response ends with tool calls. Use this for human-in-the-loop resumption when matching tool results are being submitted with the same request.

### FinishReason

Reason the model finished generating the response.

Mostly normalized to OpenTelemetry semantic convention values. Whether the agent should automatically continue is determined by `ModelResponse.state`, not by this field.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['stop', 'length', 'content_filter', 'tool_call', 'error']`

### ModelResponseState

Lifecycle state of a model response.

-   `'complete'`: the response has been fully received from the model.
-   `'incomplete'`: the response is still being streamed and may receive more parts. Yielded by [`AgentStream.response`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.AgentStream.response) and [`StreamedRunResult.stream_response`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.stream_response) while iteration is in flight.
-   `'suspended'`: the model paused mid-turn and expects a continuation request. Used by Anthropic `pause_turn` and OpenAI background mode. Pydantic AI issues these continuations transparently for both `agent.run` and `agent.run_stream`, merging every segment into a single completed [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse), so a finished turn in the message history is never left in this state.
-   `'interrupted'`: generation was explicitly stopped before the model finished. Set when a streamed response is cancelled via [`StreamedResponse.cancel()`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.StreamedResponse.cancel), and when a realtime turn is cut off by a barge-in or [`RealtimeSession.interrupt()`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession.interrupt) -- in which case the cut-off point is recorded on the last [`SpeechPart.interrupted_at_ms`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SpeechPart.interrupted_at_ms).

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['complete', 'incomplete', 'suspended', 'interrupted']`

### ModelRequestState

Lifecycle state of a model request.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['complete', 'interrupted']`

### ForceDownloadMode

Type for the force\_download parameter on FileUrl subclasses.

-   `False`: The URL is sent directly to providers that support it. For providers that don't, the file is downloaded with SSRF protection (blocks private IPs and cloud metadata).
-   `True`: The file is always downloaded with SSRF protection (blocks private IPs and cloud metadata).
-   `'allow-local'`: The file is always downloaded, allowing private IPs but still blocking cloud metadata.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `bool | Literal['allow-local']`

### ProviderDetailsDelta

Type for provider\_details input: can be a static dict, a callback to update existing details, or None.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Annotated[dict[str, Any] | Callable[[dict[str, Any] | None], dict[str, Any]] | None, pydantic.PlainSerializer(_serialize_provider_details_delta, return_type=(dict[str, Any] | None), when_used='json')]`

### UploadedFileProviderName

Provider names supported by [`UploadedFile`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UploadedFile).

The `'google-gla'` and `'google-vertex'` values are retained for backward compatibility with message history captured before the v2 provider rename -- current code emits `'google'` and `'google-cloud'` respectively.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['anthropic', 'openai', 'google', 'google-cloud', 'google-gla', 'google-vertex', 'bedrock', 'xai']`

### MultiModalContent

Union of all multi-modal content types with a discriminator for Pydantic validation.

**Default:** `Annotated[ImageUrl | AudioUrl | DocumentUrl | VideoUrl | Annotated[BinaryContent, pydantic.AfterValidator(BinaryContent.narrow_type)] | UploadedFile, pydantic.Discriminator('kind')]`

### UserContent

A single item of user prompt content: a string, a typed text or multi-modal content part, or a [`CachePoint`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CachePoint) marker.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `str | TextContent | MultiModalContent | CachePoint`

### RETURN\_VALUE\_KEY

Key used to wrap non-dict tool return values in `model_response_object()`.

**Default:** `'return_value'`

### tool\_return\_content\_ta

TypeAdapter for `ToolReturnContent` -- used by UI adapters to rehydrate multimodal items (`BinaryContent`, `ImageUrl`, etc.) from raw JSON/dict payloads carried in wire-protocol fields typed as `Any` (e.g. Vercel's `ToolOutputAvailablePart.output`).

**Type:** [`pydantic.TypeAdapter`](https://docs.pydantic.dev/latest/api/pydantic/type_adapter/#pydantic.type_adapter.TypeAdapter)\[`ToolReturnContent`\] **Default:** `pydantic.TypeAdapter(ToolReturnContent, config=(pydantic.ConfigDict(defer_build=True)))`

### ToolPartKind

Discriminator value for the typed call/return-part subclass associated with a tool.

Set on [`BaseToolCallPart.tool_kind`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BaseToolCallPart.tool_kind), [`BaseToolReturnPart.tool_kind`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.BaseToolReturnPart.tool_kind), and [`ToolDefinition.tool_kind`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolDefinition.tool_kind). Extended as new typed-part families (e.g. web search) gain dedicated subclasses.

Distinct from [`ToolKind`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolKind) (invocation semantics -- `'function'`, `'output'`, `'external'`, `'unapproved'`).

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['tool-search', 'capability-load']`

### INTERRUPTED\_TOOL\_RETURN\_CONTENT

Placeholder content for a tool call that was interrupted before producing a result (e.g. by run cancellation). Shared between the agent graph's history repair and the UI adapters' stream closeout so both synthesize the same `outcome='interrupted'` return.

**Default:** `'The tool call was interrupted before a result was produced.'`

### InstructionSource

The source that authored an instruction part.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `AgentInstructionSource | ToolsetInstructionSource | CapabilityInstructionSource`

### SerializedInstructionId

An [`InstructionId`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.InstructionId) that persists as the string it renders to.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Annotated[InstructionId | None, pydantic.BeforeValidator(_deserialize_instruction_id), pydantic.PlainSerializer(_serialize_instruction_id, return_type=(str | None), when_used='json')]`

### STANDING\_PROMPT\_PLANTED\_KEY

`CompactionPart.provider_details` key stamped on compaction items minted by our own compact call, whose input window explicitly planted the standing prompt. Provenance for `_trim_messages_before_compaction`'s `standing_prompt_retained` fast path: only a stamped item is trusted to retain the standing prompt; anything else -- an externally supplied or spliced history, or an item produced by a provider-initiated compaction of an ordinary request window -- gets the standing prompt re-inserted.

**Default:** `'pydantic_ai_standing_prompt_planted'`

### ModelRequestPart

A message part sent by Pydantic AI to a model.

**Default:** `Annotated[Annotated[SystemPromptPart, pydantic.Tag('system-prompt')] | Annotated[UserPromptPart, pydantic.Tag('user-prompt')] | Annotated[SpeechPart, pydantic.Tag('speech')] | Annotated[ToolSearchReturnPart, pydantic.Tag('tool-search-return')] | Annotated[LoadCapabilityReturnPart, pydantic.Tag('capability-load-return')] | Annotated[ToolReturnPart, pydantic.Tag('tool-return')] | Annotated[RetryPromptPart, pydantic.Tag('retry-prompt')] | Annotated[ToolAvailabilityDeltaPart, pydantic.Tag('tool-availability-delta')], pydantic.Discriminator(_model_request_part_discriminator)]`

### ModelResponsePart

A message part returned by a model.

**Default:** `Annotated[Annotated[TextPart, pydantic.Tag('text')] | Annotated[ToolSearchCallPart, pydantic.Tag('tool-search-call')] | Annotated[LoadCapabilityCallPart, pydantic.Tag('capability-load-call')] | Annotated[ToolCallPart, pydantic.Tag('tool-call')] | Annotated[NativeToolSearchCallPart, pydantic.Tag('builtin-tool-search-call')] | Annotated[NativeToolCallPart, pydantic.Tag('builtin-tool-call')] | Annotated[NativeToolSearchReturnPart, pydantic.Tag('builtin-tool-search-return')] | Annotated[NativeToolReturnPart, pydantic.Tag('builtin-tool-return')] | Annotated[ThinkingPart, pydantic.Tag('thinking')] | Annotated[CompactionPart, pydantic.Tag('compaction')] | Annotated[FilePart, pydantic.Tag('file')] | Annotated[SpeechPart, pydantic.Tag('speech')], pydantic.Discriminator(_model_response_part_discriminator)]`

### ModelMessage

Any message sent to or returned by a model.

**Default:** `Annotated[ModelRequest | ModelResponse, pydantic.Discriminator('kind')]`

### ModelMessagesTypeAdapter

Pydantic [`TypeAdapter`](https://docs.pydantic.dev/latest/api/pydantic/type_adapter/#pydantic.type_adapter.TypeAdapter) for (de)serializing messages.

**Default:** `pydantic.TypeAdapter(list[ModelMessage], config=(pydantic.ConfigDict(defer_build=True, ser_json_bytes='base64', val_json_bytes='base64')))`

### ModelResponsePartDelta

A partial update (delta) for any model response part.

**Default:** `Annotated[TextPartDelta | ThinkingPartDelta | ToolCallPartDelta | SpeechPartDelta, pydantic.Discriminator('part_delta_kind')]`

### ModelResponseStreamEvent

An event in the model response stream, starting a new part, applying a delta to an existing one, indicating a part is complete, or indicating the final result.

**Default:** `Annotated[PartStartEvent | PartDeltaEvent | PartEndEvent | FinalResultEvent, pydantic.Discriminator('event_kind')]`

### HandleResponseEvent

An event yielded when handling a model response, indicating tool calls and results.

**Default:** `Annotated[FunctionToolCallEvent | FunctionToolResultEvent | ToolAvailabilityDeltaEvent | OutputToolCallEvent | OutputToolResultEvent | DeferredToolRequestsEvent | DeferredToolResultsEvent, pydantic.Discriminator('event_kind')]`

### CUSTOM\_EVENT\_TYPES

Registry of [`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent) subclasses, keyed by their `name`.

Subclasses register automatically when their class is defined, so an event type is only deserializable in processes that have imported the module defining it; see [`UnknownCustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UnknownCustomEvent) for what happens otherwise.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`type`](https://docs.python.org/3/glossary.html#term-type)\[[`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent)\]\] **Default:** `_EventRegistry[type['CustomEvent']]()`

### CAPABILITY\_EVENT\_TYPES

Registry of [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent) subclasses, keyed by `kind`.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`type`](https://docs.python.org/3/glossary.html#term-type)\[[`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent)\]\] **Default:** `_EventRegistry[type['CapabilityEvent']]()`

### RealtimeSessionEvent

An event that occurs only in realtime session streams.

**Default:** `Annotated[RealtimeTurnCompleteEvent | RealtimeInputSpeechStartEvent | RealtimeInputSpeechEndEvent | RealtimeOutputSpeechStartEvent | RealtimeOutputSpeechEndEvent | RealtimeResponseInterruptedEvent | RealtimeInputTranscriptionErrorEvent | RealtimeSessionReconnectEvent | RealtimeSessionErrorEvent, pydantic.Discriminator('event_kind')]`

### AgentStreamEvent

An event in an agent run or realtime session stream.

**Default:** `Annotated[ModelResponseStreamEvent | EnqueuedMessagesEvent | HandleResponseEvent | RealtimeSessionEvent | CustomEvent | CapabilityEvent, pydantic.Discriminator('event_kind')]`

### ToolSearchArgs

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Typed arguments for a tool-search call.

Carried on [`NativeToolSearchCallPart.args`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolSearchCallPart.args) (native server-side path) and [`ToolSearchCallPart.args`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchCallPart.args) (local-fallback path) as the canonical cross-provider shape. Each adapter normalizes its provider's wire format into this shape on parse, and rebuilds the wire format from this shape on emit.

#### Attributes

##### queries

Normalized search inputs.

-   Anthropic BM25 / regex: single-item list with the query string.
-   OpenAI server-executed `tool_search`: the list of tool paths the model picked.
-   OpenAI client-execution / local `search_tools` fallback: single-item list with the keywords string.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

### ToolSearchReturnContent

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Typed return value of the framework-managed tool-search builtin.

Carried on [`NativeToolSearchReturnPart.content`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolSearchReturnPart.content) (native server-side path) and [`ToolSearchReturnPart.content`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchReturnPart.content) (local-fallback path) as the canonical cross-provider shape.

#### Attributes

##### discovered\_tools

Matches ordered by relevance. An empty list means "search ran, nothing matched".

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ToolSearchMatch`\]

##### message

Optional text shown to the model when no matches were found.

Rendered as text on local fallback / Anthropic custom-callable empty-results path. Stripped on OpenAI client-execution and Anthropic server-side replay (those carry only structural fields).

**Type:** [`NotRequired`](https://docs.python.org/3/library/typing.html#typing.NotRequired)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

### ToolSearchCallPart

**Bases:** [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart)

Typed view of a [`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart) for the local `search_tools` function call.

Used on the local-fallback path (and as the synthetic-injection target on non-native providers receiving cross-provider history). The native server-side path uses [`NativeToolSearchCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolSearchCallPart) instead.

To detect a tool-search part regardless of execution path (native server-side vs. local fallback), check `part.tool_kind == 'tool-search'` -- this works across both call/return and both server/local variants.

Shadows `args` with the canonical typed shape. The `str` variant covers the streaming / partial-args case before parsing completes; once parsed, `args` is a [`ToolSearchArgs`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchArgs) `TypedDict`.

#### Attributes

##### tool\_name

Default tool name for the typed subclass. Discrimination drives off `tool_kind`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['search\_tools'\] **Default:** `'search_tools'`

##### args

Tool-search query payload.

Narrows the parent's `str | dict[str, Any] | None` to a typed [`ToolSearchArgs`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchArgs) when parsed. Streaming / partial-args still arrive as `str` until they're complete.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `ToolSearchArgs` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_kind

Discriminator for the typed subclass (framework-emitted `search_tools` call).

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool-search'\] **Default:** `'tool-search'`

##### typed\_args

Typed view of the validated tool-search arguments, or `None` if not yet parseable.

In non-streaming code (a typed call part on a finalized [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)), this is always populated -- once a part is narrowed to this typed subclass, its `args` have been parsed and validated.

Returns `None` only in streaming-partial state, where `args` is still an in-progress JSON string the model hasn't finished emitting. For raw string-tolerant access, use the inherited `args_as_dict()`.

**Type:** `ToolSearchArgs` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### queries

Subfield accessor for `typed_args['queries']`.

Returns an empty list if args haven't been parsed yet (streaming-partial, i.e. `typed_args` is `None`).

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

### ToolSearchReturnPart

**Bases:** [`ToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturnPart)

Typed view of a [`ToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolReturnPart) for the local `search_tools` function return.

Used on the local-fallback path (and as the synthetic-injection target on non-native providers receiving cross-provider history). The native server-side path uses [`NativeToolSearchReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolSearchReturnPart) instead.

To detect a tool-search part regardless of execution path (native server-side vs. local fallback), check `part.tool_kind == 'tool-search'` -- this works across both call/return and both server/local variants.

Shadows `content` with a narrower [`ToolSearchReturnContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchReturnContent) `TypedDict`.

#### Attributes

##### content

Discovered-tools payload.

Narrows the parent's `ToolReturnContent` to a typed [`ToolSearchReturnContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchReturnContent).

**Type:** `ToolSearchReturnContent` **Default:** `field(kw_only=True)`

##### tool\_name

Default tool name for the typed subclass. Discrimination drives off `tool_kind`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['search\_tools'\] **Default:** `'search_tools'`

##### tool\_kind

Discriminator for the typed subclass (framework-emitted `search_tools` return).

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool-search'\] **Default:** `'tool-search'`

##### discovered\_tools

Subfield accessor for `content['discovered_tools']`.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ToolSearchMatch`\]

##### message

Subfield accessor for `content.get('message')`.

The message is `NotRequired` on [`ToolSearchReturnContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchReturnContent); returns `None` when no message was set (e.g. on non-empty match returns).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### ToolAvailabilityDeltaPart

Records that the set of tools available to the model changed at this point.

Additions only. Withdrawing a tool is not supported yet, because no provider can be told about one without also invalidating the prompt cache this part exists to protect: Anthropic rejects a reference to a tool the request doesn't declare, so a withdrawn tool has to leave the `tools` array, and that is itself the invalidation. The name says _availability_ rather than _addition_ so removals can join once they can be done cache-safely -- see [https://github.com/pydantic/pydantic-ai/issues/6985](https://github.com/pydantic/pydantic-ai/issues/6985).

#### Attributes

##### tools\_added

Names of tools this point in history reveals.

A reveal is what the model has been _shown_; whether the tool is callable is the broader availability question, which for a capability-owned tool also asks whether its owning capability is loaded.

**Type:** [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated)\[[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], [`pydantic.Field`](https://docs.pydantic.dev/latest/api/pydantic/fields/#pydantic.fields.Field)(`validation_alias`\=([`pydantic.AliasChoices`](https://docs.pydantic.dev/latest/api/pydantic/aliases/#pydantic.aliases.AliasChoices)(`tools_added`, `added`)))\] **Default:** `field(default_factory=(lambda: []))`

##### tool\_call\_id

The tool call associated with the change, if any.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### part\_kind

Part type identifier, this is available on all parts as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool-availability-delta'\] **Default:** `'tool-availability-delta'`

#### Methods

##### otel\_message\_parts

```python
def otel_message_parts(
    settings: InstrumentationSettings,
) -> list[_otel_messages.MessagePart]
```

Render the change as trace content.

Tool names are recorded regardless of `include_content`: they aren't user content, they're already visible in the request's tool definitions, and a run where the model suddenly can call something is unreadable without them.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_otel_messages.MessagePart`\]

### ToolAvailabilityDeltaEvent

An event indicating tools were made available mid-run, carrying the recorded delta part.

This is request-side because the delta is created while executing a tool, after response-part streaming has finished. It records the post-dedup change, while `ToolReturnPart.tools` preserves the caller's pre-dedup intent, and is emitted for capability loads as well as tool returns.

#### Attributes

##### part

The tool availability delta part that will be recorded in message history.

**Type:** [`ToolAvailabilityDeltaPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolAvailabilityDeltaPart)

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool\_availability\_delta'\] **Default:** `'tool_availability_delta'`

### NativeToolSearchCallPart

**Bases:** [`NativeToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolCallPart)

Typed view of a [`NativeToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolCallPart) for tool search.

Used on the native server-side tool-search path (Anthropic BM25/regex, OpenAI Responses) where the provider executes the search and emits a native result. The local-fallback path uses [`ToolSearchCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchCallPart) instead.

To detect a tool-search part regardless of execution path (native server-side vs. local fallback), check `part.tool_kind == 'tool-search'` -- this works across both call/return and both server/local variants.

Shadows `args` with a narrower type. The `str` variant covers the streaming / partial-args case before parsing completes; once parsed, `args` is a [`ToolSearchArgs`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchArgs) `TypedDict`.

#### Attributes

##### tool\_name

Default tool name for the typed subclass. Discrimination drives off `tool_kind`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool\_search'\] **Default:** `'tool_search'`

##### args

Tool-search query payload.

Narrows the parent's `str | dict[str, Any] | None` to a typed [`ToolSearchArgs`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchArgs) when parsed. Streaming / partial-args still arrive as `str` until they're complete.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `ToolSearchArgs` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tool\_kind

Discriminator for the typed subclass (cross-provider tool-search call).

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool-search'\] **Default:** `'tool-search'`

##### typed\_args

Typed view of the validated tool-search arguments, or `None` if not yet parseable.

In non-streaming code (a typed call part on a finalized [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)), this is always populated -- once a part is narrowed to this typed subclass, its `args` have been parsed and validated.

Returns `None` only in streaming-partial state, where `args` is still an in-progress JSON string the model hasn't finished emitting. For raw string-tolerant access, use the inherited `args_as_dict()`.

**Type:** `ToolSearchArgs` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### queries

Subfield accessor for `typed_args['queries']`.

Returns an empty list if args haven't been parsed yet (streaming-partial, i.e. `typed_args` is `None`).

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

### NativeToolSearchReturnPart

**Bases:** [`NativeToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolReturnPart)

Typed view of a [`NativeToolReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.NativeToolReturnPart) for tool search.

Used on the native server-side tool-search path (Anthropic BM25/regex, OpenAI Responses) where the provider executes the search and emits a native result. The local-fallback path uses [`ToolSearchReturnPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchReturnPart) instead.

To detect a tool-search part regardless of execution path (native server-side vs. local fallback), check `part.tool_kind == 'tool-search'` -- this works across both call/return and both server/local variants.

Shadows `content` with a narrower [`ToolSearchReturnContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchReturnContent) `TypedDict`.

#### Attributes

##### content

Discovered-tools payload.

Narrows the parent's `ToolReturnContent` to a typed [`ToolSearchReturnContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchReturnContent).

**Type:** `ToolSearchReturnContent` **Default:** `field(kw_only=True)`

##### tool\_name

Default tool name for the typed subclass. Discrimination drives off `tool_kind`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool\_search'\] **Default:** `'tool_search'`

##### tool\_kind

Discriminator for the typed subclass (cross-provider tool-search return).

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['tool-search'\] **Default:** `'tool-search'`

##### discovered\_tools

Subfield accessor for `content['discovered_tools']`.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ToolSearchMatch`\]

##### message

Subfield accessor for `content.get('message')`.

The message is `NotRequired` on [`ToolSearchReturnContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolSearchReturnContent); returns `None` when no message was set (e.g. on non-empty match returns).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

---
