# [Reinject System Prompt](https://pydantic.dev/docs/ai/capabilities/reinject-system-prompt/)

# Reinject System Prompt

[`ReinjectSystemPrompt`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ReinjectSystemPrompt) is a [capability](https://pydantic.dev/docs/ai/capabilities/overview/) that ensures the agent's configured [`system_prompt`](https://pydantic.dev/docs/ai/core-concepts/agent/#system-prompts) is at the head of the first [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest) on every model request. By default, if any [`SystemPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SystemPromptPart) is already present in the history, the capability is a no-op (so multi-agent handoff and user-managed system prompts remain authoritative). Set `replace_existing=True` to instead strip any existing `SystemPromptPart`s before prepending the agent's configured prompt -- useful when the history comes from an untrusted source and the server's prompt must win.

It declares a default `id` of `'reinject_system_prompt'`, so two instances merge instead of raising a duplicate-id error -- see [building custom capabilities](https://pydantic.dev/docs/ai/capabilities/custom/) for the merge rules.

Useful when `message_history` comes from a source that doesn't round-trip system prompts -- UI frontends, database persistence layers, conversation compaction pipelines. Without this capability, an agent configured with a `system_prompt` will silently run without it if the history doesn't already include one.

reinject\_system\_prompt.py

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import ReinjectSystemPrompt
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

agent = Agent('test', system_prompt='You are a helpful assistant.', capabilities=[ReinjectSystemPrompt()])

# History that's missing the system prompt (e.g. reconstructed from a UI frontend).
history = [
    ModelRequest(parts=[UserPromptPart(content='Hi')]),
    ModelResponse(parts=[TextPart(content='Hello!')]),
]

# Without the capability, the agent would run without its configured system prompt.
# With the capability, the system prompt is reinjected at the head of the first request.
result = agent.run_sync('Follow up', message_history=history)
first_request = result.all_messages()[0]
assert isinstance(first_request, ModelRequest)
assert first_request.parts[0].content == 'You are a helpful assistant.'
```

_(This example is complete, it can be run "as is")_

The [UI adapters](https://pydantic.dev/docs/ai/integrations/ui/ag-ui/) (AG-UI, Vercel AI) automatically add this capability with `replace_existing=True` in their `manage_system_prompt='server'` mode.

---
