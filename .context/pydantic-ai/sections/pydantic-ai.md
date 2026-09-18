# [Pydantic AI](https://pydantic.dev/docs/ai/overview/)

> How Python does AI: agents, realtime voice, image generation, embeddings. Every model, every interface, typed end to end.

# Pydantic AI

![Pydantic AI](https://pydantic.dev/docs/ai/img/pydantic-ai-dark.svg)

![Pydantic AI](https://pydantic.dev/docs/ai/img/pydantic-ai-light.svg)

_How Python does AI_

[![CI](https://github.com/pydantic/pydantic-ai/actions/workflows/ci.yml/badge.svg?event=push)](https://github.com/pydantic/pydantic-ai/actions/workflows/ci.yml?query=branch%3Amain)[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://coverage-badge.samuelcolvin.workers.dev/redirect/pydantic/pydantic-ai)[![PyPI](https://img.shields.io/pypi/v/pydantic-ai.svg)](https://pypi.python.org/pypi/pydantic-ai)[![versions](https://img.shields.io/pypi/pyversions/pydantic-ai.svg)](https://github.com/pydantic/pydantic-ai)[![license](https://img.shields.io/github/license/pydantic/pydantic-ai.svg)](https://github.com/pydantic/pydantic-ai/blob/main/LICENSE)[![Join Slack](https://img.shields.io/badge/Slack-Join%20Slack-4A154B?logo=slack)](https://logfire.pydantic.dev/docs/join-slack/)

Agents, realtime voice, image generation, embeddings. Every model, every interface, typed end to end.

**Pydantic AI** is the Python AI SDK: a typed, [extensible](https://pydantic.dev/docs/ai/guides/extensibility/) agent loop with [every model](https://pydantic.dev/docs/ai/models/overview/) a string swap away. The same agent [runs everywhere you need it](https://pydantic.dev/docs/ai/overview/interfaces/): behind a [web frontend](https://pydantic.dev/docs/ai/integrations/ui/overview/), in the [terminal](https://pydantic.dev/docs/ai/integrations/cli/), on a [voice call](https://pydantic.dev/docs/ai/realtime/overview/), on a [durable background queue](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/), or as a plain object you call [`run()`](https://pydantic.dev/docs/ai/core-concepts/agent/#running-agents) on. [Image generation](https://pydantic.dev/docs/ai/guides/image-generation/) and [embeddings](https://pydantic.dev/docs/ai/guides/embeddings/) come in the same box.

**[Pydantic AI Harness](https://pydantic.dev/docs/ai/harness/)** has everything an agent needs for complex, long-running work, snapped on as [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/), from [memory](https://pydantic.dev/docs/ai/harness/memory/), [sub-agents](https://pydantic.dev/docs/ai/harness/subagents/), and [context management](https://pydantic.dev/docs/ai/harness/compaction/) to a complete [coding agent](https://pydantic.dev/docs/ai/harness/coder/).

## What are you building?

From simple typed data extraction to complex, long-running multi-agent collaboration, Pydantic AI and [Pydantic AI Harness](https://pydantic.dev/docs/ai/harness/) have got you covered.

-   [Coding agent](#tab-panel-236)
-   [Data extraction](#tab-panel-237)
-   [Durable workflow](#tab-panel-238)
-   [Realtime voice](#tab-panel-239)
-   [Image gen](#tab-panel-240)

A complete coding agent in your terminal: workspace-rooted [file access](https://pydantic.dev/docs/ai/harness/filesystem/), allowlisted [shell](https://pydantic.dev/docs/ai/harness/shell/), [repo orientation](https://pydantic.dev/docs/ai/harness/repo-context/), [planning](https://pydantic.dev/docs/ai/harness/planning/), and [context management](https://pydantic.dev/docs/ai/harness/compaction/) that survives long sessions. Here with [web search](https://pydantic.dev/docs/ai/capabilities/web-search/) and a second-opinion [advisor](https://pydantic.dev/docs/ai/harness/advisor/) snapped on alongside:

-   [pip](#tab-panel-226)
-   [uv](#tab-panel-227)

Terminal

```bash
pip install pydantic-ai pydantic-ai-harness
```

Terminal

```bash
uv add pydantic-ai pydantic-ai-harness
```

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import WebSearch
from pydantic_ai_harness import Advisor, Coder

agent = Agent(
    'anthropic:claude-fable-5',
    capabilities=[
        Coder(),  # files, shell, repo context, planning, sub-agents, context management
        WebSearch(),  # look up docs and error messages on the web
        Advisor('openai:gpt-5.6-sol'),  # a second opinion from another model when stuck
    ],
)
agent.to_cli_sync()
```

[`Coder`](https://pydantic.dev/docs/ai/harness/coder/) is a regular [combined capability](https://pydantic.dev/docs/ai/capabilities/custom/#composition-and-middleware-semantics), not a black box: use it whole, or use the blocks it bundles directly; the two are equivalent:

```python
capabilities = [
    FileSystem('.'), Shell(cwd='.'), RepoContext(), Planning(), SubAgents(...),
    ClearToolResults(), WarnNearLimits(), ToolOutputLimits(),
]
```

Run the file and you're chatting with the agent in your terminal. To try it before writing any code, run the exported [`coder_agent`](https://pydantic.dev/docs/ai/harness/coder/#api-reference) with [`clai`](https://pydantic.dev/docs/ai/integrations/cli/#custom-agents) (the Pydantic AI CLI), via [`uvx`](https://docs.astral.sh/uv/guides/tools/):

Terminal

```bash
uvx --with pydantic-ai-harness clai -a pydantic_ai_harness.coder:coder_agent -m anthropic:claude-fable-5
```

**Build this →** [Coder](https://pydantic.dev/docs/ai/harness/coder/), from the [Harness](https://pydantic.dev/docs/ai/harness/)

Give the agent an [output type](https://pydantic.dev/docs/ai/core-concepts/output/) and [tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/), and every run comes back validated and typed:

-   [pip](#tab-panel-228)
-   [uv](#tab-panel-229)

Terminal

```bash
pip install pydantic-ai
```

Terminal

```bash
uv add pydantic-ai
```

review\_sentiment.py

```python
from typing import Literal

from pydantic import BaseModel, Field

from pydantic_ai import Agent, RunContext


class Sentiment(BaseModel):
    label: Literal['positive', 'negative', 'neutral']
    score: float = Field(ge=-1, le=1)


agent = Agent('openai:gpt-5.6-sol', output_type=Sentiment)


@agent.tool
def recent_reviews(ctx: RunContext[None], product: str) -> list[str]:
    """Fetch recent review snippets for a product."""
    return ['The new release fixed everything I complained about!']


result = agent.run_sync('How are people feeling about the Extract app?')
print(result.output)
#> label='positive' score=0.9
```

The [`@agent.tool`](https://pydantic.dev/docs/ai/tools-toolsets/tools/) function receives a [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) that carries your [dependencies](https://pydantic.dev/docs/ai/core-concepts/dependencies/) in; the rest of its signature and its docstring become the tool schema, arguments are [validated](https://pydantic.dev/docs/ai/tools-toolsets/tools/#function-tools-and-schema) before your code runs, and the run is guaranteed to return a `Sentiment`, so your IDE, type checker, and the LLM all agree on the returned type.

**Build this →** [Agents](https://pydantic.dev/docs/ai/core-concepts/agent/), [Function Tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/), and [Structured Output](https://pydantic.dev/docs/ai/core-concepts/output/)

Attach [`TemporalDurability`](https://pydantic.dev/docs/ai/capabilities/durable_execution/temporal/) and the same agent runs inside a [Temporal](https://pydantic.dev/docs/ai/capabilities/durable_execution/temporal/) workflow under [durable execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/): every model and tool call becomes a durable activity, so a run working through a background queue survives restarts, failures, and long waits:

-   [pip](#tab-panel-230)
-   [uv](#tab-panel-231)

Terminal

```bash
pip install "pydantic-ai[temporal]"
```

Terminal

```bash
uv add "pydantic-ai[temporal]"
```

durable\_research.py

```python
from temporalio import workflow

from pydantic_ai import Agent
from pydantic_ai.capabilities import WebFetch, WebSearch
from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow, TemporalDurability

agent = Agent(
    'openai:gpt-5.6-sol',
    instructions='Research the topic and write a structured brief.',
    name='researcher',
    capabilities=[WebSearch(), WebFetch(), TemporalDurability()],
)


@workflow.defn
class ResearchWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [agent]

    @workflow.run
    async def run(self, topic: str) -> str:
        result = await agent.run(f'Write a brief on: {topic}')
        return result.output
```

[DBOS](https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/) and [Prefect](https://pydantic.dev/docs/ai/capabilities/durable_execution/prefect/) attach the same way, first-party and co-maintained, with [Restate, Kitaru, and Airflow](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/) integrations besides.

**Build this →** [Durable Execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/)

Put the same agent on a live voice session, [tools](https://pydantic.dev/docs/ai/realtime/tools/) and [capabilities](https://pydantic.dev/docs/ai/realtime/capabilities/) included:

-   [pip](#tab-panel-232)
-   [uv](#tab-panel-233)

Terminal

```bash
pip install "pydantic-ai[openai-realtime]"
```

Terminal

```bash
uv add "pydantic-ai[openai-realtime]"
```

```python
import asyncio

from pydantic_ai import Agent
from pydantic_ai.capabilities import MCP

agent = Agent(
    instructions='You are a helpful voice assistant.',
    capabilities=[MCP('https://internal.example.com/mcp')],  # capabilities work in voice too
)

@agent.tool_plain
def order_status(order_id: str) -> str:
    """Look up the status of an order."""
    return f'Order {order_id}: shipped, arriving Thursday.'

async with agent.realtime('openai:gpt-realtime-2.1').session() as session:
    microphone = asyncio.create_task(session.send_audio(microphone_chunks()))  # your microphone → the model
    speaker = asyncio.create_task(play_audio(session.stream_audio()))  # model audio → your speaker
    async for part in session.stream_transcripts():
        print(f'{part.speaker}: {part.transcript}')
```

The model calls your tools mid-conversation while it keeps talking, and every session is [instrumented](https://pydantic.dev/docs/ai/integrations/logfire/); voice is just another frontend, on OpenAI Realtime, Gemini Live, Azure, and xAI Grok Voice.

**Build this →** [Realtime Voice](https://pydantic.dev/docs/ai/realtime/overview/), starting from the [voice assistant example](https://pydantic.dev/docs/ai/examples/realtime/realtime-voice/)

Generate an image with a dedicated image model, no agent run required:

-   [pip](#tab-panel-234)
-   [uv](#tab-panel-235)

Terminal

```bash
pip install pydantic-ai
```

Terminal

```bash
uv add pydantic-ai
```

logo\_generation.py

```python
from pathlib import Path

from pydantic_ai import ImageGenerator

generator = ImageGenerator('openai:gpt-image-2')
result = generator.generate_sync('A minimalist logo for a coffee shop called Extract.')
Path('logo.png').write_bytes(result.image.data)
```

That [standalone image API](https://pydantic.dev/docs/ai/guides/image-generation/) is for when your application decides; when an agent run decides, there is [provider-native generation](https://pydantic.dev/docs/ai/tools-toolsets/native-tools/#image-generation-tool) with `output_type=BinaryImage` for a typed image [output](https://pydantic.dev/docs/ai/core-concepts/output/#image-output), and the [`ImageGeneration` capability](https://pydantic.dev/docs/ai/capabilities/image-generation/) with its fallbacks for models that generate no images of their own.

**Build this →** [Image Generation](https://pydantic.dev/docs/ai/guides/image-generation/)

No API key yet?

You don't need a provider API key to try any of this. Pass the built-in [`'test'` model](https://pydantic.dev/docs/ai/guides/testing/#unit-testing-with-testmodel) (`Agent('test')`), which runs entirely offline without calling an LLM, so you can exercise your agent, tools, and outputs first. When you're ready for a real model, see [Models and Providers](https://pydantic.dev/docs/ai/models/overview/) to pick a provider and set its API key.

## Why Pydantic AI

-   **Any model, one Python API.** [Virtually every model and provider](https://pydantic.dev/docs/ai/models/overview/) (OpenAI, Anthropic, Google, Bedrock, Azure AI Foundry, Groq, Mistral, xAI, Ollama, and dozens more), swappable with a string, or through the [Pydantic AI Gateway](https://pydantic.dev/docs/ai/overview/gateway/): one key for all of them, with failover and cost monitoring built in. No flagship feature is locked to one vendor.
    
-   **Typed end to end.** [Structured outputs](https://pydantic.dev/docs/ai/core-concepts/output/), typed [dependency injection](https://pydantic.dev/docs/ai/core-concepts/dependencies/), [typed tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/): your IDE, type checker, and coding agent all know what your agent returns, moving whole classes of errors from runtime to write-time. When plain control flow isn't enough, [Pydantic Graph](https://pydantic.dev/docs/ai/graph/graph/) brings the same typing to graph-based workflows.
    
-   **Measured, not vibes.** OpenTelemetry-native [instrumentation](https://pydantic.dev/docs/ai/integrations/logfire/) works with any OTel backend; one line lights up [Pydantic Logfire](https://pydantic.dev/logfire) for real-time debugging, tracing, and cost tracking backed by [genai-prices](https://github.com/pydantic/genai-prices). [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/) tests agent behavior the way pytest tests code.
    
-   **Batteries, composably.** One primitive, the [capability](https://pydantic.dev/docs/ai/capabilities/overview/), bundles [tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/), [instructions](https://pydantic.dev/docs/ai/core-concepts/agent/#instructions), [hooks](https://pydantic.dev/docs/ai/core-concepts/hooks/), and [model settings](https://pydantic.dev/docs/ai/core-concepts/agent/#model-run-settings) into reusable units. Core ships fundamentals like [MCP](https://pydantic.dev/docs/ai/capabilities/mcp/) and [web search](https://pydantic.dev/docs/ai/capabilities/web-search/), the [Harness](https://pydantic.dev/docs/ai/harness/) ships everything else, and complete agents like [Coder](https://pydantic.dev/docs/ai/harness/coder/) and [Researcher](https://pydantic.dev/docs/ai/harness/researcher/) are just capabilities composed: they come apart the way they went together. Or skip code entirely with [YAML/JSON agent specs](https://pydantic.dev/docs/ai/core-concepts/agent-spec/).
    
-   **[Every interface](https://pydantic.dev/docs/ai/overview/interfaces/).** One agent definition runs as a [CLI](https://pydantic.dev/docs/ai/integrations/cli/), a [built-in web chat](https://pydantic.dev/docs/ai/guides/web/), or [realtime speech](https://pydantic.dev/docs/ai/realtime/overview/); [UI event streams](https://pydantic.dev/docs/ai/integrations/ui/overview/) (AG-UI, Vercel AI) connect it to your own frontend or anything else; and [ACP](https://pydantic.dev/docs/ai/harness/acp/) _(experimental)_ serves it as an editor agent.
    
-   **Durable execution.** First-party, co-maintained [durable execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/) on Temporal, DBOS, Prefect, and Restate, plus external SDK integrations for Kitaru and Airflow. Agents survive restarts and run for days on the engine you already operate, with [human-in-the-loop approval](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/#human-in-the-loop-tool-approval) built in.
    

Built by the [Pydantic](https://docs.pydantic.dev/) team: [Pydantic Validation](https://pydantic.dev/docs/) is the validation layer of the OpenAI SDK, the Anthropic SDK, the Google ADK, LangChain, and most of the AI ecosystem (and the foundation FastAPI was built on). Pydantic AI brings that same feeling to agents.

**Sign up for our newsletter, _The Pydantic Stack_, with updates & tutorials on Pydantic AI, Logfire, and Pydantic:**

Subscribe

## Putting it together: a bank support agent

Here's a support agent for a bank, showing several features working together: [dependency injection](https://pydantic.dev/docs/ai/core-concepts/dependencies/) carrying a database connection into instructions and tools, [function tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/) the model calls, [structured output](https://pydantic.dev/docs/ai/core-concepts/output/) validated on every run, a reusable [capability](https://pydantic.dev/docs/ai/capabilities/overview/) bundling the customer context, and an [on-demand capability](https://pydantic.dev/docs/ai/capabilities/on-demand/) the model loads only when the conversation calls for it:

bank\_support.py

```python
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, Capability, RunContext

from bank_database import DatabaseConn


@dataclass
class SupportDependencies:  # (1)
    customer_id: int
    db: DatabaseConn  # (2)


class SupportOutput(BaseModel):  # (3)
    support_advice: str = Field(description='Advice returned to the customer')
    block_card: bool = Field(description="Whether to block the customer's card")
    risk: int = Field(description='Risk level of query', ge=0, le=10)


customer_context = Capability[SupportDependencies](  # (4)
    id='customer-context',
    description="Who the customer is and what's on their account.",
)


@customer_context.instructions  # (5)
async def add_customer_name(ctx: RunContext[SupportDependencies]) -> str:
    customer_name = await ctx.deps.db.customer_name(id=ctx.deps.customer_id)
    return f"The customer's name is {customer_name!r}"


@customer_context.tool  # (6)
async def customer_balance(
    ctx: RunContext[SupportDependencies], include_pending: bool
) -> float:
    """Returns the customer's current account balance."""  # (7)
    return await ctx.deps.db.customer_balance(
        id=ctx.deps.customer_id,
        include_pending=include_pending,
    )


refunds = Capability[SupportDependencies](  # (8)
    id='refunds',
    description='Refund eligibility and refund status.',
    defer_loading=True,
)


@refunds.tool
async def refund_status(ctx: RunContext[SupportDependencies]) -> str:
    """Look up the refund status for the customer's most recent charge."""
    return await ctx.deps.db.refund_status(id=ctx.deps.customer_id)


support_agent = Agent(  # (9)
    'openai:gpt-5.6-sol',  # (10)
    deps_type=SupportDependencies,
    output_type=SupportOutput,  # (11)
    instructions=(
        'You are a support agent in our bank, give the '
        'customer support and judge the risk level of their query.'
    ),
    capabilities=[customer_context, refunds],  # (12)
)


...  # (13)


async def main():
    deps = SupportDependencies(customer_id=123, db=DatabaseConn())
    result = await support_agent.run('What is my balance?', deps=deps)  # (14)
    print(result.output)
    """
    support_advice='Hello John, your current account balance, including pending transactions, is $123.45.' block_card=False risk=1
    """

    result = await support_agent.run('I just lost my card!', deps=deps)
    print(result.output)
    """
    support_advice="I'm sorry to hear that, John. We are temporarily blocking your card to prevent unauthorized transactions." block_card=True risk=8
    """

    result = await support_agent.run(  # (15)
        'Was I refunded for the duplicate charge on my last statement?', deps=deps
    )
    print(result.output)
    """
    support_advice='Good news, John: the duplicate charge on your last statement was refunded on 2026-05-01.' block_card=False risk=1
    """
```

The `SupportDependencies` dataclass is used to pass data, connections, and logic into the model that will be needed when running [instructions](https://pydantic.dev/docs/ai/core-concepts/agent/#instructions) and [tool](https://pydantic.dev/docs/ai/tools-toolsets/tools/) functions. Pydantic AI's system of [dependency injection](https://pydantic.dev/docs/ai/core-concepts/dependencies/) provides a [type-safe](https://pydantic.dev/docs/ai/core-concepts/agent/#static-type-checking) way to customise the behavior of your agents, and can be especially useful when running [unit tests](https://pydantic.dev/docs/ai/guides/testing/) and evals.

This is a simple sketch of a database connection, used to keep the example short and readable. In reality, you'd be connecting to an external database (e.g. PostgreSQL) to get information about customers.

This [Pydantic](https://docs.pydantic.dev/) model is used to constrain the structured data returned by the agent. From this simple definition, Pydantic builds the JSON Schema that tells the LLM how to return the data, and performs validation to guarantee the data is correct at the end of the run.

A [`Capability`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Capability) bundles related instructions and tools into one reusable unit: the same primitive behind [built-in capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) like [web search](https://pydantic.dev/docs/ai/capabilities/web-search/) and everything in the [Harness](https://pydantic.dev/docs/ai/harness/). This one carries the customer context; you could drop it into any other agent's `capabilities` list as-is.

Dynamic [instructions](https://pydantic.dev/docs/ai/core-concepts/agent/#instructions) can make use of dependency injection. Dependencies are carried via the [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext) argument, which is parameterized with the `deps_type` from above. If the type annotation here is wrong, static type checkers will catch it.

The [`tool`](https://pydantic.dev/docs/ai/tools-toolsets/tools/) decorator registers a function whose signature becomes a tool the LLM may call while responding to a user. Again, dependencies are carried via [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext); any other arguments become the tool schema passed to the LLM. Pydantic is used to validate these arguments, and errors are passed back to the LLM so it can retry.

The docstring of a tool is also passed to the LLM as the description of the tool. Parameter descriptions are [extracted](https://pydantic.dev/docs/ai/tools-toolsets/tools/#function-tools-and-schema) from the docstring and added to the parameter schema sent to the LLM.

`defer_loading=True` makes this an [on-demand capability](https://pydantic.dev/docs/ai/capabilities/on-demand/), like an [Agent Skill](https://pydantic.dev/docs/ai/capabilities/on-demand/#loading-skills-from-markdown-files). It collapses to a one-line catalog entry in the prompt, and its tools stay hidden until the model decides it's relevant and loads it with the framework-managed `load_capability` tool.

This [agent](https://pydantic.dev/docs/ai/core-concepts/agent/) will act as first-tier support in a bank. Agents are generic in the type of dependencies they accept and the type of output they return. In this case, the support agent has type `Agent[SupportDependencies, SupportOutput]`.

Here we configure the agent to use [OpenAI's GPT-5.6 Sol](https://pydantic.dev/docs/ai/api/models/openai/) model; you can also set the model when running the agent.

The response from the agent will be guaranteed to be a `SupportOutput`. Since the agent is generic, it'll also be typed as a `SupportOutput` to aid with static type checking. If validation fails, the agent is [prompted to try again](https://pydantic.dev/docs/ai/core-concepts/agent/#reflection-and-self-correction).

Mount the capabilities on the agent. More [capabilities](https://pydantic.dev/docs/ai/capabilities/overview/), like [web search](https://pydantic.dev/docs/ai/capabilities/web-search/) or anything from the [Harness](https://pydantic.dev/docs/ai/harness/), snap on alongside them in the same list.

In a real use case, you'd add more tools and longer instructions to the agent to extend the context it's equipped with and support it can provide.

[Run the agent](https://pydantic.dev/docs/ai/core-concepts/agent/#running-agents) asynchronously, conducting a conversation with the LLM until a final response is reached. Even in this fairly simple case, the agent will exchange multiple messages with the LLM as tools are called to retrieve an output.

This turn exercises the deferred capability: the model sees the `refunds` catalog entry, calls `load_capability` with `id='refunds'`, and only then gets the `refund_status` tool to answer with: [on-demand loading](https://pydantic.dev/docs/ai/capabilities/on-demand/) in action.

The [dependencies](https://pydantic.dev/docs/ai/core-concepts/dependencies/) dataclass carries the database connection into [instructions](https://pydantic.dev/docs/ai/core-concepts/agent/#instructions) and [tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/) with full type safety: swap in a test double and the same agent runs in [unit tests](https://pydantic.dev/docs/ai/guides/testing/) and evals. And because the customer context is a [capability](https://pydantic.dev/docs/ai/capabilities/overview/), it composes: the same unit drops into a voice agent or a web app unchanged.

Complete `bank_support.py` example

The code included here is incomplete for the sake of brevity (the definition of `DatabaseConn` is missing); you can find the complete `bank_support.py` example [here](https://pydantic.dev/docs/ai/examples/conversational-agents/bank-support/).

## Instrumentation with Pydantic Logfire

Pydantic AI is [OpenTelemetry](https://opentelemetry.io/)\-native: the [Instrumentation](https://pydantic.dev/docs/ai/capabilities/instrumentation/) capability emits standard OTel spans for every model call and tool call, and [any OTLP backend works](https://pydantic.dev/docs/ai/integrations/logfire/#alternative-observability-backends). The easiest setup is the [`logfire` SDK](https://pydantic.dev/docs/ai/integrations/logfire/#using-logfire), which speaks plain OpenTelemetry and can point at [Pydantic Logfire](https://pydantic.dev/logfire) or any other backend.

Even a simple agent with just a handful of tools can result in a lot of back-and-forth with the LLM, making it nearly impossible to be confident of what's going on just from reading the code. To watch the runs above in action, [set up Logfire](https://pydantic.dev/docs/ai/integrations/logfire/#using-logfire) and add the following to the code:

bank\_support\_with\_logfire.py

```python
...
from pydantic_ai import Agent, RunContext

from bank_database import DatabaseConn

import logfire

logfire.configure()  # (1)
logfire.instrument_pydantic_ai()  # (2)
logfire.instrument_sqlite3()  # (3)

...

support_agent = Agent(
    'openai:gpt-5.6-sol',
    deps_type=SupportDependencies,
    output_type=SupportOutput,
    instructions=(
        'You are a support agent in our bank, give the '
        'customer support and judge the risk level of their query.'
    ),
    capabilities=[customer_context],
)
```

Configure the Logfire SDK, this will fail if project is not set up.

This will instrument all Pydantic AI agents used from here on out. To instrument only a specific agent, add an [`Instrumentation`](https://pydantic.dev/docs/ai/api/pydantic-ai/capabilities/#pydantic_ai.capabilities.Instrumentation) entry to the agent's `capabilities=[...]`.

In our demo, `DatabaseConn` uses [`sqlite3`](https://docs.python.org/3/library/sqlite3.html#module-sqlite3) to connect to a PostgreSQL database, so [`logfire.instrument_sqlite3()`](https://logfire.pydantic.dev/docs/integrations/databases/sqlite3/) is used to log the database queries.

That's enough to get the following view of your agent in action:

Logfire instrumentation for the bank agent -- [View in Logfire](https://logfire-eu.pydantic.dev/public-trace/a2957caa-b7b7-4883-a529-777742649004?spanId=31aade41ab896144)

See [Monitoring and Performance](https://pydantic.dev/docs/ai/integrations/logfire/) to learn more.

## `llms.txt`

The Pydantic AI documentation is available in the [llms.txt](https://llmstxt.org/) format. This format is defined in Markdown and suited for LLMs and AI coding assistants and agents.

Two formats are available:

-   [`llms.txt`](https://pydantic.dev/docs/ai/llms.txt): a file containing a brief description of the project, along with links to the different sections of the documentation. The structure of this file is described in details [here](https://llmstxt.org/#format).
-   [`llms-full.txt`](https://pydantic.dev/docs/ai/llms-full.txt): Similar to the `llms.txt` file, but every link content is included. Note that this file may be too large for some LLMs.

As of today, these files are not automatically leveraged by IDEs or coding agents, but they will use it if you provide a link or the full text.

## Next steps

**Run something right now.** One command puts a complete [coding agent](https://pydantic.dev/docs/ai/harness/coder/) in your terminal:

Terminal

```bash
uvx --with pydantic-ai-harness clai -a pydantic_ai_harness.coder:coder_agent -m anthropic:claude-fable-5
```

Or [install Pydantic AI](https://pydantic.dev/docs/ai/overview/install/), pick a [model](https://pydantic.dev/docs/ai/models/overview/), and put your own coding agent to work: install the [Pydantic AI skill](https://pydantic.dev/docs/ai/overview/coding-agent-skills/) to give it up-to-date framework knowledge, point it at the [examples](https://pydantic.dev/docs/ai/examples/setup/) and the [Harness index](https://pydantic.dev/docs/ai/harness/), and tell it what you'd like to build.

**See what your agent did.** [Instrument it](https://pydantic.dev/docs/ai/integrations/logfire/): one line of setup, and every model call and tool call shows up. It's standard OpenTelemetry: [Pydantic Logfire](https://pydantic.dev/logfire) is the easiest way to look, any OTLP backend works.

**Go deeper.** The [Agents guide](https://pydantic.dev/docs/ai/core-concepts/agent/) is the core walkthrough; the [API Reference](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/) covers the full interface; the [Harness](https://pydantic.dev/docs/ai/harness/) has the batteries.

**Get help.** Join [Slack](https://logfire.pydantic.dev/docs/join-slack/) or file an issue on [GitHub](https://github.com/pydantic/pydantic-ai/issues).

---
