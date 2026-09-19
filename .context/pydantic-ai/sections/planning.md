# [Planning](https://pydantic.dev/docs/ai/harness/planning/)

> Give an agent a structured, self-updating task list -- with a cache-safe live reminder, optional persistence, subtasks, dependencies, and events.

# Planning

`Planning` gives the model a structured, self-updating task list through a small toolset -- and surfaces the current plan back to the model every turn without ever invalidating the prompt cache. It can stay in memory for a single run or persist to SQLite/Postgres, break steps into subtasks with dependencies, and emit events from granular changes.

[Source](https://github.com/pydantic/pydantic-ai-harness/tree/main/pydantic_ai_harness/planning/)

> This capability incorporates the task-list features of the standalone [`pydantic-ai-todo`](https://github.com/vstorm-co/pydantic-ai-todo) library -- persistent stores, subtasks, dependencies, and events -- which it supersedes. If you are migrating from `pydantic-ai-todo`, the tools are renamed:
> 
> `pydantic-ai-todo`
> 
> `Planning`
> 
> `write_todos`
> 
> `write_plan`
> 
> `read_todos`
> 
> `read_plan`
> 
> `add_todo`
> 
> `add_task`
> 
> `update_todo_status` / `update_todo_statuses`
> 
> `update_task_status` / `update_task_statuses`
> 
> `remove_todo`
> 
> `remove_task`
> 
> `add_subtask`, `set_dependency`, `get_available_tasks`
> 
> unchanged
> 
> Two differences to plan for: there is no connection-string convenience (`create_storage(backend=...)` and friends are gone -- you construct your own asyncpg pool or Redis client, which is what keeps the harness driver-free), and `PlanEvent` carries no `timestamp`, so a consumer that ordered or logged by it supplies its own clock.

> While Pydantic AI Harness is on 0.x releases, the API may change between minor releases; when it does, deprecation warnings and release-note migration guidance tell you (or your agent) exactly how to upgrade. See the [version policy](https://pydantic.dev/docs/ai/harness/#version-policy).

## The problem

Long agentic runs drift: the model loses track of what it set out to do and what's left. The usual fix -- keep a running plan and re-inject it into the system prompt each turn -- invalidates the prompt cache. The system prompt sits at the front of the request, so every plan edit changes the cached prefix and forces the whole conversation to be re-processed at full token price.

## The solution

The model owns the plan through the `planning` toolset. The current plan is surfaced back as an ephemeral reminder appended to the tail of each request, with the single cache breakpoint anchored on the last durable user content:

-   The reminder is added after the durable history is persisted, so it reaches the model but is never written to `message_history`. No reminders accumulate across turns.
-   The `CachePoint` sits on the last durable user content, so the prefix it saves is a prefix of the next request and cache hits survive turn over turn. The reminder carries no breakpoint, so re-sending its mutable content never invalidates the cache.

As with all capability cache breakpoints, provider mapping applies: OpenAI models only receive the `CachePoint` when the model profile enables explicit cache control, and with no durable user content to anchor on the reminder is sent without a breakpoint.

Note that the anchor lands on the last `UserPromptPart` present in the request. A capability listed before `Planning` that appends user content each request (for example `SystemReminders`) displaces the anchor onto that part, so the prefix stays cache-stable only while that content is stable across turns.

## Usage

Construct an `Agent` with `Planning()` in its `capabilities`. The tools are registered automatically and static usage guidance is added to the system prompt:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import Planning

agent = Agent('anthropic:claude-sonnet-4-6', capabilities=[Planning()])

result = agent.run_sync('Refactor the auth module and add tests.')
print(result.output)
```

## The tools

Tool

Purpose

`write_plan(items)`

Create or replace the full plan (whole-list replacement).

`read_plan()`

Read the current plan with step ids and a progress summary.

`add_task(content, active_form)`

Append a single `pending` step.

`update_task_status(task_id, status)`

Move one step between statuses by id.

`update_task_statuses(updates)`

Apply several status changes in one call, validated all-or-nothing.

`remove_task(task_id)`

Delete a step by id.

Each step is a `content` string, an optional present-continuous `active_form` label, and a `status` (`pending`, `in_progress`, `completed`, `cancelled`). The convention -- stated in the guidance and the tools' replies -- is to keep exactly one step `in_progress`.

All six are registered by default. `tools=` narrows that to an allowlist, and the built-in guidance follows it:

```python
from pydantic_ai_harness import Planning

planning = Planning(tools=['write_plan'])  # whole-plan replacement only -- one tool, no step ids to track
```

Naming a tool the current mode does not register raises `ValueError`, as does an unknown key in `descriptions`.

### Subtasks and dependencies

Pass `enable_subtasks=True` to add three more tools, the `blocked` status, and a `hierarchical` view in `read_plan`:

Tool

Purpose

`add_subtask(parent_id, content, active_form)`

Add a child step under a parent.

`set_dependency(task_id, depends_on_id)`

Make one step wait for another; the dependent step is auto-`blocked` until its prerequisite is resolved (completed or cancelled). Self-dependencies, cycles, and duplicates are rejected.

`get_available_tasks()`

List steps with no incomplete dependencies -- the ones that can start now.

`parent_id`, `depends_on`, and the `blocked` status are rejected by `write_plan` unless `enable_subtasks` is set: without the subtask tools nothing reconciles a dependency and no view renders the hierarchy, so storing them would be a write the plan does not reflect.

## Persistence

By default the plan is a fresh, isolated in-memory plan per run. Pass a `store` to persist it:

```python
from pydantic_ai_harness import Planning
from pydantic_ai_harness.planning import SqlitePlanStore

planning = Planning(store=SqlitePlanStore('plan.db', session='user-123'))
```

Built-in stores are `InMemoryPlanStore`, `SqlitePlanStore`, `PostgresPlanStore` (over a caller-owned asyncpg pool), and `RedisPlanStore` (over a caller-owned `redis.asyncio` client) -- so the harness needs no database driver. Any `PlanStore` implementation works, and `store_resolver` selects one per run. `SqlitePlanStore` requires a file-backed database; use `InMemoryPlanStore` for ephemeral plans rather than `':memory:'`.

The tail reminder reads the store on every model request, so a store that raises fails the run rather than degrading -- the reminder is not best-effort. That is deliberate: a plan the model can no longer see is not a state to continue running in silently. Retry and fallback policy belongs to the store, not to `Planning`, and `PlanStore` is a protocol precisely so you can wrap one:

```python
class BestEffort:
    """Serve the last known plan when the backing store is unreachable."""

    def __init__(self, inner: PlanStore) -> None:
        self._inner, self._last = inner, []

    async def get_items(self) -> list[PlanItem]:
        try:
            self._last = await self._inner.get_items()
        except ConnectionError:
            pass
        return self._last

    # ... delegate the other five methods to `self._inner`
```

### Planning and executing in separate runs

A shared store is the whole handoff mechanism between two runs. One agent writes the plan, a second one executes it, and the plan is the only state that crosses between them:

```python
store = SqlitePlanStore('plan.db', session='issue-403')

planner = Agent('anthropic:claude-opus-4-7', capabilities=[Planning(store=store)])
executor = Agent('anthropic:claude-sonnet-4-6', capabilities=[Planning(store=store)])

await planner.run('Investigate the issue and write a plan. Do not implement anything.')
await executor.run('Implement the plan.')
```

The executor starts with no `message_history`, so it never pays for the planner's investigation. Its first request carries only the new prompt plus the plan reminder, which the capability rebuilds from the store. That is why the two agents can run on different models: a large-context model can do the reading and the reasoning, and a smaller one can execute against the resulting checklist.

The planner's read-only discipline is a property of how you configure that agent (which toolsets it gets, and what its instructions say), not something the capability enforces.

## Events

Subscribe to typed plan events to react to changes made through the `Planning` tools:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import Planning
from pydantic_ai_harness.planning import PlanCompletedEvent

agent = Agent('anthropic:claude-sonnet-4-6', capabilities=[Planning()])

@agent.on_event(PlanCompletedEvent)
async def announce(ctx, event):
    print('done:', event.item.content)
```

The family contains `PlanCreatedEvent`, `PlanUpdatedEvent`, `PlanStatusChangedEvent`, `PlanCompletedEvent`, and `PlanDeletedEvent`; each carries the affected `item` and, for updates, `previous_state`.

Run events come from planning tool paths, including `write_plan`. Direct application mutations on a `PlanStore` have no run context and do not produce run events. `PlanEventEmitter`, `EventCallback`, and store `event_emitter` parameters remain supported but are deprecated.

## Why whole-plan replacement

Addressing steps by mutable integer index (insert/remove/reorder) is error-prone for both the code and the model. `write_plan` restates the whole plan each call, so there are no indices to track. Granular edits (`add_task`, `update_task_status`, `remove_task`) instead reference the stable `id` shown by `read_plan`.

## Caching guarantee

The plan is never injected into the system prompt or instructions. Static usage guidance goes there (cache-stable); only the mutable plan rides the ephemeral tail reminder, which lives solely in the per-request copy and is never persisted. Set `inject=False` to disable it. Pydantic AI maps `CachePoint` for models whose profiles support prompt caching; on other models it is ignored.

With a durable-execution capability attached, the plan read used to build that reminder is a journaled capability operation. Replay reuses the recorded plan instead of reading the store again. `Planning` carries the stable default `id='planning'`, so durable recovery works without configuration.

## Configuration

```python
from pydantic_ai_harness import Planning

Planning(
    guidance=None,           # static system-prompt guidance; None = default, '' = omit
    cache_ttl='5m',          # TTL for the cache breakpoint anchored on the last durable user content ('5m' | '1h')
    store=None,              # None = fresh in-memory plan per run; or a PlanStore to persist
    enable_subtasks=False,   # add subtask/dependency tools and the 'blocked' status
    inject=True,             # surface the current plan as a cache-safe tail reminder
    tools=None,              # None = every tool the mode registers; or an allowlist of names
    descriptions=None,       # optional per-tool description overrides, keyed by tool name
)
```

## Agent spec (YAML/JSON)

`Planning` works with Pydantic AI's [agent spec](https://pydantic.dev/docs/ai/core-concepts/agent-spec/):

```yaml
# agent.yaml
model: anthropic:claude-sonnet-4-6
capabilities:
  - Planning: {}
```

```python
from pydantic_ai import Agent
from pydantic_ai_harness import Planning

agent = Agent.from_file('agent.yaml', custom_capability_types=[Planning])
result = agent.run_sync('...')
print(result.output)
```

## Further reading

-   [Pydantic AI capabilities](https://pydantic.dev/docs/ai/capabilities/overview/)
-   [Anthropic prompt caching](https://docs.claude.com/en/docs/build-with-claude/prompt-caching)
-   [Code Mode](https://pydantic.dev/docs/ai/harness/code-mode/) -- another prompt-cache-aware harness capability

## API reference

### Planning

**Bases:** `AbstractCapability[AgentDepsT]`

Structured task planning that never invalidates the prompt cache.

The model owns the plan through a small toolset (`write_plan`, `read_plan`, `add_task`, `update_task_status`, `update_task_statuses`, `remove_task`, and -- when `enable_subtasks` is set -- `add_subtask`, `set_dependency`, `get_available_tasks`); `tools` narrows that surface to an allowlist. The current plan is surfaced back as an _ephemeral_ reminder appended to the tail of each request. A single `CachePoint` is anchored on the last durable user content, so the prefix it saves is a prefix of the next request; the reminder itself carries no breakpoint, so only the mutable plan content is re-read each turn.

By default the plan lives in memory for the duration of a single run (a fresh, isolated plan per run). Pass a `store` (or `store_resolver`) to persist it -- e.g. `SqlitePlanStore` or `PostgresPlanStore`.

```python
from pydantic_ai import Agent
from pydantic_ai_harness.planning import Planning

agent = Agent('anthropic:claude-sonnet-4-6', capabilities=[Planning()])
```

#### Attributes

##### guidance

Static planning guidance for the system prompt. Cache-stable.

Three states, so opting out is something you do on purpose rather than by accident:

-   `None` (the default): use the built-in guidance.
-   `''`: no guidance at all.
-   any other string: use it instead of the built-in guidance.

A single `str | None` where `None` meant "no guidance" would leave no way to ask for the default explicitly, and would turn a config that resolves to `None` into a silent opt-out. This matches `memory`, `exa` and `runtime_authoring`, which read the same way.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### cache\_ttl

TTL for the cache breakpoint anchored on the last durable user content.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['5m', '1h'\] **Default:** `'5m'`

##### store

Storage backend. `None` keeps a fresh in-memory plan per run (the original ephemeral behaviour). Pass a store to persist the plan across runs.

**Type:** `PlanStore` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### store\_resolver

Optional per-run store resolver, e.g. `lambda ctx: ctx.deps.plan_store`.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]\], `PlanStore`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### enable\_subtasks

Add the subtask/dependency tools and the `blocked` status when true.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### inject

Surface the current plan as an ephemeral tail reminder each turn.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### tools

Optional allowlist of tool names to register; `None` registers all of them.

The full surface is `write_plan`, `read_plan`, `add_task`, `update_task_status`, `update_task_statuses`, `remove_task`, plus `add_subtask`, `set_dependency` and `get_available_tasks` under `enable_subtasks`. `tools=['write_plan']` is the smallest useful plan surface. Naming a tool this mode does not register raises `ValueError`.

The built-in `guidance` follows the allowlist for the whole-plan/granular/subtask split; trimming within a group is better paired with a `guidance` string of your own.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### descriptions

Optional per-tool description overrides, keyed by tool name. Unknown names raise `ValueError`.

**Type:** [`dict`](https://docs.python.org/3/reference/expressions.html#dict)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### for\_run

`@async`

```python
def for_run(ctx: RunContext[AgentDepsT]) -> Planning[AgentDepsT]
```

Return a clone with this run's store resolved and cached (per-run isolation).

###### Returns

`Planning`\[`AgentDepsT`\]

##### resolve\_store

```python
def resolve_store(ctx: RunContext[AgentDepsT]) -> PlanStore
```

Return the cached run store, or resolve one for direct toolset use.

###### Returns

`PlanStore`

##### get\_toolset

```python
def get_toolset() -> AgentToolset[AgentDepsT] | None
```

Provide the `planning` toolset over this run's resolved store.

###### Returns

[`AgentToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AgentToolset)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_instructions

```python
def get_instructions() -> AgentInstructions[AgentDepsT] | None
```

Provide static, cache-stable guidance on using the planning tools.

A custom `guidance` string is used verbatim. The default is assembled from the tools actually registered -- the granular sentence is dropped when `tools` excludes them all, and the subtask/dependency workflow is added under `enable_subtasks` -- so the model is not told about tools it lacks.

###### Returns

`AgentInstructions`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### wrap\_model\_request

`@async`

```python
def wrap_model_request(
    ctx: RunContext[AgentDepsT],
    *,
    request_context: ModelRequestContext,
    handler: WrapModelRequestHandler,
) -> ModelResponse
```

Anchor a cache breakpoint on durable user content, then append the ephemeral plan reminder.

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

##### from\_spec

`@classmethod`

```python
def from_spec(
    cls,
    *,
    backend: Literal['memory', 'sqlite'] = 'memory',
    database: str = '.agent-plan.db',
    session: str = 'default',
    enable_subtasks: bool = False,
    inject: bool = True,
    guidance: str | None = None,
    cache_ttl: Literal['5m', '1h'] = '5m',
    tools: list[str] | None = None,
) -> Planning[AgentDepsT]
```

Construct a `Planning` capability from serializable options.

###### Returns

`Planning`\[`AgentDepsT`\]

##### get\_serialization\_name

`@classmethod`

```python
def get_serialization_name(cls) -> str | None
```

Serialization name for agent-spec support.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

---
