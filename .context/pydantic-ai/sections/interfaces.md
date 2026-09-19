# [Interfaces](https://pydantic.dev/docs/ai/overview/interfaces/)

# Interfaces

A Pydantic AI [agent](https://pydantic.dev/docs/ai/core-concepts/agent/) is plain Python with no interface baked in: the same agent can run headless inside your backend, chat in a terminal, serve a web UI, power your own frontend, live inside an editor, or hold a spoken conversation. Each surface has its own page:

Surface

What it looks like

Where

**Your code**

`result = await agent.run('...')`, an ordinary awaitable in any Python function, with [typed output](https://pydantic.dev/docs/ai/core-concepts/output/)

[Running agents](https://pydantic.dev/docs/ai/core-concepts/agent/#running-agents)

**Terminal**

`agent.to_cli_sync()`, or `clai -a mymodule:agent` against any agent you can import

[CLI](https://pydantic.dev/docs/ai/integrations/cli/)

**Web chat**

A built-in browser chat for any agent: `clai web` or `agent.to_web()`

[Web Chat UI](https://pydantic.dev/docs/ai/guides/web/)

**Your frontend**

Stream agent runs to your own UI over the [AG-UI](https://pydantic.dev/docs/ai/integrations/ui/ag-ui/) or [Vercel AI](https://pydantic.dev/docs/ai/integrations/ui/vercel-ai/) protocols, including Vercel's `useChat` React hooks

[UI Event Streams](https://pydantic.dev/docs/ai/integrations/ui/overview/)

**Editors**

Serve an agent to Zed and other editors over the [Agent Client Protocol](https://agentclientprotocol.com/)

[ACP](https://pydantic.dev/docs/ai/harness/acp/) (Harness, experimental)

**Voice**

The same agent, tools, and observability over a live audio session; voice is just another frontend

[Realtime](https://pydantic.dev/docs/ai/realtime/overview/)

Because interfaces are separate from the agent, features work across all of them: [deferred tools and approval](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval) surface wherever the agent runs (approval prompts in the CLI, approval UI events in your frontend), the same deployed agent can serve the web UI for your team and the AG-UI stream for your product at once, and a [realtime session](https://pydantic.dev/docs/ai/realtime/overview/) can hand its history to a text run and back. Complete agents work everywhere too: `clai -a pydantic_ai_harness.coder:coder_agent` runs the [Harness](https://pydantic.dev/docs/ai/harness/)'s [Coder](https://pydantic.dev/docs/ai/harness/coder/) in your terminal.

---
