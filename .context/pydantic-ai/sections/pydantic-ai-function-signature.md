# [pydantic_ai.function_signature](https://pydantic.dev/docs/ai/api/pydantic-ai/function_signature/)

# pydantic\_ai.function\_signature

Generate function signatures from functions and JSON schemas.

This module provides utilities to represent tool definitions as human-readable function signatures, which LLMs can understand more easily than raw JSON schemas. Used by code mode to present tools as callable functions.

### SimpleTypeExpr

A simple named type like `str`, `int`, `Any`, `None`.

### LiteralTypeExpr

A Literal type expression like `Literal['a', 'b']` or `Literal[42]`.

### GenericTypeExpr

A generic type expression like `list[User]`, `dict[str, User]`, `tuple[int, str]`.

### UnionTypeExpr

A union type expression like `User | None`, `str | int`.

### TypeFieldSignature

A single field in a TypedDict-style type definition.

#### Methods

##### \_\_str\_\_

```python
def __str__() -> str
```

Render this field as a line in a TypedDict class body.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### TypeSignature

A TypedDict-style class definition with named fields.

#### Attributes

##### display\_name

The type name, with tool-name prefix applied if rendering context is set.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### \_\_str\_\_

```python
def __str__() -> str
```

Return the type name (for use in type expressions like `def foo(x: User)`).

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### render\_definition

```python
def render_definition(
    *,
    owner_name: str | None = None,
    conflicting_type_names: frozenset[str] = frozenset(),
) -> str
```

Render the full TypedDict class definition.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

###### Parameters

**`owner_name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The owning tool name, used to build prefixed type names for conflicting types (e.g. `get_user_Address`).

**`conflicting_type_names`** : [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] _Default:_ `frozenset()`

Set of type names that need tool-name prefixes (from `get_conflicting_type_names`). Only effective when `owner_name` is also provided.

##### structurally\_equal

```python
def structurally_equal(other: TypeSignature) -> bool
```

Compare two TypeSignatures structurally, ignoring descriptions.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### FunctionParam

A single parameter in a function signature.

#### Methods

##### \_\_str\_\_

```python
def __str__() -> str
```

Render this parameter as a function parameter string.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### FunctionSignature

Function signature shape with referenced type definitions.

This class holds the structural data (params, return type, referenced types) needed to render a function signature. Name and description can be overridden at render time (e.g. from a `ToolDefinition`).

#### Attributes

##### params

Function parameters, all rendered as keyword-only (JSON schema doesn't distinguish positional/keyword).

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `FunctionParam`\] **Default:** `field(default_factory=(dict[str, FunctionParam]))`

##### return\_type

The return type expression.

**Type:** `TypeExpr`

##### referenced\_types

TypedDict class definitions needed by the signature.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`TypeSignature`\] **Default:** `field(default_factory=(list[TypeSignature]))`

##### is\_async

Whether the underlying function is async.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

#### Methods

##### render

```python
def render(
    body: str,
    *,
    name: str | None = None,
    description: str | None = None,
    is_async: bool | None = None,
    conflicting_type_names: frozenset[str] = frozenset(),
) -> str
```

Render the signature with a specific body.

Sets `_type_name_overrides` so that dedup-prefixed types resolve correctly during rendering.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

###### Parameters

**`body`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The function body (e.g. `'...'` or `'return await tool()'`).

**`name`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The function name (also used for dedup prefix resolution). Falls back to `self.name`.

**`description`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Optional docstring to include. Falls back to `self.description`.

**`is_async`** : [`bool`](https://docs.python.org/3/builtins/functions.html#bool) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Override async rendering. If `None`, uses `self.is_async`.

**`conflicting_type_names`** : [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] _Default:_ `frozenset()`

Set of type names that need tool-name prefixes (from `get_conflicting_type_names`).

##### from\_schema

`@classmethod`

```python
def from_schema(
    cls,
    *,
    name: str,
    parameters_schema: dict[str, Any],
    return_schema: dict[str, Any] | None = None,
) -> FunctionSignature
```

Build a FunctionSignature from JSON schemas.

`name` is stored on the resulting signature and also used for generating fallback type names (e.g. `GetUserAddress`) when the schema has no `title`.

Parameter and return schemas are processed independently -- each resolves `$ref`s against its own `$defs`. Name collisions between parameter and return types (e.g. both define a `User` `$def` with different structures) are handled by `get_conflicting_type_names` at a later stage.

###### Returns

`FunctionSignature`

##### get\_conflicting\_type\_names

`@staticmethod`

```python
def get_conflicting_type_names(signatures: list[FunctionSignature]) -> frozenset[str]
```

Identify TypedDict name conflicts across multiple tool signatures.

Each signature keeps all its referenced types (so it remains self-contained), but identical types (same name and structure) are unified to the same object instance.

Returns the set of type names that have conflicts (same name, different structure) and need tool-name prefixes at render time. Pass this set to `FunctionSignature.render(conflicting_type_names=...)`.

Use `collect_unique_referenced_types()` when rendering to emit each definition once.

###### Returns

[`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### collect\_unique\_referenced\_types

`@staticmethod`

```python
def collect_unique_referenced_types(
    signatures: list[FunctionSignature],
) -> list[TypeSignature]
```

Collect unique TypeSignature objects from signatures, deduplicating by identity.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`TypeSignature`\]

##### render\_type\_definitions

`@staticmethod`

```python
def render_type_definitions(
    signatures: list[FunctionSignature],
    conflicting_type_names: frozenset[str],
) -> list[str]
```

Render unique TypedDict definitions for a set of function signatures.

For types whose names conflict across signatures (as identified by `get_conflicting_type_names`), each definition is rendered with a tool-name prefix (e.g. `get_user_Address`).

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] -- A list of rendered TypedDict class definitions as strings.

###### Parameters

**`signatures`** : [`list`](https://docs.python.org/3/glossary.html#term-list)\[`FunctionSignature`\]

The function signatures (after `get_conflicting_type_names`).

**`conflicting_type_names`** : [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

The set returned by `get_conflicting_type_names`.

### TypeExpr

A type expression node in the signature's type tree.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `'TypeSignature | SimpleTypeExpr | LiteralTypeExpr | GenericTypeExpr | UnionTypeExpr'`

---
