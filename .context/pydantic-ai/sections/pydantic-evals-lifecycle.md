# [pydantic_evals.lifecycle](https://pydantic.dev/docs/ai/api/pydantic_evals/lifecycle/)

# pydantic\_evals.lifecycle

Case lifecycle hooks for pydantic evals.

This module provides the [`CaseLifecycle`](https://pydantic.dev/docs/ai/api/pydantic_evals/lifecycle/#pydantic_evals.lifecycle.CaseLifecycle) class, which allows defining setup, context preparation, and teardown hooks that run at different stages of case evaluation.

### CaseLifecycle

**Bases:** `Generic[InputsT, OutputT, MetadataT]`

Per-case lifecycle hooks for evaluation.

A new instance is created for each case during evaluation. Subclass and override any methods you need -- all methods are no-ops by default.

The evaluation flow for each case is:

1.  `setup()` -- called before task execution
2.  Task runs
3.  `prepare_context()` -- called after task, before evaluators; can enrich metrics/attributes
4.  Evaluators run
5.  `teardown()` -- called after evaluators complete; receives the full result (or `None` when interrupted)

Exceptions raised by `setup()` or `prepare_context()` are caught and recorded as a `ReportCaseFailure`; `teardown()` is still called afterward so you can clean up. Exceptions raised by `teardown()` propagate to the caller and may abort the evaluation. If your teardown may raise and you don't want it to crash the evaluation run, handle exceptions within your `teardown()` implementation itself.

#### Constructor Parameters

**`case`** : `Case`\[`InputsT`, `OutputT`, `MetadataT`\]

The case being evaluated. Available as `self.case` in all hooks.

#### Attributes

##### case

The case being evaluated.

**Type:** `Case`\[`InputsT`, `OutputT`, `MetadataT`\]

#### Methods

##### setup

`@async`

```python
def setup() -> None
```

Called before task execution.

Override to perform per-case resource setup (e.g., create a test database, start a service). The case metadata is available via `self.case.metadata`.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### prepare\_context

`@async`

```python
def prepare_context(
    ctx: EvaluatorContext[InputsT, OutputT, MetadataT],
) -> EvaluatorContext[InputsT, OutputT, MetadataT]
```

Called after the task completes, before evaluators run.

Override to enrich the evaluator context with additional metrics or attributes derived from the task output, span tree, or external state.

###### Returns

`EvaluatorContext`\[`InputsT`, `OutputT`, `MetadataT`\] -- The (possibly modified) evaluator context to pass to evaluators.

###### Parameters

**`ctx`** : `EvaluatorContext`\[`InputsT`, `OutputT`, `MetadataT`\]

The evaluator context produced by the task run.

##### teardown

`@async`

```python
def teardown(
    result: ReportCase[InputsT, OutputT, MetadataT] | ReportCaseFailure[InputsT, OutputT, MetadataT] | None,
) -> None
```

Called after evaluators complete.

Override to perform per-case resource cleanup. The result is provided so that teardown logic can vary based on success/failure (e.g., keep resources up for inspection on failure).

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`result`** : `ReportCase`\[`InputsT`, `OutputT`, `MetadataT`\] | `ReportCaseFailure`\[`InputsT`, `OutputT`, `MetadataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

The evaluation result -- a `ReportCase` (success), `ReportCaseFailure`, or `None` if the run ended without a report object (e.g. cancellation).

---
