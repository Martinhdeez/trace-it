# [Prepare Tools](https://pydantic.dev/docs/ai/capabilities/prepare-tools/)

# Prepare Tools

[`PrepareTools`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.PrepareTools) and [`PrepareOutputTools`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.PrepareOutputTools) wrap a [`ToolsPrepareFunc`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.ToolsPrepareFunc) as a [capability](https://pydantic.dev/docs/ai/capabilities/overview/), for filtering or modifying [tool definitions](https://pydantic.dev/docs/ai/tools-toolsets/tools/) per step. `PrepareTools` handles function tools; `PrepareOutputTools` handles [output tools](https://pydantic.dev/docs/ai/api/pydantic-ai/output/#pydantic_ai.output.ToolOutput).

prepare\_tools\_native.py

```python
from pydantic_ai import Agent, RunContext, ToolDefinition
from pydantic_ai.capabilities import PrepareTools


async def hide_dangerous(ctx: RunContext, tool_defs: list[ToolDefinition]) -> list[ToolDefinition]:
    return [td for td in tool_defs if not td.name.startswith('delete_')]


agent = Agent('openai:gpt-5.2', capabilities=[PrepareTools(hide_dangerous)])


@agent.tool_plain
def delete_file(path: str) -> str:
    """Delete a file."""
    return f'deleted {path}'


@agent.tool_plain
def read_file(path: str) -> str:
    """Read a file."""
    return f'contents of {path}'


result = agent.run_sync('hello')
# The model only sees `read_file`, not `delete_file`
```

For more complex tool preparation logic, see [Tool preparation](https://pydantic.dev/docs/ai/capabilities/custom/#tool-preparation) under lifecycle hooks.

---
