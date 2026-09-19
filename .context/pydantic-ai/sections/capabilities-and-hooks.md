# [Capabilities and hooks](https://pydantic.dev/docs/ai/realtime/capabilities/)

# Capabilities and hooks

A [capability](https://pydantic.dev/docs/ai/capabilities/overview/) attached to the agent or passed to `realtime(capabilities=...)` participates in a realtime session where its lifecycle maps onto a persistent connection. [Third-party capabilities](https://pydantic.dev/docs/ai/capabilities/overview/#third-party-capabilities) load exactly the same way as in a regular run; nothing realtime-specific is required of them.

## Capability stages in a session

Capability stage

Session behavior

`for_agent`, `for_run`, `get_instructions`

Runs during setup; dynamic instructions are evaluated once at connect.

`get_toolset`, `get_wrapper_toolset`, `prepare_tools`

Contributes, wraps, and prepares local tools before connecting.

`get_native_tools`

Contributes native tools before connecting; a dynamic native-tool function is resolved once against the connect-time context, like dynamic instructions.

Tool validation/execution hooks

Runs around each local function-tool call.

`handle_deferred_tool_calls`

Resolves deferred requests inline; see [deferred and approval-required tools](https://pydantic.dev/docs/ai/realtime/tools/#deferred-and-approval-required-tools).

Graph node, model-request, and output-processing hooks

Do not run; no agent graph or output-processing stage exists.

All regular [tool validation](https://pydantic.dev/docs/ai/core-concepts/hooks/#tool-validation-hooks) and [tool execution](https://pydantic.dev/docs/ai/core-concepts/hooks/#tool-execution-hooks) hooks -- `before`, `after`, `wrap`, and `on_error` for both stages -- run around every local function-tool call exactly as in a standard run, retries and all. What does not run is anything tied to the request-response graph: [node hooks](https://pydantic.dev/docs/ai/core-concepts/hooks/#node-hooks), [model request hooks](https://pydantic.dev/docs/ai/core-concepts/hooks/#model-request-hooks) such as `before_model_request`, and [output validation](https://pydantic.dev/docs/ai/core-concepts/hooks/#output-validation-hooks) and [output processing](https://pydantic.dev/docs/ai/core-concepts/hooks/#output-processing-hooks) hooks -- a session has no graph nodes, no per-request boundary, and no output stage.

## Run hooks

`before_run`, `after_run`, `wrap_run`, and `on_run_error` [run hooks](https://pydantic.dev/docs/ai/core-concepts/hooks/#run-hooks) run once around the session -- a realtime session is a run -- with the same close-boundary recovery and result-transformation semantics as [`iter()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.iter).

## The event stream

`wrap_run_event_stream` wraps the consumer-facing session iterator. It can observe or transform shared [`AgentStreamEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.AgentStreamEvent) members and realtime-only [`RealtimeEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeEvent) members (see the [event reference](https://pydantic.dev/docs/ai/realtime/events/)) without changing history or tool execution. There is no `event_stream_handler` parameter on `realtime()`; a handler-style consumer is attached with the [`ProcessEventStream`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.ProcessEventStream) capability, which works through this same stream.

## Model settings and `RunContext`

`get_model_settings()` may run during capability setup, but regular model settings do not configure a realtime model. Pass [`RealtimeModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings) through `realtime(model_settings=...)` instead. Inside session hooks and tools, the [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) reflects the session:

`RunContext` field

Value in a realtime session

[`ctx.model_settings`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.model_settings)

The merged [`RealtimeModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeModelSettings) the session was connected with.

[`ctx.realtime`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.realtime)

`True` for the whole run, including `for_run` and instruction functions that run before the connection exists.

[`ctx.realtime_session`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.realtime_session)

The live [`RealtimeSession`](https://pydantic.dev/docs/ai/api/pydantic-ai/realtime/#pydantic_ai.realtime.RealtimeSession) once it is connected.

Note

`ctx.realtime_session` is still `None` in `before_run`, in instruction functions, and in the pre-handler part of `wrap_run`, which all run before the connection is established.

## Seeded history is not processed

History-processing capabilities do not transform `message_history` before it is [seeded into a session](https://pydantic.dev/docs/ai/realtime/history/#seeding-a-session); preprocess the history before opening the session when filtering or redaction is required.

## Deferred capability loading

Deferred capabilities load in a session the same way they do in a regular run: the capability catalog is part of the session's instructions, and calling the `load_capability` tool returns the loaded capability's instructions as its result -- which works on every provider. What a session cannot do is advertise _new tools_ mid-conversation (the connection's tools are fixed when it opens; see [#7288](https://github.com/pydantic/pydantic-ai/issues/7288)), so opening a session with a `defer_loading=True` capability that contributes tools or native tools raises [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError) before connecting -- accepting it would silently provide less than requested. Realtime per-turn/exchange hooks are expected to widen this boundary in the future; see [#7190](https://github.com/pydantic/pydantic-ai/issues/7190) and [#7191](https://github.com/pydantic/pydantic-ai/issues/7191).

---
