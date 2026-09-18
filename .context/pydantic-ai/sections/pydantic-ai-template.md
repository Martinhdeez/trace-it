# [pydantic_ai.template](https://pydantic.dev/docs/ai/api/pydantic-ai/template/)

# pydantic\_ai.template

Template string support for dynamic instructions.

### TemplateStr

**Bases:** `Generic[AgentDepsT]`

A Handlebars template string that renders against `RunContext.deps`.

When used in type hints, strings containing `{{` are automatically compiled as Handlebars templates during Pydantic validation.

Uses [pydantic-handlebars](https://github.com/pydantic/pydantic-handlebars) for template compilation, schema validation, and rendering.

When used with an `Agent`, `deps_type` is inferred automatically from the agent's validation context, so you only need to pass it when constructing a `TemplateStr` outside of an agent (e.g. for standalone rendering).

#### Methods

##### render

```python
def render(deps: AgentDepsT | None = None) -> str
```

Render the template against the given deps object.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### \_\_call\_\_

```python
def __call__(ctx: RunContext[AgentDepsT]) -> str
```

Render the template against `ctx.deps`.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

---
