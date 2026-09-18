# [pydantic_ai.models.instrumented](https://pydantic.dev/docs/ai/api/models/instrumented/)

# pydantic\_ai.models.instrumented

### InstrumentationSettings

Options for instrumenting models and agents with OpenTelemetry.

Used in:

-   [`Instrumentation`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Instrumentation) capability
-   [`Agent.instrument`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.instrument) / [`Agent.instrument_all()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.instrument_all)
-   [`InstrumentedModel`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentedModel)

See the [Debugging and Monitoring guide](https://pydantic.dev/docs/ai/integrations/logfire/) for more info.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    tracer_provider: TracerProvider | None = None,
    meter_provider: MeterProvider | None = None,
    include_binary_content: bool = True,
    include_content: bool = True,
    include_model_request_parameters: bool = True,
    version: Literal[2, 3, 4, 5, 6] = DEFAULT_INSTRUMENTATION_VERSION,
    use_aggregated_usage_attribute_names: bool = True,
)
```

Create instrumentation options.

###### Parameters

**`tracer_provider`** : `TracerProvider` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The OpenTelemetry tracer provider to use. If not provided, the global tracer provider is used. Calling `logfire.configure()` sets the global tracer provider, so most users don't need this.

**`meter_provider`** : `MeterProvider` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The OpenTelemetry meter provider to use. If not provided, the global meter provider is used. Calling `logfire.configure()` sets the global meter provider, so most users don't need this.

**`include_binary_content`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to include binary file data in the instrumentation events: user prompts and model responses, tool returns, the agent's output and the arguments its output function receives, and run and tool deferral metadata. The media type is recorded either way. Binary content is found inside dictionaries, lists and `ToolReturn`s, but not inside your own types: a `BinaryContent` held as a field of a model or dataclass you define is still recorded in full.

**`include_content`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to include prompts, completions, and tool call arguments and responses in the instrumentation events.

**`include_model_request_parameters`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to emit the `model_request_parameters` span attribute on model request spans. This serializes the full `ModelRequestParameters` (output configuration and every tool definition, including fields that are not sent to the model such as tool `metadata` and, when not requested, `return_schema`). Defaults to `True`. Set to `False` to omit it entirely, which is useful when large tool output schemas make the attribute big enough to strain span export. The OpenTelemetry `gen_ai.tool.definitions` attribute (tool name, description, and parameters) is always emitted regardless of this setting.

**`version`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\[2, 3, 4, 5, 6\] _Default:_ `DEFAULT_INSTRUMENTATION_VERSION`

Version of the data format. This is unrelated to the Pydantic AI package version. Defaults to version 5. Versions 2, 3, and 4 are deprecated compatibility formats and emit a `PydanticAIDeprecationWarning` when used. Version 2 uses the newer OpenTelemetry GenAI spec and stores messages in the following attributes:

-   `gen_ai.system_instructions` for instructions passed to the agent.
-   `gen_ai.input.messages` and `gen_ai.output.messages` on model request spans.
-   `pydantic_ai.all_messages` on agent run spans. Version 3 is the same as version 2, with additional support for thinking tokens. Version 4 is the same as version 3, with GenAI semantic conventions for multimodal content: URL-based media uses type='uri' with uri and mime\_type fields (and modality for image/audio/video). Inline binary content uses type='blob' with mime\_type and content fields (and modality for image/audio/video). [https://opentelemetry.io/docs/specs/semconv/gen-ai/non-normative/examples-llm-calls/#multimodal-inputs-example](https://opentelemetry.io/docs/specs/semconv/gen-ai/non-normative/examples-llm-calls/#multimodal-inputs-example) Version 5 is the same as version 4, but CallDeferred and ApprovalRequired exceptions no longer record an exception event or set the span status to ERROR -- the span is left as UNSET, since deferrals are control flow, not errors. Version 6 is the same as version 5, but tool results are emitted in a message with `role='tool'` rather than `role='user'`, which is the role the GenAI semantic conventions pair with the `tool_call_response` parts they carry. Opt in to it when your telemetry consumer keys on the message role; it is not the default.

**`use_aggregated_usage_attribute_names`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to use `gen_ai.aggregated_usage.*` attribute names for token usage on agent run spans instead of the standard `gen_ai.usage.*` names. Defaults to True to prevent double-counting in observability backends that aggregate span attributes across parent and child spans. Note: `gen_ai.aggregated_usage.*` is a custom namespace, not part of the OpenTelemetry Semantic Conventions. It may be updated if OTel introduces an official convention.

##### aggregated\_usage\_attributes

```python
def aggregated_usage_attributes(usage: UsageBase) -> dict[str, int]
```

Cumulative-usage OpenTelemetry attributes for a run/session span.

Remaps `gen_ai.usage.*` to `gen_ai.aggregated_usage.*` when `use_aggregated_usage_attribute_names` is set, so a backend that sums span attributes doesn't double-count the run's cumulative usage against the per-request `chat` spans' `gen_ai.usage.*`. Shared by the classic agent-run span (the `Instrumentation` capability) and the realtime session span so the two can't drift.

###### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`int`](https://docs.python.org/3/builtins/functions.html#int)\]

### InstrumentedModel

**Bases:** `WrapperModel`

Model which wraps another model so that requests are instrumented with OpenTelemetry.

See the [Debugging and Monitoring guide](https://pydantic.dev/docs/ai/integrations/logfire/) for more info.

#### Attributes

##### instrumentation\_settings

Instrumentation settings for this model.

**Type:** [`InstrumentationSettings`](https://pydantic.dev/docs/ai/api/models/instrumented/#pydantic_ai.models.instrumented.InstrumentationSettings) **Default:** `options or InstrumentationSettings()`

### instrument\_model

```python
def instrument_model(model: Model, instrument: InstrumentationSettings | bool) -> Model
```

Wrap `model` in an `InstrumentedModel` so OTel/Logfire spans are emitted around requests.

#### Returns

`Model`

---
