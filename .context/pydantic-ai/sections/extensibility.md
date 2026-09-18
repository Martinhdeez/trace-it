# [Extensibility](https://pydantic.dev/docs/ai/guides/extensibility/)

# Extensibility

Pydantic AI is designed to be extended. [Capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) are the primary extension point -- they bundle tools, lifecycle hooks, instructions, and model settings into reusable units that can be shared across agents, packaged as libraries, and loaded from [spec files](https://pydantic.dev/docs/ai/core-concepts/agent-spec/).

Beyond capabilities, Pydantic AI provides several other extension mechanisms for specialized needs.

## Capabilities

Capabilities are the recommended way to extend Pydantic AI. They are useful for:

-   **Teams** building reusable internal agent components (guardrails, audit logging, authentication)
-   **Package authors** shipping extensions that work across models and agents
-   **Community contributors** sharing solutions to common problems

See [Capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) for using and building capabilities, and [Hooks](https://pydantic.dev/docs/ai/core-concepts/hooks/) for the lightweight decorator-based approach.

Tip

If you want to contribute a capability, open an issue on [**Pydantic AI Harness**](https://github.com/pydantic/pydantic-ai-harness) rather than on pydantic-ai. Most capabilities belong in the harness -- see [What goes where?](https://pydantic.dev/docs/ai/harness/#what-goes-where) for the distinction.

## Publishing capability packages

To make a capability installable and usable in [agent specs](https://pydantic.dev/docs/ai/core-concepts/agent-spec/):

1.  **Implement [`get_serialization_name()`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.get_serialization_name)** -- defaults to the class name. Return `None` to opt out of spec support.
    
2.  **Implement [`from_spec()`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.AbstractCapability.from_spec)** -- defaults to `cls(*args, **kwargs)`. Override when your constructor takes non-serializable types.
    
3.  **Package naming** -- use the `pydantic-ai-` prefix (e.g. `pydantic-ai-guardrails`) so users can find your package.
    
4.  **Registration** -- users pass custom capability types via `custom_capability_types` on [`Agent.from_spec`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.from_spec) or [`Agent.from_file`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.from_file).
    

```python
from pydantic_ai import Agent

from my_package import MyCapability

agent = Agent.from_file('agent.yaml', custom_capability_types=[MyCapability])
```

See [Custom capabilities in specs](https://pydantic.dev/docs/ai/core-concepts/agent-spec/#custom-capabilities-in-specs) for implementation details.

## Pydantic AI Harness

[**Pydantic AI Harness**](https://pydantic.dev/docs/ai/harness/) is the official capability library for Pydantic AI -- standalone capabilities like memory, guardrails, and context management live there rather than in core. See [What goes where?](https://pydantic.dev/docs/ai/harness/#what-goes-where) for the full breakdown, or jump to the [capability matrix](https://github.com/pydantic/pydantic-ai-harness#capability-matrix).

## Third-party ecosystem

### Capabilities

[Capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) are the recommended extension mechanism for packages that need to bundle tools with hooks, instructions, or model settings. See [Third-party capabilities](https://pydantic.dev/docs/ai/capabilities/third-party/) for community packages.

### Toolsets

Many third-party extensions are available as [toolsets](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/), which can also be wrapped as [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) to take advantage of hooks, instructions, and model settings. See [Third-party toolsets](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#third-party-toolsets) for the full list.

## Other extension points

### Custom toolsets

For specialized tool execution needs (custom transport, tool filtering, execution wrapping), implement [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset) or subclass [`WrapperToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.WrapperToolset):

-   [`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset) -- full control over tool definitions and execution
-   [`WrapperToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.WrapperToolset) -- delegates to a wrapped toolset, override specific methods

See [Building a Custom Toolset](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#building-a-custom-toolset) for details.

Tip

If your toolset also needs to provide instructions, model settings, or hooks, consider building a [custom capability](https://pydantic.dev/docs/ai/capabilities/custom/) instead.

### Custom models

For connecting to model providers not yet supported by Pydantic AI, implement [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model):

-   [`Model`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.Model) -- the base interface for model implementations
-   [`WrapperModel`](https://pydantic.dev/docs/ai/api/models/wrapper/#pydantic_ai.models.wrapper.WrapperModel) -- delegates to a wrapped model, useful for adding instrumentation or transformations

See [Custom Models](https://pydantic.dev/docs/ai/models/overview/#custom-models) for details.

### Custom agents

For custom agent behavior, subclass [`AbstractAgent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent) or [`WrapperAgent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.WrapperAgent):

-   [`AbstractAgent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent) -- the base interface for agent implementations, providing `run`, `run_sync`, and `run_stream`
-   [`WrapperAgent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.WrapperAgent) -- delegates to a wrapped agent, useful for adding pre/post-processing or context management

---
