# [Spend](https://pydantic.dev/docs/ai/harness/spend/)

> Track what an agent costs and refuse the next request once a budget is spent, with windows longer than a run, per-tenant scopes, and a counter shared across worker processes.

# Spend

Track what an agent costs, and stop it when a budget is gone.

> While Pydantic AI Harness is on 0.x releases, the API may change between minor releases; when it does, deprecation warnings and release-note migration guidance tell you (or your agent) exactly how to upgrade. See the [version policy](https://pydantic.dev/docs/ai/harness/#version-policy).

## The problem

A loop that calls a model until a condition it never reaches will keep calling until something stops it. `UsageLimits` in Pydantic AI is that stop for one run: it caps tokens, requests and cost for the duration of a single `run()`. What it does not cover is a period longer than one run, a per-tenant share of a shared allowance, or a counter that several worker processes agree on. A daily ceiling spread across a queue's workers is exactly the case where each worker independently believes it has the whole budget.

Provider usage APIs do not close that gap. They are billing and observability pipelines: usage is aggregated after the fact and read by polling, so a number there moves only once the requests behind it have already been made. That is enough to reconcile a ledger and not enough to refuse the request a runaway loop is about to make.

## The solution

`SpendLimits` prices every model response with [`ModelResponse.cost()`](https://pydantic.dev/docs/ai/api/messages/), adds it to each window you configure, and refuses the next request once a window is spent.

```python
from decimal import Decimal

from pydantic_ai import Agent
from pydantic_ai_harness import SpendLimits
from pydantic_ai_harness.spend import Budget

agent = Agent(
    'openai:gpt-5.4',
    capabilities=[SpendLimits(budgets=[Budget(usd=Decimal('100'), window='day')])],
)
```

Past $100 in a UTC day, the next request raises `SpendLimitExceeded`.

## Budgets

A budget is a ceiling, a period, and optionally a partition. They compose, so several apply at once:

```python
from decimal import Decimal

from pydantic_ai_harness import SpendLimits
from pydantic_ai_harness.spend import Budget

SpendLimits(
    budgets=[
        Budget(usd=Decimal('5'), window='run'),  # one runaway run
        Budget(usd=Decimal('100'), window='day'),  # the whole deployment, per day
        Budget(usd=Decimal('2000'), window='month', warn_at=0.8),
        Budget(usd=Decimal('10'), window='day', scope=lambda ctx: ctx.deps.tenant_id, name='tenant'),
    ]
)
```

Field

Meaning

`usd` / `tokens`

ceilings; set either, both, or neither

`window`

`run`, `conversation`, `day`, `month`, `total`

`scope`

derives a partition key from the run, so tenants count separately; typed against the agent's `deps`

`warn_at`

fraction past which `BudgetStatus.warning` is set; never blocks

`name`

distinguishes budgets sharing a window and scope

`retain`

how long the counter is kept after its last write; `'window default'`, `'forever'`, or a `timedelta`

A window rolls over by producing a different store key rather than by resetting a counter, so a new day is simply a new key and nothing has to run at midnight. A `total` counter never expires. `run` and `conversation` buckets never roll over either, so expiry there hands back the ceiling rather than starting a new period -- but each mints a key per run or per conversation, so they carry a long horizon (24 hours and 30 days) instead, past which the counter is dropped rather than kept forever. That default is a compromise, and it is visible: a conversation resumed past its horizon starts from zero again, so set `retain='forever'` where a conversation ceiling has to hold for as long as the conversation does, and clean the keys up some other way.

Budgets that share a `name`, `window`, and `scope` share one counter, which is how a single window carries both a USD and a token ceiling. The response is added to that counter once, not once per budget. Two budgets that share a `name` and `window` but declare _different_ `scope` callables are refused at construction: they are different dimensions -- per tenant and per user, say -- and nothing stops the two returning the same string, which would merge them into one counter. Give them different names, or pass the same callable to both. Budgets that do share a counter must also agree on `retain`: one counter has one expiry, and the accrual writes whichever of them is listed first, so disagreeing would let declaration order decide when a `'forever'` ceiling rolls over.

`Budget` is generic in the agent's dependency type, so a `scope` is checked against it: pass the capability to an `Agent` with a `deps_type` and a scope reaching for a field those deps do not have is a type error rather than an `AttributeError` on the first request.

**A budget with no ceiling is a counter.** It accumulates and reports and never refuses anything, which is how per-tenant accounting with no cap is expressed:

```python
from pydantic_ai_harness import SpendLimits
from pydantic_ai_harness.spend import Budget

SpendLimits(budgets=[Budget(window='month', scope=lambda ctx: ctx.deps.tenant_id, name='chargeback')])
```

## What the gate guarantees

No request **starts** after a budget is exhausted.

Not: that spend stays under the ceiling. The request that crosses the line completes, and concurrent runs can each pass the check before any of them records anything. Three further gaps are worth knowing rather than discovering: a stream the caller abandons part-way never reaches the accounting hook, so its tokens are billed by the provider and invisible here; a capability that answers from a cache without calling a provider is charged the registry price for the response it returns; and a continuation chain (Anthropic `pause_turn`, OpenAI background mode) arrives at the hook as one merged response, which is what Pydantic AI counts as one request too, so its segments are priced on summed usage rather than one at a time -- the difference only shows where pricing is tiered rather than linear. Treat this as a brake on a runaway loop, not as an accounting ledger; reconcile against the provider's own numbers if you need the second thing.

## Reading the numbers

```python
from decimal import Decimal

from pydantic_ai import Agent
from pydantic_ai_harness import SpendLimits
from pydantic_ai_harness.spend import Budget, SpendRecordedEvent

limits = SpendLimits(budgets=[Budget(usd=Decimal('100'))])
agent = Agent('anthropic:claude-sonnet-4-6', capabilities=[limits])

@agent.on_event(SpendRecordedEvent)
async def show(ctx, event):
    print(f'{event.model} cost ${event.usd}')
```

`SpendRecordedEvent` is emitted after every response, including one that `on_unpriced='raise'` is about to reject. Its flat payload carries the response usage and serializable budget readings. Under durable execution, orchestration can deliver it again even though the journaled accrual ran only once, so keep a listener that writes an audit record or emits a billing event idempotent.

Migration: `on_spend` remains supported but is deprecated. Move its callback body to a `SpendRecordedEvent` subscription; the same idempotency requirement applies to it.

`status()` reads the same numbers without a run, which is what a cost display in a UI wants:

```python
from pydantic_ai_harness import SpendLimits


async def report(limits: SpendLimits[None]) -> None:
    for status in await limits.status(scope='acme'):
        print(status.budget.name, status.spent.usd, status.exhausted)
```

Without a run context, budgets on a `run` or `conversation` window are omitted, and so is a budget declaring a `scope` unless `scope=` names the partition to read. Pass `ctx` inside a run and every budget resolves.

Set `expose_tools=True` to give the agent a `get_spend` tool. It is off by default: a tool costs schema tokens on every request, and most applications want the number on a screen rather than in the model's context.

## Reacting to a threshold

Spend events are reporting signals, not approval points: they can follow the response carrying the final answer.

The seam that runs before a request rather than after a response is `before_model_request`. A small capability of your own can read `status(ctx)` there and hold the run until someone decides:

```python
import asyncio
from dataclasses import dataclass
from decimal import Decimal

from pydantic_ai import Agent
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.models import ModelRequestContext
from pydantic_ai.tools import RunContext

from pydantic_ai_harness import SpendLimits
from pydantic_ai_harness.spend import Budget

limits = SpendLimits[None](budgets=[Budget(usd=Decimal('100'), warn_at=0.8)])
approvals: asyncio.Queue[bool] = asyncio.Queue()


@dataclass
class ApproveBeforeSpending(AbstractCapability[None]):
    async def before_model_request(
        self, ctx: RunContext[None], request_context: ModelRequestContext
    ) -> ModelRequestContext:
        if any(status.warning for status in await limits.status(ctx)) and not await approvals.get():
            raise RuntimeError('spending past the warning threshold was not approved')
        return request_context


agent = Agent('openai:gpt-5.4', deps_type=type(None), capabilities=[limits, ApproveBeforeSpending()])
```

The gate reads numbers `SpendLimits` has already accrued, because the previous response was counted inside `wrap_model_request` before this request was prepared. It gates the first request of a run too, which is what carries a threshold crossed by an earlier run into the next one. A capability listed after it can still skip the request with `SkipModelRequest`, so an approval taken here is not proof that a request followed.

That pause holds a coroutine, so it lasts as long as the process does and no longer. A _serializable_ pause at a model-request boundary is not available: Pydantic AI's deferral path is tool-boundary only. `CallDeferred` and `ApprovalRequired` are honored where a tool call is validated or executed; raised from a model-request hook, nothing catches them and the run ends on the bare exception, which carries no message of its own. [#151](https://github.com/pydantic/pydantic-ai-harness/issues/151) tracks a general interrupt with a serializable continuation.

For a ceiling that expands rather than stops, `budgets` is read fresh on every request, so replacing it after a refusal lets the work continue against the larger ceiling. The counter is keyed on `name`, `window`, `scope` and the period the window is currently in, never on the ceiling, so what is already spent carries over.

A refusal can land mid-run, after tool calls have already run and been paid for. Re-running the original prompt would repeat that work and any side effects it had, so resume from what the refused run produced instead: `capture_run_messages` holds the partial history, and a run given that history and no new prompt continues from the request that was refused.

```python
import dataclasses
from decimal import Decimal

from pydantic_ai import Agent, capture_run_messages

from pydantic_ai_harness import SpendLimits
from pydantic_ai_harness.spend import Budget, SpendLimitExceeded

limits = SpendLimits[None](budgets=[Budget(usd=Decimal('1'), name='daily')])
agent = Agent('openai:gpt-5.4', deps_type=type(None), capabilities=[limits])


async def ask(prompt: str, ceiling: Decimal) -> str:
    with capture_run_messages() as messages:
        try:
            return (await agent.run(prompt)).output
        except SpendLimitExceeded:
            (budget,) = limits.budgets
            limits.budgets = [dataclasses.replace(budget, usd=ceiling)]
            resumable = list(messages)
    return (await agent.run(message_history=resumable)).output
```

Assigning `budgets` does not repeat the checks the constructor runs over budget combinations, so keep a replacement to the same names, windows, and scopes. It also raises the ceiling for every run sharing this `SpendLimits`, not just the one that was refused, and nothing lowers it again.

## Sharing a counter across processes

The default store keeps counters in the process, which catches a runaway loop inside one worker and does nothing for a budget spread across a queue. `RedisSpendStore` is the shared counter:

```python
from decimal import Decimal

from redis.asyncio import Redis

from pydantic_ai_harness import SpendLimits
from pydantic_ai_harness.spend import Budget, RedisSpendStore

store = RedisSpendStore(Redis.from_url('redis://localhost'))
limits = SpendLimits(budgets=[Budget(usd=Decimal('100'), window='day')], store=store)
```

It adds no dependency: `RedisClient` is a protocol of the two coroutines used, so any compatible client satisfies it. Amounts are stored as integer billionths of a dollar rather than through `INCRBYFLOAT`, which accumulates rounding error over the tens of thousands of requests a busy day produces. Billionths rather than millionths because the residue does not average out: an agent repeats requests of near-identical shape, so the same fraction rounds the same way every time.

Every window a response counts against is applied as one Lua script, so no other client sees the response part-applied: not across the four counters of one window, and not across the windows themselves. A response counting against a day budget and a month budget is one script rather than two, so there is no failure between them to leave the day counted and the month not. The one exception is the overflow below: it aborts the script where it happens and leaves the windows already applied, which takes a counter near $9.22 billion to reach. Each key also costs a second read for as long as the compatibility fallback below is in place.

A failure _after_ the server has run a script does not say whether it committed -- the connection can drop once `EVAL` has landed -- so a write that errors leaves the outcome unknown rather than untried. Nothing retries it: counting a billed response twice is a direction the brake survives, and counting it zero times is not.

The counters do not round. `HINCRBY` is 64-bit integer arithmetic and takes its increment as a string, so what Redis holds is exact, and the totals come back as bulk strings read with `HMGET` rather than as the integer replies `HINCRBY` returns -- those become Lua numbers, which are doubles, and would round a total past `2**53` billionths on the way out. What is left is `HINCRBY`'s own range: a counter passing the signed 64-bit range, around **$9.22 billion** against a single key, which Redis refuses before writing that field.

Keys are `{prefix}:budget-key`, with the braces around the prefix literal. That is a Redis Cluster hash tag, so the slot comes from the prefix alone and every key of one store lands in the same slot, which is what lets one script take several of them. The cost is that a cluster cannot spread a store's keys across its nodes, and that a `prefix` of your own is refused at construction if it is empty or carries a brace of its own, either of which stops the tag being read as one. `BudgetStatus.key` reports the budget key without the prefix, so what it shows is unchanged. The dedup markers below share that namespace, so a key beginning `dedup|` is refused: it would name a marker, which holds a string, and the counter would fail with `WRONGTYPE` rather than accumulate. No budget produces such a key -- the second segment of one is always a window -- so this only reaches a caller driving the store itself.

A counter written by an earlier release, under the untagged name, is read alongside the tagged one and added to it, so an upgrade needs no migration step. Added rather than moved: a move would have to decide when it is complete, and nothing here can know that, since a worker still on the old release can write to the old name at any point in a rolling deploy and a move that already ran would never pick that up. The cost is one extra read per key, on reads and writes alike.

The compatibility only runs one way, which is worth planning around on three counts. A **rolling deploy** under-counts while it lasts: an upgraded worker sees both names, but one still on the old release reads only the untagged one and cannot see what the upgraded workers have written, so it admits requests against a total that is missing them. A **downgrade** loses the tagged counter outright for the same reason, and this release never writes the old name, so nothing carries back. And the old key's **expiry is frozen** at whatever the last old-release write set: nothing here refreshes it, so it goes when it goes and the total drops by what it held. Keep the deploy short, and treat a downgrade as a reset rather than a rollback.

The fallback goes away in 0.28.0. A counter still living under the old name stops being counted at that point, so a window set to `retain='forever'`, or one whose horizon outlasts the gap between the two releases, is worth moving by hand before then.

`add_many` carries a token identifying the response, and `RedisSpendStore` reads a marker for it before the increments and writes it after them, inside the same script. `InMemorySpendStore` remembers the same tokens under its lock, so the default store behaves the same way while its process survives. The token combines the run id and step with a digest of replay-stable response content, usage, and provider identity; it excludes clock-derived and arbitrary provider bookkeeping. The token layer protects recovery that presents an entry without consulting the journal only when the caller supplies the same `run_id` to `Agent.run` on the original run and its recovery. When `run_id` is omitted, Pydantic AI creates a fresh one and the store cannot recognise the entry. Ordinary durable replay remains protected by the journaled `_accrue` operation regardless. Markers are held for `dedup_retain`, a field on both stores, an hour by default, or for the window's own horizon where that is shorter, and cost one small key per response per window. That horizon is the window in which recovery outside the durable journal is recognised, not the counter's lifetime: a response presented again later is counted again, which is the direction to err in, since a brake that trips early survives and one that releases late does not. Set `dedup_retain=None` to hold no markers and apply every entry, which also gives up that store-side protection. Recognition starts at the upgrade either way: a response an earlier release counted left no marker behind, so presenting that response again counts it again.

The default store is built per capability, so two `SpendLimits` instances do not quietly share one counter. Pass the same store object to both when you want them to. `InMemorySpendStore` cannot survive worker replacement: a replacement process has neither the counters nor the deduplication markers accumulated by the first one. Use a shared store for durable workflows that can recover on another worker.

A store that fails does not fail quietly. An error reading the counter refuses the request, which is the safe direction. An error writing it propagates out of the run after the model has already answered and been charged. That is deliberate: a swallowed write would drift the counter down and weaken the gate, which is worse than a visible failure. If your deployment would rather keep the answer than the count, wrap the store and decide there.

Any object with `get_many` and `add_many` works, so a Postgres or DynamoDB counter is a small class rather than a fork. Four obligations come with writing one. Return a total for every key you were handed, keyed by `SpendEntry.key`, including one you skipped as a replay. A missing total raises `UserError`, which names either this store contract or a non-deterministic scope during durable replay as the cause. Read a key that was never written as zero rather than leaving it out. Skip an entry whose `token` has already been applied to that key, or recovery outside the durable journal can count one response twice. And apply the whole call or none of it -- the guarantee at the top of this section is only as good as the backend behind it, and a store that commits each entry as it goes puts back the split write this seam exists to remove. Neither method is ever handed an empty sequence, so there is no such case to answer for.

`SpendStore`, the single-key `get` and `add` pair released in 0.17.0, is deprecated: a store of that shape still works, driven one window per call, and emits one `HarnessDeprecationWarning` when the `SpendLimits` holding it is constructed. The warning names both losses: windows are applied one at a time, and the token has nowhere to go. A durable journal still prevents duplicate execution while its record is available, but recovery that cannot consult that journal has no store-side deduplication. The single-key `get` and `add` on `InMemorySpendStore` and `RedisSpendStore` are deprecated too. A direct call to either does not warn, so this is the notice; reach for `get_many` and `add_many` instead. A subclass that _overrode_ one of them without also overriding the batch pair is warned when the store itself is constructed, because that case loses behavior rather than just naming a deprecated method: `SpendLimits` drives `get_many` and `add_many`, so an override on `get` or `add` is never called and whatever it added -- an audit, a mirrored write -- stops happening. Move it onto `get_many` or `add_many`, which is also what makes the warning stop.

## Pricing

Prices come from [genai-prices](https://github.com/pydantic/genai-prices) via `ModelResponse.cost()`, per response: cache and tier pricing are per request, so summing usage across requests and pricing the total gives the wrong number.

A model the registry does not know -- a local deployment, a negotiated rate -- is handled by `price`:

```python
from decimal import Decimal

from pydantic_ai_harness import SpendLimits

SpendLimits(price=lambda response: Decimal('0.002') if response.model_name == 'internal-7b' else None)
```

An amount returned by `price` must be finite and not negative. Anything else -- a credit, a `NaN`, an infinity -- fails the run with `UserError`, because a credit moves a budget away from its ceiling and the other two are a broken pricing function rather than a price. The response is still recorded first: it was billed by the provider whatever the function returned, so its tokens and request count are accrued and `on_spend` fires before the error is raised.

Under durable execution, `price` and each budget's `scope` callable must be deterministic for the same response and run context. Pricing runs in orchestration outside the journaled accrual, so a changed result can make `on_spend` disagree with the recorded counter or turn a successful recovery into a pricing error. Moving it into a durable operation would require the durability backend to serialize the complete provider response, including arbitrary metadata, so the callable remains outside that boundary. A changed scope selects a different store key from the one in the recorded accrual; `SpendLimits` reports that mismatch as a `UserError` naming the determinism requirement.

Returning `None` falls through to the registry. When nothing can price a response, `on_unpriced` decides: `'zero'` (the default) counts it as free and increments `Spent.unpriced_requests` so the gap is visible, and `'raise'` fails the run with `UnpricedModelError`. Either way the response is recorded first and the tokens are counted, so a token ceiling still holds for a model with no price and an application that catches the error does not carry on against an understated counter. Under `'zero'` a USD ceiling is the one that cannot hold: nothing priceable accrues, so no number of such requests reaches it. That combination -- `'zero'` plus a `usd` budget -- warns once per model with `UnpricedModelWarning`, rather than once per request. If callers choose the model, prefer `'raise'` or supply `price`.

## Composition

State lives across runs deliberately, so `for_run` is not overridden: a daily budget that reset every run would not be a daily budget. Per-run isolation comes from `Budget(window='run')`, whose key carries the run id.

`defer_loading=True` is refused. A deferred capability's hooks do not run until the model loads it, so an exhausted budget would not stop a request and the requests made meanwhile would go uncounted -- a brake the thing being braked decides when to apply.

The accrual happens in `wrap_model_request`, immediately around the provider call, and the capability declares itself innermost so that wrapper sits inside every capability outside the innermost tier. Every `after_model_request` runs outside it, and so does every wrapper except an innermost-tier capability listed after it.

`after_model_request` is the wrong hook for this. It runs once the whole wrap chain has returned, so a capability whose own `wrap_model_request` awaits the response and then raises `ModelRetry` sends the run straight to a fresh request and the rejected one -- generated, billed, kept in history -- is never counted. Ordering cannot reach that case: the rejecting capability need not be innermost, and one listed _before_ `SpendLimits` still wraps outside it.

Wrapping also means a request the provider never saw is not charged for. `SkipModelRequest` from an earlier capability's `before_model_request` reaches `after_model_request` with a response the run never paid for, but never reaches the wrapped handler.

What is left is siblings. Pydantic AI orders innermost capabilities against non-innermost ones only, and among themselves the one listed _later_ nests further in. `InputGuardrail` and the durability capabilities also declare themselves innermost, so either listed after `SpendLimits` wraps inside it. `InputGuardrail` is the one that can reject a billed response before it is counted. With `InputGuardrail(parallel=True)` what decides is whether the guard blocks, not who wins the race: a blocked prompt is counted in neither outcome, because the guard cancels the call when it settles first and discards the answer when the model does. The second is the under-count -- a response the provider billed that `SpendLimits` never sees. A durability wrapper dispatches rather than rejects, so it does not create that gap and is omitted from the warning. List `SpendLimits` last among your other innermost capabilities where the difference matters. Closing the guardrail case outright needs a way to order innermost capabilities against each other, tracked in [#534](https://github.com/pydantic/pydantic-ai-harness/issues/534).

`SpendLimits` reports that arrangement rather than leaving it to be read here. Before each model request it reads the sorted chain from `RunContext.root_capability` and warns with `SpendCompositionWarning`, naming the capabilities listed after it that bring a `wrap_model_request` of their own. One arrangement reports once, not once per request -- and it is the arrangement that is remembered rather than the fact of having reported, so an agent whose first run was safe is still read on a later run that adds an inner wrapper through `agent.run(capabilities=[...])`. A warning rather than a refusal, and keyed on the ordering rather than on what the capabilities do with it. None of the conditions above is read: `parallel` can be flipped without moving anything in the list, and neither the verdict nor the race is settled at the point the report is made. So it also names a sequential `InputGuardrail` listed after `SpendLimits`, which raises before the request is made and cannot under-count. Reordering silences it, and is what the paragraph above recommends anyway.

Three kinds of capability are left out of that report. A `Hooks` is not named: it defines `wrap_model_request` whether or not a `model_request` hook was registered, and the registry that would say is private ([pydantic-ai#7177](https://github.com/pydantic/pydantic-ai/issues/7177)). A `WrapperCapability` is answered on whatever it wraps, since its own `wrap_model_request` only delegates -- so a wrapper over a real rejector is still named. A durable-execution capability is also left out: its wrapper dispatches work rather than rejecting a response, and core requires that dispatch to be the last wrapper around the model handler. `SpendLimits` crosses that boundary through its own durable operations instead of by reordering the wrapper.

**Durable execution.** `SpendLimits` supports Pydantic AI durability capabilities. Its clock read, counter read, and accrual are separate durable operations. Temporal therefore reads the clock in an activity rather than workflow orchestration, and DBOS or Prefect record the same boundary in their own durable units. On replay, the engine returns each operation's recorded result without reading the clock or store again. The response is accrued once, and the window key comes from the original recorded clock value.

Attach the durability capability to the same agent as `SpendLimits`. Running a `SpendLimits` agent directly inside a Temporal workflow without `TemporalDurability` leaves the clock read in workflow orchestration; the sandbox error is translated into advice to attach durability.

The journal covers replay while its records are available. Store-side idempotency covers a different recovery path: one that presents the same `SpendEntry` without consulting the recorded accrual. A `BatchSpendStore` uses the replay-stable token to apply that entry once within `dedup_retain`. A deprecated `SpendStore` drops the token and warns, so it cannot provide this second layer. `InMemorySpendStore` can deduplicate only while recovery reaches the same process. Use a shared `BatchSpendStore`, such as `RedisSpendStore`, when recovery can land on another worker.

`exhausted()` remains useful as a workflow admission check without a `RunContext`:

```python
from collections.abc import Awaitable, Callable

from pydantic_ai_harness import SpendLimits


async def start_if_funded(
    limits: SpendLimits[None], tenant_id: str, start_workflow: Callable[[], Awaitable[object]]
) -> None:
    if await limits.exhausted(scope=tenant_id):
        raise RuntimeError('daily budget exhausted')
    await start_workflow()
```

`exhausted` rather than `any(s.exhausted for s in await limits.status(...))`: `status` omits the budgets it cannot resolve, and `any()` over what is left is a brake that passes having inspected nothing -- which is exactly what a `SpendLimits` whose budgets are all scoped returns when the scope is missing. `exhausted` raises there instead, naming the budgets that need a `scope` or a run context. Use `status` for a reading, `exhausted` for a decision.

Admission is all that call does: it reserves nothing. The durable operations then account for the workflow's model responses. Issue [#531](https://github.com/pydantic/pydantic-ai-harness/issues/531) tracks this support and its remaining store-lifetime limits.

For a ceiling that covers one run and nothing else, Pydantic AI's own [`UsageLimits`](https://pydantic.dev/docs/ai/core-concepts/agent/#usage-limits) does the same job in-process with no store and no capability: `total_tokens_limit` for tokens and `cost_limit` for money, both over a single `run()`. An unpriced response adds nothing to `RunUsage.cost`, so `cost_limit` measures a run against whichever part of it could be priced: a `CostNotFoundWarning` after the run when none of it was, and silence when only some of it was. `SpendLimits` counts the same gap and lets `on_unpriced` decide what to do about it. `UsageLimits` also carries the two input-token granularities `SpendLimits` has no equivalent for: `input_tokens_limit` is cumulative over the run, and `per_request_input_tokens_limit` caps one request against the provider-reported input tokens of the response that already paid for it. `count_tokens_before_request=True` counts the pending request with the model's own `count_tokens` and applies both limits to that count before the send, so an oversized context is refused rather than billed on the providers that implement `count_tokens`; the field names them, and a model without it raises `NotImplementedError` instead. Reach for `Budget(tokens=..., window='run')` when the same configuration also has to express a window longer than one run, a tenant scope, or a counter shared between processes.

## Tracing

A refusal emits a `spend budget exhausted` span with `spend.budget` and `spend.window`. Accrual emits nothing: a span per model request would double the size of a trace without adding a decision. `spend.scope` is attached only when `RunContext.trace_include_content` is set, since a scope key is usually a tenant or user id and a trace has a wider audience than the application that produced it.

## Specs

`Agent.from_spec` supports the part of the configuration a spec can express:

```yaml
- SpendLimits:
    budgets:
      - {usd: '100', window: day}
      - {usd: '2000', window: month, warn_at: 0.8}
    on_unpriced: raise
```

`store`, `price`, `on_spend`, `clock`, and a budget's `scope` take callables or live objects. A spec naming them is rejected rather than silently ignored, because a spec that promises per-tenant scoping and does not deliver it is worse than one that refuses to load.

The fields above are what `SpendLimits.from_spec` names in its signature, which is also what Pydantic AI reads to generate the spec's JSON schema -- so an editor following the `$schema` line completes and validates them. `BudgetSpec` is the entry shape, exported for anyone building a spec in code.

Source: [`pydantic_ai_harness/spend/`](https://github.com/pydantic/pydantic-ai-harness/tree/main/pydantic_ai_harness/spend/).

## API reference

### SpendLimits

**Bases:** `AbstractCapability[AgentDepsT]`

Accumulate spend per window and refuse a request once a window is exhausted.

```python
from decimal import Decimal

from pydantic_ai import Agent
from pydantic_ai_harness.spend import Budget, SpendLimits

agent = Agent(
    'openai:gpt-5.4',
    capabilities=[SpendLimits(budgets=[Budget(usd=Decimal('100'), window='day')])],
)
```

With no budgets the capability only reports through `SpendRecordedEvent`. Add a `Budget` with no ceiling to keep a running total that never blocks.

What the gate guarantees: no request **starts** after a budget is exhausted. What it does not: that spend stays under the ceiling. The request that crosses the line completes, and concurrent runs can each pass the check before any of them records anything. This is a brake on a runaway loop, not an accounting ledger.

State lives across runs on purpose, so `for_run` is left alone: a daily budget that reset every run would not be a daily budget. Per-run isolation comes from `Budget(window='run')`, whose key carries the run id.

Under a durability capability, clock reads, counter reads, and accruals are durable operations. Their recorded results are replayed without re-entering the store. A shared store is still required when recovery can move to another worker: the default `InMemorySpendStore` loses its counters and deduplication markers with the process. A deprecated `SpendStore` also loses token-based deduplication outside the journal because its single-key `add` method has nowhere to receive `SpendEntry.token`.

#### Attributes

##### budgets

Windows to accumulate against, and which of them can refuse a request.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`Budget`\[`AgentDepsT`\]\] **Default:** `()`

##### store

Where counters live. The default holds them for the lifetime of the process.

A store implementing only the deprecated `SpendStore` pair is driven one window per call through an adapter, which warns once at construction about what that costs.

**Type:** `SpendStore` | `BatchSpendStore` **Default:** `field(default_factory=InMemorySpendStore)`

##### price

Prices a response before the registry is consulted.

Returning `None` falls through to `genai-prices`. This is the way to charge a self-hosted model, or a negotiated rate the public registry does not know.

An amount must be finite and not negative. Anything else fails the run with `UserError`, after the response's tokens and request count have been recorded: a credit would move a budget away from its ceiling, and a NaN or an infinity is a broken pricing function rather than a price.

Under durable execution this callable must return the same result when replayed for the same response. It runs in orchestration after the durable model request, outside the journaled accrual.

**Type:** `PriceFunc` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### on\_spend

Deprecated callback after each response. Subscribe to `SpendRecordedEvent` instead.

Durable replay can invoke this callback again after the response's journaled accrual has run only once, so the callback must be idempotent.

**Type:** `SpendCallback` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### on\_unpriced

What to do when a response cannot be priced.

`'zero'` counts it as free and increments `Spent.unpriced_requests`, so the gap shows up instead of disappearing. `'raise'` fails the run with `UnpricedModelError`. Tokens are counted either way, so a token ceiling still holds for a model the registry does not know.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['zero', 'raise'\] **Default:** `'zero'`

##### expose\_tools

Offer the agent a `get_spend` tool.

Off by default: a tool costs schema tokens on every request, and most applications want the number on a screen rather than in the model's context.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### clock

Supplies the time that day and month windows are derived from.

It does not reach a default-constructed `store`, which keeps its own `utc_now` for expiry. Both remain absolute instants, so a custom clock buckets on one and expires on the other; pass the same callable to the store when that matters.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[\], [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)\] **Default:** `utc_now`

#### Methods

##### \_\_post\_init\_\_

```python
def __post_init__() -> None
```

Reject an `on_unpriced` that arrived as plain data and is not one of the two policies.

Anything other than `'raise'` behaves as `'zero'`, so a typo in a spec would quietly turn unpriced responses free instead of failing the run.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_serialization\_name

`@classmethod`

```python
def get_serialization_name(cls) -> str | None
```

Serialization name for agent-spec support.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_ordering

```python
def get_ordering() -> CapabilityOrdering
```

Sit innermost, so the accrual happens as close to the provider call as ordering allows.

Innermost puts this capability's `wrap_model_request` inside every capability outside that tier, so their wrappers -- and every capability's `after_model_request` -- run outside the accrual and cannot reject a response the counter has not already seen.

This orders against non-innermost capabilities only. Innermost members are not ordered among themselves, and the one listed later nests further in, so another innermost capability placed after this one still wraps inside it. `InputGuardrail` is the one that reaches a billed response before the counter does. List `SpendLimits` last among innermost capabilities where that matters; closing it outright is [https://github.com/pydantic/pydantic-ai-harness/issues/534](https://github.com/pydantic/pydantic-ai-harness/issues/534).

###### Returns

`CapabilityOrdering`

##### get\_toolset

```python
def get_toolset() -> AgentToolset[AgentDepsT] | None
```

Offer `get_spend` when `expose_tools` is set.

###### Returns

[`AgentToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AgentToolset)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### before\_model\_request

`@async`

```python
def before_model_request(
    ctx: RunContext[AgentDepsT],
    request_context: ModelRequestContext,
) -> ModelRequestContext
```

Refuse the request if any budget with a ceiling is already spent.

Also where the arrangement `get_ordering` cannot rule out is reported. The sorted chain is readable from `RunContext.root_capability` from `before_run` onward but not before it: `for_agent` sees only the capabilities the agent was constructed with, and `ctx.root_capability` is still `None` in `for_run`, so neither covers a capability added through `agent.run(capabilities=...)`. `before_run` would serve as well, since the chain is fixed for a run; the read sits here to stay on the request path, beside the accrual it is about. Re-reading per request costs nothing because `_reported_arrangements` makes it idempotent, and keying on the arrangement rather than on having reported is what covers a chain that differs between runs.

###### Returns

[`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

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

Price what the provider returned and add it to every window, before an outer capability can reject it.

The accrual belongs here rather than in `after_model_request` because `after_model_request` runs outside this chain, once the whole chain has returned. A capability whose own `wrap_model_request` awaits the response and then raises `ModelRetry` sends the run straight to a fresh request, and the response it rejected -- generated, billed, and kept in history -- is never counted. Ordering cannot close that: the rejecting wrapper does not have to be innermost, and one listed _before_ this capability still nests outside it.

Wrapping is also why a request the provider never saw is not charged for. `SkipModelRequest` from an earlier `before_model_request` reaches `after_model_request` with a response the run never paid for; it does not reach `handler`, so nothing accrues here.

###### Returns

[`ModelResponse`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelResponse)

##### status

`@async`

```python
def status(
    ctx: RunContext[AgentDepsT] | None = None,
    *,
    scope: str | None = None,
) -> tuple[BudgetStatus, ...]
```

Where each budget stands.

Inside a run, pass `ctx` and every budget resolves. Without one -- the reading a cost display wants, and the check to make before starting a durable workflow -- budgets on a `run` or `conversation` window are omitted, since those periods have no meaning outside a run, and a budget declaring a `scope` is omitted unless `scope` names the partition to read, since its callable has no run context to resolve against.

Reach for [`exhausted`](https://pydantic.dev/docs/ai/harness/spend/#pydantic_ai_harness.spend.SpendLimits.exhausted) when the answer gates something: `any(s.exhausted for s in ...)` over a tuple that happens to be empty is a brake that reads as enforcement and inspects nothing, and a `SpendLimits` whose budgets are all scoped returns exactly that tuple.

###### Returns

[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[`BudgetStatus`, ...\]

##### exhausted

`@async`

```python
def exhausted(
    ctx: RunContext[AgentDepsT] | None = None,
    *,
    scope: str | None = None,
) -> bool
```

Whether any budget this call can read is exhausted, refusing to guess about the rest.

An admission check, and only that. It reads the counters; it reserves nothing and records nothing, so work started on the strength of it is measured only if the agent also carries this capability. Under durable execution, the agent's clock reads, counter reads, and accruals are journaled. The store still has to survive worker replacement for a budget shared across those workers.

`status()` omits what it cannot resolve, and `any(...)` over the remainder is a brake that silently checks nothing when every budget is scoped -- so this raises instead, naming the budgets that need a `scope` or a `ctx`.

###### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### from\_spec

`@classmethod`

```python
def from_spec(
    cls,
    *,
    budgets: Sequence[BudgetSpec] = (),
    on_unpriced: Literal['zero', 'raise'] = 'zero',
    expose_tools: bool = False,
    id: str | None = 'spend_limits',
    description: str | None = None,
    defer_loading: bool = False,
    **unsupported: Any,
) -> SpendLimits[Any]
```

Build from an agent spec, covering the fields a spec can express.

Every parameter is named because that signature is what core reads to generate the spec's JSON schema: `build_schema_types` drops `*args`/`**kwargs`, so a catch-all signature publishes the bare string `'SpendLimits'` and an editor marks every documented `budgets:` block as invalid even though it loads.

`budgets` arrive as mappings and become `Budget` instances, with `usd` accepted as a string so YAML cannot round a price through a float. The callables and the store have no spec representation and are rejected rather than dropped: a spec that promises per-tenant scoping and does not deliver it is worse than a spec that refuses to load. `**unsupported` stays so that rejection keeps naming the field; core drops it from the schema, so it costs nothing there.

###### Returns

`SpendLimits`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

### Budget

**Bases:** `Generic[AgentDepsT]`

One spend window: what it limits, over what period, for whom.

A budget with neither `usd` nor `tokens` is a pure counter: it accumulates and reports, and never stops a run. That is how per-tenant accounting with no cap is expressed.

Generic in the agent's dependency type so `scope` is checked against it: the parameter comes from the `Agent` the capability is passed to, so a scope reaching for a field the deps do not have is a type error rather than an `AttributeError` on the first request.

```python
from decimal import Decimal

from pydantic_ai_harness.spend import Budget

Budget(usd=Decimal('100'), window='day')
Budget(usd=Decimal('10'), window='day', scope=lambda ctx: ctx.deps.tenant_id)
Budget(window='month', name='accounting')  # counts, never blocks
```

#### Attributes

##### usd

Ceiling in US dollars. `None` means this budget does not limit spend.

**Type:** `Decimal` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tokens

Ceiling in total tokens. `None` means this budget does not limit tokens.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### window

The period the ceiling applies to.

**Type:** `Window` **Default:** `'day'`

##### scope

Partitions the counter -- per tenant, per user, per agent. `None` counts globally.

Under durable execution this callable must return the same value when replayed with the same run context, because its result is part of the store key.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]\], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### warn\_at

Fraction of the ceiling past which `BudgetStatus.warning` is set. Never blocks.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### name

Distinguishes budgets sharing a window and scope. Part of the store key.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'default'`

##### retain

How long a store may keep this window's counter after its last write.

`'window default'` takes the horizon from `window` (see `_TTLS`). A time window may expire freely once it has rolled over, but `run` and `conversation` buckets never roll over, so their defaults are a compromise between never expiring and growing the store without bound -- and a conversation resumed past the horizon starts again from zero. Set `'forever'` where that matters and the keys are cleaned up some other way, or a `timedelta` to pick the horizon outright.

**Type:** `timedelta` | [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['window default', 'forever'\] **Default:** `'window default'`

##### enforces

Whether this budget can refuse a request, rather than only counting.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### ttl

How long a store may keep this window's counter after its last write.

**Type:** `timedelta` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_post\_init\_\_

```python
def __post_init__() -> None
```

Reject configurations that would quietly misbehave rather than fail.

A ceiling of zero or less makes a budget exhausted before anything is spent, so the first request is refused with no way to tell that from a real overspend -- and `usd: 0` in a spec is far more likely to mean "no limit", which is what `None` says. A `warn_at` on a budget with no ceiling has nothing to be a fraction of, so it can never fire. Both read as configuration and behave as breakage, which is why they are errors here rather than surprises later.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

### SpendSnapshot

What one model response cost, and where every budget stands after it.

#### Attributes

##### model

The model that produced the response, or `None` if it reported none.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### usage

The response's usage verbatim, including cache reads, writes, and audio.

**Type:** [`RequestUsage`](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/#pydantic_ai.usage.RequestUsage)

##### usd

What this response cost. Zero when it could not be priced.

**Type:** `Decimal`

##### priced

Whether `usd` is a real price or a stand-in zero.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### budgets

One entry per configured budget, in the order they were declared.

**Type:** [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[`BudgetStatus`, ...\]

### BudgetStatus

A budget and how much of it is left.

#### Attributes

##### budget

The budget this describes.

Unparameterised because this is a reading: the dependency type only types `Budget.scope`, and nothing calls a scope through a status.

**Type:** `Budget`\[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)\]

##### key

The store key it accumulates under. Useful for debugging a scope or window.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### spent

What the budget's current window has accumulated.

**Type:** `Spent`

##### remaining\_usd

`None` when the budget sets no USD limit.

**Type:** `Decimal` | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### remaining\_tokens

`None` when the budget sets no token limit.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### warning

Whether spend has crossed `Budget.warn_at`. Always `False` without one.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### exhausted

Whether a further request would be refused.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### Spent

Everything one window has accumulated so far.

#### Attributes

##### usd

Priced cost. Requests with no resolvable price contribute nothing here.

**Type:** `Decimal` **Default:** `Decimal(0)`

##### tokens

Total tokens, counted whether or not the request could be priced.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### requests

Model requests recorded against this window.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### unpriced\_requests

How many of `requests` had no resolvable price, so `usd` understates them.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

### BatchSpendStore

**Bases:** [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Reads and accumulates the counters behind every window of one response.

`add_many` returns the state **after** the increment so an atomic backend can answer without a second round trip, keyed by `SpendEntry.key` rather than positionally so entries sharing a key collapse the way the caller expects.

Both methods take a sequence rather than a single key so a backend that can read or apply the whole set as one unit does, and one that cannot still sees the whole set and can say so.

#### Methods

##### get\_many

`@async`

```python
def get_many(keys: Sequence[str]) -> Mapping[str, Spent]
```

What each key has accumulated. A key that was never written reads as zero.

###### Returns

[`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `Spent`\]

##### add\_many

`@async`

```python
def add_many(entries: Sequence[SpendEntry]) -> Mapping[str, Spent]
```

Apply every entry and return each key's new total.

###### Returns

[`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `Spent`\]

### SpendEntry

One window's share of one response.

Everything except `key` defaults to nothing, so a reconciler correcting drift against an external source can post a `usd` delta on its own without inflating the request count.

#### Attributes

##### key

The window's store key.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### usd

Priced cost to add. May be negative, which is how a reconciler corrects drift.

**Type:** `Decimal` **Default:** `Decimal(0)`

##### tokens

Total tokens to add.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### requests

Model requests to add. Explicit rather than an implied `+= 1` so a correction can move the money without moving the count.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### unpriced

How many of `requests` had no resolvable price.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `0`

##### ttl

How long the key may be kept after this write. `None` means indefinitely.

**Type:** `timedelta` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### token

Identifies the response this entry came from, so it is applied at most once.

The durable accrual operation handles ordinary replay through its journal. Recovery without that record can still present the same response to the store. A store that recognises a token it has already applied to `key` returns the current total instead of adding again.

`None` means "apply unconditionally", which is what a reconciler posting a delta wants: two corrections of the same size are two corrections.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### SpendStore

**Bases:** [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Reads and accumulates the counter behind one budget window at a time.

Deprecated. Implement [`BatchSpendStore`](https://pydantic.dev/docs/ai/harness/spend/#pydantic_ai_harness.spend.BatchSpendStore) instead: it takes every window of a response in one call, which is what lets a backend apply them together, and it carries the replay token that keeps a re-executed accrual from counting twice. `SpendLimits` still accepts a store of this shape and drives it through an adapter, one window per call, warning once about what that costs.

The two protocols are separate names rather than two versions of one, because `runtime_checkable` tests method presence and not signatures: reusing `add` and `get` would leave nothing able to tell a store that batches from one that cannot.

#### Methods

##### get

`@async`

```python
def get(key: str) -> Spent
```

What `key` has accumulated. A key that was never written reads as zero.

###### Returns

`Spent`

##### add

`@async`

```python
def add(
    key: str,
    *,
    usd: Decimal,
    tokens: int,
    requests: int,
    unpriced: int,
    ttl: timedelta | None,
) -> Spent
```

Add to `key` and return the result. `ttl` is how long the key may be kept.

###### Returns

`Spent`

### InMemorySpendStore

Counters for the lifetime of one process.

Catches a runaway loop inside the worker it runs in. It does not enforce a budget across processes and cannot survive durable recovery on a replacement worker: each process has its own counters and deduplication markers. A shared store such as [`RedisSpendStore`](https://pydantic.dev/docs/ai/harness/spend/#pydantic_ai_harness.spend.RedisSpendStore) is for.

#### Attributes

##### clock

Supplies the time expiry is measured against.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[\], [`datetime`](https://docs.python.org/3/library/datetime.html#module-datetime)\] **Default:** `utc_now`

##### sweep\_every

Writes between expiry sweeps.

Expiry cannot wait for the next read of a key: a day window produces a new key each day, so yesterday's is never asked for again. The scan is linear in resident keys, so it is amortised over this many writes rather than run on each one, which bounds dead entries to roughly that many. Lower it where scopes are high-cardinality and memory matters more than the scan.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `256`

##### dedup\_retain

How long an applied `SpendEntry.token` is remembered, or `None` to apply every entry.

This is the window a replay is recognised in, not the counter's lifetime: a response replayed later than this is counted again. A remembered token costs one small entry per response per window until it is swept.

**Type:** `timedelta` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `DEFAULT_DEDUP_RETAIN`

#### Methods

##### \_\_post\_init\_\_

```python
def __post_init__() -> None
```

Report a subclass whose single-key overrides the batch pair has left unreachable.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### \_\_len\_\_

```python
def __len__() -> int
```

How many windows are still live.

Rolled-over entries are excluded whether or not the amortised sweep has reached them yet, so this counts what is being tracked rather than what happens to be resident. That is one entry per budget, scope and period -- and for a `run` or `conversation` budget the period is an id, so the count grows with traffic until those entries reach their horizon. Worth watching there and wherever scopes are high-cardinality.

Defining `__len__` makes an empty store falsy, so write `if store is not None`.

###### Returns

[`int`](https://docs.python.org/3/builtins/functions.html#int)

##### get

`@async`

```python
def get(key: str) -> Spent
```

What `key` has accumulated. Deprecated in favour of `get_many`.

###### Returns

`Spent`

##### add

`@async`

```python
def add(
    key: str,
    *,
    usd: Decimal,
    tokens: int,
    requests: int,
    unpriced: int,
    ttl: timedelta | None,
) -> Spent
```

Add to `key` and return the result. Deprecated in favour of `add_many`.

###### Returns

`Spent`

##### get\_many

`@async`

```python
def get_many(keys: Sequence[str]) -> Mapping[str, Spent]
```

What each key has accumulated, treating an expired key as absent.

Under the lock, because `_live` deletes the key it finds expired: unlocked, that `del` races the `_sweep` iteration inside `add_many` (`RuntimeError: dictionary changed size during iteration`) and a second concurrent reader (`KeyError`). Reachable whenever the guard is shared across threads -- `run_sync` from a pool, a sync endpoint -- and any key is read past its horizon.

###### Returns

[`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `Spent`\]

##### add\_many

`@async`

```python
def add_many(entries: Sequence[SpendEntry]) -> Mapping[str, Spent]
```

Apply every entry and return each key's new total.

The mutation spans no `await`, so concurrent runs on one event loop cannot interleave halfway through it and no reader sees some of a response applied and not the rest. The lock covers the case that is not free: `run_sync` called from a thread pool, or a free-threaded interpreter, where a read-modify-write loses updates in the direction that under-counts spend.

Every entry is worked out before any of them is stored, so a response that fails part-way through -- an amount whose arithmetic raises, say -- leaves none of its windows applied rather than the ones before the failure. Applying the whole set together is what this method exists for.

The clock is read once, before anything is applied, and a token is remembered only once the counter it stands for has moved. A token remembered ahead of that write would be consumed by a call that then failed, and the retry that could have recorded the response would be skipped as a replay of it.

###### Returns

[`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `Spent`\]

### RedisSpendStore

Spend counters in Redis, so every worker enforces one budget.

One hash per window, holding the four counters as integers.

```python
from redis.asyncio import Redis

from pydantic_ai_harness.spend import RedisSpendStore

store = RedisSpendStore(Redis.from_url('redis://localhost'))
```

A read and the increment that follows it are separate round trips, so concurrent runs can each observe a budget as unexhausted and push past it together. That is the same overshoot the in-process store has, widened by the number of workers; see the README on what the gate does and does not guarantee.

#### Attributes

##### client

Any client exposing `hgetall` and `eval`.

**Type:** `RedisClient`

##### prefix

Namespace for the keys, so a shared Redis stays tidy.

Every key this store writes is `{prefix}:...` with the braces literal, which is a Redis Cluster hash tag: the slot is computed from the prefix alone, so all of a store's keys land in one slot and a script may take several of them at once. Applying one response to a day and a month window in one script is what that buys, and the cost is that a cluster cannot spread this store's keys across its nodes.

A prefix carrying a brace of its own is refused at construction, since it would move the tag and put two windows of one budget in different slots.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'pydantic-ai-harness:spend'`

##### dedup\_retain

How long an applied `SpendEntry.token` is remembered, or `None` to apply every entry.

This is the window a replay is recognised in, not the counter's lifetime: a response replayed later than this is counted again, because the marker it would have matched has expired. The counter usually lives far longer, since every write extends it.

Each remembered token is one small key per response per window. Raise it where a durable engine may recover long after the fact; lower it where the write rate makes that memory matter more.

**Type:** `timedelta` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `DEFAULT_DEDUP_RETAIN`

#### Methods

##### \_\_post\_init\_\_

```python
def __post_init__() -> None
```

Reject a prefix that would break the hash tag it is wrapped in, and report dead overrides.

A brace inside the prefix moves or truncates the tag, so two windows of one budget would hash to different slots and a cluster would refuse the script that applies them together. Checked here for the same reason `Budget.name` is checked against its separator: the failure otherwise arrives as a `CROSSSLOT` error on a model request.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get

`@async`

```python
def get(key: str) -> Spent
```

What `key` has accumulated. Deprecated in favour of `get_many`.

###### Returns

`Spent`

##### add

`@async`

```python
def add(
    key: str,
    *,
    usd: Decimal,
    tokens: int,
    requests: int,
    unpriced: int,
    ttl: timedelta | None,
) -> Spent
```

Add to `key` and return the result. Deprecated in favour of `add_many`.

One window per call, so a response counting against a day and a month budget is two calls and a failure between them leaves the day counted and the month not. `add_many` is one script over every window, which is what closes that.

###### Returns

`Spent`

##### get\_many

`@async`

```python
def get_many(keys: Sequence[str]) -> Mapping[str, Spent]
```

What each key has accumulated. An absent hash reads as zero.

Two round trips per key while the pre-hash-tag fallback is in place: the key's own hash, and the one an earlier release would have written; see `_before_hash_tags`.

###### Returns

[`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `Spent`\]

##### add\_many

`@async`

```python
def add_many(entries: Sequence[SpendEntry]) -> Mapping[str, Spent]
```

Apply every entry as one script and return each key's new total.

One unit of work: every window of the response lands or none does, and the script returns each new total, so the totals need no second read. What does cost a read is the pre-hash-tag fallback, one per key, until it goes away; see `_before_hash_tags`.

A failure before the server runs the script -- the client cannot connect, the request never lands -- writes nothing. A failure after it does not say which: the connection can drop once `EVAL` has already committed, so an error here means the outcome is unknown rather than that nothing happened. Retrying therefore risks counting the response twice, which is why `SpendLimits.wrap_model_request` does not retry and lets the error end the run instead. Over-counting a response the provider did bill is the direction a brake can survive; under-counting is not.

A `SpendEntry.token` makes the retry that _is_ safe: a durable engine re-executing an accrual it already committed finds the marker for it already written, so the entry is skipped and the current total is returned.

###### Returns

[`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `Spent`\]

### SpendLimitExceeded

**Bases:** [`UsageLimitExceeded`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UsageLimitExceeded)

Raised when a [`Budget`](https://pydantic.dev/docs/ai/harness/spend/#pydantic_ai_harness.spend.Budget) is exhausted.

Subclasses [`UsageLimitExceeded`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UsageLimitExceeded) so an application that already stops on a usage limit stops on a spend limit too, while code that needs to tell "the daily budget is gone" from "this run used too many tokens" can catch this type specifically.

### UnpricedModelError

**Bases:** [`UserError`](https://pydantic.dev/docs/ai/api/pydantic-ai/exceptions/#pydantic_ai.exceptions.UserError)

Raised when `on_unpriced='raise'` and no price could be resolved for a response.

Either the model is absent from the `genai-prices` registry (a local or custom deployment) or the response carries no model name. Supply `SpendLimits.price` to price it yourself, or use `on_unpriced='zero'` to count the request as free and surface it as `Spent.unpriced_requests`.

### UnpricedModelWarning

**Bases:** [`UserWarning`](https://docs.python.org/3/builtins/exceptions.html#UserWarning)

Warned once per model when an unpriced response counts as free against a USD ceiling.

Only warned under `on_unpriced='zero'`, and only while a `Budget` carries a `usd` ceiling. That is the combination where the gap is silent: the response contributes nothing in dollars, so that ceiling cannot be reached however many such requests are made. A token ceiling still holds, because tokens are counted whether or not a price was found.

Deduplicated per model name for the life of the capability instance, so a model the registry does not know reports once rather than once per request.

### SpendCompositionWarning

**Bases:** [`UserWarning`](https://docs.python.org/3/builtins/exceptions.html#UserWarning)

Warned when another capability is composed so that it wraps inside the accrual.

Pydantic AI orders the `innermost` tier against non-innermost capabilities only. Among themselves the one listed later nests further in, so a capability listed after `SpendLimits` wraps inside it. Such a capability can await a response and then raise, which sends the run to a fresh request while the rejected response -- generated, billed, and kept in history -- is never counted.

This reports the ordering, not an under-count that has happened. Reaching one needs the nested capability to reject a response it has already awaited, and whether it does is its own business: an `InputGuardrail` gets there only when `parallel=True`, its guard blocks, and the provider answers before the guard does. Sequentially the guard raises before the request is made, and a parallel guard that blocks first cancels the call, so neither leaves anything billed to count. None of those conditions is read here -- `parallel` can be flipped without moving anything in the list, so the ordering is the durable property and the one you control. List `SpendLimits` last among the innermost capabilities to remove it.

Silence it with::

import warnings from pydantic\_ai\_harness.spend import SpendCompositionWarning

warnings.filterwarnings('ignore', category=SpendCompositionWarning)

---
