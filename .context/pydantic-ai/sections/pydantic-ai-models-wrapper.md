# [pydantic_ai.models.wrapper](https://pydantic.dev/docs/ai/api/models/wrapper/)

# pydantic\_ai.models.wrapper

### WrapperModel

**Bases:** `Model`

Model which wraps another model.

Does nothing on its own, used as a base class.

#### Attributes

##### wrapped

The underlying model being wrapped.

**Type:** `Model` **Default:** `infer_model(wrapped)`

##### settings

Get the settings from the wrapped model.

**Type:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

---
