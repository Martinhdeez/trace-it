# [Compaction](https://pydantic.dev/docs/ai/harness/compaction/)

> A menu of strategies -- clear, dedupe, trim, or summarize -- for keeping an agent's conversation history within the model's context window.

# Compaction

Compaction is a menu of strategies for keeping an agent's conversation history within a model's context window. Most are Pydantic AI `Capability` classes that edit the message history just before each request goes out. `FallbackCompaction` is instead a composing `CompactionStrategy` used through `TieredCompaction` or `compact_now`; it has no request trigger of its own. The edits **persist** into the run's message history, so a trim, clear, or summary carries forward to later steps -- it is not recomputed from the full history every turn.

All strategies preserve tool-call / tool-return **pairing**. Core does not validate this, and a provider rejects an orphaned pair, so the pairing guarantee is what makes these safe to drop into an agent. The zero-LLM strategies never call a model; only `SummarizingCompaction` (and `TieredCompaction` when it escalates that far) spends tokens.

On OpenAI and Anthropic, core also ships [provider-native compaction](https://pydantic.dev/docs/ai/capabilities/compaction/) -- the provider summarizes history server-side. The strategies on this page are the model-agnostic alternative: they work with every model and keep the compaction logic (and its costs) under your control.

[Source](https://github.com/pydantic/pydantic-ai-harness/tree/main/pydantic_ai_harness/compaction/)

> While Pydantic AI Harness is on 0.x releases, the API may change between minor releases; when it does, deprecation warnings and release-note migration guidance tell you (or your agent) exactly how to upgrade. See the [version policy](https://pydantic.dev/docs/ai/harness/#version-policy).

## The problem

An agent that runs for many turns accumulates history: tool outputs, file reads, model reasoning, repeated content. Left unchecked, that history outgrows the model's context window and the next request fails. Compaction keeps the history bounded, and the right strategy depends on where the bloat lives and how much you can afford to spend reclaiming it.

## The menu

Component

Cost

What it does

Reach for it when

`ClampOversizedMessages`

zero-LLM

Head/tail-truncates a single oversized part (response text, tool-call args)

One runaway generation blew past the context cap and no other strategy can reach it

`SlidingWindowCompaction`

zero-LLM

Drops the oldest whole messages down to a tail

You only need the recent turns and can discard old context entirely

`ClearToolResults`

zero-LLM

Blanks the content of old tool _results_ in place, keeping the last `keep_pairs`

Tool outputs dominate context and can be re-fetched on demand (the cheap first tier)

`DeduplicateFileReads`

zero-LLM

Blanks every file read superseded by a newer read of the same file

The agent re-reads files and only the latest version matters

`SummarizingCompaction`

one LLM call

Summarizes older messages into a structured summary, keeping the recent tail

Old context still matters but must be compressed; use behind the cheap tiers

`TieredCompaction`

escalates

Runs cheap passes first, summarizes only if still over `target_tokens`

You want a sensible default: spend the expensive summary only when needed

`FallbackCompaction`

depends on chain

Tries the next strategy when one raises

Summarization can fail and deterministic truncation must keep the run alive

`WarnNearLimits`

zero-LLM

Injects an URGENT/CRITICAL warning as limits approach

You want the agent to wrap up rather than have its history rewritten

`ReportContextUsage`

zero-LLM

Reports context usage to your application; never edits history

You want a live context gauge in a UI

## Triggers

Instruction replacement and withdrawal records contribute their full rendered system text to token estimates. Superseded updates before a new instruction baseline are excluded.

Every size-based strategy triggers on `max_messages`, `max_tokens` (estimated), or `max_fraction`. Token counts anchor on the provider-reported usage of the most recent model response when one is available. That provider usage includes the instructions, tool definitions, and `FilePart` payloads sent in the anchored request; only the messages added since are estimated. The suffix after the anchor, or a history with no usage anchor, uses `tokenizer` or a ~4-chars-per-token heuristic and cannot see `FilePart` payloads. Pending tool schemas newly revealed for the request are conservatively estimated by the implementation. `DeduplicateFileReads` runs on every request when no trigger is set (it is cheap and near-lossless). `TieredCompaction` triggers and stops on a single `target_tokens` / `target_fraction` budget. `ClampOversizedMessages` triggers per _part_ (`max_part_tokens` / `max_part_chars`), not on the whole history -- the failure it targets is one oversized part, not a large total.

### `max_fraction`: one setting for every model

An absolute `max_tokens` is only correct for the model it was measured against. Configure `180_000` and a 1M-context model compacts at a fifth of its capacity, paying for summaries it did not need; a 128K model configured for `1_000_000` never compacts before the provider rejects the request.

`max_fraction` is resolved per request against the model's real context window, so one configuration is correct everywhere:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import SummarizingCompaction

agent = Agent(
    'anthropic:claude-sonnet-5',
    capabilities=[SummarizingCompaction(max_fraction=0.9, keep_messages=20)],
)
```

That compacts at 900K on a 1M model and at 115K on a 128K one. `WarnNearLimits` takes the same shape as `max_context_fraction`, and `TieredCompaction` as `target_fraction`. `max_tokens` and `max_fraction` are mutually exclusive -- a strategy taking both would have to pick one and discard the other, leaving the caller unable to tell which budget was in force.

The window comes from [`genai-prices`](https://github.com/pydantic/genai-prices), already a dependency of `pydantic-ai-slim`; `resolve_context_window` is exported if you want the number yourself. Pydantic AI does not expose it yet (`ModelProfile` has no `context_window` field), so when it does, that one function switches over. Nothing is cached: only a registry-confirmed number is ever treated as the real window.

The model consulted is `ModelRequestContext.model`, the one the request will be sent to, not the one the run started with. A capability ordered earlier may replace it, and the budget follows.

### When the window does not resolve

Not every model is in the registry. A local endpoint, a bespoke deployment, a Bedrock-prefixed reference such as `bedrock:us.anthropic.claude-sonnet-5`, a model the registry knows without a recorded window, and any `FallbackModel` (its `model_id` is a composite `fallback:...`) all resolve to nothing. The fraction is then taken of `fallback_context_window`, which defaults to a conservative 200K (`DEFAULT_CONTEXT_WINDOW`): compacting earlier than necessary costs one summary, overestimating costs the whole request.

Every capability that takes a fraction takes the fallback too, so you are not stuck with 200K on a model you know the size of:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import SummarizingCompaction

agent = Agent(
    'bedrock:us.anthropic.claude-sonnet-5',
    capabilities=[SummarizingCompaction(max_fraction=0.9, fallback_context_window=1_000_000)],
)
```

It is only consulted when resolution fails, so it costs nothing on a model the registry does know.

`TestModel` is one of the models that does not resolve: its `model_id` is `test:test`, so a fraction is taken of `fallback_context_window` and `max_fraction=0.9` becomes a 180,000-token trigger. A compaction config exercised only against `TestModel` will look like it never fires; pass `context_window=` or `fallback_context_window=` in the test to put the trigger where you can reach it.

### When the window resolves to the wrong number

Resolution can also succeed and be wrong, which `fallback_context_window` cannot help with -- it applies only when resolution fails. Three cases:

-   **The registry entry itself is wrong.** Harness reads `genai-prices` and cannot validate it. Measured against `genai-prices` 0.1.3:
    
    model id
    
    registry records
    
    real window
    
    `anthropic:claude-sonnet-4-5`
    
    1,000,000
    
    200,000
    
    `anthropic:claude-opus-4-6`
    
    200,000
    
    1,000,000
    
    An over-recorded window is the direction that breaks a run. On `anthropic:claude-sonnet-4-5`, `max_fraction=0.9` resolves to a 900,000-token trigger against a 200,000-token window: compaction never fires, and the provider rejects the request instead. **Pass `context_window=200_000` explicitly on `claude-sonnet-4-5`.** `claude-sonnet-5`'s recorded 1,000,000 matches Anthropic's model documentation, so it needs no override; check any other Sonnet id you use against the provider's own documentation before relying on the resolved number. An under-recorded window is safe but wasteful -- it compacts earlier than it has to.
    
-   The registry records the maximum a model can be made to accept. Where that maximum is gated -- a beta header, a pricing tier -- an ordinary request gets less, and a fraction of the recorded number never triggers before the provider rejects the request.
    
-   A self-hosted or proxied endpoint reports a model id whose registry entry describes someone else's deployment.
    

`context_window` overrides resolution outright, on every capability that takes a fraction:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import SummarizingCompaction

agent = Agent(
    'openai:gpt-5.6-luna',  # served by a local endpoint with a smaller window than the registry records
    capabilities=[SummarizingCompaction(max_fraction=0.9, context_window=32_000)],
)
```

### What counts toward the fraction

With a usage anchor, the provider-reported usage covers everything billed for the anchored request, including its instructions, tool definitions, and `FilePart` payloads. For the suffix after the anchor, and for a whole history with no usage anchor, the estimator uses `tokenizer` when supplied or a ~4-characters-per-token heuristic. That estimated portion cannot see `FilePart` payloads. Pending tool schemas newly revealed for the request are conservatively estimated by the implementation, since they are not covered by the earlier anchor.

**If you already set an absolute `max_tokens`, re-check it.** The estimator used to count only user and system prompts, tool returns, response text, and tool calls. `ThinkingPart` / `CompactionPart` content, `RetryPromptPart` content, `NativeToolCallPart` / `NativeToolReturnPart`, and the most recent `ModelRequest.instructions` are now counted too, so the same history measures higher and an unchanged `max_tokens` compacts earlier. How much earlier depends on how much of the history is thinking blocks, retries, and instructions; on a thinking-heavy tool-calling history it can be several times the old count. What each strategy clears is unchanged -- only when it runs.

## Reporting usage: `ReportContextUsage`

A strategy knows when to act but says nothing about how close the run is to the limit, so an application that wants to show `context: 73%` ends up re-counting the history and guessing the denominator. `ReportContextUsage` does neither -- it reuses the same estimator and the same resolved window, and only observes:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import ReportContextUsage, SummarizingCompaction
from pydantic_ai_harness.compaction import ContextUsageEvent

agent = Agent(
    'anthropic:claude-sonnet-5',
    capabilities=[
        SummarizingCompaction(max_fraction=0.9, keep_messages=20),
        ReportContextUsage(),
    ],
)

@agent.on_event(ContextUsageEvent)
async def show(ctx, event):
    print(f'{event.fraction:.0%}')
```

Each reading carries `used_tokens`, `window_tokens`, `fraction`, and `resolved` -- `False` when the window is the fallback rather than the model's real one, so a gauge can show that the percentage is a guess. Migration: `on_usage` remains supported but is deprecated. Move its callback body to a `ContextUsageEvent` subscription. Order matters: register the monitor _after_ a compaction capability to observe the corrected current history after same-cycle compaction, or before it to see what triggered the compaction.

`used_tokens` follows the accounting above: provider usage anchors include instructions, tool definitions, and `FilePart` payloads from the anchored request. The suffix after the anchor, or a history with no anchor, uses `tokenizer` or a ~4-characters-per-token heuristic and cannot see `FilePart` payloads. Pending newly revealed tool schemas are conservatively estimated by the implementation. When a compaction capability runs earlier in the same cycle, a monitor registered after it subtracts the rewrite's heuristic reclaim while retaining the anchor's fixed provider overhead.

## Compacting outside a run: `compact_now`

A strategy's `compact` takes a `RunContext`, which an application holding a conversation _between_ runs does not have -- and that is exactly when a user types `/compact`. `compact_now` builds a throwaway context so the same strategy the agent uses can be driven from a command handler:

```python
from pydantic_ai_harness import SummarizingCompaction
from pydantic_ai_harness.compaction import compact_now

strategy = SummarizingCompaction(max_fraction=0.9, keep_messages=20)
history = await compact_now(
    strategy,
    history,
    model='anthropic:claude-sonnet-5',
    focus='the auth refactor, not the earlier CSS work',
)
```

`compact_now` applies no trigger of its own, so a strategy whose `compact` is unconditional runs whatever the history size. A strategy that defines its own stop condition still honours it: `TieredCompaction` escalates only until the history fits its target, so a history already under target comes back unchanged. Pass the tier directly if you need it to run regardless.

`focus` steers strategies that write prose -- `SummarizingCompaction`, via the exported `SupportsFocus` protocol's `with_focus` -- and is passed over by the ones that drop or blank content by rule, since they have nothing to steer. `TieredCompaction` is focusable when any of its tiers is, so a focus reaches the summarizing tier rather than stopping at the wrapper.

A compaction that changes the history emits the same `compact_messages` span the in-run path emits, so an instrumented application sees one shape however compaction was triggered. Pass `tracer=` to record it; without one the span goes to a no-op tracer.

## The recommended default: `TieredCompaction`

The field consensus (Anthropic, OpenCode, Letta) is to clear and dedupe first, and summarize only when that is not enough. Summarization turns input tokens into output tokens, which are billed at a premium and generated serially, so it is genuinely expensive. The zero-LLM strategies touch only the cheaper input side.

`TieredCompaction` encodes that escalation: it runs each tier in order, re-measures the token count after each, and stops as soon as the conversation fits `target_tokens`. Order the tiers cheap-to-expensive so the expensive summarization tier is only reached when the cheap passes cannot reclaim enough.

```python
from pydantic_ai import Agent
from pydantic_ai_harness import ClearToolResults, DeduplicateFileReads, SummarizingCompaction, TieredCompaction
from pydantic_ai.messages import ToolCallPart


def my_file_key(call: ToolCallPart) -> str | None:
    if call.tool_name != 'read_file':
        return None
    return call.args_as_dict().get('path')


agent = Agent(
    'openai:gpt-5.6-luna',
    capabilities=[
        TieredCompaction(
            tiers=[
                DeduplicateFileReads(file_key=my_file_key),
                ClearToolResults(max_tokens=1, keep_pairs=3),
                SummarizingCompaction(max_messages=1, keep_messages=20),  # model inherits the run's
            ],
            target_tokens=120_000,
        )
    ],
)
```

A tier inside `TieredCompaction` is driven directly by the orchestrator, which re-measures after each tier and stops once under `target_tokens`. A tier's own `max_*` trigger is therefore irrelevant when it runs inside `TieredCompaction` -- set it to anything valid (for example `ClearToolResults(max_tokens=1)`). Any object with `async def compact(messages, ctx) -> list[ModelMessage]` (the `CompactionStrategy` protocol) can be a tier, so you can plug in your own.

## `FallbackCompaction`: recover when a strategy fails

`TieredCompaction` advances when a successful tier does not reclaim enough. `FallbackCompaction` advances only when a strategy raises an exception selected by `fallback_on`, which defaults to Pydantic AI's `ModelAPIError` and `FallbackExceptionGroup`. The latter is raised when every model in a `FallbackModel` fails. Each attempt receives a fresh list containing the original message objects, so list-level changes by a failed strategy do not affect its fallback. Strategies must still honor the `CompactionStrategy` contract and avoid mutating message objects. If every strategy fails, the last exception is re-raised. Non-matching exceptions, cancellation, and other `BaseException` subclasses pass through immediately; `fallback_on` rejects types that do not derive from `Exception`.

Use it as a tier when summarization should fall back to deterministic truncation:

```python
from pydantic_ai_harness import FallbackCompaction, SlidingWindowCompaction, SummarizingCompaction

fallback = FallbackCompaction(
    fallback_chain=[
        SummarizingCompaction(max_messages=1, keep_tokens=20_000),
        SlidingWindowCompaction(max_messages=1, keep_tokens=20_000),
    ]
)
```

The strategies' trigger fields are not consulted when a composing strategy calls `compact` directly. Put `fallback` inside `TieredCompaction` to give the chain a context trigger, or pass it to `compact_now` for manual compaction.

## `ClampOversizedMessages`: surviving a runaway generation

A single model response of repeated whitespace, or a single tool call with a giant payload, can produce one part so large the _next_ request exceeds the provider's context cap. None of the other strategies can reach it: `SlidingWindowCompaction` drops the oldest messages but the offender is the newest; `ClearToolResults` only touches tool _results_; `WarnNearLimits` never edits history; and feeding the history to `SummarizingCompaction` hits the same cap.

`ClampOversizedMessages` truncates the offending part in place, keeping a head slice and a tail slice with a `[clamped: removed N of M characters]` marker between them. Degenerate generations are low-entropy repetition, so a head/tail slice loses little.

```python
from pydantic_ai import Agent
from pydantic_ai_harness import ClampOversizedMessages

agent = Agent(
    'openai:gpt-5.6-terra',
    capabilities=[
        ClampOversizedMessages(max_part_tokens=50_000, keep_head_chars=2_000, keep_tail_chars=2_000)
    ],
)
```

A part is clamped only when it is oversized _and_ the clamp actually shrinks it, so keep `keep_head_chars + keep_tail_chars` well below your per-part threshold.

It clamps two kinds of part inside each `ModelResponse`:

-   **Response text** (`TextPart`) -- the critical case, a runaway model-response text part.
-   **Tool-call args** (`ToolCallPart`), when `clamp_tool_call_args=True` (the default) -- the same failure shape for a giant payload (for example a runaway `write_plan`). The args are replaced with a small JSON object `{"_clamped": "<head>...<tail>"}` so they stay valid function arguments; the original call already executed, so this only shrinks the history copy. Set `clamp_tool_call_args=False` to clamp response text only. Framework-typed call parts -- core's `search_tools` and `load_capability` calls -- are never clamped, because their typed args are validated when persisted history is restored (for example a `StepPersistence` resume) and the `_clamped` object would fail that round-trip.

Request-side parts (user prompts, tool _returns_, system prompts) are deliberately out of scope: user input should not be silently rewritten, and oversized tool returns are the job of `ClearToolResults`.

Use it as the first tier of `TieredCompaction`, before `ClearToolResults`:

```python
from pydantic_ai_harness import ClampOversizedMessages, ClearToolResults, TieredCompaction

TieredCompaction(
    tiers=[
        ClampOversizedMessages(max_part_tokens=50_000),
        ClearToolResults(max_tokens=1, keep_pairs=3),
    ],
    target_tokens=120_000,
)
```

## `ClearToolResults`: the cheap first tier

Tool outputs typically dominate an agent's context, and the agent can usually re-run a tool if it needs the data again. `ClearToolResults` replaces the content of the oldest tool _results_ with a short placeholder while keeping the most recent `keep_pairs` tool-call / tool-return pairs intact. The tool calls stay paired with their now-blanked results, so the history stays valid.

Framework-typed tool results -- core's `search_tools` and `load_capability` returns -- are left intact (a small token floor), because their structured content is re-parsed on later requests and rewriting it via `dataclasses.replace` would bypass validation and corrupt the part.

```python
from pydantic_ai import Agent
from pydantic_ai_harness import ClearToolResults

agent = Agent(
    'openai:gpt-5.6-luna',
    capabilities=[ClearToolResults(max_tokens=100_000, keep_pairs=3)],
)
```

Set `clear_tool_inputs=True` to also blank the arguments of the cleared calls, and `exclude_tools` to a set of tool names whose results are never cleared.

## `DeduplicateFileReads`: drop superseded reads

When the same file is read more than once, only the latest read keeps its content; earlier reads are blanked with a placeholder, with pairing preserved.

There is no default `file_key`: identifying a file read is agent-specific, and a wrong guess would drop live data. Supply a callable mapping a `ToolCallPart` to a stable file key, or `None` when the call is not a file read:

```python
from pydantic_ai import Agent
from pydantic_ai.messages import ToolCallPart
from pydantic_ai_harness import DeduplicateFileReads


def file_key(call: ToolCallPart) -> str | None:
    if call.tool_name != 'read_file':
        return None
    return call.args_as_dict().get('path')


agent = Agent('openai:gpt-5.6-terra', capabilities=[DeduplicateFileReads(file_key=file_key)])
```

With no `max_messages` or `max_tokens` trigger set, `DeduplicateFileReads` runs on every request. It is cheap and near-lossless, so that default is usually what you want.

## `SlidingWindowCompaction`: keep only the recent tail

When the conversation exceeds the configured threshold, `SlidingWindowCompaction` discards the oldest whole messages down to a tail, preserving tool-call / tool-return pairs. Reach for it when you only need the recent turns and can discard old context entirely.

```python
from pydantic_ai import Agent
from pydantic_ai_harness import SlidingWindowCompaction

agent = Agent(
    'openai:gpt-5.6-terra',
    capabilities=[SlidingWindowCompaction(max_messages=80, keep_messages=40)],
)
```

By default `preserve_first_user_message=True` keeps the first user turn (in addition to system prompts) even when it falls outside the window, so the agent does not lose the original task. Pass `keep_tokens` instead of `keep_messages` to trim to a token budget rather than a message count.

## `SummarizingCompaction`: compress, do not discard

When old context still matters but must be compressed, `SummarizingCompaction` summarizes the older messages with a dedicated model call and replaces them with a single structured summary, preserving the recent tail and tool-call integrity. It is the expensive tier, so it is best used behind the cheaper passes (see `TieredCompaction`).

```python
from pydantic_ai import Agent
from pydantic_ai_harness import SummarizingCompaction

agent = Agent(
    'anthropic:claude-opus-5',
    capabilities=[
        SummarizingCompaction(
            model='anthropic:claude-sonnet-5',
            max_messages=60,
            keep_messages=20,
        )
    ],
)
```

`model` accepts a model name or a `Model`; when left `None` it inherits the running agent's model. Its nested summary run inherits the parent usage limits and reserves one request from a finite request limit for the pending parent request. Pass `model_settings` to give the dedicated summary call settings that differ from defaults carried by that model; the supplied settings merge over the model defaults without mutating the model or the settings dictionary. By default `incremental=True` updates the newest existing summary as an anchor. This changes the summary-call prompt from earlier releases; set `incremental=False` to retain the prior regeneration behavior.

Both prompt surfaces of the summary request are fields: `summary_prompt` is the user-turn template (it must contain a `{messages}` placeholder), and `instructions` sets the internal agent's static instructions, which Pydantic AI sends in the request's system prompt. Override `instructions` when the summarizer endpoint requires a fixed leading instruction.

The messages served into that template are rendered to text, and each tool return is capped per return at `tool_return_max_chars` (default 500) characters using the same explicit truncation marker as kept user turns. Raise it, or set it to `None` to render each return whole, when the summarizer's context window is large enough to absorb the payloads. `max_tokens` and `keep_tokens` control when compaction runs and which history messages are retained; they do not cap the summary-request payload.

The summary request is non-streaming unless `event_stream_handler` is set. Supply a handler to watch the summary as it is written, or pass `drain_summary_events` to take the streaming request path without handling the events -- which is what a summarizer endpoint that rejects non-streaming requests needs:

```python
from pydantic_ai import Agent
from pydantic_ai_harness.compaction import SummarizingCompaction, drain_summary_events

agent = Agent(
    'openai:gpt-5.6-terra',
    capabilities=[
        SummarizingCompaction(max_messages=60, event_stream_handler=drain_summary_events),
    ],
)
```

Neither transport works everywhere, which is why this is a choice rather than a default: some endpoints reject non-streaming requests and others reject streaming ones. The handler receives the summary run's own `RunContext` and event stream; the outer `Agent.run(...)` handler is not inherited and never sees the summary token deltas.

### Usage accounting

The summary call is a real request to the model, so its full usage -- tokens **and** the request itself -- is folded into the run's `ctx.usage`. This is deliberate: it keeps cost honest, keeps the request count consistent (a model request that did not count as one would be the surprise), and lets a `UsageLimits` request limit catch a runaway compaction. The nested run receives the other parent limits unchanged; the finite request limit is reduced by one so it cannot spend the slot already approved for the parent request. A run-request or iteration limiter will therefore see compaction calls among its requests.

With a durable-execution capability attached, the summary call runs as a contributed durable operation, so replay uses the recorded summary instead of calling the model again. When `model` is not set, the operation uses the run's model. The capability carries a stable default `id`, which durable execution uses to recover the operation by the same identity. Overriding it with a custom value orphans recorded operations for in-flight workflows, so keep it fixed once a workflow is live.

## `WarnNearLimits`: warn instead of rewrite

`WarnNearLimits` never edits history. As the run approaches a configured limit, it injects an URGENT (then CRITICAL) warning as a trailing user turn, so the model wraps up rather than having its context rewritten under it. Models tend to pay more attention to user messages than system messages, which is why the warning is a user turn. Previous warnings from this capability are stripped before deciding whether to inject a new one.

```python
from pydantic_ai import Agent
from pydantic_ai_harness import WarnNearLimits

agent = Agent(
    'google:gemini-3.6-flash',
    capabilities=[
        WarnNearLimits(
            max_iterations=40,
            max_context_tokens=100_000,
        )
    ],
)
```

Warnings begin at `warning_threshold` (default `0.7`, a fraction of the limit) and become CRITICAL for iterations once the remaining request count drops to `critical_remaining_iterations` (default `3`). It watches three kinds of limit -- `max_iterations`, `max_context_tokens` (or `max_context_fraction`), and `max_total_tokens` -- and by default warns on whichever are configured; narrow that with `warn_on`.

## Cache tradeoff

Clearing, deduplicating, clamping, and summarizing all rewrite message content, which invalidates the provider's prompt cache from the edit point onward -- the next request pays a cache-write. For `ClearToolResults`, use `min_clear_tokens` to skip clearing that reclaims too little to be worth busting the cache. For `ClampOversizedMessages` the cache bust is unavoidable, because the alternative is a failed request.

## Tracing

When core instrumentation is active (the `Instrumentation` capability, `agent.instrument`, or `Agent.instrument_all()`), each strategy emits a `compact_messages` span on the run's tracer the moment it actually compacts -- that is, in `before_model_request`, once the strategy's threshold is exceeded (`ClampOversizedMessages` emits only when a part is actually clamped). `TieredCompaction` emits a single span for the whole escalation rather than one per tier, because it drives each tier's `compact` directly. Without instrumentation the tracer is a no-op, so the span adds no overhead.

The span name is the static `compact_messages`; the strategy is an attribute, not part of the name, to keep span cardinality low. Attributes:

Attribute

Type

Meaning

`gen_ai.conversation.compacted`

bool

Always `true`; the OpenTelemetry GenAI convention's flag for a compacted context

`compaction.strategy`

str

Strategy class name (for example `SlidingWindowCompaction`, `SummarizingCompaction`)

`compaction.messages_before`

int

Message count before compaction

`compaction.messages_after`

int

Message count after compaction

`compaction.tokens_before`

int

Estimated token count before compaction

`compaction.tokens_after`

int

Estimated token count after compaction

`gen_ai.conversation.compacted` is the GenAI semantic convention's flag; the rest is harness-specific. Token counts use the strategy's `tokenizer` when set, otherwise the ~4-chars-per-token heuristic. Raw message content is not recorded.

`SummarizingCompaction` runs its summarizer as a nested `Agent` named `summarizing_compaction`, so under `Agent.instrument_all()` (or `logfire.instrument_pydantic_ai()`) its runs carry `agent_name = summarizing_compaction`. Filter on that to track summarization usage and cost separately from the parent agent.

## Compaction receipts

Compaction is a memory wipe the model cannot veto and often cannot detect, which invites _resumption drift_ -- the model confabulates continuity with history it no longer has. A receipt makes the wipe legible: after a boundary-crossing strategy rewrites history it appends a short, deterministic note recording how much was compacted, warning that what survives is secondhand, and -- when a handle provider is attached -- an identifier for persisted run history.

```python
from pydantic_ai_harness import SlidingWindowCompaction, SummarizingCompaction

SummarizingCompaction(max_messages=60, keep_messages=20, receipts=True)
SlidingWindowCompaction(max_messages=80, keep_messages=40, receipts=True)
```

The receipt text carries no timestamp, so it is a pure function of the compaction. The message part still has its ordinary request timestamp.

Wording follows what actually survived. `SummarizingCompaction` leaves a summary, so its receipt says the summary above is secondhand; `SlidingWindowCompaction` drops history outright, so its receipt says that context is gone. The blank-in-place strategies (`ClearToolResults`, `DeduplicateFileReads`, `ClampOversizedMessages`) keep every message and cross no boundary, so they emit no receipt.

Attach any capability exposing `compaction_transcript_handle() -> str | None` -- the `TranscriptHandleProvider` protocol -- and the receipt gains a `Persisted run handle: <handle>` pointer. `StepPersistence` implements it, returning its `run_id`, so attaching it is enough. Each receipt is also emitted as a `compaction.receipt` event on the `compact_messages` span, carrying `compaction.receipt.strategy`, `compaction.receipt.messages_dropped`, `compaction.receipt.tokens_dropped`, `compaction.receipt.by`, and `compaction.receipt.handle` when a handle was found.

The handle addresses the **persisted run**, not a pristine transcript. Compaction's edits persist into the run's message history, so the run's latest snapshot reflects the _compacted_ history -- reading it back does not recover what the receipt says was dropped. A store keeping per-step snapshots may still hold pre-compaction steps, subject to its own retention (`max_snapshots_per_run` on the shipped stores). Treat the handle as a pointer to the run, and check your store's retention before promising an agent it can read the original.

The receipt's `by` attribution uses the same coarse family heuristic as the bridge prefix, with the same approximations -- see [the note below](#anchored-incremental-summarization-and-the-cross-model-bridge).

Receipts are opt-in (`receipts=False` by default) because the receipt text is content: the exact wording is provisional pending a benchmark eval-rig pass, while the mechanism is structural.

## Pinning: content that survives compaction

`pin` marks content that every shipped strategy must preserve:

```python
from pydantic_ai_harness.compaction import pin

# In a ModelRequest placed in the run's message history (by a capability or the user):
pinned = pin('Durable task state the model must never lose across compaction.')
```

A pinned part is never summarized away or dropped; if a strategy would have discarded it, the strategy re-injects it near the top of the surviving history. `is_pinned` reports whether a given part carries the marker.

Pins use model-invisible `TextContent.metadata`, so their contents remain ordinary user context while compaction can distinguish them from user turns.

The `Planning` capability does not need pinning: its plan is re-injected ephemerally on every request in `wrap_model_request`, so it already survives compaction by construction. Pinning is for durable task state and scratchpads that live _in_ the history.

## Keeping user messages (`keep_user_messages`)

User turns are the highest signal-per-token content in a conversation, and losing them is the main driver of resumption drift. `SummarizingCompaction(keep_user_messages=True)` preserves the newest user turns from the summarized prefix alongside the summary. They consume the existing `keep_messages` tail budget, so at most that many retained user messages and tail messages survive together; compaction therefore does not grow retained copies on each cycle. When `keep_tokens` is set, those same retained user messages and tail messages also share its token budget; a user turn that does not fit is summarized instead. Each retained turn is bounded to `keep_user_messages_max_chars` (default 20k) with an explicit truncation marker when it overruns. The character budget applies per part and is shared across the text items of a multi-part prompt; images, audio, and cache points pass through untouched. This supersedes `preserve_first_user_message`, which keeps only the first turn.

```python
from pydantic_ai_harness import SummarizingCompaction

SummarizingCompaction(max_tokens=120_000, keep_messages=20, keep_user_messages=True)
```

Retaining user turns leaves the summary, any receipt, and the retained turns as adjacent `ModelRequest`s. Providers that require one request per turn -- Bedrock Converse and Gemini among them -- never see that shape: Pydantic AI normalizes the history with `_merge_consecutive_messages` after the `before_model_request` hooks run, combining adjacent requests into a single turn before dispatch. `keep_user_messages` therefore needs no provider-specific handling.

## Anchored incremental summarization and the cross-model bridge

With `incremental=True` (the default), a prior summary is not re-summarized -- summarizing summaries decays over successive compactions. It is fed back as an anchored `<previous-summary>` block with an _update_ instruction: preserve still-true details, remove stale ones, merge in new facts. The summary becomes a living document updated in place under a fixed structure.

Behavior change: `incremental=True` is the default

Every existing `SummarizingCompaction` user gets a different summary-call prompt from this release on: once a prior summary exists, the summarizer is asked to _update_ it under `<previous-summary>` rather than regenerate one from the conversation. The summaries it produces will read differently. Set `incremental=False` to keep the previous regenerate-from-scratch behavior.

`bridge_prefix=True` prepends a one-line note to the summary only when the summarizer's model family differs from the family that produced the history, derived from the history's `model_name` and the summarizer config. It marks the summary as a cross-model handoff so the resuming model builds on it rather than confabulating that it did the work itself. It never fires in the common same-model case, so it is cheap. It defaults to `False` because the note is prompt content.

The family token is a coarse approximation: drop any `provider:` prefix, then take the leading token before the first `-` or `/`. It separates `gpt` from `claude` on ordinary references (`openai:gpt-5.6-luna` -> `gpt`, `google:gemini-3.6-flash` -> `gemini`) and misreads several real ones -- `us.anthropic.claude-sonnet-4-5-v1:0` reduces to `0`, `ollama/llama3` to `ollama`, and a `fallback:` model _string_ to its last listed model rather than its first. A `FallbackModel` object is read correctly, from its first model. So bridge and receipt attribution are best-effort: a misread family can suppress a bridge note or fire one between two same-family models. Neither outcome changes what compaction keeps or drops.

As with receipts, the update instruction and the bridge-prefix wording are content, shipped minimal and neutral pending the eval-rig pass; the anchoring and family-gating mechanisms are structural.

## Out of scope

These strategies compress or drop context _inside_ the window. Moving large tool outputs _out_ of the window -- overflowing them to a file the agent (or a subagent) can query on demand -- is a separate capability ([tool output limits](https://pydantic.dev/docs/ai/harness/tool-output-limits/)), not lossy truncation. Within `SummarizingCompaction`, `tool_return_max_chars` makes the summarizer's per-return cap tunable (or `None` to render returns whole), but the summary request still reads a lossy rendering; prefer tool output limits when a payload must be queryable in full.

## API reference

The recommended default is `TieredCompaction`; the other strategies below can be used standalone or plugged in as its tiers.

### TieredCompaction

**Bases:** `AbstractCapability[AgentDepsT]`

Escalation orchestrator over a sequence of compaction strategies.

Runs each tier in order, re-measuring the token count after each, and stops as soon as the conversation fits `target_tokens`. Order tiers cheap-to-expensive (e.g. clear tool results, deduplicate reads, then summarize) so the expensive summarization tier is only reached when the cheap passes cannot reclaim enough.

Each tier's own trigger is bypassed -- `TieredCompaction` drives the tiers directly via their `compact` method and decides when to stop.

#### Attributes

##### tiers

Strategies to apply in order, cheap-to-expensive. The last is typically a summarizer.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`CompactionStrategy`\[`AgentDepsT`\]\]

##### target\_tokens

Stop escalating once the estimated token count is at or below this value.

Mutually exclusive with `target_fraction`; exactly one of the two must be set.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### target\_fraction

Target expressed as a fraction of the model's context window, resolved per request.

Use this instead of `target_tokens` when the same agent runs on models with different windows. Mutually exclusive with `target_tokens`.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### context\_window

Window override in tokens. `None` resolves it from the request's model.

Unlike `fallback_context_window`, this applies whether or not resolution succeeds. Reach for it when the registry is confidently wrong: a beta- or tier-gated window it records as the maximum, or a self-hosted endpoint whose model id describes someone else's deployment. Only consulted alongside `target_fraction`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### fallback\_context\_window

Window assumed when the model is not in the pricing registry.

Only consulted alongside `target_fraction`. Supply the real number for a deployment the registry cannot resolve.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `field(default=DEFAULT_CONTEXT_WINDOW, kw_only=True)`

##### tokenizer

Optional tokenizer for accurate token counting.

A callable that returns the token count for a given string. When `None`, uses a ~4 characters-per-token heuristic.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], [`int`](https://docs.python.org/3/builtins/functions.html#int)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### with\_focus

```python
def with_focus(focus: str) -> TieredCompaction[AgentDepsT]
```

Return a copy whose focus-capable tiers prioritize `focus`.

A tiered strategy is focusable when any of its tiers is: the summarizing tier writes the prose, so the hint has to reach it rather than stopping at this wrapper. Tiers that cannot honour a focus are passed through unchanged.

###### Returns

`TieredCompaction`\[`AgentDepsT`\]

##### compact

`@async`

```python
def compact(
    messages: list[ModelMessage],
    ctx: RunContext[AgentDepsT],
) -> list[ModelMessage]
```

Apply tiers in order until the history fits the target or tiers run out.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### before\_model\_request

`@async`

```python
def before_model_request(
    ctx: RunContext[AgentDepsT],
    request_context: ModelRequestContext,
) -> ModelRequestContext
```

Escalate through the tiers when the conversation exceeds the target.

###### Returns

[`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

### ClampOversizedMessages

**Bases:** `AbstractCapability[AgentDepsT]`

Zero-cost head/tail truncation of any single oversized message part.

A runaway generation -- a model response of repeated whitespace, a giant tool-call payload -- can produce one part so large the next request exceeds the provider's context cap. The size-based strategies cannot help: `SlidingWindowCompaction` drops the _oldest_ messages (the offender is the newest), `ClearToolResults` only touches tool _results_, and feeding the history to `SummarizingCompaction` hits the same cap. This strategy truncates the offending part in place: it keeps a head slice and a tail slice and inserts a marker for the removed middle. Degenerate generations are low-entropy repetition, so a head/tail slice loses little. No LLM calls are made.

What it clamps, in each `ModelResponse`:

-   `TextPart` content (the critical case -- a runaway model-response text part).
-   `ToolCallPart` args, when `clamp_tool_call_args` is set (the same failure shape for a giant tool-call payload). The args are replaced with a small JSON object so they stay valid function arguments; the original call already executed, so this only shrinks the history copy. Framework-typed subclasses (`ToolSearchCallPart`, `LoadCapabilityCallPart`) are never clamped: their typed args must survive the `ModelMessagesTypeAdapter` round-trip that persistence relies on.

Request-side parts (user prompts, tool returns, system prompts) are out of scope: user input should not be silently rewritten, and oversized tool _returns_ are the job of `ClearToolResults`.

Clamping rewrites message content, so it invalidates the provider's prompt cache from the clamped message onward. That is unavoidable here -- the alternative is a failed request.

A part is clamped only when it is oversized _and_ the clamp actually shrinks it, so set `keep_head_chars` + `keep_tail_chars` well below your per-part threshold.

Composes as the first tier of a `TieredCompaction` (run it before `ClearToolResults`): it is the only zero-LLM way to keep a run alive after a runaway generation.

#### Attributes

##### max\_part\_tokens

Clamp a part whose estimated token count exceeds this value. `None` disables this trigger.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_part\_chars

Clamp a part whose character count exceeds this value. `None` disables this trigger.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### keep\_head\_chars

Characters of the part's head to retain.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `2000`

##### keep\_tail\_chars

Characters of the part's tail to retain.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `2000`

##### clamp\_tool\_call\_args

When `True`, also clamp oversized `ToolCallPart` args, not just response text.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### tokenizer

Optional tokenizer for accurate token counting.

A callable that returns the token count for a given string. When `None`, uses a ~4 characters-per-token heuristic.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], [`int`](https://docs.python.org/3/builtins/functions.html#int)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### compact

`@async`

```python
def compact(
    messages: list[ModelMessage],
    ctx: RunContext[AgentDepsT],
) -> list[ModelMessage]
```

Clamp every oversized response text part (and tool-call args, if enabled).

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### before\_model\_request

`@async`

```python
def before_model_request(
    ctx: RunContext[AgentDepsT],
    request_context: ModelRequestContext,
) -> ModelRequestContext
```

Clamp any oversized response part before the request is sent.

###### Returns

[`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

### ClearToolResults

**Bases:** `AbstractCapability[AgentDepsT]`

Zero-cost in-place clearing of old tool results.

Replaces the content of the oldest tool _results_ with a short placeholder while keeping the most recent `keep_pairs` tool-call / tool-return pairs intact. Tool calls remain paired with their (now-blanked) results, so the history stays valid. No LLM calls are made.

This is the cheap first tier of compaction -- tool results typically dominate context, and the agent can re-run a tool if it needs the data again.

Cache tradeoff: clearing rewrites message content, which invalidates the provider's prompt cache from the clear point onward (the next request pays a cache-write). Use `min_clear_tokens` to skip clearing that reclaims too little to be worth busting the cache.

#### Attributes

##### max\_messages

Trigger clearing when message count exceeds this value. `None` disables.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_tokens

Trigger clearing when estimated token count exceeds this value. `None` disables.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_fraction

Trigger when estimated tokens exceed this fraction of the model's context window.

Resolved per request from the request's model, so one setting behaves correctly on any model. Mutually exclusive with `max_tokens`.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### context\_window

Window override in tokens. `None` resolves it from the request's model.

Unlike `fallback_context_window`, this applies whether or not resolution succeeds. Reach for it when the registry is confidently wrong: a beta- or tier-gated window it records as the maximum, or a self-hosted endpoint whose model id describes someone else's deployment. Only consulted alongside `max_fraction`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### fallback\_context\_window

Window assumed when the request's model is not in the pricing registry.

Only consulted alongside `max_fraction`. Supply the real number for a deployment the registry cannot resolve.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `field(default=DEFAULT_CONTEXT_WINDOW, kw_only=True)`

##### keep\_pairs

Number of most-recent tool-call / tool-return pairs left untouched.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `3`

##### placeholder

Replacement content for a cleared tool result.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'[tool result cleared]'`

##### exclude\_tools

Tool names whose results are never cleared.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `frozenset()`

##### clear\_tool\_inputs

When `True`, also blank the arguments of the cleared tool calls.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### min\_clear\_tokens

Only clear if doing so reclaims at least this many estimated tokens.

Protects the prompt cache from being invalidated for a trivial gain. `None` always clears.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tokenizer

Optional tokenizer for accurate token counting.

A callable that returns the token count for a given string. When `None`, uses a ~4 characters-per-token heuristic.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], [`int`](https://docs.python.org/3/builtins/functions.html#int)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### compact

`@async`

```python
def compact(
    messages: list[ModelMessage],
    ctx: RunContext[AgentDepsT],
) -> list[ModelMessage]
```

Blank the oldest tool results beyond the most recent `keep_pairs`.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### before\_model\_request

`@async`

```python
def before_model_request(
    ctx: RunContext[AgentDepsT],
    request_context: ModelRequestContext,
) -> ModelRequestContext
```

Clear old tool results if the conversation exceeds the configured threshold.

###### Returns

[`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

### DeduplicateFileReads

**Bases:** `AbstractCapability[AgentDepsT]`

Zero-cost in-place clearing of superseded file reads.

When the same file is read more than once, only the latest read keeps its content; earlier reads are blanked with a placeholder. Tool-call pairing is preserved. No LLM calls are made.

File identity is supplied by the `file_key` seam -- given a `ToolCallPart` it returns a stable key for the file being read, or `None` if the call is not a file read. There is no default: file-read identification is agent-specific, and a wrong guess would drop live data.

#### Attributes

##### file\_key

Map a tool call to a stable file key, or `None` if it is not a file read.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`ToolCallPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ToolCallPart)\], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)\]

##### placeholder

Replacement content for a superseded file read.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'[superseded file read]'`

##### max\_messages

Optional message-count trigger. When both triggers are `None`, runs whenever invoked.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_tokens

Optional token-count trigger. When both triggers are `None`, runs whenever invoked.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_fraction

Trigger when estimated tokens exceed this fraction of the model's context window.

Resolved per request from the request's model, so one setting behaves correctly on any model. Mutually exclusive with `max_tokens`.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### context\_window

Window override in tokens. `None` resolves it from the request's model.

Unlike `fallback_context_window`, this applies whether or not resolution succeeds. Reach for it when the registry is confidently wrong: a beta- or tier-gated window it records as the maximum, or a self-hosted endpoint whose model id describes someone else's deployment. Only consulted alongside `max_fraction`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### fallback\_context\_window

Window assumed when the request's model is not in the pricing registry.

Only consulted alongside `max_fraction`. Supply the real number for a deployment the registry cannot resolve.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `field(default=DEFAULT_CONTEXT_WINDOW, kw_only=True)`

##### tokenizer

Optional tokenizer for accurate token counting.

A callable that returns the token count for a given string. When `None`, uses a ~4 characters-per-token heuristic.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], [`int`](https://docs.python.org/3/builtins/functions.html#int)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### compact

`@async`

```python
def compact(
    messages: list[ModelMessage],
    ctx: RunContext[AgentDepsT],
) -> list[ModelMessage]
```

Blank every file read that is later superseded by a newer read of the same file.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### before\_model\_request

`@async`

```python
def before_model_request(
    ctx: RunContext[AgentDepsT],
    request_context: ModelRequestContext,
) -> ModelRequestContext
```

Deduplicate file reads, optionally gated on a size threshold.

###### Returns

[`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

### SlidingWindowCompaction

**Bases:** `AbstractCapability[AgentDepsT]`

Zero-cost sliding-window trimmer.

When the conversation exceeds a configurable threshold (message count or estimated token count), the oldest messages are discarded while preserving tool-call / tool-return pairs. No LLM calls are made.

Trimming happens in `before_model_request` so it is transparent to the rest of the agent run.

#### Attributes

##### max\_messages

Trigger trimming when message count exceeds this value. `None` disables.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_tokens

Trigger trimming when estimated token count exceeds this value. `None` disables.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_fraction

Trigger when estimated tokens exceed this fraction of the model's context window.

Resolved per request from the request's model, so one setting behaves correctly on any model. Mutually exclusive with `max_tokens`.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### context\_window

Window override in tokens. `None` resolves it from the request's model.

Unlike `fallback_context_window`, this applies whether or not resolution succeeds. Reach for it when the registry is confidently wrong: a beta- or tier-gated window it records as the maximum, or a self-hosted endpoint whose model id describes someone else's deployment. Only consulted alongside `max_fraction`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### fallback\_context\_window

Window assumed when the request's model is not in the pricing registry.

Only consulted alongside `max_fraction`. Supply the real number for a deployment the registry cannot resolve.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `field(default=DEFAULT_CONTEXT_WINDOW, kw_only=True)`

##### keep\_messages

Number of tail messages to retain after trimming (message-count trigger).

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `40`

##### keep\_tokens

Target token budget after trimming (token-count trigger).

When `None`, falls back to `keep_messages`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### tokenizer

Optional tokenizer for accurate token counting.

A callable that returns the token count for a given string. When `None`, uses a ~4 characters-per-token heuristic.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], [`int`](https://docs.python.org/3/builtins/functions.html#int)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### preserve\_first\_user\_message

When `True`, the first `ModelRequest` containing a `UserPromptPart` is always kept after trimming, in addition to system prompts.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### receipts

When `True`, prepend a deterministic compaction receipt recording how much history was dropped, with a transcript handle when a `TranscriptHandleProvider` capability is attached.

Opt-in for now: the receipt text is content, so defaulting it on is deferred to the benchmark eval-rig pass. The mechanism itself is structural.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

#### Methods

##### compact

`@async`

```python
def compact(
    messages: list[ModelMessage],
    ctx: RunContext[AgentDepsT],
) -> list[ModelMessage]
```

Drop the oldest messages down to the configured tail.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### before\_model\_request

`@async`

```python
def before_model_request(
    ctx: RunContext[AgentDepsT],
    request_context: ModelRequestContext,
) -> ModelRequestContext
```

Trim the message list if it exceeds the configured threshold.

###### Returns

[`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

### SummarizingCompaction

**Bases:** `AbstractCapability[AgentDepsT]`

LLM-powered conversation compaction.

When the conversation exceeds a configurable threshold, older messages are summarized using a dedicated model call and replaced with a compact, structured summary message, preserving recent context and tool-call integrity.

This is the expensive tier -- summarization turns input tokens into (pricier) output tokens -- so it is best used behind cheaper passes (see `TieredCompaction`).

The summary call's usage is folded into the parent run's usage (it counts as a real request), so cost accounting stays honest; note this also increments the run's request count, which a request-count limiter would see.

#### Attributes

##### model

Model used to generate summaries.

When `None`, inherits the model the request being compacted is going to. Core starts that as the run's model, so the two differ only where a capability replaced `ModelRequestContext.model`; set this explicitly to pin the summarizer regardless.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | `Model` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### model\_settings

Settings for the dedicated summary model call.

These merge over defaults carried by `model`, allowing the summary call to use a policy that differs from the running agent without mutating the model.

**Type:** [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### event\_stream\_handler

If set, this handler is passed to the nested summary run, so the summarizer's own model-streaming events surface to the caller.

Setting it also selects the streaming request path, which is what a summarizer endpoint that rejects non-streaming requests needs; pass `drain_summary_events` to take that path without handling the events. Left `None`, the summary request is non-streaming, which is what an endpoint that rejects streaming requests needs. The handler receives the summary run's own `RunContext`, never the outer run's, and the outer `Agent.run(...)` handler is not inherited.

**Type:** `EventStreamHandler`\[[`object`](https://docs.python.org/3/glossary.html#term-object)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### max\_messages

Trigger compaction when message count exceeds this value.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_tokens

Trigger compaction when estimated token count exceeds this value.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_fraction

Trigger when estimated tokens exceed this fraction of the model's context window.

Resolved per request from the request's model, so one setting behaves correctly on any model. Mutually exclusive with `max_tokens`.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### context\_window

Window override in tokens. `None` resolves it from the request's model.

Unlike `fallback_context_window`, this applies whether or not resolution succeeds. Reach for it when the registry is confidently wrong: a beta- or tier-gated window it records as the maximum, or a self-hosted endpoint whose model id describes someone else's deployment. Only consulted alongside `max_fraction`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### fallback\_context\_window

Window assumed when the request's model is not in the pricing registry.

Only consulted alongside `max_fraction`. Supply the real number for a deployment the registry cannot resolve.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `field(default=DEFAULT_CONTEXT_WINDOW, kw_only=True)`

##### keep\_messages

Number of tail messages to preserve after compaction (message-count trigger).

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `20`

##### keep\_tokens

Target token budget to preserve after compaction (token-count trigger).

When `None`, falls back to `keep_messages`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### summary\_prompt

Prompt template for generating summaries.

Must contain a `{messages}` placeholder.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `_DEFAULT_SUMMARY_PROMPT`

##### instructions

Instructions for the internal agent that writes the summary.

`summary_prompt` shapes the user turn of the summary request; this sets the internal agent's static instructions, which Pydantic AI sends in the request's system prompt. Override it when the summarizer endpoint requires a fixed leading instruction.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `field(default=_DEFAULT_INSTRUCTIONS, kw_only=True)`

##### tokenizer

Optional tokenizer for accurate token counting.

A callable that returns the token count for a given string. When `None`, uses a ~4 characters-per-token heuristic.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], [`int`](https://docs.python.org/3/builtins/functions.html#int)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### preserve\_first\_user\_message

When `True`, the first `ModelRequest` containing a `UserPromptPart` is always kept after compaction, in addition to system prompts.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### incremental

When `True`, feed any existing summary from a prior compaction back as an anchored `<previous-summary>` block with an update instruction (preserve still-true, remove stale, merge new) so it is updated in place rather than re-summarized -- avoiding summary-of-summary decay.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### bridge\_prefix

When `True` and the summarizer's model family differs from the family that produced the history, prepend a neutral one-line note marking the summary as a cross-model handoff (Codex prior art, anti-confabulation). Only fires on a genuine family mismatch, so it is cheap and off in the common same-model case; the note's wording is flagged pending eval-rig.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### keep\_user\_messages

When `True`, preserve recent summarized user messages (each truncated to `keep_user_messages_max_chars`) alongside the summary. Retained messages consume the `keep_messages` tail budget, keeping compaction bounded. Supersedes `preserve_first_user_message`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### keep\_user\_messages\_max\_chars

Per-message character cap for `keep_user_messages`; oversized messages are truncated with an explicit marker (the shared truncation-marker convention).

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `20000`

##### tool\_return\_max\_chars

Per-return character cap when rendering tool results for the summarizer. `None` renders them whole.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=500, kw_only=True)`

##### receipts

When `True`, append a deterministic compaction receipt after the summary noting how much history was summarized, that the summary is secondhand, and -- when a `TranscriptHandleProvider` capability is attached -- a persisted-run handle.

Opt-in for now: the receipt text is content, so defaulting it on is deferred to the benchmark eval-rig pass. The mechanism itself is structural.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

#### Methods

##### with\_focus

```python
def with_focus(focus: str) -> SummarizingCompaction[AgentDepsT]
```

Return a copy whose summary prompt prioritizes `focus`.

Used by `compact_now` so a user-invoked compaction can say what the summary must not lose. The prompt is later run through `str.format`, so braces in a user- or model-supplied focus are escaped to survive it.

###### Returns

`SummarizingCompaction`\[`AgentDepsT`\]

##### compact

`@async`

```python
def compact(
    messages: list[ModelMessage],
    ctx: RunContext[AgentDepsT],
) -> list[ModelMessage]
```

Summarize older messages, replacing them with a single summary message.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

##### before\_model\_request

`@async`

```python
def before_model_request(
    ctx: RunContext[AgentDepsT],
    request_context: ModelRequestContext,
) -> ModelRequestContext
```

Summarize older messages when the threshold is exceeded.

###### Returns

[`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

### WarnNearLimits

**Bases:** `AbstractCapability[AgentDepsT]`

Injects a warning message when the agent approaches configured limits.

The warning is appended as a trailing `ModelRequest` with a `UserPromptPart` so that the model treats it as a distinct user turn (models tend to pay more attention to user messages than system messages).

Previous warnings injected by this capability are stripped before deciding whether to inject a new one.

#### Attributes

##### max\_iterations

Maximum allowed requests for the run.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_context\_tokens

Maximum context-window size to warn against.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_context\_fraction

Context limit as a fraction of the model's real context window, resolved per request.

Use this instead of `max_context_tokens` when the same agent runs on models with different windows. Mutually exclusive with `max_context_tokens`.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### context\_window

Window override in tokens. `None` resolves it from the request's model.

Unlike `fallback_context_window`, this applies whether or not resolution succeeds. Reach for it when the registry is confidently wrong: a beta- or tier-gated window it records as the maximum, or a self-hosted endpoint whose model id describes someone else's deployment. Only consulted alongside `max_context_fraction`.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, kw_only=True)`

##### fallback\_context\_window

Window assumed when the request's model is not in the pricing registry.

Only consulted alongside `max_context_fraction`. Supply the real number for a deployment the registry cannot resolve.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `field(default=DEFAULT_CONTEXT_WINDOW, kw_only=True)`

##### max\_total\_tokens

Maximum cumulative run token budget to warn against.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### warn\_on

Which limits should emit warnings. Defaults to all configured limits.

**Type:** [`list`](https://docs.python.org/3/glossary.html#term-list)\[`WarningKind`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### warning\_threshold

Fraction of a limit at which warnings begin (between 0 and 1).

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) **Default:** `0.7`

##### critical\_remaining\_iterations

Remaining request count at which iteration warnings become CRITICAL.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `3`

#### Methods

##### before\_model\_request

`@async`

```python
def before_model_request(
    ctx: RunContext[AgentDepsT],
    request_context: ModelRequestContext,
) -> ModelRequestContext
```

Strip old warnings, then inject a new one if thresholds are exceeded.

###### Returns

[`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

### ReportContextUsage

**Bases:** `AbstractCapability[AgentDepsT]`

Report context usage to the application before each model request.

A compaction strategy knows when to act but says nothing about how close the run is to the limit, so an application that wants to show "context: 73%" has to re-count the history itself and guess the denominator. This capability does neither: it reuses the same estimator the strategies use and the model's real context window.

It only observes -- it never edits the history.

Order matters: register it _after_ a compaction capability to see the compacted history, or before it to see what triggered the compaction. After a preceding compactor rewrites anchored history, the reading subtracts that compactor's heuristic reclaim while retaining the anchor's fixed provider overhead.

#### Attributes

##### on\_usage

Deprecated callback with a fresh reading before every model request.

Subscribe to `ContextUsageEvent` instead. A coroutine function is awaited and an exception raised here propagates and fails the run.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[`ContextUsage`\], [`None`](https://docs.python.org/3/builtins/constants.html#None) | [`Awaitable`](https://docs.python.org/3/library/typing.html#typing.Awaitable)\[[`None`](https://docs.python.org/3/builtins/constants.html#None)\]\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### context\_window

Window override in tokens. `None` resolves it from the request's model.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### fallback\_context\_window

Window assumed when the request's model is not in the pricing registry.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `DEFAULT_CONTEXT_WINDOW`

##### tokenizer

Optional tokenizer, matching the one your compaction strategy uses.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\], [`int`](https://docs.python.org/3/builtins/functions.html#int)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### before\_model\_request

`@async`

```python
def before_model_request(
    ctx: RunContext[AgentDepsT],
    request_context: ModelRequestContext,
) -> ModelRequestContext
```

Measure the pending history, emit it, and invoke the compatibility callback.

###### Returns

[`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

### ContextUsage

A single reading of how full the context is.

#### Attributes

##### used\_tokens

Estimated tokens in the message history about to be sent.

Counted by `estimate_context_tokens`: the provider-reported usage of the most recent model response (tool schemas included) plus an estimate of messages and newly revealed tool schemas added since. With no reported usage, message text falls back to the character heuristic; schemas named by availability deltas are still estimated from the pending request parameters, but other tool schemas remain outside that heuristic.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### window\_tokens

Context window the reading is measured against.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### resolved

Whether `window_tokens` is the model's real window or the fallback.

A gauge can render an unresolved window differently -- the percentage is a guess when the model is not in the pricing registry.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

##### fraction

`used_tokens` as a fraction of the window.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float)

### pin

```python
def pin(content: str) -> UserPromptPart
```

Mark _content_ so every shipped compaction strategy preserves it.

The returned `UserPromptPart` can be placed in a `ModelRequest` in the run's message history (e.g. by a capability or by the user); compaction keeps it verbatim.

#### Returns

[`UserPromptPart`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.UserPromptPart)

### is\_pinned

```python
def is_pinned(part: object) -> bool
```

Return True if _part_ carries the pin metadata marker.

#### Returns

[`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### reinject\_pinned

```python
def reinject_pinned(
    original: Sequence[ModelMessage],
    compacted: list[ModelMessage],
) -> list[ModelMessage]
```

Re-inject any pinned parts from _original_ that _compacted_ dropped.

Pinned parts already present in _compacted_ are left where they are; missing ones are gathered into a single `ModelRequest` placed right after any leading system/summary messages, so they sit near the top of the surviving history. A no-op when _original_ has no pins or all pins survived, so it is always safe to call.

#### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`ModelMessage`](https://pydantic.dev/docs/ai/api/pydantic-ai/messages/#pydantic_ai.messages.ModelMessage)\]

### TranscriptHandleProvider

**Bases:** [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

A capability that can hand out a handle for its persisted run history.

Any capability implementing this method is discovered from `RunContext.capabilities`; the first non-`None` handle is used. `StepPersistence` implements it by returning its `run_id`.

---
