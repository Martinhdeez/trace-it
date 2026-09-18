# [pydantic_evals.generation](https://pydantic.dev/docs/ai/api/pydantic_evals/generation/)

# pydantic\_evals.generation

Utilities for generating example datasets for pydantic\_evals.

This module provides functions for generating sample datasets for testing and examples, using LLMs to create realistic test data with proper structure.

### generate\_dataset

`@async`

```python
def generate_dataset(
    *,
    dataset_type: type[Dataset[InputsT, OutputT, MetadataT]],
    path: Path | str | None = None,
    custom_evaluator_types: Sequence[type[Evaluator[InputsT, OutputT, MetadataT]]] = (),
    model: models.Model | models.KnownModelName = 'openai:gpt-5.2',
    n_examples: int = 3,
    extra_instructions: str | None = None,
) -> Dataset[InputsT, OutputT, MetadataT]
```

Use an LLM to generate a dataset of test cases, each consisting of input, expected output, and metadata.

This function creates a properly structured dataset with the specified input, output, and metadata types. It uses an LLM to attempt to generate realistic test cases that conform to the types' schemas.

#### Returns

`Dataset`\[`InputsT`, `OutputT`, `MetadataT`\] -- A properly structured Dataset object with generated test cases.

#### Parameters

**`path`** : `Path` | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional path to save the generated dataset. If provided, the dataset will be saved to this location.

**`dataset_type`** : [`type`](https://docs.python.org/3/glossary.html#term-type)\[`Dataset`\[`InputsT`, `OutputT`, `MetadataT`\]\]

The type of dataset to generate, with the desired input, output, and metadata types.

**`custom_evaluator_types`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`type`](https://docs.python.org/3/glossary.html#term-type)\[`Evaluator`\[`InputsT`, `OutputT`, `MetadataT`\]\]\] _Default:_ `()`

Optional sequence of custom evaluator classes to include in the schema.

**`model`** : [`models.Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) | [`models.KnownModelName`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName) _Default:_ `'openai:gpt-5.2'`

The Pydantic AI model to use for generation. Defaults to 'openai:gpt-5.2'.

**`n_examples`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) _Default:_ `3`

Number of examples to generate. Defaults to 3.

**`extra_instructions`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional additional instructions to provide to the LLM.

#### Raises

-   `ValidationError` -- If the LLM's response cannot be parsed as a valid dataset.

### InputsT

Generic type for the inputs to the task being evaluated.

**Default:** `TypeVar('InputsT', default=Any)`

### OutputT

Generic type for the expected output of the task being evaluated.

**Default:** `TypeVar('OutputT', default=Any)`

### MetadataT

Generic type for the metadata associated with the task being evaluated.

**Default:** `TypeVar('MetadataT', default=Any)`

---
