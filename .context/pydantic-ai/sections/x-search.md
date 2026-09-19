# [X Search](https://pydantic.dev/docs/ai/capabilities/x-search/)

# X Search

The [`XSearch`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.XSearch) [capability](https://pydantic.dev/docs/ai/capabilities/overview/) gives your agent search over X (Twitter) posts. It's a [provider-adaptive tool](https://pydantic.dev/docs/ai/capabilities/overview/#provider-adaptive-tools) backed by [`XSearchTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.XSearchTool) on the native side -- see [X Search Tool](https://pydantic.dev/docs/ai/tools-toolsets/native-tools/#x-search-tool) for configuration options.

Unlike [Web Search](https://pydantic.dev/docs/ai/capabilities/web-search/) and [Web Fetch](https://pydantic.dev/docs/ai/capabilities/web-fetch/), there is no default non-xAI fallback: X search is only available natively on xAI models. If your agent is not running on an xAI model, set `fallback_subagent_model` explicitly to an xAI model that supports [`XSearchTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.XSearchTool), and search requests are delegated to that model as a subagent tool:

x\_search.py

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import XSearch

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[XSearch(fallback_subagent_model='xai:grok-4.3')],
)
```

`fallback_model` is deprecated

`fallback_model` is the former name of `fallback_subagent_model`. It keeps working, in Python and in an [agent spec](https://pydantic.dev/docs/ai/core-concepts/agent-spec/), and warns; passing both names is refused: [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) when you construct the capability, and the `ValueError` the spec loader wraps it in when you load a spec.

`native=` can be a factory: a callable taking [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) that returns [`XSearchTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.XSearchTool) or `None` -- [`XSearchNativeTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/common_tools/#pydantic_ai.common_tools.x_search.XSearchNativeTool) is the type the `fallback_subagent_model` subagent accepts. It resolves on each model request, and again when the subagent runs -- so keep it free of one-shot side effects. Both resolutions belong to the same run and carry the same `deps`, but they do not share a [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext): the subagent resolves from its own tool call, so `tool_call_id` and `tool_name` name that call instead of being `None`, and `messages` holds the run so far. Read `ctx.deps` for configuration that has to match across both. On the subagent, capability-level fields such as `include_output` override the factory result. See [Dynamic Configuration](https://pydantic.dev/docs/ai/tools-toolsets/native-tools/#dynamic-configuration).

A factory returning `None`

`None` omits the tool for that request only when no `fallback_subagent_model` is set. With a `fallback_subagent_model`, the subagent tool is offered to the model whenever the factory returns `None` -- even on a model that supports [`XSearchTool`](https://pydantic.dev/docs/ai/api/pydantic-ai/native_tools/#pydantic_ai.native_tools.XSearchTool) natively -- and calling it raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) rather than searching X with default settings.

Durable execution with Temporal

The `fallback_subagent_model` subagent's tool call runs inside a Temporal activity, so a `native=` factory resolved there receives the limited [`TemporalRunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/durable_exec/#pydantic_ai.durable_exec.temporal.TemporalRunContext): reading `ctx.messages`, or any other field Temporal does not carry, raises a [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError). `ctx.deps` does cross the boundary, so keep the factory reading `deps` only. See [Agent Run Context and Dependencies](https://pydantic.dev/docs/ai/capabilities/durable_execution/temporal/#agent-run-context-and-dependencies) for the fields that are available. [DBOS](https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/) and [Prefect](https://pydantic.dev/docs/ai/capabilities/durable_execution/prefect/) pass the live `RunContext` and are unaffected.

---
