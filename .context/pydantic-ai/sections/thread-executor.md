# [Thread Executor](https://pydantic.dev/docs/ai/capabilities/thread-executor/)

# Thread Executor

The [`UseThreadExecutor`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.UseThreadExecutor) [capability](https://pydantic.dev/docs/ai/capabilities/overview/) provides a custom [`Executor`](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Executor) for running sync tool functions and other sync callbacks in threads. This is useful in long-running servers (e.g. FastAPI) where the default ephemeral threads from `anyio.to_thread.run_sync` can accumulate under sustained load:

```python
from concurrent.futures import ThreadPoolExecutor

from pydantic_ai import Agent
from pydantic_ai.capabilities import UseThreadExecutor

executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix='agent-worker')
agent = Agent('openai:gpt-5.2', capabilities=[UseThreadExecutor(executor)])
```

It declares a default `id` of `'use_thread_executor'`, so two instances merge instead of raising a duplicate-id error -- see [building custom capabilities](https://pydantic.dev/docs/ai/capabilities/custom/) for the merge rules.

See [Thread executor for long-running servers](https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/#thread-executor-for-long-running-servers) for more details.

---
