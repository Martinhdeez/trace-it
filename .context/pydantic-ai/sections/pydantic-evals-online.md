# [pydantic_evals.online](https://pydantic.dev/docs/ai/api/pydantic_evals/online/)

# pydantic\_evals.online

Online evaluation -- attach evaluators to live functions for automatic background evaluation.

This module provides the infrastructure for running evaluators on production (or staging) traffic. The same `Evaluator` instances used with `Dataset.evaluate()` work here, the difference is in how they are wired up (decorator vs dataset) rather than what they are.

Example:

```python
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.online import evaluate


@dataclass
class IsNonEmpty(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return bool(ctx.output)


@evaluate(IsNonEmpty())
async def my_function(x: int) -> int:
    return x
```

### SinkPayload

Container passed to [`EvaluationSink.submit`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.EvaluationSink.submit).

Do not instantiate directly

`SinkPayload` is constructed internally by pydantic-evals. We reserve the right to add fields in any release -- if you build your own instances, a future version may break your code. Sink implementations should accept the payload as-is and read only the fields they need.

#### Attributes

##### results

Evaluation results from the evaluator run.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`EvaluationResult`\]

##### failures

Failures from the evaluator run if it raised.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`EvaluatorFailure`\]

##### context

The full evaluator context for the function call.

**Type:** `EvaluatorContext`

##### span\_reference

Reference to the OTel span for the function call, if available.

**Type:** `SpanReference` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### target

Identifies the function/agent being evaluated, supplied by the `@evaluate` decorator (defaults resolved at decoration time).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### EvaluationSink

**Bases:** [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Protocol for **additional** evaluation result destinations.

By default, online evaluation emits `gen_ai.evaluation.result` OTel events for every evaluator run -- no sink registration required. Sinks are the escape hatch for custom handling _in addition to_ OTel emission: in-memory test capture, fan-out to Slack/DB, non-OTel backends, alerting pipelines, etc. See [`OnlineEvalConfig.default_sink`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.OnlineEvalConfig.default_sink).

To disable the default OTel emission (e.g. in tests that only want to assert on a custom sink), set [`emit_otel_events=False`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.OnlineEvalConfig.emit_otel_events) on the config.

#### Methods

##### submit

`@async`

```python
def submit(payload: SinkPayload) -> None
```

Submit evaluation results to the sink.

The payload may include results from one or more evaluators that ran for a given function call -- when multiple evaluators share this sink, their results are batched into a single `submit()` call. Each result carries enough metadata (name, evaluator version, source) to be attributed downstream; the exact batching behavior is an implementation detail and may change.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`payload`** : `SinkPayload`

A [`SinkPayload`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.SinkPayload) bundling results, failures, context, span reference, and target. Sinks should read only the fields they need; new fields may be added in future releases.

### SamplingContext

Context available when deciding whether to sample an evaluator.

Contains the information available _before_ the decorated function runs -- the evaluator instance, function inputs, config metadata, and a per-call random seed. The function's output and duration are not yet available at sampling time.

#### Attributes

##### evaluator

The evaluator being sampled.

**Type:** `Evaluator`

##### inputs

The inputs to the decorated function.

**Type:** [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### metadata

Metadata from the [`OnlineEvalConfig`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.OnlineEvalConfig), if set.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### call\_seed

A uniform random value in \[0, 1) generated once per decorated function call.

Shared across all evaluators for the same call. In `'correlated'` sampling mode this is used automatically; in `'independent'` mode it is available for custom `sample_rate` callables that want to implement their own correlated logic.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

### CallbackSink

An `EvaluationSink` that delegates to a user-provided callable.

The callback receives the results, failures, and context. Other fields on the [`SinkPayload`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.SinkPayload) (such as `span_reference` and `target`) are not passed -- use a custom `EvaluationSink` implementation if you need them.

### SpanReference

Identifies a span that evaluation results should be associated with.

Used by sinks to associate evaluation results with the original function execution span.

#### Attributes

##### trace\_id

The trace ID of the span.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### span\_id

The span ID of the span.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### OnlineEvaluator

Wraps an `Evaluator` with per-evaluator online configuration.

Different evaluators often need different settings -- a cheap heuristic should run on 100% of traffic while an expensive LLM judge might run on only 1%.

#### Attributes

##### evaluator

The evaluator to run.

To version an evaluator, override [`get_evaluator_version`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.Evaluator.get_evaluator_version) on the `Evaluator` subclass (see `Evaluator` docstring). The framework calls it at dispatch time and propagates the value to sinks alongside each result.

**Type:** `Evaluator`

##### sample\_rate

Probability of running this evaluator (0.0-1.0), or a callable returning a float or bool.

When a callable, it receives a [`SamplingContext`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.SamplingContext) with the function inputs, config metadata, and evaluator name -- but not the output or duration (which aren't available yet at sampling time).

Defaults to `None`, which uses the config's `default_sample_rate` at each call. Set explicitly to override.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`SamplingContext`\], [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_concurrency

Maximum number of concurrent evaluations for this evaluator.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `10`

##### sink

Override additional sink(s) for this evaluator. If `None`, the config's `default_sink` is used.

Sinks are _additive_ to the default OTel event emission -- not replacements. See [`EvaluationSink`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.EvaluationSink).

**Type:** `EvaluationSink` | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`EvaluationSink` | `SinkCallback`\] | `SinkCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### on\_max\_concurrency

Called when an evaluation is dropped because `max_concurrency` was reached.

Receives the `EvaluatorContext` that would have been evaluated. Can be sync or async. If `None` (the default), dropped evaluations are silently ignored.

**Type:** `OnMaxConcurrencyCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### on\_sampling\_error

Called synchronously when a `sample_rate` callable raises an exception.

Receives the exception and the evaluator. Must be sync (not async), since sampling runs before the decorated function. If set, the evaluator is skipped. If `None`, uses the config's `on_sampling_error` default. If neither is set, the exception propagates to the caller.

**Type:** `OnSamplingErrorCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### on\_error

Called when an exception occurs in a sink or on\_max\_concurrency callback.

Receives the exception, evaluator context, evaluator instance, and a location string (see [`OnErrorLocation`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.OnErrorLocation)). Can be sync or async. `'sink'` covers both custom sink failures and the rarer default OTel event emission failures -- the value is intentionally broad. If `None`, uses the config's `on_error` default. If neither is set, exceptions are silently suppressed.

**Type:** `OnErrorCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### run\_on\_errors

Whether to run this evaluator when the wrapped function/agent raises.

When `False` (the default), the evaluator is skipped if the wrapped call raises -- only successful results reach the evaluator. When `True`, the raised exception is passed as `EvaluatorContext.output` so the evaluator can score failure modes (e.g. count tool errors, classify exception types). The exception still propagates to the caller after dispatch.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

### EvaluatorContextSource

**Bases:** [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Protocol for retrieving stored evaluator contexts.

Implementations reconstruct [`EvaluatorContext`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.EvaluatorContext) objects from stored traces (e.g., Logfire). The batch method allows fetching contexts for multiple spans in a single call.

#### Methods

##### fetch

`@async`

```python
def fetch(span: SpanReference) -> EvaluatorContext
```

Fetch an evaluator context for a single span.

###### Returns

`EvaluatorContext` -- The evaluator context for the span.

###### Parameters

**`span`** : `SpanReference`

Reference to the span to fetch context for.

##### fetch\_many

`@async`

```python
def fetch_many(spans: Sequence[SpanReference]) -> list[EvaluatorContext]
```

Fetch evaluator contexts for multiple spans in a single batch.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`EvaluatorContext`\] -- Evaluator contexts in the same order as the input spans.

###### Parameters

**`spans`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`SpanReference`\]

References to the spans to fetch context for.

### OnlineEvalConfig

Holds cross-evaluator defaults for online evaluation.

Create instances for different evaluation configurations, or use the global `DEFAULT_CONFIG` via the module-level `evaluate()` and `configure()` functions.

#### Attributes

##### default\_sink

Additional sink(s) to receive results, for evaluators that don't specify their own.

Sinks run _in addition to_ the default `gen_ai.evaluation.result` OTel event emission -- they are the escape hatch for custom destinations (in-memory test capture, fan-out to Slack/DB, non-OTel backends). To disable OTel emission itself, set [`emit_otel_events=False`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.OnlineEvalConfig.emit_otel_events).

**Type:** `EvaluationSink` | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`EvaluationSink` | `SinkCallback`\] | `SinkCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### default\_sample\_rate

Default sample rate for evaluators that don't specify their own.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`SamplingContext`\], [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool)\] **Default:** `1.0`

##### emit\_otel\_events

Whether to emit `gen_ai.evaluation.result` OTel events for every evaluator run.

When `True` (the default), dispatch emits one OTel log event per `EvaluationResult` or `EvaluatorFailure`, following the [OTel GenAI evaluation semconv](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-events/#event-gen_aievaluationresult). If no OTel SDK is configured in the process, emission is a cheap no-op.

Set to `False` to disable -- useful for tests that want to assert on a custom sink alone, or in environments where OTel emission is undesirable. Custom sinks registered via `default_sink` still run regardless of this flag. With `emit_otel_events=False` AND no sinks configured, dispatch short-circuits entirely (the evaluator never runs) since results would have nowhere to go.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### include\_baggage

Whether to copy OTel baggage entries onto every emitted evaluation event.

When `True` (the default), each emitted `gen_ai.evaluation.result` event also carries the keys present in the current OTel baggage as attributes -- useful for propagating tenant/user/request identifiers from the calling context. Standard `gen_ai.*` and `error.type` attributes always win on conflict, so baggage cannot accidentally overwrite the semantic-convention attributes.

Set to `False` to skip the baggage snapshot per event.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### sampling\_mode

Controls how per-evaluator sample rates interact for a single call.

-   `'independent'` (default): each evaluator decides independently.
-   `'correlated'`: a shared random seed is used so that lower-rate evaluators' calls are a subset of higher-rate ones, minimising total overhead.

See [`SamplingMode`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.SamplingMode) for details.

**Type:** `SamplingMode` **Default:** `'independent'`

##### enabled

Whether online evaluation is enabled for this config.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### metadata

Optional metadata to include in evaluator contexts.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### on\_max\_concurrency

Default handler called when an evaluation is dropped because `max_concurrency` was reached.

Receives the `EvaluatorContext` that would have been evaluated. Can be sync or async. If `None` (the default), dropped evaluations are silently ignored. Per-evaluator `OnlineEvaluator.on_max_concurrency` overrides this default.

**Type:** `OnMaxConcurrencyCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### on\_sampling\_error

Default handler called synchronously when a `sample_rate` callable raises.

Receives the exception and the evaluator. Must be sync (not async). If set, the evaluator is skipped. If `None` (the default), the exception propagates to the caller. Per-evaluator `OnlineEvaluator.on_sampling_error` overrides this default.

**Type:** `OnSamplingErrorCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### on\_error

Default handler called when an exception occurs in a sink or on\_max\_concurrency callback.

Receives the exception, evaluator context, evaluator instance, and a location string (see [`OnErrorLocation`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.OnErrorLocation)). Can be sync or async. `'sink'` covers both custom sink failures and the rarer default OTel event emission failures -- the value is intentionally broad. If `None` (the default), exceptions are silently suppressed. Per-evaluator `OnlineEvaluator.on_error` overrides this default.

**Type:** `OnErrorCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### evaluate

```python
def evaluate(
    *evaluators: Evaluator | OnlineEvaluator,
    target: str | None = None,
    msg_template: LiteralString | None = None,
    span_name: str | None = None,
    extract_args: bool | Iterable[str] = False,
    record_return: bool = False,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]
```

Decorator to attach online evaluators to a function.

Each decorated call opens a dedicated span representing the function invocation -- evaluator events are parented to this span, and the span itself appears in the user's configured OTel/logfire traces.

Bare `Evaluator` instances are auto-wrapped in `OnlineEvaluator` at decoration time (so concurrency semaphores are shared across calls). Their `sample_rate` defaults to `None`, which resolves to the config's `default_sample_rate` at each call -- so changes to the config after decoration take effect.

To version an evaluator, override [`get_evaluator_version`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.Evaluator.get_evaluator_version) on the `Evaluator` subclass -- the framework calls it at dispatch time and records the value on every [`EvaluationResult`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.EvaluationResult) and [`EvaluatorFailure`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.EvaluatorFailure) the evaluator emits:

```python
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.online import evaluate


@dataclass
class Tone(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> str:
        return 'neutral'

    def get_evaluator_version(self) -> str | None:
        return 'v2'


@evaluate(Tone())
async def summarize(text: str) -> str:
    return text
```

###### Returns

[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[`_P`, `_R`\]\], [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[`_P`, `_R`\]\] -- A decorator that wraps the function with online evaluation.

###### Parameters

**`*evaluators`** : `Evaluator` | `OnlineEvaluator` _Default:_ `()`

Evaluators to attach. Can be `Evaluator` or `OnlineEvaluator` instances.

**`target`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Name of the thing being evaluated. Written to sinks and emitted OTel events as `gen_ai.evaluation.target`. Defaults to the decorated function's `__name__` when omitted.

**`msg_template`** : [`LiteralString`](https://docs.python.org/3/library/typing.html#typing.LiteralString) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Template for the call span's message. Defaults to `"Calling {module}.{qualname}"` like `@logfire.instrument`. When logfire is installed, `{arg=}`\-style placeholders in the template are formatted against the function's arguments.

**`span_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override for the call span's name. Defaults to `msg_template`.

**`extract_args`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] _Default:_ `False`

Whether to record function arguments as span attributes. `False` (default) records nothing; `True` records all bound arguments; an iterable of names records only those arguments. Requires logfire to be installed so arguments are serialised with their JSON schema -- raises `RuntimeError` at decoration time otherwise.

**`record_return`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether to record the function's return value as a `return` span attribute. Requires logfire for the same reason as `extract_args`.

##### should\_evaluate

```python
def should_evaluate() -> bool
```

Whether evaluators with this config should run, based on the current settings and context.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### disable\_evaluation

```python
def disable_evaluation() -> Generator[None]
```

Context manager to disable all online evaluation in the current context.

When active, decorated functions still execute normally but no evaluators are dispatched.

#### Returns

[`Generator`](https://docs.python.org/3/library/typing.html#typing.Generator)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]

### run\_evaluators

`@async`

```python
def run_evaluators(
    evaluators: Sequence[Evaluator],
    context: EvaluatorContext,
) -> tuple[list[EvaluationResult], list[EvaluatorFailure]]
```

Run evaluators on a context and return results.

Useful for re-running evaluators from stored data.

#### Returns

[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`list`](https://docs.python.org/3/glossary.html#term-list)\[`EvaluationResult`\], [`list`](https://docs.python.org/3/glossary.html#term-list)\[`EvaluatorFailure`\]\] -- A tuple of (results, failures).

#### Parameters

**`evaluators`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`Evaluator`\]

The evaluators to run.

**`context`** : `EvaluatorContext`

The evaluator context to evaluate against.

### evaluate

```python
def evaluate(
    *evaluators: Evaluator | OnlineEvaluator,
    target: str | None = None,
    msg_template: LiteralString | None = None,
    span_name: str | None = None,
    extract_args: bool | Iterable[str] = False,
    record_return: bool = False,
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]
```

Decorator to attach online evaluators to a function using the global default config.

Equivalent to `DEFAULT_CONFIG.evaluate(...)`.

Example:

```python
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.online import evaluate


@dataclass
class IsNonEmpty(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return bool(ctx.output)


@evaluate(IsNonEmpty())
async def my_function(x: int) -> int:
    return x
```

#### Returns

[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[`_P`, `_R`\]\], [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[`_P`, `_R`\]\] -- A decorator that wraps the function with online evaluation.

#### Parameters

**`*evaluators`** : `Evaluator` | `OnlineEvaluator` _Default:_ `()`

Evaluators to attach. Can be `Evaluator` or `OnlineEvaluator` instances.

**`target`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Name of the thing being evaluated. Written to sinks and emitted OTel events as `gen_ai.evaluation.target`. Defaults to the decorated function's `__name__` when omitted.

**`msg_template`** : [`LiteralString`](https://docs.python.org/3/library/typing.html#typing.LiteralString) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Template for the call span's message. Defaults to `"Calling {module}.{qualname}"` like `@logfire.instrument`.

**`span_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override for the call span's name. Defaults to `msg_template`.

**`extract_args`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] _Default:_ `False`

Whether to record function arguments as span attributes. `False` (default) records nothing; `True` records all bound arguments; an iterable of names records only those arguments. Requires logfire to be installed -- raises `RuntimeError` at decoration time otherwise.

**`record_return`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

Whether to record the function's return value as a `return` span attribute. Requires logfire for the same reason as `extract_args`.

### configure

```python
def configure(
    *,
    default_sink: EvaluationSink | Sequence[EvaluationSink | SinkCallback] | SinkCallback | None | Unset = UNSET,
    default_sample_rate: float | Callable[[SamplingContext], float | bool] | Unset = UNSET,
    sampling_mode: SamplingMode | Unset = UNSET,
    enabled: bool | Unset = UNSET,
    metadata: dict[str, Any] | None | Unset = UNSET,
    on_max_concurrency: OnMaxConcurrencyCallback | None | Unset = UNSET,
    on_sampling_error: OnSamplingErrorCallback | None | Unset = UNSET,
    on_error: OnErrorCallback | None | Unset = UNSET,
    emit_otel_events: bool | Unset = UNSET,
    include_baggage: bool | Unset = UNSET,
) -> None
```

Configure the global default `OnlineEvalConfig`.

Only provided values are updated; unset arguments are ignored. Pass `None` explicitly to clear `default_sink`, `metadata`, `on_max_concurrency`, `on_sampling_error`, or `on_error`.

#### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Parameters

**`default_sink`** : `EvaluationSink` | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`EvaluationSink` | `SinkCallback`\] | `SinkCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) | `Unset` _Default:_ `UNSET`

Default sink(s) for evaluators. Pass `None` to clear.

**`default_sample_rate`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`SamplingContext`\], [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool)\] | `Unset` _Default:_ `UNSET`

Default sample rate for evaluators.

**`sampling_mode`** : `SamplingMode` | `Unset` _Default:_ `UNSET`

Sampling mode (`'independent'` or `'correlated'`).

**`enabled`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | `Unset` _Default:_ `UNSET`

Whether online evaluation is enabled.

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) | `Unset` _Default:_ `UNSET`

Metadata to include in evaluator contexts. Pass `None` to clear.

**`on_max_concurrency`** : `OnMaxConcurrencyCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) | `Unset` _Default:_ `UNSET`

Default handler for dropped evaluations. Pass `None` to clear.

**`on_sampling_error`** : `OnSamplingErrorCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) | `Unset` _Default:_ `UNSET`

Default handler for sample\_rate exceptions. Pass `None` to clear.

**`on_error`** : `OnErrorCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) | `Unset` _Default:_ `UNSET`

Default handler for pipeline exceptions. Pass `None` to clear.

**`emit_otel_events`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | `Unset` _Default:_ `UNSET`

Whether to emit `gen_ai.evaluation.result` OTel events.

**`include_baggage`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | `Unset` _Default:_ `UNSET`

Whether to copy current OTel baggage onto every emitted event.

### wait\_for\_evaluations

`@async`

```python
def wait_for_evaluations(*, timeout: float = 30.0) -> None
```

Wait for all pending background evaluation tasks and threads to complete.

This is useful in tests to deterministically wait for background evaluators to finish instead of relying on timing-based sleeps.

For async decorated functions, evaluators run as tasks on the caller's event loop and are awaited directly. For sync decorated functions, evaluators run in background threads which are joined with the given timeout.

#### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Parameters

**`timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) _Default:_ `30.0`

Maximum seconds to wait for each background thread. Defaults to 30.

### OnErrorLocation

The location within the online evaluation pipeline where an error occurred.

-   `'sink'` -- something went wrong delivering results downstream. This is most often an exception raised by a registered [`EvaluationSink.submit`](https://pydantic.dev/docs/ai/api/pydantic_evals/online/#pydantic_evals.online.EvaluationSink.submit), but it's also used as a catch-all for failures in the default OTel event emission path (which is rare in practice; the OTel SDK rarely raises during `emit()`).
-   `'on_max_concurrency'` -- the evaluator's `on_max_concurrency` callback itself raised while being notified about a dropped evaluation.

**Default:** `Literal['sink', 'on_max_concurrency']`

### SamplingMode

Controls how per-evaluator sample rates interact across evaluators for a single call.

-   `'independent'` (default): Each evaluator flips its own coin. With N evaluators each at rate _r_, the probability of _any_ evaluation overhead is `1 − (1−r)^N`.
-   `'correlated'`: A single random seed is generated per call and shared across evaluators. An evaluator runs when `call_seed < rate`, so lower-rate evaluators' calls are always a subset of higher-rate ones. The probability of _any_ overhead equals `max(rate_i)`.

**Default:** `Literal['independent', 'correlated']`

### OnMaxConcurrencyCallback

Callback invoked when an evaluation is dropped due to concurrency limits.

Receives the `EvaluatorContext` that would have been evaluated. Can be sync or async.

**Default:** `Callable[[EvaluatorContext], None | Awaitable[None]]`

### OnSamplingErrorCallback

Callback invoked when a `sample_rate` callable raises an exception.

Called synchronously before the decorated function runs. Receives the exception and the evaluator whose `sample_rate` failed. Must be sync (not async). If set, the evaluator is skipped. If not set, the exception propagates to the caller.

**Default:** `Callable[[Exception, Evaluator], None]`

### OnErrorCallback

Callback invoked when an exception occurs in the online evaluation pipeline.

Receives the exception, the evaluator context, the evaluator instance, and a location string indicating where the error occurred. Can be sync or async.

**Default:** `Callable[[Exception, EvaluatorContext, Evaluator, OnErrorLocation], None | Awaitable[None]]`

### SinkCallback

Type alias for bare callables accepted wherever an `EvaluationSink` is expected.

Auto-wrapped in `CallbackSink` when passed as a `sink` parameter.

**Default:** `Callable[[Sequence[EvaluationResult], Sequence[EvaluatorFailure], EvaluatorContext], None | Awaitable[None]]`

### DEFAULT\_CONFIG

The global default `OnlineEvalConfig` instance.

Module-level functions like `evaluate()` and `configure()` delegate to this instance.

**Default:** `OnlineEvalConfig()`

---
