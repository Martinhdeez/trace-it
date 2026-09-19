# [pydantic_ai.direct](https://pydantic.dev/docs/ai/api/pydantic-ai/direct/)

# pydantic\_ai.direct

Methods for making imperative requests to language models with minimal abstraction.

These methods allow you to make requests to LLMs where the only abstraction is input and output schema translation so you can use all models with the same API.

These methods are thin wrappers around [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) implementations.

### StreamedResponseSync

Synchronous wrapper for an async streaming response, running the whole stream on the caller's event loop.

The stream uses the internal `SyncStreamBridge` to keep context-manager and iterator lifecycles in stable tasks. Exiting the `with` block cancels the underlying request promptly and closes the connection instead of waiting for the whole response to arrive.

This class must be used as a context manager with the `with` statement. The synchronous stream is created when the `with` block is entered and must be used and closed on that thread.

#### Attributes

##### response

Get the current state of the response.

**Type:** [`messages.ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

##### usage

Get the usage of the response so far.

**Type:** [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage)

##### model\_name

Get the model name of the response.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### timestamp

Get the timestamp of the response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

#### Methods

##### \_\_iter\_\_

```python
def __iter__() -> Iterator[messages.ModelResponseStreamEvent]
```

Stream the response as an iterable of [`ModelResponseStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponseStreamEvent)s.

###### Returns

[`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)\[[`messages.ModelResponseStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponseStreamEvent)\]

### model\_request

`@async`

```python
def model_request(
    model: models.Model | models.KnownModelName | str,
    messages: Sequence[messages.ModelMessage],
    *,
    model_settings: settings.ModelSettings | None = None,
    model_request_parameters: models.ModelRequestParameters | None = None,
    instrument: instrumented_models.InstrumentationSettings | bool | None = None,
) -> messages.ModelResponse
```

Make a non-streamed request to a model.

model\_request\_example.py

```py
from pydantic_ai import ModelRequest
from pydantic_ai.direct import model_request


async def main():
    model_response = await model_request(
        'anthropic:claude-haiku-4-5',
        [ModelRequest.user_text_prompt('What is the capital of France?')]  # (1)
    )
    print(model_response)
    '''
    ModelResponse(
        parts=[TextPart(content='The capital of France is Paris.')],
        usage=RequestUsage(input_tokens=56, output_tokens=7),
        model_name='claude-haiku-4-5',
        timestamp=datetime.datetime(...),
    )
    '''
```

See [`ModelRequest.user_text_prompt`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest.user_text_prompt) for details.

#### Returns

[`messages.ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse) -- The model response and token usage associated with the request.

#### Parameters

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The model to make a request to. We allow `str` here since the actual list of allowed models changes frequently.

**`messages`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`messages.ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

Messages to send to the model

**`model_settings`** : [`settings.ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

optional model settings

**`model_request_parameters`** : [`models.ModelRequestParameters`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestParameters) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

optional model request parameters

**`instrument`** : `instrumented_models.InstrumentationSettings` | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to instrument the request with OpenTelemetry/Logfire, if `None` the value from [`logfire.instrument_pydantic_ai`](https://logfire.pydantic.dev/docs/api/logfire/#logfire.Logfire.instrument_pydantic_ai) is used.

### model\_request\_sync

```python
def model_request_sync(
    model: models.Model | models.KnownModelName | str,
    messages: Sequence[messages.ModelMessage],
    *,
    model_settings: settings.ModelSettings | None = None,
    model_request_parameters: models.ModelRequestParameters | None = None,
    instrument: instrumented_models.InstrumentationSettings | bool | None = None,
) -> messages.ModelResponse
```

Make a Synchronous, non-streamed request to a model.

This is a convenience method that wraps [`model_request`](https://pydantic.dev/docs/ai/api/pydantic-ai/direct/#pydantic_ai.direct.model_request) with `loop.run_until_complete(...)`. You therefore can't use this method inside async code or if there's an active event loop.

model\_request\_sync\_example.py

```py
from pydantic_ai import ModelRequest
from pydantic_ai.direct import model_request_sync

model_response = model_request_sync(
    'anthropic:claude-haiku-4-5',
    [ModelRequest.user_text_prompt('What is the capital of France?')]  # (1)
)
print(model_response)
'''
ModelResponse(
    parts=[TextPart(content='The capital of France is Paris.')],
    usage=RequestUsage(input_tokens=56, output_tokens=7),
    model_name='claude-haiku-4-5',
    timestamp=datetime.datetime(...),
)
'''
```

See [`ModelRequest.user_text_prompt`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest.user_text_prompt) for details.

#### Returns

[`messages.ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse) -- The model response and token usage associated with the request.

#### Parameters

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The model to make a request to. We allow `str` here since the actual list of allowed models changes frequently.

**`messages`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`messages.ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

Messages to send to the model

**`model_settings`** : [`settings.ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

optional model settings

**`model_request_parameters`** : [`models.ModelRequestParameters`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestParameters) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

optional model request parameters

**`instrument`** : `instrumented_models.InstrumentationSettings` | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to instrument the request with OpenTelemetry/Logfire, if `None` the value from [`logfire.instrument_pydantic_ai`](https://logfire.pydantic.dev/docs/api/logfire/#logfire.Logfire.instrument_pydantic_ai) is used.

### model\_request\_stream

```python
def model_request_stream(
    model: models.Model | models.KnownModelName | str,
    messages: Sequence[messages.ModelMessage],
    *,
    model_settings: settings.ModelSettings | None = None,
    model_request_parameters: models.ModelRequestParameters | None = None,
    instrument: instrumented_models.InstrumentationSettings | bool | None = None,
) -> AbstractAsyncContextManager[models.StreamedResponse]
```

Make a streamed async request to a model.

model\_request\_stream\_example.py

```py
from pydantic_ai import ModelRequest
from pydantic_ai.direct import model_request_stream


async def main():
    messages = [ModelRequest.user_text_prompt('Who was Albert Einstein?')]  # (1)
    async with model_request_stream('openai:gpt-5-mini', messages) as stream:
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        print(chunks)
        '''
        [
            PartStartEvent(index=0, part=TextPart(content='Albert Einstein was ')),
            FinalResultEvent(tool_name=None, tool_call_id=None),
            PartDeltaEvent(
                index=0, delta=TextPartDelta(content_delta='a German-born theoretical ')
            ),
            PartDeltaEvent(index=0, delta=TextPartDelta(content_delta='physicist.')),
            PartEndEvent(
                index=0,
                part=TextPart(
                    content='Albert Einstein was a German-born theoretical physicist.'
                ),
            ),
        ]
        '''
```

See [`ModelRequest.user_text_prompt`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest.user_text_prompt) for details.

#### Returns

`AbstractAsyncContextManager`\[[`models.StreamedResponse`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.StreamedResponse)\] -- A [stream response](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.StreamedResponse) async context manager.

#### Parameters

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The model to make a request to. We allow `str` here since the actual list of allowed models changes frequently.

**`messages`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`messages.ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

Messages to send to the model

**`model_settings`** : [`settings.ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

optional model settings

**`model_request_parameters`** : [`models.ModelRequestParameters`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestParameters) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

optional model request parameters

**`instrument`** : `instrumented_models.InstrumentationSettings` | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to instrument the request with OpenTelemetry/Logfire, if `None` the value from [`logfire.instrument_pydantic_ai`](https://logfire.pydantic.dev/docs/api/logfire/#logfire.Logfire.instrument_pydantic_ai) is used.

### model\_request\_stream\_sync

```python
def model_request_stream_sync(
    model: models.Model | models.KnownModelName | str,
    messages: Sequence[messages.ModelMessage],
    *,
    model_settings: settings.ModelSettings | None = None,
    model_request_parameters: models.ModelRequestParameters | None = None,
    instrument: instrumented_models.InstrumentationSettings | bool | None = None,
) -> StreamedResponseSync
```

Make a streamed synchronous request to a model.

This is the synchronous version of [`model_request_stream`](https://pydantic.dev/docs/ai/api/pydantic-ai/direct/#pydantic_ai.direct.model_request_stream). It drives the asynchronous stream on the caller's event loop while providing a synchronous iterator interface. The returned context manager must be used and closed on the thread where the synchronous stream is created.

model\_request\_stream\_sync\_example.py

```py

from pydantic_ai import ModelRequest
from pydantic_ai.direct import model_request_stream_sync

messages = [ModelRequest.user_text_prompt('Who was Albert Einstein?')]
with model_request_stream_sync('openai:gpt-5-mini', messages) as stream:
    chunks = []
    for chunk in stream:
        chunks.append(chunk)
    print(chunks)
    '''
    [
        PartStartEvent(index=0, part=TextPart(content='Albert Einstein was ')),
        FinalResultEvent(tool_name=None, tool_call_id=None),
        PartDeltaEvent(
            index=0, delta=TextPartDelta(content_delta='a German-born theoretical ')
        ),
        PartDeltaEvent(index=0, delta=TextPartDelta(content_delta='physicist.')),
        PartEndEvent(
            index=0,
            part=TextPart(
                content='Albert Einstein was a German-born theoretical physicist.'
            ),
        ),
    ]
    '''
```

#### Returns

`StreamedResponseSync` -- A [sync stream response](https://pydantic.dev/docs/ai/api/pydantic-ai/direct/#pydantic_ai.direct.StreamedResponseSync) context manager.

#### Parameters

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The model to make a request to. We allow `str` here since the actual list of allowed models changes frequently.

**`messages`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`messages.ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

Messages to send to the model

**`model_settings`** : [`settings.ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

optional model settings

**`model_request_parameters`** : [`models.ModelRequestParameters`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestParameters) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

optional model request parameters

**`instrument`** : `instrumented_models.InstrumentationSettings` | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Whether to instrument the request with OpenTelemetry/Logfire, if `None` the value from [`logfire.instrument_pydantic_ai`](https://logfire.pydantic.dev/docs/api/logfire/#logfire.Logfire.instrument_pydantic_ai) is used.

---
