# [pydantic_graph.util](https://pydantic.dev/docs/ai/api/pydantic_graph/util/)

# pydantic\_graph.util

Utility types and functions for type manipulation and introspection.

This module provides helper classes and functions for working with Python's type system, including workarounds for type checker limitations and utilities for runtime type inspection.

### TypeExpression

**Bases:** `Generic[T]`

A workaround for type checker limitations when using complex type expressions.

This class serves as a wrapper for types that cannot normally be used in positions requiring `type[T]`, such as `Any`, `Union[...]`, or `Literal[...]`. It provides a way to pass these complex type expressions to functions expecting concrete types.

### Some

**Bases:** `Generic[T]`

Container for explicitly present values in Maybe type pattern.

This class represents a value that is definitely present, as opposed to None. It's part of the Maybe pattern, similar to Option/Maybe in functional programming, allowing distinction between "no value" (None) and "value is None" (Some(None)).

#### Attributes

##### value

The wrapped value.

**Type:** `T`

### unpack\_type\_expression

```python
def unpack_type_expression(type_: TypeOrTypeExpression[T]) -> type[T]
```

Extract the actual type from a TypeExpression wrapper or return the type directly.

#### Returns

[`type`](https://docs.python.org/3/glossary.html#term-type)\[`T`\] -- The unwrapped type, ready for use in runtime type operations.

#### Parameters

**`type_`** : `TypeOrTypeExpression`\[`T`\]

Either a direct type or a TypeExpression wrapper.

### get\_callable\_name

```python
def get_callable_name(callable_: Any) -> str
```

Extract a human-readable name from a callable object.

#### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) -- The callable's **name** attribute if available, otherwise its string representation.

#### Parameters

**`callable_`** : [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

Any callable object (function, method, class, etc.).

### T

Generic type variable with inferred variance.

**Default:** `TypeVar('T', infer_variance=True)`

### TypeOrTypeExpression

Type alias allowing both direct types and TypeExpression wrappers.

This alias enables functions to accept either regular types (when compatible with type checkers) or TypeExpression wrappers for complex type expressions. The correct type should be inferred automatically in either case.

**Default:** `TypeAliasType('TypeOrTypeExpression', type[TypeExpression[T]] | type[T], type_params=(T,))`

### Maybe

Optional-like type that distinguishes between absence and None values.

Unlike Optional\[T\], Maybe\[T\] can differentiate between:

-   No value present: represented as None
-   Value is None: represented as Some(None)

This is particularly useful when None is a valid value in your domain.

**Default:** `TypeAliasType('Maybe', Some[T] | None, type_params=(T,))`

---
