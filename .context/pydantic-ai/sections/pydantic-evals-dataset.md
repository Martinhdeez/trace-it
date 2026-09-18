# [pydantic_evals.dataset](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/)

# pydantic\_evals.dataset

Dataset management for pydantic evals.

This module provides functionality for creating, loading, saving, and evaluating datasets of test cases. Each case must have inputs, and can optionally have a name, expected output, metadata, and case-specific evaluators.

Datasets can be loaded from and saved to YAML or JSON files, and can be evaluated against a task function to produce an evaluation report.

### Case

**Bases:** `Generic[InputsT, OutputT, MetadataT]`

A single row of a [`Dataset`](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/#pydantic_evals.dataset.Dataset).

Each case represents a single test scenario with inputs to test. A case may optionally specify a name, expected outputs to compare against, and arbitrary metadata.

Cases can also have their own specific evaluators which are run in addition to dataset-level evaluators.

Example:

```python
from pydantic_evals import Case

case = Case(
    name='Simple addition',
    inputs={'a': 1, 'b': 2},
    expected_output=3,
    metadata={'description': 'Tests basic addition'},
)
```

#### Attributes

##### name

Name of the case. This is used to identify the case in the report and can be used to filter cases.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `name`

##### inputs

Inputs to the task. This is the input to the task that will be evaluated.

**Type:** `InputsT` **Default:** `inputs`

##### metadata

Metadata to be used in the evaluation.

This can be used to provide additional information about the case to the evaluators.

**Type:** `MetadataT` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `metadata`

##### expected\_output

Expected output of the task. This is the expected output of the task that will be evaluated.

**Type:** `OutputT` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `expected_output`

##### evaluators

Evaluators to be used just on this case.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`Evaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\] **Default:** `list(evaluators)`

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    name: str | None = None,
    inputs: InputsT,
    metadata: MetadataT | None = None,
    expected_output: OutputT | None = None,
    evaluators: tuple[Evaluator[InputsT, OutputT, MetadataT], ...] = (),
)
```

Initialize a new test case.

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional name for the case. If not provided, a generic name will be assigned when added to a dataset.

**`inputs`** : `InputsT`

The inputs to the task being evaluated.

**`metadata`** : `MetadataT` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata for the case, which can be used by evaluators.

**`expected_output`** : `OutputT` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional expected output of the task, used for comparison in evaluators.

**`evaluators`** : [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[`Evaluator`\[`InputsT`, `OutputT`, `MetadataT`\], ...\] _Default:_ `()`

Tuple of evaluators specific to this case. These are in addition to any dataset-level evaluators.

### Dataset

**Bases:** `BaseModel`, `Generic[InputsT, OutputT, MetadataT]`

A dataset of test [cases](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/#pydantic_evals.dataset.Case).

Datasets allow you to organize a collection of test cases and evaluate them against a task function. They can be loaded from and saved to YAML or JSON files, and can have dataset-level evaluators that apply to all cases.

Example:

```python
# Create a dataset with two test cases
from dataclasses import dataclass

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext


@dataclass
class ExactMatch(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return ctx.output == ctx.expected_output

dataset = Dataset(
    name='uppercase_tests',
    cases=[
        Case(name='test1', inputs={'text': 'Hello'}, expected_output='HELLO'),
        Case(name='test2', inputs={'text': 'World'}, expected_output='WORLD'),
    ],
    evaluators=[ExactMatch()],
)

# Evaluate the dataset against a task function
async def uppercase(inputs: dict) -> str:
    return inputs['text'].upper()

async def main():
    report = await dataset.evaluate(uppercase)
    report.print()
'''
   Evaluation Summary: uppercase
┏━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Case ID  ┃ Assertions ┃ Duration ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━┩
│ test1    │ ✔          │     10ms │
├──────────┼────────────┼──────────┤
│ test2    │ ✔          │     10ms │
├──────────┼────────────┼──────────┤
│ Averages │ 100.0% ✔   │     10ms │
└──────────┴────────────┴──────────┘
'''
```

#### Attributes

##### name

Name of the dataset.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### cases

List of test cases in the dataset.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`Case`\[`InputsT`, `OutputT`, `MetadataT`\]\]

##### evaluators

List of evaluators to be used on all cases in the dataset.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`Evaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\] **Default:** `[]`

##### report\_evaluators

Evaluators that operate on the full report to produce experiment-wide analyses.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`ReportEvaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\] **Default:** `[]`

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    name: str,
    cases: Sequence[Case[InputsT, OutputT, MetadataT]],
    evaluators: Sequence[Evaluator[InputsT, OutputT, MetadataT]] = (),
    report_evaluators: Sequence[ReportEvaluator[InputsT, OutputT, MetadataT]] = (),
)
```

Initialize a new dataset with test cases and optional evaluators.

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Name for the dataset.

**`cases`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`Case`\[`InputsT`, `OutputT`, `MetadataT`\]\]

Sequence of test cases to include in the dataset.

**`evaluators`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`Evaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\] _Default:_ `()`

Optional sequence of evaluators to apply to all cases in the dataset.

**`report_evaluators`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`ReportEvaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\] _Default:_ `()`

Optional sequence of report evaluators that run on the full evaluation report.

##### evaluate

`@async`

```python
def evaluate(
    task: Callable[[InputsT], Awaitable[OutputT]] | Callable[[InputsT], OutputT],
    *,
    name: str | None = None,
    max_concurrency: int | None = None,
    progress: bool = True,
    retry_task: RetryConfig | None = None,
    retry_evaluators: RetryConfig | None = None,
    task_name: str | None = None,
    metadata: dict[str, Any] | None = None,
    repeat: int = 1,
    lifecycle: type[CaseLifecycle[InputsT, OutputT, MetadataT]] | Callable[[Case[InputsT, OutputT, MetadataT]], CaseLifecycle[InputsT, OutputT, MetadataT]] | None = None,
) -> EvaluationReport[InputsT, OutputT, MetadataT]
```

Evaluates the test cases in the dataset using the given task.

This method runs the task on each case in the dataset, applies evaluators, and collects results into a report. Cases are run concurrently, limited by `max_concurrency` if specified.

###### Returns

`EvaluationReport`\[`InputsT`, `OutputT`, `MetadataT`\] -- A report containing the results of the evaluation.

###### Parameters

**`task`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`InputsT`\], [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[`OutputT`\]\] | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`InputsT`\], `OutputT`\]

The task to evaluate. This should be a callable that takes the inputs of the case and returns the output.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The name of the experiment being run, this is used to identify the experiment in the report. If omitted, the task\_name will be used; if that is not specified, the name of the task function is used.

**`max_concurrency`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The maximum number of concurrent evaluations of the task to allow. If None, all cases will be evaluated concurrently.

**`progress`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to show a progress bar for the evaluation. Defaults to `True`.

**`retry_task`** : `RetryConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional retry configuration for the task execution.

**`retry_evaluators`** : `RetryConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional retry configuration for evaluator execution.

**`task_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional override to the name of the task being executed, otherwise the name of the task function will be used.

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional dict of experiment metadata.

**`repeat`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) _Default:_ `1`

Number of times to run each case. When > 1, each case is run multiple times and results are grouped by the original case name for aggregation. Defaults to 1.

**`lifecycle`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`CaseLifecycle`\[`InputsT`, `OutputT`, `MetadataT`\]\] | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`Case`\[`InputsT`, `OutputT`, `MetadataT`\]\], `CaseLifecycle`\[`InputsT`, `OutputT`, `MetadataT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional lifecycle class for per-case setup, context preparation, and teardown hooks. A new instance is created for each case. See [`CaseLifecycle`](https://pydantic.dev/docs/ai/api/pydantic_evals/lifecycle/#pydantic_evals.lifecycle.CaseLifecycle).

##### evaluate\_sync

```python
def evaluate_sync(
    task: Callable[[InputsT], Awaitable[OutputT]] | Callable[[InputsT], OutputT],
    *,
    name: str | None = None,
    max_concurrency: int | None = None,
    progress: bool = True,
    retry_task: RetryConfig | None = None,
    retry_evaluators: RetryConfig | None = None,
    task_name: str | None = None,
    metadata: dict[str, Any] | None = None,
    repeat: int = 1,
    lifecycle: type[CaseLifecycle[InputsT, OutputT, MetadataT]] | Callable[[Case[InputsT, OutputT, MetadataT]], CaseLifecycle[InputsT, OutputT, MetadataT]] | None = None,
) -> EvaluationReport[InputsT, OutputT, MetadataT]
```

Evaluates the test cases in the dataset using the given task.

This is a synchronous wrapper around [`evaluate`](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/#pydantic_evals.dataset.Dataset.evaluate) provided for convenience.

###### Returns

`EvaluationReport`\[`InputsT`, `OutputT`, `MetadataT`\] -- A report containing the results of the evaluation.

###### Parameters

**`task`** : [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`InputsT`\], [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[`OutputT`\]\] | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`InputsT`\], `OutputT`\]

The task to evaluate. This should be a callable that takes the inputs of the case and returns the output.

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The name of the experiment being run, this is used to identify the experiment in the report. If omitted, the task\_name will be used; if that is not specified, the name of the task function is used.

**`max_concurrency`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The maximum number of concurrent evaluations of the task to allow. If None, all cases will be evaluated concurrently.

**`progress`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) _Default:_ `True`

Whether to show a progress bar for the evaluation. Defaults to `True`.

**`retry_task`** : `RetryConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional retry configuration for the task execution.

**`retry_evaluators`** : `RetryConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional retry configuration for evaluator execution.

**`task_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional override to the name of the task being executed, otherwise the name of the task function will be used.

**`metadata`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional dict of experiment metadata.

**`repeat`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) _Default:_ `1`

Number of times to run each case. When > 1, each case is run multiple times and results are grouped by the original case name for aggregation. Defaults to 1.

**`lifecycle`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`CaseLifecycle`\[`InputsT`, `OutputT`, `MetadataT`\]\] | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`Case`\[`InputsT`, `OutputT`, `MetadataT`\]\], `CaseLifecycle`\[`InputsT`, `OutputT`, `MetadataT`\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional lifecycle class for per-case setup, context preparation, and teardown hooks. A new instance is created for each case. See [`CaseLifecycle`](https://pydantic.dev/docs/ai/api/pydantic_evals/lifecycle/#pydantic_evals.lifecycle.CaseLifecycle).

##### add\_case

```python
def add_case(
    *,
    name: str | None = None,
    inputs: InputsT,
    metadata: MetadataT | None = None,
    expected_output: OutputT | None = None,
    evaluators: tuple[Evaluator[InputsT, OutputT, MetadataT], ...] = (),
) -> None
```

Adds a case to the dataset.

This is a convenience method for creating a [`Case`](https://pydantic.dev/docs/ai/api/pydantic_evals/dataset/#pydantic_evals.dataset.Case) and adding it to the dataset.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional name for the case. If not provided, a generic name will be assigned.

**`inputs`** : `InputsT`

The inputs to the task being evaluated.

**`metadata`** : `MetadataT` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional metadata for the case, which can be used by evaluators.

**`expected_output`** : `OutputT` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The expected output of the task, used for comparison in evaluators.

**`evaluators`** : [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[`Evaluator`\[`InputsT`, `OutputT`, `MetadataT`\], ...\] _Default:_ `()`

Tuple of evaluators specific to this case, in addition to dataset-level evaluators.

##### add\_evaluator

```python
def add_evaluator(
    evaluator: Evaluator[InputsT, OutputT, MetadataT],
    specific_case: str | None = None,
) -> None
```

Adds an evaluator to the dataset or a specific case.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`evaluator`** : `Evaluator`\[`InputsT`, `OutputT`, `MetadataT`\]

The evaluator to add.

**`specific_case`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

If provided, the evaluator will only be added to the case with this name. If None, the evaluator will be added to all cases in the dataset.

###### Raises

-   `ValueError` -- If `specific_case` is provided but no case with that name exists in the dataset.

##### from\_file

`@classmethod`

```python
def from_file(
    cls,
    path: Path | str,
    fmt: Literal['yaml', 'json'] | None = None,
    custom_evaluator_types: Sequence[type[Evaluator[InputsT, OutputT, MetadataT]]] = (),
    custom_report_evaluator_types: Sequence[type[ReportEvaluator[InputsT, OutputT, MetadataT]]] = (),
) -> Self
```

Load a dataset from a file.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self) -- A new Dataset instance loaded from the file.

###### Parameters

**`path`** : `Path` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Path to the file to load.

**`fmt`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['yaml', 'json'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Format of the file. If None, the format will be inferred from the file extension. Must be either 'yaml' or 'json'.

**`custom_evaluator_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`Evaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\]\] _Default:_ `()`

Custom evaluator classes to use when deserializing the dataset. These are additional evaluators beyond the default ones.

**`custom_report_evaluator_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`ReportEvaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\]\] _Default:_ `()`

Custom report evaluator classes to use when deserializing the dataset. These are additional report evaluators beyond the default ones.

###### Raises

-   `ValidationError` -- If the file cannot be parsed as a valid dataset.
-   `ValueError` -- If the format cannot be inferred from the file extension.

##### from\_text

`@classmethod`

```python
def from_text(
    cls,
    contents: str,
    fmt: Literal['yaml', 'json'] = 'yaml',
    custom_evaluator_types: Sequence[type[Evaluator[InputsT, OutputT, MetadataT]]] = (),
    custom_report_evaluator_types: Sequence[type[ReportEvaluator[InputsT, OutputT, MetadataT]]] = (),
    *,
    default_name: str | None = None,
) -> Self
```

Load a dataset from a string.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self) -- A new Dataset instance parsed from the string.

###### Parameters

**`contents`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The string content to parse.

**`fmt`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['yaml', 'json'\] _Default:_ `'yaml'`

Format of the content. Must be either 'yaml' or 'json'.

**`custom_evaluator_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`Evaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\]\] _Default:_ `()`

Custom evaluator classes to use when deserializing the dataset. These are additional evaluators beyond the default ones.

**`custom_report_evaluator_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`ReportEvaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\]\] _Default:_ `()`

Custom report evaluator classes to use when deserializing the dataset. These are additional report evaluators beyond the default ones.

**`default_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Default name of the dataset, to be used if not specified in the serialized contents.

###### Raises

-   `ValidationError` -- If the content cannot be parsed as a valid dataset.

##### from\_dict

`@classmethod`

```python
def from_dict(
    cls,
    data: dict[str, Any],
    custom_evaluator_types: Sequence[type[Evaluator[InputsT, OutputT, MetadataT]]] = (),
    custom_report_evaluator_types: Sequence[type[ReportEvaluator[InputsT, OutputT, MetadataT]]] = (),
    *,
    default_name: str | None = None,
) -> Self
```

Load a dataset from a dictionary.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self) -- A new Dataset instance created from the dictionary.

###### Parameters

**`data`** : [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

Dictionary representation of the dataset.

**`custom_evaluator_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`Evaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\]\] _Default:_ `()`

Custom evaluator classes to use when deserializing the dataset. These are additional evaluators beyond the default ones.

**`custom_report_evaluator_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`ReportEvaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\]\] _Default:_ `()`

Custom report evaluator classes to use when deserializing the dataset. These are additional report evaluators beyond the default ones.

**`default_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Default name of the dataset, to be used if not specified in the data.

###### Raises

-   `ValidationError` -- If the dictionary cannot be converted to a valid dataset.

##### to\_file

```python
def to_file(
    path: Path | str,
    fmt: Literal['yaml', 'json'] | None = None,
    schema_path: Path | str | None = DEFAULT_SCHEMA_PATH_TEMPLATE,
    custom_evaluator_types: Sequence[type[Evaluator[InputsT, OutputT, MetadataT]]] = (),
    custom_report_evaluator_types: Sequence[type[ReportEvaluator[InputsT, OutputT, MetadataT]]] = (),
)
```

Save the dataset to a file.

###### Parameters

**`path`** : `Path` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Path to save the dataset to.

**`fmt`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['yaml', 'json'\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Format to use. If None, the format will be inferred from the file extension. Must be either 'yaml' or 'json'.

**`schema_path`** : `Path` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `DEFAULT_SCHEMA_PATH_TEMPLATE`

Path to save the JSON schema to. If None, no schema will be saved. Can be a string template with {stem} which will be replaced with the dataset filename stem.

**`custom_evaluator_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`Evaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\]\] _Default:_ `()`

Custom evaluator classes to include in the schema.

**`custom_report_evaluator_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`ReportEvaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\]\] _Default:_ `()`

Custom report evaluator classes to include in the schema.

##### model\_json\_schema\_with\_evaluators

`@classmethod`

```python
def model_json_schema_with_evaluators(
    cls,
    custom_evaluator_types: Sequence[type[Evaluator[InputsT, OutputT, MetadataT]]] = (),
    custom_report_evaluator_types: Sequence[type[ReportEvaluator[InputsT, OutputT, MetadataT]]] = (),
) -> dict[str, Any]
```

Generate a JSON schema for this dataset type, including evaluator details.

This is useful for generating a schema that can be used to validate YAML-format dataset files.

###### Returns

[`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] -- A dictionary representing the JSON schema.

###### Parameters

**`custom_evaluator_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`Evaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\]\] _Default:_ `()`

Custom evaluator classes to include in the schema.

**`custom_report_evaluator_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`ReportEvaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\]\] _Default:_ `()`

Custom report evaluator classes to include in the schema.

### set\_eval\_attribute

```python
def set_eval_attribute(name: str, value: Any) -> None
```

Set an attribute on the current task run.

#### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The name of the attribute.

**`value`** : [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

The value of the attribute.

### increment\_eval\_metric

```python
def increment_eval_metric(name: str, amount: int | float) -> None
```

Increment a metric on the current task run.

#### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Parameters

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The name of the metric.

**`amount`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`float`](https://docs.python.org/3/builtins/functions.html#float)

The amount to increment by.

### InputsT

Generic type for the inputs to the task being evaluated.

**Default:** `TypeVar('InputsT', default=Any)`

### OutputT

Generic type for the expected output of the task being evaluated.

**Default:** `TypeVar('OutputT', default=Any)`

### MetadataT

Generic type for the metadata associated with the task being evaluated.

**Default:** `TypeVar('MetadataT', default=Any)`

### DEFAULT\_DATASET\_PATH

Default path for saving/loading datasets.

**Default:** `'./test_cases.yaml'`

### DEFAULT\_SCHEMA\_PATH\_TEMPLATE

Default template for schema file paths, where {stem} is replaced with the dataset filename stem.

**Default:** `'./{stem}_schema.json'`

---
