# [pydantic_evals.evaluators](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/)

# pydantic\_evals.evaluators

### ReportEvaluatorContext

**Bases:** `Generic[InputsT, OutputT, MetadataT]`

Context for report-level evaluation, containing the full experiment results.

#### Attributes

##### name

The experiment name.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### report

The full evaluation report.

**Type:** `EvaluationReport`\[`InputsT`, `OutputT`, `MetadataT`\]

##### experiment\_metadata

Experiment-level metadata.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### EvaluatorContext

**Bases:** `Generic[InputsT, OutputT, MetadataT]`

Context for evaluating a task execution.

An instance of this class is the sole input to all Evaluators. It contains all the information needed to evaluate the task execution, including inputs, outputs, metadata, and telemetry data.

Evaluators use this context to access the task inputs, actual output, expected output, and other information when evaluating the result of the task execution.

Example:

```python
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext


@dataclass
class ExactMatch(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        # Use the context to access task inputs, outputs, and expected outputs
        return ctx.output == ctx.expected_output
```

#### Attributes

##### name

The name of the case.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### inputs

The inputs provided to the task for this case.

**Type:** `InputsT`

##### metadata

Metadata associated with the case, if provided. May be None if no metadata was specified.

**Type:** `MetadataT` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### expected\_output

The expected output for the case, if provided. May be None if no expected output was specified.

**Type:** `OutputT` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### output

The actual output produced by the task for this case.

**Type:** `OutputT`

##### duration

The duration of the task run for this case.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

##### attributes

Attributes associated with the task run for this case.

These can be set by calling `pydantic_evals.dataset.set_eval_attribute` in any code executed during the evaluation task.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### metrics

Metrics associated with the task run for this case.

These can be set by calling `pydantic_evals.dataset.increment_eval_metric` in any code executed during the evaluation task.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`float`](https://docs.python.org/3/builtins/functions.html#float)\]

##### span\_tree

Get the `SpanTree` for this task execution.

The span tree is a graph where each node corresponds to an OpenTelemetry span recorded during the task execution, including timing information and any custom spans created during execution.

**Type:** `SpanTree`

### Equals

**Bases:** `Evaluator[object, object, object]`

Check if the output exactly equals the provided value.

### EvaluationReason

The result of running an evaluator with an optional explanation.

Contains a scalar value and an optional "reason" explaining the value.

#### Constructor Parameters

**`value`** : `EvaluationScalar`

The scalar result of the evaluation (boolean, integer, float, or string).

**`reason`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

An optional explanation of the evaluation result.

### ReportEvaluator

**Bases:** `BaseEvaluator`, `Generic[InputsT, OutputT, MetadataT]`

Base class for experiment-wide evaluators that analyze full reports.

Unlike case-level Evaluators which assess individual task outputs, ReportEvaluators see all case results together and produce experiment-wide analyses like confusion matrices, precision-recall curves, or scalar statistics.

#### Methods

##### evaluate

`@abstractmethod`

```python
def evaluate(
    ctx: ReportEvaluatorContext[InputsT, OutputT, MetadataT],
) -> ReportAnalysis | list[ReportAnalysis] | Awaitable[ReportAnalysis | list[ReportAnalysis]]
```

Evaluate the full report and return experiment-wide analysis/analyses.

###### Returns

`ReportAnalysis` | [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ReportAnalysis`\] | [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[`ReportAnalysis` | [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ReportAnalysis`\]\]

##### evaluate\_async

`@async`

```python
def evaluate_async(
    ctx: ReportEvaluatorContext[InputsT, OutputT, MetadataT],
) -> ReportAnalysis | list[ReportAnalysis]
```

Evaluate, handling both sync and async implementations.

###### Returns

`ReportAnalysis` | [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ReportAnalysis`\]

### EqualsExpected

**Bases:** `Evaluator[object, object, object]`

Check if the output exactly equals the expected output.

### EvaluationResult

**Bases:** `Generic[EvaluationScalarT]`

The details of an individual evaluation result.

Contains the name, value, reason, and source evaluator for a single evaluation.

#### Constructor Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The name of the evaluation.

**`value`** : `EvaluationScalarT`

The scalar result of the evaluation.

**`reason`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

An optional explanation of the evaluation result.

**`source`** : `EvaluatorSpec`

The spec of the evaluator that produced this result.

**`evaluator_version`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional version tag for the evaluator that produced this result (e.g. `'v2'`). Sourced automatically from the evaluator's [`get_evaluator_version`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.Evaluator.get_evaluator_version) method. Lets online-evaluation dashboards filter out results from retired versions without deleting historical rows.

#### Methods

##### downcast

```python
def downcast(*value_types: type[T]) -> EvaluationResult[T] | None
```

Attempt to downcast this result to a more specific type.

###### Returns

`EvaluationResult`\[`T`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- A downcast version of this result if the value is an instance of one of the given types, `EvaluationResult`\[`T`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- otherwise None.

###### Parameters

**`*value_types`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`T`\] _Default:_ `()`

The types to check the value against.

### Contains

**Bases:** `Evaluator[object, object, object]`

Check if the output contains the expected output.

For strings, checks if expected\_output is a substring of output. For lists/tuples, checks if expected\_output is in output. For dicts, checks if all key-value pairs in expected\_output are in output. For model-like types (BaseModel, dataclasses), converts to a dict and checks key-value pairs.

Note: case\_sensitive only applies when both the value and output are strings.

### EvaluatorFailure

Represents a failure raised during the execution of an evaluator.

#### Attributes

##### evaluator\_version

Optional version tag for the evaluator that raised (e.g. `'v2'`). Sourced automatically from the evaluator's [`get_evaluator_version`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.Evaluator.get_evaluator_version) method.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### error\_type

Class name of the exception that caused the failure (e.g. `'ValueError'`). Populated automatically when `EvaluatorFailure` is constructed from a caught exception; surfaced as the `error.type` attribute on emitted OTel events.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### ConfusionMatrixEvaluator

**Bases:** `ReportEvaluator`

Computes a confusion matrix from case data.

### Evaluator

**Bases:** `BaseEvaluator`, `Generic[InputsT, OutputT, MetadataT]`

Base class for all evaluators.

Evaluators can assess the performance of a task in a variety of ways, as a function of the EvaluatorContext.

Subclasses must implement the `evaluate` method. Note it can be defined with either `def` or `async def`.

Example:

```python
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext


@dataclass
class ExactMatch(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return ctx.output == ctx.expected_output
```

Override [`get_default_evaluation_name`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.Evaluator.get_default_evaluation_name) to customize the name used in reports, and [`get_evaluator_version`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.Evaluator.get_evaluator_version) to tag the evaluator with a version that downstream sinks can filter on.

Example:

```python
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext


@dataclass
class LLMJudge(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool: ...

    def get_evaluator_version(self) -> str | None:
        return 'v2'  # bumped after prompt rewrite
```

#### Methods

##### get\_default\_evaluation\_name

```python
def get_default_evaluation_name() -> str
```

Return the default name to use in reports for the output of this evaluator.

Defaults to the serialization name of the evaluator (which is usually the class name). Override this method to customize the name, e.g. using instance information.

Note that evaluators that return a mapping of results will always use the keys of that mapping as the names of the associated evaluation results.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### get\_evaluator\_version

```python
def get_evaluator_version() -> str | None
```

Return the version tag for this evaluator, or `None` if it has no version.

Propagated to online-evaluation sinks so dashboards can filter out results produced by retired versions without deleting historical rows. Applies to every result the evaluator emits; bump whenever behavior changes in a way that invalidates prior scores. Override this method to set a non-`None` version.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### evaluate

`@abstractmethod`

```python
def evaluate(
    ctx: EvaluatorContext[InputsT, OutputT, MetadataT],
) -> EvaluatorOutput | Awaitable[EvaluatorOutput]
```

Evaluate the task output in the given context.

This is the main evaluation method that subclasses must implement. It can be either synchronous or asynchronous, returning either an EvaluatorOutput directly or an Awaitable\[EvaluatorOutput\].

###### Returns

`EvaluatorOutput` | [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[`EvaluatorOutput`\] -- The evaluation result, which can be a scalar value, an EvaluationReason, or a mapping `EvaluatorOutput` | [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[`EvaluatorOutput`\] -- of evaluation names to either of those. Can be returned either synchronously or as an `EvaluatorOutput` | [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[`EvaluatorOutput`\] -- awaitable for asynchronous evaluation.

###### Parameters

**`ctx`** : `EvaluatorContext`\[`InputsT`, `OutputT`, `MetadataT`\]

The context containing the inputs, outputs, and metadata for evaluation.

##### evaluate\_sync

```python
def evaluate_sync(ctx: EvaluatorContext[InputsT, OutputT, MetadataT]) -> EvaluatorOutput
```

Run the evaluator synchronously, handling both sync and async implementations.

This method ensures synchronous execution by running any async evaluate implementation to completion using run\_until\_complete.

###### Returns

`EvaluatorOutput` -- The evaluation result, which can be a scalar value, an EvaluationReason, or a mapping `EvaluatorOutput` -- of evaluation names to either of those.

###### Parameters

**`ctx`** : `EvaluatorContext`\[`InputsT`, `OutputT`, `MetadataT`\]

The context containing the inputs, outputs, and metadata for evaluation.

##### evaluate\_async

`@async`

```python
def evaluate_async(
    ctx: EvaluatorContext[InputsT, OutputT, MetadataT],
) -> EvaluatorOutput
```

Run the evaluator asynchronously, handling both sync and async implementations.

This method ensures asynchronous execution by properly awaiting any async evaluate implementation. For synchronous implementations, it returns the result directly.

###### Returns

`EvaluatorOutput` -- The evaluation result, which can be a scalar value, an EvaluationReason, or a mapping `EvaluatorOutput` -- of evaluation names to either of those.

###### Parameters

**`ctx`** : `EvaluatorContext`\[`InputsT`, `OutputT`, `MetadataT`\]

The context containing the inputs, outputs, and metadata for evaluation.

### IsInstance

**Bases:** `Evaluator[object, object, object]`

Check if the output is an instance of a type with the given name.

### PrecisionRecallEvaluator

**Bases:** `ReportEvaluator`

Computes a precision-recall curve from case data.

Returns both a `PrecisionRecall` chart and a `ScalarResult` with the AUC value. The AUC is computed at full resolution (every unique score threshold) for accuracy, while the chart points are downsampled to `n_thresholds` for display.

### MaxDuration

**Bases:** `Evaluator[object, object, object]`

Check if the execution time is under the specified maximum.

### ToolCorrectness

**Bases:** `Evaluator[object, object, object]`

Assert that the agent called a specific multiset of tools.

This compares the names of tools actually invoked (as a multiset) against `expected_tools`. Repeated names require repeated calls -- for example, `expected_tools=['search', 'search']` passes only if `search` was called at least twice.

#### Constructor Parameters

**`expected_tools`** : [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

The tool names the agent is expected to call. Order does not matter; duplicates are significant.

**`allow_extra`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

If `False` (the default), any tool call not listed in `expected_tools` fails the check. Set to `True` to only require that the expected tools were called, permitting extras.

**`include_failed`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

If `False` (the default), tool-call attempts that ended in an error (a raised exception, or a retry requested via `ModelRetry`) are not counted. Set to `True` to count every attempt.

**`evaluation_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional override for the reported evaluation name.

Returns `EvaluationReason` with a `bool` value.

### OutputConfig

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

Configuration for the score and assertion outputs of the LLMJudge evaluator.

### LLMJudge

**Bases:** `Evaluator[object, object, object]`

Judge whether the output of a language model meets the criteria of a provided rubric.

If you do not specify a model, it uses the default model for judging. This starts as 'openai:gpt-5.2', but can be overridden by calling [`set_default_judge_model`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.llm_as_a_judge.set_default_judge_model).

### ROCAUCEvaluator

**Bases:** `ReportEvaluator`

Computes an ROC curve and AUC from case data.

Returns a `LinePlot` with the ROC curve (plus a dashed random-baseline diagonal) and a `ScalarResult` with the AUC value.

### TrajectoryMatch

**Bases:** `Evaluator[object, object, object]`

Compare the agent's tool-call trajectory to an expected one.

#### Constructor Parameters

**`expected_trajectory`** : [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

The expected ordered list of tool names.

**`order`** : `TrajectoryOrder` _Default:_ `'in_order'`

How strictly to compare:

-   `'exact'`: actual must equal expected (1.0) or not (0.0).
-   `'in_order'` (default): F1 computed from the longest common subsequence (LCS) of the two sequences. Extra calls reduce precision; missing calls reduce recall.
-   `'any_order'`: F1 computed from the multiset intersection of the two trajectories. Order is ignored, but extra and missing calls still reduce the score.

**`include_failed`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

If `False` (the default), tool-call attempts that ended in an error (a raised exception, or a retry requested via `ModelRetry`) are not part of the trajectory. Set to `True` to include every attempt.

**`evaluation_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional override for the reported evaluation name.

Returns `EvaluationReason` with a `float` value in `[0.0, 1.0]` (including when no span tree was captured, in which case the value is `0.0`). For the F1-based modes, the `reason` text shows the precision, recall and F1 numbers so the score can be reproduced from the reported mismatch.

If both the expected and actual trajectories are empty, all modes score `1.0`; if only one of them is empty, all modes score `0.0`.

### GEval

**Bases:** `Evaluator[object, object, object]`

G-Eval-style chain-of-thought evaluator (Liu et al., 2023).

The judge is shown the evaluation `criteria` and a list of explicit `evaluation_steps`, produces a short reasoning trace, and emits an integer score within `score_range` (inclusive), returned as an [`EvaluationReason`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.EvaluationReason). Because the criteria and steps are user-supplied, `GEval` puts no structural requirements on `ctx.inputs` or `ctx.output`.

If you do not specify a model, it uses the default model for judging. This starts as 'openai:gpt-5.2', but can be overridden by calling [`set_default_judge_model`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.llm_as_a_judge.set_default_judge_model).

Simplified G-Eval

The paper computes a probability-weighted expectation over score tokens using log-probs. We ask the model for a direct integer score instead, trading some correlation with human judgment for provider-agnostic simplicity.

### KolmogorovSmirnovEvaluator

**Bases:** `ReportEvaluator`

Computes a Kolmogorov-Smirnov plot and statistic from case data.

Plots the empirical CDFs of the score distribution for positive and negative cases, and computes the KS statistic (maximum vertical distance between the two CDFs).

Returns a `LinePlot` with the two CDF curves and a `ScalarResult` with the KS statistic.

### HasMatchingSpan

**Bases:** `Evaluator[object, object, object]`

Check if the span tree contains a span that matches the specified query.

### ArgumentCorrectness

**Bases:** `Evaluator[object, object, object]`

Assert that a specific tool call received particular arguments.

Finds all local spans for `tool_name` in the run, picks the requested occurrence, parses the recorded JSON arguments, and compares them to `expected_arguments`.

#### Constructor Parameters

**`tool_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The tool whose arguments should be checked.

**`expected_arguments`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

Expected argument keys/values.

**`match_mode`** : `ArgumentMatchMode` _Default:_ `'subset'`

`'subset'` (default) checks that every expected key/value is present in the actual arguments. `'exact'` requires deep equality. Note that the subset comparison applies only to top-level keys: an expected _value_ (including a nested dict) must compare equal to the actual value in full.

**`occurrence`** : `ArgumentOccurrence` | [`int`](https://docs.python.org/3/builtins/functions.html#int) _Default:_ `'first'`

Which invocation of the tool to inspect when the tool is called multiple times: `'first'`, `'last'`, or a 0-based integer index. A negative int is not supported.

**`include_failed`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `False`

If `False` (the default), tool-call attempts that ended in an error (a raised exception, or a retry requested via `ModelRetry`) are not considered. Set to `True` to consider every attempt; each attempt then counts as a separate occurrence, so `'first'` may select an attempt that was subsequently retried.

**`evaluation_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional override for the reported evaluation name.

Returns `EvaluationReason` with a `bool` value. Fails gracefully with a descriptive reason if the tool was never called, the requested occurrence doesn't exist, or arguments weren't recorded (e.g. `include_content=False`).

### MaxToolCalls

**Bases:** `Evaluator[object, object, object]`

Assert that the agent made at most `max_calls` locally-executed tool calls.

#### Constructor Parameters

**`max_calls`** : [`int`](https://docs.python.org/3/builtins/functions.html#int)

Maximum allowed locally-executed tool calls.

**`include_failed`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

If `True` (the default), tool-call attempts that ended in an error (a raised exception, or a retry requested via `ModelRetry`) count against the budget -- they still consumed time and tokens. Set to `False` to count only successful calls.

**`evaluation_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional override for the reported evaluation name.

Returns `EvaluationReason` with a `bool` value.

### MaxModelRequests

**Bases:** `Evaluator[object, object, object]`

Assert that the agent made at most `max_requests` model (chat) requests.

Prefers the `requests` value from `ctx.metrics` when available, otherwise counts LLM request spans in the span tree directly (both use the same criteria, so the two sources agree whenever both are populated).

#### Constructor Parameters

**`max_requests`** : [`int`](https://docs.python.org/3/builtins/functions.html#int)

Maximum allowed model requests.

**`evaluation_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional override for the reported evaluation name.

Returns `EvaluationReason` with a `bool` value.

### EvaluatorSpec

The specification of an evaluator to be run.

This class is used to represent evaluators in a serializable format, supporting various short forms for convenience when defining evaluators in YAML or JSON dataset files.

In particular, each of the following forms is supported for specifying an evaluator with name `MyEvaluator`:

-   `'MyEvaluator'` - Just the (string) name of the Evaluator subclass is used if its `__init__` takes no arguments
-   `{'MyEvaluator': first_arg}` - A single argument is passed as the first positional argument to `MyEvaluator.__init__`
-   `{'MyEvaluator': {k1: v1, k2: v2}}` - Multiple kwargs are passed to `MyEvaluator.__init__`

**Default:** `NamedSpec`

### EvaluatorOutput

Type for the output of an evaluator, which can be a scalar, an EvaluationReason, or a mapping of names to either.

**Default:** `EvaluationScalar | EvaluationReason | Mapping[str, EvaluationScalar | EvaluationReason]`

### TrajectoryOrder

How to compare the actual tool sequence to `expected_trajectory`.

-   `'exact'`: actual must equal expected (1.0) or not (0.0).
-   `'in_order'`: F1 score combining precision and recall of the longest common subsequence.
-   `'any_order'`: F1 score combining precision and recall of the multiset intersection (order is ignored, but extra and missing calls both reduce the score).

**Default:** `Literal['exact', 'in_order', 'any_order']`

### ArgumentMatchMode

How to compare actual tool arguments to `expected_arguments`.

-   `'exact'`: actual must deep-equal expected.
-   `'subset'`: every key/value in expected must be present (and equal) in actual.

**Default:** `Literal['exact', 'subset']`

### ArgumentOccurrence

Which occurrence of a tool call to inspect when a tool is called multiple times.

**Default:** `Literal['first', 'last']`

### GradingOutput

**Bases:** `BaseModel`

The output of a grading operation.

### GEvalOutput

**Bases:** `BaseModel`

The output of a G-Eval grading operation.

G-Eval asks the judge to emit a short chain-of-thought `reason` followed by an integer `score` in a user-specified range (see [`judge_g_eval`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.llm_as_a_judge.judge_g_eval)).

### judge\_output

`@async`

```python
def judge_output(
    output: Any,
    rubric: str,
    model: models.Model | models.KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GradingOutput
```

Judge the output of a model based on a rubric.

If the model is not specified, a default model is used. The default model starts as 'openai:gpt-5.2', but this can be changed using the `set_default_judge_model` function.

#### Returns

`GradingOutput`

### judge\_input\_output

`@async`

```python
def judge_input_output(
    inputs: Any,
    output: Any,
    rubric: str,
    model: models.Model | models.KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GradingOutput
```

Judge the output of a model based on the inputs and a rubric.

If the model is not specified, a default model is used. The default model starts as 'openai:gpt-5.2', but this can be changed using the `set_default_judge_model` function.

#### Returns

`GradingOutput`

### judge\_input\_output\_expected

`@async`

```python
def judge_input_output_expected(
    inputs: Any,
    output: Any,
    expected_output: Any,
    rubric: str,
    model: models.Model | models.KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GradingOutput
```

Judge the output of a model based on the inputs and a rubric.

If the model is not specified, a default model is used. The default model starts as 'openai:gpt-5.2', but this can be changed using the `set_default_judge_model` function.

#### Returns

`GradingOutput`

### judge\_output\_expected

`@async`

```python
def judge_output_expected(
    output: Any,
    expected_output: Any,
    rubric: str,
    model: models.Model | models.KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GradingOutput
```

Judge the output of a model based on the expected output, output, and a rubric.

If the model is not specified, a default model is used. The default model starts as 'openai:gpt-5.2', but this can be changed using the `set_default_judge_model` function.

#### Returns

`GradingOutput`

### set\_default\_judge\_model

```python
def set_default_judge_model(model: models.Model | models.KnownModelName) -> None
```

Set the default model used for judging.

This model is used if `None` is passed to the `model` argument of `judge_output` and `judge_input_output`.

#### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### judge\_g\_eval

`@async`

```python
def judge_g_eval(
    output: Any,
    criteria: str,
    evaluation_steps: Sequence[str],
    score_range: tuple[int, int] = (1, 5),
    inputs: Any | None = None,
    model: models.Model | models.KnownModelName | str | None = None,
    model_settings: ModelSettings | None = None,
) -> GEvalOutput
```

Judge an output using a G-Eval style chain-of-thought prompt.

This is a simplified implementation of G-Eval (Liu et al., 2023, "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment"). The original paper computes an expectation over the distribution of score tokens using log-probs. We skip that step and simply ask the model for a direct integer score. This keeps the evaluator provider-agnostic at the cost of some correlation with human judgments.

#### Returns

`GEvalOutput` -- A [`GEvalOutput`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/#pydantic_evals.evaluators.llm_as_a_judge.GEvalOutput) containing `GEvalOutput` -- the judge's reasoning and integer score.

#### Parameters

**`output`** : [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

The output being evaluated.

**`criteria`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The aspect being evaluated (e.g. "coherence", "fluency").

**`evaluation_steps`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

Explicit chain-of-thought steps the judge should follow.

**`score_range`** : [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`int`](https://docs.python.org/3/builtins/functions.html#int), [`int`](https://docs.python.org/3/builtins/functions.html#int)\] _Default:_ `(1, 5)`

Inclusive `(min, max)` integer score range.

**`inputs`** : [`Any`](https://docs.python.org/3/library/typing.html#typing.Any) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional inputs/context to show alongside the output.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model to use. If not specified, the default judge model is used.

**`model_settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional model settings.

#### Raises

-   `ValueError` -- If `score_range` is invalid, `evaluation_steps` is empty, or the judge returns a score outside the range.

---
