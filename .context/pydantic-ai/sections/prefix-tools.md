# [Prefix Tools](https://pydantic.dev/docs/ai/capabilities/prefix-tools/)

# Prefix Tools

[`PrefixTools`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.PrefixTools) is a [capability](https://pydantic.dev/docs/ai/capabilities/overview/) that wraps another capability and prefixes all of its tool names, useful for namespacing when composing multiple capabilities that might have conflicting tool names:

prefix\_tools\_example.py

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import MCP, PrefixTools

agent = Agent(
    'openai:gpt-5.2',
    capabilities=[
        PrefixTools(MCP(url='https://api1.example.com', native=True), prefix='api1'),
        PrefixTools(MCP(url='https://api2.example.com', native=True), prefix='api2'),
    ],
)
```

Every [`AbstractCapability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability) has a convenience method [`prefix_tools`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.prefix_tools) that returns a [`PrefixTools`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.PrefixTools) wrapper:

prefix\_convenience.py

```python
MCP(url='https://mcp.example.com/api', native=True).prefix_tools('mcp')
```

---
