# [Process Event Stream](https://pydantic.dev/docs/ai/capabilities/process-event-stream/)

# Process Event Stream

[`ProcessEventStream`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ProcessEventStream) is a [capability](https://pydantic.dev/docs/ai/capabilities/overview/) that forwards the agent's stream of [`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent)s -- model streaming and tool execution events -- to a handler. When it's registered, `agent.run()` automatically enables streaming, so the handler fires without passing an explicit [`event_stream_handler`](https://pydantic.dev/docs/ai/core-concepts/agent/#streaming-all-events) argument:

During a realtime session, the stream also contains realtime-only [`RealtimeEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeEvent) members.

process\_event\_stream.py

```python
from collections.abc import AsyncIterable

from pydantic_ai import Agent, AgentStreamEvent, RunContext
from pydantic_ai.capabilities import ProcessEventStream


async def log_events(ctx: RunContext, events: AsyncIterable[AgentStreamEvent]) -> None:
    async for event in events:
        print(event)  # (1)


agent = Agent('openai:gpt-5.2', capabilities=[ProcessEventStream(log_events)])
```

For example, forward events to a websocket, progress bar, or audit log.

The handler comes in two forms:

-   An [`EventStreamHandler`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.EventStreamHandler) -- an `async def` returning `None`, as above. Events are forwarded to the handler and passed through unchanged, so multiple handlers (and a top-level `event_stream_handler` argument) can all observe the same stream. Events are delivered synchronously, so a slow handler back-pressures the rest of the stream.
-   An `EventStreamProcessor` -- an async generator that yields events. What it yields replaces the stream for downstream consumers, so it can modify, drop, or add events.

Registering the capability composes with other streaming mechanisms: see [Streaming all events](https://pydantic.dev/docs/ai/core-concepts/agent/#streaming-all-events) for the event vocabulary and handler examples.

Durable execution

Under a [durable execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/) capability, a `ProcessEventStream` handler runs in workflow code and must be deterministic, because it re-runs on workflow replay. Tool and final-output events arrive live, while model events are replayed after each model request completes. For handler I/O that must run exactly once inside the durable boundary, pass `event_stream_handler=` to the durability capability instead.

---
