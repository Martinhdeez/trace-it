# [pydantic_ai.ext](https://pydantic.dev/docs/ai/api/pydantic-ai/ext/)

# pydantic\_ai.ext

### LangChainToolset

**Bases:** [`FunctionToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.FunctionToolset)

A toolset that wraps LangChain tools.

### tool\_from\_langchain

```python
def tool_from_langchain(langchain_tool: LangChainTool) -> Tool
```

Creates a Pydantic AI tool proxy from a LangChain tool.

#### Returns

[`Tool`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.Tool) -- A Pydantic AI tool that corresponds to the LangChain tool.

#### Parameters

**`langchain_tool`** : `LangChainTool`

The LangChain tool to wrap.

---
