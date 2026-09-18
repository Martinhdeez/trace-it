# [pydantic_evals.reporting](https://pydantic.dev/docs/ai/api/pydantic_evals/reporting/)

# pydantic\_evals.reporting

### ConfusionMatrix

**Bases:** `BaseModel`

A confusion matrix comparing expected vs predicted labels across cases.

#### Attributes

##### class\_labels

Ordered list of class labels (used for both axes).

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### matrix

`matrixexpected_idx` is the count of cases.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`int`](https://docs.python.org/3/builtins/functions.html#int)\]\]

### PrecisionRecallPoint

**Bases:** `BaseModel`

A single point on a precision-recall curve.

### PrecisionRecallCurve

**Bases:** `BaseModel`

A single precision-recall curve.

#### Attributes

##### name

Name of this curve (e.g., experiment name or evaluator name).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### points

Points on the curve, ordered by threshold.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`PrecisionRecallPoint`\]

##### auc

Area under the precision-recall curve.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### PrecisionRecall

**Bases:** `BaseModel`

Precision-recall curve data across cases.

#### Attributes

##### curves

One or more curves.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`PrecisionRecallCurve`\]

### ScalarResult

**Bases:** `BaseModel`

A single scalar statistic (e.g., F1 score, accuracy, BLEU).

#### Attributes

##### unit

Optional unit label (e.g., '%', 'ms').

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### TableResult

**Bases:** `BaseModel`

A generic table of data (fallback for custom analyses).

#### Attributes

##### columns

Column headers.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### rows

Row data, one list per row.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None)\]\]

### ReportCase

**Bases:** `Generic[InputsT, OutputT, MetadataT]`

A single case in an evaluation report.

#### Attributes

##### name

The name of the [case](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/#pydantic_evals.dataset.Case).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### inputs

The inputs to the task, from [`Case.inputs`](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/#pydantic_evals.dataset.Case.inputs).

**Type:** `InputsT`

##### metadata

Any metadata associated with the case, from [`Case.metadata`](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/#pydantic_evals.dataset.Case.metadata).

**Type:** `MetadataT` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### expected\_output

The expected output of the task, from [`Case.expected_output`](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/#pydantic_evals.dataset.Case.expected_output).

**Type:** `OutputT` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### output

The output of the task execution.

**Type:** `OutputT`

##### source\_case\_name

The original case name before run-indexing. Serves as the aggregation key for multi-run experiments. None when repeat == 1.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### trace\_id

The trace ID of the case span.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### span\_id

The span ID of the case span.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### LinePlot

**Bases:** `BaseModel`

A generic XY line plot with labeled axes, supporting multiple curves.

Use this for ROC curves, KS plots, calibration curves, or any custom line chart that doesn't fit the specific PrecisionRecall type.

#### Attributes

##### x\_label

Label for the x-axis.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### y\_label

Label for the y-axis.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### x\_range

Optional fixed range for x-axis (min, max).

**Type:** [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### y\_range

Optional fixed range for y-axis (min, max).

**Type:** [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`float`](https://docs.python.org/3/builtins/functions.html#float), [`float`](https://docs.python.org/3/builtins/functions.html#float)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### curves

One or more curves to plot.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`LinePlotCurve`\]

### ReportCaseFailure

**Bases:** `Generic[InputsT, OutputT, MetadataT]`

A single case in an evaluation report that failed due to an error during task execution.

#### Attributes

##### name

The name of the [case](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/#pydantic_evals.dataset.Case).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### inputs

The inputs to the task, from [`Case.inputs`](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/#pydantic_evals.dataset.Case.inputs).

**Type:** `InputsT`

##### metadata

Any metadata associated with the case, from [`Case.metadata`](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/#pydantic_evals.dataset.Case.metadata).

**Type:** `MetadataT` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### expected\_output

The expected output of the task, from [`Case.expected_output`](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/#pydantic_evals.dataset.Case.expected_output).

**Type:** `OutputT` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### error\_message

The message of the exception that caused the failure.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### error\_stacktrace

The stacktrace of the exception that caused the failure.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### source\_case\_name

The original case name before run-indexing. Serves as the aggregation key for multi-run experiments. None when repeat == 1.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### trace\_id

The trace ID of the case span.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### span\_id

The span ID of the case span.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### ReportCaseGroup

**Bases:** `Generic[InputsT, OutputT, MetadataT]`

Grouped results from running the same case multiple times.

This is a computed view, not stored data. Obtain via `EvaluationReport.case_groups()`.

#### Attributes

##### name

The original case name (shared across all runs).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### inputs

The inputs (same for all runs).

**Type:** `InputsT`

##### metadata

The metadata (same for all runs).

**Type:** `MetadataT` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### expected\_output

The expected output (same for all runs).

**Type:** `OutputT` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### runs

Individual run results.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`ReportCase`\[`InputsT`, `OutputT`, `MetadataT`\]\]

##### failures

Runs that failed with exceptions.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`ReportCaseFailure`\[`InputsT`, `OutputT`, `MetadataT`\]\]

##### summary

Aggregated statistics across runs.

**Type:** `ReportCaseAggregate`

### ReportCaseAggregate

**Bases:** `BaseModel`

A synthetic case that summarizes a set of cases.

#### Methods

##### average

`@staticmethod`

```python
def average(cases: list[ReportCase]) -> ReportCaseAggregate
```

Produce a synthetic "summary" case by averaging quantitative attributes.

###### Returns

`ReportCaseAggregate`

##### average\_from\_aggregates

`@staticmethod`

```python
def average_from_aggregates(
    aggregates: list[ReportCaseAggregate],
) -> ReportCaseAggregate
```

Average across multiple aggregates (used for multi-run experiment summaries).

###### Returns

`ReportCaseAggregate`

### EvaluationReport

**Bases:** `Generic[InputsT, OutputT, MetadataT]`

A report of the results of evaluating a model on a set of cases.

#### Attributes

##### name

The name of the report.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### cases

The cases in the report.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ReportCase`\[`InputsT`, `OutputT`, `MetadataT`\]\]

##### failures

The failures in the report. These are cases where task execution raised an exception.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ReportCaseFailure`\[`InputsT`, `OutputT`, `MetadataT`\]\] **Default:** `field(default_factory=(list[ReportCaseFailure[InputsT, OutputT, MetadataT]]))`

##### analyses

Experiment-wide analyses produced by report evaluators.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ReportAnalysis`\] **Default:** `field(default_factory=(list[ReportAnalysis]))`

##### report\_evaluator\_failures

Failures from report evaluators that raised exceptions.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`EvaluatorFailure`\] **Default:** `field(default_factory=(list[EvaluatorFailure]))`

##### experiment\_metadata

Metadata associated with the specific experiment represented by this report.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### trace\_id

The trace ID of the evaluation.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### span\_id

The span ID of the evaluation.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### case\_groups

```python
def case_groups() -> list[ReportCaseGroup[InputsT, OutputT, MetadataT]] | None
```

Group cases by source\_case\_name and compute per-group aggregates.

Returns None if no cases have source\_case\_name set (i.e., single-run experiment).

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`ReportCaseGroup`\[`InputsT`, `OutputT`, `MetadataT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### averages

```python
def averages() -> ReportCaseAggregate | None
```

Aggregate scores, labels, and metrics averaged across the report's cases.

For multi-run reports, per-group summaries are averaged instead; returns `None` when there is nothing to aggregate.

###### Returns

`ReportCaseAggregate` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### render

```python
def render(
    width: int | None = None,
    baseline: EvaluationReport[InputsT, OutputT, MetadataT] | None = None,
    *,
    include_input: bool = False,
    include_metadata: bool = False,
    include_expected_output: bool = False,
    include_output: bool = False,
    include_durations: bool = True,
    include_total_duration: bool = False,
    include_removed_cases: bool = False,
    include_averages: bool = True,
    include_errors: bool = True,
    include_error_stacktrace: bool = False,
    include_evaluator_failures: bool = True,
    include_analyses: bool = True,
    input_config: RenderValueConfig | None = None,
    metadata_config: RenderValueConfig | None = None,
    output_config: RenderValueConfig | None = None,
    score_configs: dict[str, RenderNumberConfig] | None = None,
    label_configs: dict[str, RenderValueConfig] | None = None,
    metric_configs: dict[str, RenderNumberConfig] | None = None,
    duration_config: RenderNumberConfig | None = None,
    include_reasons: bool = False,
) -> str
```

Render this report to a nicely-formatted string, optionally comparing it to a baseline report.

If you want more control over the output, use `console_table` instead and pass it to `rich.Console.print`.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### print

```python
def print(
    width: int | None = None,
    baseline: EvaluationReport[InputsT, OutputT, MetadataT] | None = None,
    *,
    console: Console | None = None,
    include_input: bool = False,
    include_metadata: bool = False,
    include_expected_output: bool = False,
    include_output: bool = False,
    include_durations: bool = True,
    include_total_duration: bool = False,
    include_removed_cases: bool = False,
    include_averages: bool = True,
    include_errors: bool = True,
    include_error_stacktrace: bool = False,
    include_evaluator_failures: bool = True,
    include_analyses: bool = True,
    input_config: RenderValueConfig | None = None,
    metadata_config: RenderValueConfig | None = None,
    output_config: RenderValueConfig | None = None,
    score_configs: dict[str, RenderNumberConfig] | None = None,
    label_configs: dict[str, RenderValueConfig] | None = None,
    metric_configs: dict[str, RenderNumberConfig] | None = None,
    duration_config: RenderNumberConfig | None = None,
    include_reasons: bool = False,
) -> None
```

Print this report to the console, optionally comparing it to a baseline report.

On a console `rich` reports as ASCII-only -- a non-UTF-8 stream, as Windows produces when stdout is redirected to a file or a pipe -- `v`, `x` and `->` stand in for the `✔`, `✗` and `→` glyphs, and default sub-millisecond duration formatters use `us` instead of `µs`.

If you want more control over the output, use `console_table` instead and pass it to `rich.Console.print`, forwarding `ascii_only=console.options.ascii_only` from the console you print to.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### console\_table

```python
def console_table(
    baseline: EvaluationReport[InputsT, OutputT, MetadataT] | None = None,
    *,
    include_input: bool = False,
    include_metadata: bool = False,
    include_expected_output: bool = False,
    include_output: bool = False,
    include_durations: bool = True,
    include_total_duration: bool = False,
    include_removed_cases: bool = False,
    include_averages: bool = True,
    include_evaluator_failures: bool = True,
    input_config: RenderValueConfig | None = None,
    metadata_config: RenderValueConfig | None = None,
    output_config: RenderValueConfig | None = None,
    score_configs: dict[str, RenderNumberConfig] | None = None,
    label_configs: dict[str, RenderValueConfig] | None = None,
    metric_configs: dict[str, RenderNumberConfig] | None = None,
    duration_config: RenderNumberConfig | None = None,
    include_reasons: bool = False,
    with_title: bool = True,
    ascii_only: bool = False,
) -> RenderableType
```

Return a table containing the data from this report.

If a baseline is provided, returns a diff between this report and the baseline report. Optionally include input and output details.

`ascii_only` renders `v`, `x` and `->` in place of the `✔`, `✗` and `→` glyphs, and uses `us` instead of `µs` from the default sub-millisecond duration formatters. Only the caller holding that console can answer this, so it defaults to `False`; pass `ascii_only=console.options.ascii_only` from the console you print the table to.

###### Returns

`RenderableType`

##### failures\_table

```python
def failures_table(
    *,
    include_input: bool = False,
    include_metadata: bool = False,
    include_expected_output: bool = False,
    include_error_message: bool = True,
    include_error_stacktrace: bool = True,
    input_config: RenderValueConfig | None = None,
    metadata_config: RenderValueConfig | None = None,
) -> RenderableType
```

Return a table containing the failures in this report.

###### Returns

`RenderableType`

##### \_\_str\_\_

```python
def __str__() -> str
```

Return a string representation of the report.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### RenderValueConfig

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

A configuration for rendering a values in an Evaluation report.

### RenderNumberConfig

**Bases:** [`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)

A configuration for rendering a particular score or metric in an Evaluation report.

See the implementation of `_RenderNumber` for more clarity on how these parameters affect the rendering.

#### Attributes

##### value\_formatter

The logic to use for formatting values.

-   If not provided, format as ints if all values are ints, otherwise at least one decimal place and at least four significant figures.
-   You can also use a custom string format spec, e.g. '{:.3f}'
-   You can also use a custom function, e.g. lambda x: f'{x:.3f}'

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`float`](https://docs.python.org/3/builtins/functions.html#float) | [`int`](https://docs.python.org/3/builtins/functions.html#int)\], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### diff\_formatter

The logic to use for formatting details about the diff.

The strings produced by the value\_formatter will always be included in the reports, but the diff\_formatter is used to produce additional text about the difference between the old and new values, such as the absolute or relative difference.

-   If not provided, format as ints if all values are ints, otherwise at least one decimal place and at least four significant figures, and will include the percentage change.
-   You can also use a custom string format spec, e.g. '{:+.3f}'
-   You can also use a custom function, e.g. lambda x: f'{x:+.3f}'. If this function returns None, no extra diff text will be added.
-   You can also use None to never generate extra diff text.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`float`](https://docs.python.org/3/builtins/functions.html#float) | [`int`](https://docs.python.org/3/builtins/functions.html#int), [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`int`](https://docs.python.org/3/builtins/functions.html#int)\], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### diff\_atol

The absolute tolerance for considering a difference "significant".

A difference is "significant" if `abs(new - old) < self.diff_atol + self.diff_rtol * abs(old)`.

If a difference is not significant, it will not have the diff styles applied. Note that we still show both the rendered before and after values in the diff any time they differ, even if the difference is not significant. (If the rendered values are exactly the same, we only show the value once.)

If not provided, use 1e-6.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

##### diff\_rtol

The relative tolerance for considering a difference "significant".

See the description of `diff_atol` for more details about what makes a difference "significant".

If not provided, use 0.001 if all values are ints, otherwise 0.05.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

##### diff\_increase\_style

The style to apply to diffed values that have a significant increase.

See the description of `diff_atol` for more details about what makes a difference "significant".

If not provided, use green for scores and red for metrics. You can also use arbitrary `rich` styles, such as "bold red".

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### diff\_decrease\_style

The style to apply to diffed values that have significant decrease.

See the description of `diff_atol` for more details about what makes a difference "significant".

If not provided, use red for scores and green for metrics. You can also use arbitrary `rich` styles, such as "bold red".

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### ReportCaseRenderer

#### Methods

##### build\_base\_table

```python
def build_base_table(title: str) -> Table
```

Build and return a Rich Table for the diff output.

###### Returns

`Table`

##### build\_failures\_table

```python
def build_failures_table(title: str) -> Table
```

Build and return a Rich Table for the failures output.

###### Returns

`Table`

##### build\_row

```python
def build_row(case: ReportCase) -> list[str]
```

Build a table row for a single case.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### build\_aggregate\_row

```python
def build_aggregate_row(aggregate: ReportCaseAggregate) -> list[str]
```

Build a table row for an aggregated case.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### build\_diff\_row

```python
def build_diff_row(new_case: ReportCase, baseline: ReportCase) -> list[str]
```

Build a table row for a given case ID.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### build\_diff\_aggregate\_row

```python
def build_diff_aggregate_row(
    new: ReportCaseAggregate,
    baseline: ReportCaseAggregate,
) -> list[str]
```

Build a table row for a given case ID.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### build\_failure\_row

```python
def build_failure_row(case: ReportCaseFailure) -> list[str]
```

Build a table row for a single case failure.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

### EvaluationRenderer

A class for rendering an EvalReport or the diff between two EvalReports.

#### Attributes

##### ascii\_only

Whether to render `v`, `x` and `->` in place of the `✔`, `✗` and `→` glyphs.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

#### Methods

##### build\_table

```python
def build_table(report: EvaluationReport, *, with_title: bool = True) -> Table
```

Build a table for the report.

###### Returns

`Table` -- A Rich Table object

###### Parameters

**`report`** : `EvaluationReport`

The evaluation report to render

**`with_title`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to include the title in the table (default True)

##### build\_diff\_table

```python
def build_diff_table(
    report: EvaluationReport,
    baseline: EvaluationReport,
    *,
    with_title: bool = True,
) -> Table
```

Build a diff table comparing report to baseline.

###### Returns

`Table` -- A Rich Table object

###### Parameters

**`report`** : `EvaluationReport`

The evaluation report to compare

**`baseline`** : `EvaluationReport`

The baseline report to compare against

**`with_title`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to include the title in the table (default True)

### ReportAnalysis

Discriminated union of all report-level analysis types.

**Default:** `Annotated[ConfusionMatrix | PrecisionRecall | ScalarResult | TableResult | LinePlot, Discriminator('type')]`

---
