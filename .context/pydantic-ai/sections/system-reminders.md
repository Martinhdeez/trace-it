# [System Reminders](https://pydantic.dev/docs/ai/harness/system-reminders/)

> Re-inject behavioral guidance mid-run -- on a cadence or reactively -- to counter instruction fade, without invalidating the prompt cache.

# System Reminders

`SystemReminders` re-states targeted behavioral guidance partway through a run -- on a fixed cadence or reactively from a condition -- to counter the instruction fade that sets in over many turns, without ever invalidating the prompt cache.

[Source](https://github.com/pydantic/pydantic-ai-harness/tree/main/pydantic_ai_harness/system_reminders/)

> While Pydantic AI Harness is on 0.x releases, the API may change between minor releases; when it does, deprecation warnings and release-note migration guidance tell you (or your agent) exactly how to upgrade. See the [version policy](https://pydantic.dev/docs/ai/harness/#version-policy).

## The problem

Long multi-turn runs suffer instruction fade: after many tool-use turns the model progressively ignores the guidance it was given at the start. A single start-of-session system prompt is not enough for extended work. The fix is to re-state targeted guidance mid-run -- on a fixed cadence, or reactively when a condition is detected.

## The solution

`SystemReminders` injects reminders on each model request, either statically (`Reminder`, on a cadence) or dynamically (a callable that reads the run context). Reminders are appended to the **tail** of the request as an ephemeral `UserPromptPart` behind a `CachePoint`:

-   The injection runs _after_ the durable history is persisted, so the reminder reaches the model but is never written to `message_history`. No reminders accumulate across turns.
-   A `CachePoint` is placed immediately _before_ the reminder, so the cached prefix (tools + system + real conversation) stays byte-identical turn over turn. Only the small reminder falls outside the cache.

Injecting into the system prompt (or any persisted part) instead would sit at the front of the request, so every reminder would bust the cached prefix and stale reminders would pile up in history. This capability avoids both.

## Usage

Construct an `Agent` with `SystemReminders(...)` in its `capabilities`:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import SystemReminders
from pydantic_ai_harness.system_reminders import Reminder

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[
        SystemReminders(
            reminders=[Reminder('Stay focused on the original request.', interval=5)],
        )
    ],
)

result = agent.run_sync('Refactor the auth module and add tests.')
print(result.output)
```

## Static reminders

A `Reminder` fires on a cadence within a run:

Field

Purpose

`content`

The reminder text.

`interval`

Fire every N model requests (`interval=3` fires on the 3rd, 6th, ...).

`first_after`

Request number of the first fire, then every `interval` after. `None` = first multiple of `interval` (plain modulo).

`trigger`

Predicate over `RunContext`. When set, fires only when it returns `True` _and_ the cadence matches.

`max_fires`

Cap the number of fires per run. `None` = no limit.

`tag`

Wrap the content in `<tag>\ncontent\n</tag>`. Defaults to `'system-reminder'`; set `None` for raw content.

The default `tag='system-reminder'` wraps every reminder in `<system-reminder>...</system-reminder>`, following Claude Code's convention so the model reads it as an out-of-band steering note rather than user text.

The `tag` wrapping applies only to static `Reminder` content. Dynamic callables (including `GoalReanchor` and `LLMReminder`) inject their returned text raw and own their own formatting.

## Dynamic reminders

A dynamic reminder is any callable `(RunContext) -> str | None` (sync or async), evaluated on every model request. Return a string to inject, or `None` to skip. This is the general seam for conditions that need run state -- token budget, post-compaction, mode switches -- without hardcoded detectors:

```python
from pydantic_ai_harness import SystemReminders

SystemReminders(
    dynamic_reminders=[
        lambda ctx: 'Wrap up soon.' if ctx.run_step > 20 else None,
    ],
)
```

### `GoalReanchor` -- zero-cost goal anchoring

`GoalReanchor` re-states the run's first user request as the anchor and asks the model to check its next action advances it. No model call, no dependencies:

```python
from pydantic_ai_harness import SystemReminders
from pydantic_ai_harness.system_reminders import GoalReanchor

SystemReminders(dynamic_reminders=[GoalReanchor()])
```

### `LLMReminder` -- model-generated nudges

`LLMReminder` has a model summarize a compact transcript (original goal + recent activity) into a short stay-on-task nudge. It requires an explicit `model` -- there is no default model id -- and falls back to `GoalReanchor` text on any error, so a failed generation never blocks the run:

```python
from pydantic_ai_harness import SystemReminders
from pydantic_ai_harness.system_reminders import LLMReminder

SystemReminders(dynamic_reminders=[LLMReminder(model='anthropic:claude-haiku-4-5')])
```

Dynamic reminders have no cadence of their own -- they run on every model request. `LLMReminder` therefore issues one extra model call per turn (its usage is threaded onto the parent run via `ctx.usage`, so it shows up in `result.usage()`). The nested call also runs under the parent's `usage_limits` with one request held back for the model request it precedes, so the reminder cannot push a run past its `request_limit`; once the budget is that tight the generation is skipped and `GoalReanchor` text is used instead. Because the fallback is silent, a persistently misconfigured `model` (bad id, missing key) looks like normal operation. To bound the cost, gate it behind a cadence with an async wrapper:

```python
_llm = LLMReminder(model='anthropic:claude-haiku-4-5')

async def every_tenth(ctx):
    return await _llm(ctx) if ctx.run_step % 10 == 0 else None

SystemReminders(dynamic_reminders=[every_tenth])
```

Under a durability engine, a `LLMReminder` listed directly in `dynamic_reminders` is a journaled capability operation: replay restores the recorded reminder instead of repeating the model call, and a generation error is recorded as the `GoalReanchor` fallback rather than inheriting the engine's retry policy, so a best-effort reminder cannot stall the run. `SystemReminders` carries the stable default `id='system_reminders'`, so durable recovery works without configuration.

Only a direct entry takes that route. Two shapes do not:

-   A wrapper like `every_tenth` above calls `LLMReminder` from orchestration context, where engines that forbid I/O can fail the call outright.
-   An `LLMReminder` subclass that overrides `__call__` runs that override directly, so it cannot be journaled either.

Without a durability engine, generation runs directly in all three cases, with the same fallback to `GoalReanchor` on error.

## Configuration

Subscribe to `ReminderFiredEvent` to observe reminders after they are appended:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import SystemReminders
from pydantic_ai_harness.system_reminders import Reminder, ReminderFiredEvent

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[SystemReminders(reminders=[Reminder('...', interval=5)])],
)

@agent.on_event(ReminderFiredEvent)
async def record(ctx, event):
    print(event.text)
```

Migration: `on_fire` remains supported but is deprecated. Move its callback body to this subscription.

```python
from pydantic_ai_harness import SystemReminders
from pydantic_ai_harness.system_reminders import Reminder

SystemReminders(
    reminders=[Reminder('...', interval=5)],
    dynamic_reminders=[],       # callables evaluated every request
    cache_ttl='5m',             # TTL for the cache breakpoint before the reminder ('5m' | '1h')
)
```

Per-run state (the request counter and per-reminder fire counts) is isolated via `for_run`, so concurrent runs on the same agent never share fire state.

## Caching guarantee

Reminders are never injected into the system prompt or instructions. They ride the ephemeral tail behind a `CachePoint`, so across turns:

-   the durable history grows append-only and is replayed byte-identically, so the whole prefix stays eligible for a cache hit (subject to the provider's cache TTL -- a gap longer than `cache_ttl` expires the entry even under an unchanged prefix);
-   the reminder and its `CachePoint` live only in the per-request copy, so they can't invalidate anything and aren't persisted.

`CachePoint` is supported on Anthropic, Amazon Bedrock (Converse API), and OpenRouter (Anthropic and Gemini models); on providers without prompt caching it's simply ignored (nothing to bust). The reminder leads with its `CachePoint` only when the request already carries user content for the breakpoint to attach to -- on a turn whose only tail content is the reminder (for example an `instructions`\-only run's first request), the reminder is injected without a breakpoint, since there is no prefix to protect.

## Composition

-   [Planning](https://pydantic.dev/docs/ai/harness/planning/) uses the same ephemeral-tail mechanism to surface the plan. Both compose in one agent: each appends its own tail part behind its own `CachePoint`, and neither is persisted. Note that each ephemeral-tail capability adds a cache breakpoint: Anthropic allows 4 (3 with automatic caching), and core trims the excess oldest-first, so stacking several tail-injecting capabilities alongside `anthropic_cache_instructions` / `anthropic_cache_tool_definitions` can evict an older breakpoint. Two capabilities plus the defaults stay within budget.
-   Loop detection (detect-and-interrupt with a durable nudge) is a separate concern. `SystemReminders` is cadence/condition steering that stays ephemeral; a dynamic reminder can read loop state from your deps if you want to steer on it.

The tail reminder is only appended when the last message in the request is a `ModelRequest` and at least one reminder fires, so a turn where nothing fires adds nothing to the request. Provider-resume turns (where the request tail is a suspended `ModelResponse` that is echoed back verbatim) are skipped and do not consume a cadence slot.

## Not spec-serializable

`SystemReminders.get_serialization_name()` returns `None`: reminders take arbitrary callables, which cannot be serialized to an [agent spec](https://pydantic.dev/docs/ai/core-concepts/agent-spec/).

## Further reading

-   [Pydantic AI capabilities](https://pydantic.dev/docs/ai/capabilities/overview/)
-   [Hooks](https://pydantic.dev/docs/ai/core-concepts/hooks/) -- `wrap_model_request` is the ephemeral injection point used here
-   [Anthropic prompt caching](https://docs.claude.com/en/docs/build-with-claude/prompt-caching)
-   [Planning](https://pydantic.dev/docs/ai/harness/planning/) -- another prompt-cache-aware harness capability

## API reference

### SystemReminders

**Bases:** `AbstractCapability[AgentDepsT]`

Inject periodic or conditional reminders to counter instruction fade in long sessions.

Long multi-turn runs suffer instruction fade: after many tool-use turns the model progressively ignores start-of-session guidance. `SystemReminders` re-injects targeted guidance mid-run, either on a fixed cadence (`Reminder`) or reactively from a callable (`dynamic_reminders`).

Cache safety is the design constraint. Reminders are appended to the _tail_ of each request as an ephemeral `UserPromptPart` behind a `CachePoint`, inside `wrap_model_request` (which runs after core persists the durable history). So reminders reach the model but never enter `message_history`: no stale reminders accumulate, and the cached prefix stays byte-identical across turns -- only the small reminder falls outside the cache. Injecting into the system prompt or a persisted part instead would bust the cache prefix on every fire and let reminders pile up.

```python
from pydantic_ai import Agent
from pydantic_ai_harness.system_reminders import SystemReminders, Reminder

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[
        SystemReminders(
            reminders=[Reminder('Stay focused on the original request.', interval=5)],
        )
    ],
)
```

#### Attributes

##### reminders

Static reminders injected on a cadence.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`Reminder`\[`AgentDepsT`\]\] **Default:** `()`

##### dynamic\_reminders

Callables evaluated every model request; return text to inject or `None` to skip.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`DynamicReminder`\[`AgentDepsT`\] | `AsyncDynamicReminder`\[`AgentDepsT`\]\] **Default:** `()`

##### cache\_ttl

TTL for the cache breakpoint placed before the tail reminder.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['5m', '1h'\] **Default:** `'5m'`

##### on\_fire

Deprecated callback invoked with each rendered reminder. Subscribe to `ReminderFiredEvent` instead.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], [`None`](https://docs.python.org/3/builtins/constants.html#None)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### for\_run

`@async`

```python
def for_run(ctx: RunContext[AgentDepsT]) -> SystemReminders[AgentDepsT]
```

Return a fresh per-run instance with reset counters (config preserved).

The clone resets `_request_count` and `_fire_counts`, so concurrent runs on the same agent do not share fire state.

###### Returns

`SystemReminders`\[`AgentDepsT`\]

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

Append fired reminders to the request tail behind a cache breakpoint, then call the model.

Runs after core persists the durable history; the per-request message list mutated here is never written back, so the reminder and its `CachePoint` reach the model but never enter `ctx.state.message_history`.

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

##### get\_serialization\_name

`@classmethod`

```python
def get_serialization_name(cls) -> str | None
```

Not spec-serializable: reminders take arbitrary callables.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### Reminder

**Bases:** `Generic[AgentDepsT]`

A static reminder injected on a cadence during an agent run.

#### Attributes

##### content

The reminder text.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### interval

Fire every N model requests within a run. `interval=3` fires on the 3rd, 6th, 9th, ... request.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `1`

##### first\_after

Request number of the first fire. `None` (the default) fires on the first multiple of `interval` (plain modulo). When set, the reminder fires at `first_after`, then every `interval` requests after that.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### trigger

Optional predicate over the current `RunContext`. When set, the reminder fires only when the trigger returns `True` _and_ the cadence condition is met.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]\], [`bool`](https://docs.python.org/3/builtins/functions.html#bool)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_fires

Maximum number of times this reminder may fire within a run. `None` means no limit.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tag

When set, wrap the content in an XML tag: `<tag>\ncontent\n</tag>`. Defaults to `'system-reminder'` (Claude Code's convention); set `None` to emit the raw content.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `'system-reminder'`

### GoalReanchor

**Bases:** `Generic[AgentDepsT]`

Zero-cost dynamic reminder that re-states the run's first user request as the anchor.

No model call and no dependencies: it reads the first user message from `ctx.messages` and asks the model to check its next action advances that goal. Falls back to a static line when there is no user message yet. Add it to `SystemReminders.dynamic_reminders`.

### LLMReminder

**Bases:** `Generic[AgentDepsT]`

Dynamic reminder whose text a model generates from a compact transcript.

Opt-in and dependency-free (it uses `pydantic_ai.Agent`). `model` is required and has no default -- pass an explicit model. On any error it falls back to `GoalReanchor` text, so a failed generation never blocks the run. Add it to `SystemReminders.dynamic_reminders`.

Like every dynamic reminder it is evaluated on every model request, so it issues one extra model call per turn; its usage is threaded onto the parent run (`ctx.usage`) and it runs under the parent's `usage_limits` minus one reserved request, so the reminder cannot push a run past its `request_limit`. Once the budget is that tight the generation is skipped and `GoalReanchor` text is used instead. Gate it on a cadence (see the docs) if per-turn generation is too costly.

When owned by `SystemReminders`, generation is a journaled capability operation under a durability engine. Replay restores the generated text instead of repeating the model call.

---
