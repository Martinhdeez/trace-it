# [Process History](https://pydantic.dev/docs/ai/capabilities/process-history/)

# Process History

[`ProcessHistory`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ProcessHistory) is a [capability](https://pydantic.dev/docs/ai/capabilities/overview/) that wraps a [history processor](https://pydantic.dev/docs/ai/core-concepts/message-history/#processing-message-history): a function that receives the message history before each model request and returns the (possibly modified) list of messages to send. Use it to trim old turns, redact sensitive content, or summarize long conversations:

process\_history.py

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import ProcessHistory
from pydantic_ai.messages import ModelMessage


def keep_recent(messages: list[ModelMessage]) -> list[ModelMessage]:
    return messages[-5:]  # (1)


agent = Agent('openai:gpt-5.2', capabilities=[ProcessHistory(keep_recent)])
```

Keep only the five most recent messages. In practice you'll want to keep the first request too, so the system prompt survives -- see [Processing Message History](https://pydantic.dev/docs/ai/core-concepts/message-history/#processing-message-history) for complete patterns.

The processor may be sync or async, and may optionally take a [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) as its first argument to access dependencies and run state. Multiple `ProcessHistory` capabilities apply in registration order. Note that the processed messages _replace_ the run's message history, so make a copy first if you need to keep the original.

`ProcessHistory` is a thin wrapper around the [`before_model_request`](https://pydantic.dev/docs/ai/core-concepts/hooks/) lifecycle hook. Hook into that event directly for richer control, such as short-circuiting the model call. See [Processing Message History](https://pydantic.dev/docs/ai/core-concepts/message-history/#processing-message-history) for the full guide, including summarization examples and interactions with [`new_messages()`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult.new_messages).

---
