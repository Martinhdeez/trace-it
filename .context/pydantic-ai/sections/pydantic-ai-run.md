# [pydantic_ai.run](https://pydantic.dev/docs/ai/api/pydantic-ai/run/)

# pydantic\_ai.run

### AgentRun

**Bases:** `Generic[AgentDepsT, OutputDataT]`

A stateful, async-iterable run of an [`Agent`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent).

You generally obtain an `AgentRun` instance by calling `async with my_agent.iter(...) as agent_run:`.

Once you have an instance, you can use it to iterate through the run's nodes as they execute. When an [`End`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.End) is reached, the run finishes and [`result`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.result) becomes available.

Example:

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')

async def main():
    nodes = []
    # Iterate through the run, recording each node along the way:
    async with agent.iter('What is the capital of France?') as agent_run:
        async for node in agent_run:
            nodes.append(node)
    print(nodes)
    '''
    [
        UserPromptNode(
            user_prompt='What is the capital of France?',
            instructions_functions=[],
            system_prompts=(),
            system_prompt_functions=[],
            system_prompt_dynamic_functions={},
        ),
        ModelRequestNode(
            request=ModelRequest(
                parts=[
                    UserPromptPart(
                        content='What is the capital of France?',
                        timestamp=datetime.datetime(...),
                    )
                ],
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        CallToolsNode(
            model_response=ModelResponse(
                parts=[TextPart(content='The capital of France is Paris.')],
                usage=RequestUsage(
                    cost=Decimal('0.000196'), input_tokens=56, output_tokens=7
                ),
                model_name='gpt-5.2',
                timestamp=datetime.datetime(...),
                run_id='...',
                conversation_id='...',
            )
        ),
        End(data=FinalResult(output='The capital of France is Paris.')),
    ]
    '''
    print(agent_run.result.output)
    #> The capital of France is Paris.
```

You can also manually drive the iteration using the [`next`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.next) method for more granular control.

#### Attributes

##### ctx

The current context of the agent run.

**Type:** `GraphRunContext`\[`_agent_graph.GraphAgentState`, `_agent_graph.GraphAgentDeps`\[`AgentDepsT`, [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]\]

##### next\_node

The next node that will be run in the agent graph.

This is the next node that will be used during async iteration, or if a node is not passed to `self.next(...)`.

**Type:** `_agent_graph.AgentNode`\[`AgentDepsT`, `OutputDataT`\] | `End`\[`FinalResult`\[`OutputDataT`\]\]

##### result

The final result of the run if it has ended, otherwise `None`.

Once the run returns an [`End`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.End) node, `result` is populated with an [`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult).

**Type:** [`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[`OutputDataT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### usage

Get usage statistics for the run so far, including token usage, model requests, and so on.

**Type:** `_usage.RunUsage`

##### metadata

Metadata associated with this agent run, if configured.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### run\_id

The unique identifier for the agent run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### conversation\_id

The unique identifier for the conversation this run belongs to.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### pending\_messages

Internal: live view of the queue mutated by `enqueue` and drained by the internal `PendingMessageDrainCapability`.

Exposed for inspection / debugging; use [`enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.enqueue) to add messages.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`PendingMessage`\]

#### Methods

##### all\_messages

```python
def all_messages() -> list[_messages.ModelMessage]
```

Return all messages for the run so far.

Messages from older runs are included.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\]

##### all\_messages\_json

```python
def all_messages_json(*, output_tool_return_content: str | None = None) -> bytes
```

Return all messages from [`all_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.all_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the messages.

##### new\_messages

```python
def new_messages() -> list[_messages.ModelMessage]
```

Return the messages produced during this run so far.

Messages provided via `message_history` and messages from older runs are excluded.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\]

##### new\_messages\_json

```python
def new_messages_json() -> bytes
```

Return new messages from [`new_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.new_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the new messages.

##### \_\_aiter\_\_

```python
def __aiter__(

) -> AsyncIterator[_agent_graph.AgentNode[AgentDepsT, OutputDataT] | End[FinalResult[OutputDataT]]]
```

Provide async-iteration over the nodes in the agent run.

###### Returns

[`AsyncIterator`](https://docs.python.org/3/library/typing.html#typing.AsyncIterator)\[`_agent_graph.AgentNode`\[`AgentDepsT`, `OutputDataT`\] | `End`\[`FinalResult`\[`OutputDataT`\]\]\]

##### \_\_anext\_\_

`@async`

```python
def __anext__(

) -> _agent_graph.AgentNode[AgentDepsT, OutputDataT] | End[FinalResult[OutputDataT]]
```

Advance to the next node automatically based on the last returned node.

Yields each node before it runs, ending with the [`End`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.End) node. Advancing goes through [`next()`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.next), so capability hooks fire exactly as they do for [`agent.run()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run).

###### Returns

`_agent_graph.AgentNode`\[`AgentDepsT`, `OutputDataT`\] | `End`\[`FinalResult`\[`OutputDataT`\]\]

##### next

`@async`

```python
def next(
    node: _agent_graph.AgentNode[AgentDepsT, OutputDataT],
) -> _agent_graph.AgentNode[AgentDepsT, OutputDataT] | End[FinalResult[OutputDataT]]
```

Manually drive the agent run by passing in the node you want to run next.

This lets you inspect or mutate the node before continuing execution, or skip certain nodes under dynamic conditions. The agent run should be stopped when you return an [`End`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.End) node.

Example:

```python
from pydantic_ai import Agent
from pydantic_graph import End

agent = Agent('openai:gpt-5.2')

async def main():
    async with agent.iter('What is the capital of France?') as agent_run:
        next_node = agent_run.next_node  # start with the first node
        nodes = [next_node]
        while not isinstance(next_node, End):
            next_node = await agent_run.next(next_node)
            nodes.append(next_node)
        # Once `next_node` is an End, we've finished:
        print(nodes)
        '''
        [
            UserPromptNode(
                user_prompt='What is the capital of France?',
                instructions_functions=[],
                system_prompts=(),
                system_prompt_functions=[],
                system_prompt_dynamic_functions={},
            ),
            ModelRequestNode(
                request=ModelRequest(
                    parts=[
                        UserPromptPart(
                            content='What is the capital of France?',
                            timestamp=datetime.datetime(...),
                        )
                    ],
                    timestamp=datetime.datetime(...),
                    run_id='...',
                    conversation_id='...',
                )
            ),
            CallToolsNode(
                model_response=ModelResponse(
                    parts=[TextPart(content='The capital of France is Paris.')],
                    usage=RequestUsage(
                        cost=Decimal('0.000196'), input_tokens=56, output_tokens=7
                    ),
                    model_name='gpt-5.2',
                    timestamp=datetime.datetime(...),
                    run_id='...',
                    conversation_id='...',
                )
            ),
            End(data=FinalResult(output='The capital of France is Paris.')),
        ]
        '''
        print('Final result:', agent_run.result.output)
        #> Final result: The capital of France is Paris.
```

###### Returns

`_agent_graph.AgentNode`\[`AgentDepsT`, `OutputDataT`\] | `End`\[`FinalResult`\[`OutputDataT`\]\] -- The next node returned by the graph logic, or an [`End`](https://pydantic.dev/docs/ai/api/pydantic_graph/basenode/#pydantic_graph.basenode.End) node if `_agent_graph.AgentNode`\[`AgentDepsT`, `OutputDataT`\] | `End`\[`FinalResult`\[`OutputDataT`\]\] -- the run has completed.

###### Parameters

**`node`** : `_agent_graph.AgentNode`\[`AgentDepsT`, `OutputDataT`\]

The node to run next in the graph.

##### emit

`@async`

```python
def emit(event: CustomEventT, /) -> CustomEventT
```

Emit a [`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent) into this run's event stream.

Lets code driving [`Agent.iter`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.iter) inject application-defined events (e.g. from an external harness or event bus) into the stream, alongside events emitted from tools via [`RunContext.emit`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.emit). The event surfaces on the next pull from the run's node stream.

Designed to be called from the same event loop driving `agent.iter()`. If you're forwarding events from a different thread, submit the coroutine to the agent's loop (e.g. `asyncio.run_coroutine_threadsafe(agent_run.emit(event), loop)`).

###### Returns

`CustomEventT` -- The event as emitted.

###### Parameters

**`event`** : `CustomEventT`

The [`CustomEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CustomEvent) to emit.

###### Raises

-   `UserError` -- If the run has already ended (no stream remains to deliver the event), or if passed a [`CapabilityEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.CapabilityEvent): those belong to capabilities, and code driving the run is application code.

##### enqueue

```python
def enqueue(
    *content: EnqueueContent,
    priority: PendingMessagePriority = 'asap',
) -> str | None
```

Enqueue content to be injected into the conversation.

Designed to be called from the same event loop driving `agent.iter()`. If you're forwarding events from a different thread (e.g. a webhook handler running on its own loop or thread), marshal the call back onto the agent's loop first (e.g. `loop.call_soon_threadsafe(agent_run.enqueue, msg)`). The drain's `queue[:] = remaining` pattern in `_drain_by_priority` isn't atomic against concurrent appends from a different thread.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- The `enqueue_id` of the queued message, echoed on the [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- [`EnqueuedMessagesEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.EnqueuedMessagesEvent) emitted when it's [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) -- delivered, or `None` when there was nothing to enqueue (an empty call).

###### Parameters

**`*content`** : `EnqueueContent` _Default:_ `()`

One or more [`EnqueueContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.EnqueueContent) items. Adjacent [`UserContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserContent) (a `str` or multi-modal content like an [`ImageUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ImageUrl)) is gathered into one [`UserPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserPromptPart), and each [`ModelRequestPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequestPart) (e.g. a [`SystemPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SystemPromptPart)) is coalesced with adjacent part-style items into one [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest); a complete [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest) or [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse) is kept as its own message. The assembled sequence must end in a request. Calling with no positional args is a no-op.

**`priority`** : `PendingMessagePriority` _Default:_ `'asap'`

When to deliver: `'asap'` (default) -- at the earliest opportunity (next model request, or a redirect if the agent would otherwise end). `'when_idle'` -- only when the agent would otherwise end, after `'asap'` messages.

##### cancel

```python
def cancel() -> None
```

Cancel the whole agent run.

The run stops what it is doing -- the in-flight model request is torn down, in-flight tool tasks are cancelled and drained, a suspended server-side job is best-effort cancelled -- and the code driving the run sees `asyncio.CancelledError`. When the `agent.iter()` context exits, this becomes [`RunCancelled`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled) (including for `agent.run()`, which wraps `iter()`). Everything that completed before the cancellation took effect is preserved in message history. [`RunCancelled.all_messages()`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.RunCancelled.all_messages) returns a complete snapshot that can be passed to a new run as `message_history` to resume the conversation.

Cancellation is terminal: capability hooks (`wrap_run`, `wrap_node_run`, `on_run_error`) may observe it and clean up, but cannot recover the run into a successful result.

Unlike [`StreamedRunResult.cancel()`](https://pydantic.dev/docs/ai/api/pydantic-ai/result/#pydantic_ai.result.StreamedRunResult.cancel), which only stops the current model response and lets the run continue, this ends the run itself.

Safe to call from another task or thread (e.g. a TUI's key handler while the run is awaited elsewhere). Idempotent; a no-op once the run has finished -- where "finished" means the `agent.iter()`/`agent.run()` context has exited. A `cancel()` issued inside the context after the run has already produced its result (e.g. after iterating to `End`) is still honored and surfaces as `RunCancelled` on exit, so that a hook running at context exit (like `after_run`) can still cancel the run; only after the context has exited is `cancel()` a true no-op. Externally cancelling the task running the agent (`asyncio.Task.cancel()`) remains supported and keeps raising `asyncio.CancelledError` instead; when both happen, the external cancellation wins.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### AgentRunResult

**Bases:** `Generic[OutputDataT]`

The final result of an agent run.

#### Attributes

##### output

The output data from the agent run.

**Type:** `OutputDataT`

##### response

Return the last response from the message history.

**Type:** `_messages.ModelResponse`

##### usage

Return the usage of the whole run.

**Type:** `_usage.RunUsage`

##### timestamp

Return the timestamp of last response.

**Type:** [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)

##### metadata

Metadata associated with this agent run, if configured.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### run\_id

The unique identifier for the agent run.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### conversation\_id

The unique identifier for the conversation this run belongs to.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

#### Methods

##### all\_messages

```python
def all_messages(
    *,
    output_tool_return_content: str | None = None,
) -> list[_messages.ModelMessage]
```

Return the history of \_messages.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\] -- List of messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### all\_messages\_json

```python
def all_messages_json(*, output_tool_return_content: str | None = None) -> bytes
```

Return all messages from [`all_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult.all_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### new\_messages

```python
def new_messages(
    *,
    output_tool_return_content: str | None = None,
) -> list[_messages.ModelMessage]
```

Return the messages produced during this run.

Messages provided via `message_history` and messages from older runs are excluded.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[`_messages.ModelMessage`\] -- List of new messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

##### new\_messages\_json

```python
def new_messages_json(*, output_tool_return_content: str | None = None) -> bytes
```

Return new messages from [`new_messages`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult.new_messages) as JSON bytes.

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes) -- JSON bytes representing the new messages.

###### Parameters

**`output_tool_return_content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The return content of the tool call to set in the last message. This provides a convenient way to modify the content of the output tool call if you want to continue the conversation and want to set the response to the output tool call. If `None`, the last message will not be modified.

### AgentRunResultEvent

**Bases:** `Generic[OutputDataT]`

An event indicating the agent run ended and containing the final result of the agent run.

#### Attributes

##### result

The result of the run.

**Type:** [`AgentRunResult`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRunResult)\[`OutputDataT`\]

##### event\_kind

Event type identifier, used as a discriminator.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['agent\_run\_result'\] **Default:** `'agent_run_result'`

### EnqueueContent

A single item accepted by [`RunContext.enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue) and [`AgentRun.enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.enqueue).

`enqueue` is variadic, so each item is one positional argument:

-   [`UserContent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserContent) (a `str` or a piece of multi-modal content like an [`ImageUrl`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ImageUrl)): adjacent user content is gathered into a single [`UserPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserPromptPart), so `enqueue('caption', image)` forms one user turn. To pass an existing list, spread it: `enqueue(*items)`.
-   [`ModelRequestPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequestPart) (e.g. a [`SystemPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.SystemPromptPart)): included verbatim.
-   [`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage) (a complete [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest) or [`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)): emitted as its own message.

Consecutive part-style items (user content and `ModelRequestPart`s) are coalesced into a single `ModelRequest`; complete `ModelMessage`s stay separate. This lets one `enqueue` call inject an interleaved exchange (e.g. a synthetic tool call + result -- a `ModelResponse` followed by a `ModelRequest`). The assembled sequence must end in a `ModelRequest` so the agent has something to respond to.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `'UserContent | ModelRequestPart | ModelMessage'`

### PendingMessage

One or more [`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)s queued for injection into the agent conversation.

Enqueued via [`RunContext.enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue) or [`AgentRun.enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/run/#pydantic_ai.run.AgentRun.enqueue) and automatically drained at the appropriate time during the agent run by the internal `PendingMessageDrainCapability`.

#### Attributes

##### messages

The message(s) to inject, in order. Always ends in a [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest).

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### priority

When to deliver these messages:

-   `'asap'`: at the earliest opportunity (next model request, or redirect if the agent would otherwise terminate).
-   `'when_idle'`: only when the agent would otherwise terminate, after `'asap'` messages.

**Type:** `PendingMessagePriority` **Default:** `'asap'`

##### enqueue\_id

Unique identifier for this enqueue call, surfaced on the [`EnqueuedMessagesEvent`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.EnqueuedMessagesEvent) emitted when the messages are delivered, and returned by [`enqueue`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext.enqueue).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `field(default_factory=(lambda: str(uuid7())))`

#### Methods

##### from\_content

`@classmethod`

```python
def from_content(
    cls,
    *content: EnqueueContent,
    priority: PendingMessagePriority = 'asap',
) -> PendingMessage | None
```

Build a `PendingMessage` from `enqueue` arguments, or `None` when there's nothing to send.

Returns `None` for an empty call (enqueueing nothing is a no-op rather than an error).

###### Returns

`PendingMessage` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Raises

-   `UserError` -- If the assembled messages don't end in a [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest) -- e.g. a lone `ModelResponse` -- since the agent needs a request to respond to.

### PendingMessagePriority

When to deliver a pending message.

-   `'asap'`: Delivered at the earliest opportunity -- either prepended to the next [`ModelRequest`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelRequest), or, if the agent would otherwise terminate before another request, used to redirect the run into one more request.
-   `'when_idle'`: Delivered only when the agent would otherwise terminate, after any `'asap'` messages. Doesn't interrupt in-flight work.

**Type:** [`TypeAlias`](https://docs.python.org/3/library/typing.html#typing.TypeAlias) **Default:** `Literal['asap', 'when_idle']`

---
