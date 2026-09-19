# [Memory](https://pydantic.dev/docs/ai/harness/memory/)

> Persistent, namespaced agent notebooks with bounded prompt injection, on-demand search, and concurrency-safe stores.

# Memory

Give an agent a persistent notebook that it can update, search, and reuse across runs without loading every stored file into every prompt.

> While Pydantic AI Harness is on 0.x releases, the API may change between minor releases; when it does, deprecation warnings and release-note migration guidance tell you (or your agent) exactly how to upgrade. See the [version policy](https://pydantic.dev/docs/ai/harness/#version-policy).

## Notebook model

Memory gives each agent a notebook made of Markdown files:

-   `MEMORY.md` is the main notebook. By default, a bounded excerpt and the names of other files are added to the current request as delimited user-role context.
-   Other files hold longer or focused notes. The model reads them on demand or finds them with bounded text search.

The model gets four tools:

Tool

Purpose

`write_memory`

Append to a file or replace one unique text fragment. Writes use optimistic concurrency and an idempotency identifier derived from the run and tool call.

`read_memory`

Read a bounded prefix of one memory file.

`delete_memory`

Delete a file. The main notebook is protected.

`search_memory`

Search across notebook files, subject to configured result, character, and file-scan limits.

```python
from pydantic_ai import Agent
from pydantic_ai_harness import Memory
from pydantic_ai_harness.memory import FileStore

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[Memory(FileStore('.agent-memory'))],
    defer_model_check=True,
)
```

The namespace is resolved by application code, not supplied to the tools. The model therefore cannot select another user's namespace in a tool call.

## Injection modes and limits

Automatic injection is enabled by default. Trusted usage guidance remains in model instructions, while model-written memory is enclosed in `<memory>` delimiters in a user-role part on the current request. Together, the guidance, main notebook, and file listing share a finite `max_tokens` budget, estimated at four characters per token. The default is 2,000 approximate tokens. `max_lines` is an additional limit on the main notebook. Backend reads are limited by `max_memory_size`, and the number of requested paths is derived from the prompt budget, so the capability never requests an unbounded file or listing. Content that does not fit is omitted with a prompt directing the model to use `read_memory` or `search_memory`.

When `heading` is set, the same `## {heading}` labels both the trusted guidance and the user-role memory block.

```python
from pydantic_ai_harness import Memory
from pydantic_ai_harness.memory import FileStore

memory = Memory(
    FileStore('.agent-memory'),
    max_tokens=2_000,
    max_lines=200,
)
```

Only the current request retains the injected user-role part, so copies do not accumulate in message history. Each model request receives the latest bounded snapshot, including after `write_memory` or an external update changes `MEMORY.md`.

Set `inject_memory=False` for cache-stable prompts. The tools remain available, and the model can fetch memory only when it needs it:

```python
from pydantic_ai_harness import Memory
from pydantic_ai_harness.memory import FileStore

memory = Memory(FileStore('.agent-memory'), inject_memory=False)
```

With `injection_errors='ignore'` (the default), a store failure skips automatic injection and emits content-safe telemetry. Spans record the backend type and a hash of the resolved scope; successful injection records counts, and failures record the exception type. They do not record memory content. Set `injection_errors='raise'` when a run must fail rather than proceed without injected memory. Namespace and store resolver failures always propagate. Tool failures are still returned as tool errors; this setting controls automatic injection only.

## Persistence and concurrency

The store contract includes optimistic compare-and-swap mutations and idempotency. A write based on a stale revision fails with a conflict instead of overwriting a concurrent edit. Replaying the same run and tool call does not apply its mutation twice; reusing that operation identifier with different arguments raises `MemoryOperationConflictError`. These guarantees belong to the mutation operation, so custom stores must implement them atomically rather than composing separate read and write calls.

Every `MemoryStore.read` call includes a finite `max_chars`, and every `list_paths` call includes a finite `limit`. A store returns the bounded prefix plus `MemoryFile.truncated=True` when more content exists, while its version still represents the complete file. `read_memory` marks that bounded result as truncated. `write_memory` refuses to append or edit an oversized externally supplied file because doing so would derive new content from a partial read; remediate or replace it through the backing store first. A custom `SearchableMemoryStore.search` must likewise honor `max_file_chars` as well as the result limits.

Store

Persistence and concurrency boundary

`InMemoryStore()`

Process lifetime; atomic across tasks using that store instance.

`FileStore(directory)`

Local filesystem; atomic Markdown replacement plus a hidden SQLite journal provide recovery, cross-process compare-and-swap, and durable idempotency receipts.

`SqliteMemoryStore(database=...)`

Durable single-host storage; compare-and-swap and idempotency are enforced in database transactions.

`PostgresMemoryStore(pool)`

Durable shared storage; compare-and-swap and idempotency are enforced in database transactions. The caller owns the pool lifecycle.

```python
from pydantic_ai_harness import Memory
from pydantic_ai_harness.memory import FileStore, SqliteMemoryStore

local_memory = Memory(FileStore('.agent-memory'))
sqlite_memory = Memory(SqliteMemoryStore(database='.agent-memory.db'))
```

`SqliteMemoryStore` can instead use a caller-owned `sqlite3.Connection`. Because operations run off the event loop, create that connection with `check_same_thread=False` and manage its lifecycle in the application. The connection must be dedicated to the store and idle at the start of every operation; a call fails rather than commit or roll back an active caller transaction.

`FileStore` keeps the journal at `.memory-store.sqlite3` inside its root. Keep it with the Markdown files when copying or backing up the store. Editing a Markdown file outside the capability changes its content version and can produce a conflict with a prepared operation; the journal recovers operations interrupted between transaction preparation and filesystem replacement.

`PostgresMemoryStore` accepts the driver-neutral `PostgresPool` protocol, so the harness does not require a particular PostgreSQL driver. Install and manage the driver in your application, for example:

-   [pip](#tab-panel-136)
-   [uv](#tab-panel-137)

Terminal

```bash
pip install asyncpg
```

Terminal

```bash
uv add asyncpg
```

```python
import asyncpg

from pydantic_ai_harness import Memory
from pydantic_ai_harness.memory import PostgresMemoryStore


async def build_memory() -> tuple[Memory[None], asyncpg.Pool]:
    pool = await asyncpg.create_pool('postgres://localhost/app')
    memory = Memory(PostgresMemoryStore(pool))
    return memory, pool
```

Call `build_memory` during application startup and close the returned pool during shutdown. The store does not manage it.

## Namespaces

Use a namespace resolver when one `Agent` serves multiple users. It runs once per run from your typed dependencies, and its result is hidden from the model-facing tool schema.

```python
from dataclasses import dataclass

from pydantic_ai import Agent
from pydantic_ai_harness import Memory
from pydantic_ai_harness.memory import FileStore


@dataclass
class AppDeps:
    user_id: str


agent = Agent(
    'anthropic:claude-sonnet-4-6',
    deps_type=AppDeps,
    capabilities=[
        Memory(
            FileStore('/var/lib/myapp/memory'),
            namespace=lambda ctx: ctx.deps.user_id,
        )
    ],
    defer_model_check=True,
)
```

Namespace isolation controls which records the capability addresses. It is not an authorization system for a custom or shared backing store. Validate the identity in application dependencies, restrict backend credentials, and ensure custom stores cannot escape the resolved namespace.

## Multiple memories on one agent

An agent can carry several `Memory` capabilities at once, for example a personal notebook plus a shared org notebook. Three constraints apply:

-   Give each instance a distinct `agent_name` or `namespace`. Injected blocks are tracked by their resolved scope, so instances that differ only in their store resolve the same scope and replace each other's injection.
-   All instances define the same tool names, so wrap every instance but one in `prefix_tools` to keep the tool schemas distinct.
-   Set a distinct `heading` on each instance so the model sees the blocks as separate sections. `agent_name` is a storage key and never appears in the prompt, so it can't label them.

```python
from pydantic_ai import Agent
from pydantic_ai_harness import Memory
from pydantic_ai_harness.memory import FileStore

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[
        Memory(FileStore('/var/lib/myapp/memory'), heading='Your notes'),
        Memory(FileStore('/var/lib/myapp/memory'), agent_name='org', heading='Org notes').prefix_tools('org'),
    ],
    defer_model_check=True,
)
```

## Search

`search_memory` performs literal text search and always applies three bounds:

-   `max_search_results` limits returned matches, default 10.
-   `max_search_result_chars` limits the combined scope-relative filename and snippet text, default 4,000 characters.
-   `max_search_files` limits how many files a fallback scan may inspect, default 1,000.

The bundled stores implement `SearchableMemoryStore`. For a custom store that implements only `MemoryStore`, `search_memory` requests at most `max_search_files + 1` paths, scans at most `max_search_files`, and performs bounded reads. Lexical scoring uses only each scope-relative filename and its bounded content; tenant namespaces and agent names never affect relevance. Implement the optional search protocol for an indexed or semantic backend while preserving the same tenant boundary and result limits. Semantic ranking is not built in.

Before backend dispatch, queries are limited to 1,000 characters and 32 unique whitespace-separated terms. Repeated case-insensitive terms are collapsed so they cannot inflate scoring or scan work.

## Configuration

```python
from pydantic_ai_harness import Memory
from pydantic_ai_harness.memory import FileStore

Memory(
    FileStore('.agent-memory'),
    store_resolver=None,               # optional per-run store resolver
    agent_name='main',                 # storage segment inside the namespace; never shown to the model
    heading='',                        # optional heading on guidance and injected content
    namespace='',                      # string or per-run resolver
    inject_memory=True,                # False keeps prompts cache-stable
    max_tokens=2_000,                  # finite approximate total injection budget
    max_lines=200,                     # additional main-notebook line limit
    max_memory_size=65_536,            # per-file read, search, and write boundary
    max_search_results=10,
    max_search_result_chars=4_000,
    max_search_files=1_000,
    injection_errors='ignore',         # or 'raise'
    guidance=None,                     # None uses the default notebook guidance
)
```

## Agent specs

Register `Memory` as a custom capability type when constructing an agent from a Python spec:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import Memory

agent = Agent.from_spec(
    {
        'model': 'anthropic:claude-sonnet-4-6',
        'capabilities': [
            {'Memory': {'backend': 'file', 'directory': '.agent-memory'}},
        ],
    },
    custom_capability_types=[Memory],
    defer_model_check=True,
)
```

The serializable backends are `memory`, `file`, and `sqlite`. A namespace callable and a live PostgreSQL pool must be configured in Python.

## Durable execution compatibility

Execution mode

Support

Normal `Agent.run` calls

Supported with automatic injection or on-demand tools.

Temporal and Prefect

Automatic snapshot loading is a journaled capability operation. On replay, the recorded snapshot is reused. `store_resolver` and a callable `namespace` run before that operation, so they must be deterministic and free of backend I/O; a per-tenant resolver that queries a backend is not workflow-safe.

DBOS

Automatic snapshot loading is a DBOS step. Ordinary `FunctionToolset` calls are not DBOS-durable; wrap memory tool operations in application-provided DBOS steps when required.

`Memory` carries the stable default `id='memory'`, so durable recovery works without configuration. The memory backend and workflow state backend remain independent: durable execution does not make an in-memory notebook persistent.

Each model request that uses automatic snapshot loading records one bounded snapshot result in workflow history, so choose `max_memory_size` and `max_tokens` with the engine's history limits in mind.

## Security and provenance

Memory is model-written, untrusted content that can re-enter future prompts. Keeping it in a delimited user-role part lowers its authority relative to model instructions, but this is not a hard prompt-injection boundary. Use `inject_memory=False` when less-trusted actors can write to the store, and expose memory only through application-controlled retrieval when stronger isolation is required. Do not store secrets unless the backend, retention policy, and access controls are appropriate. Sanitize content before rendering it into another trust domain.

Memory records do not carry source citations or verified provenance. If an application needs auditable facts, store provenance in the note itself or implement a custom store and schema. Optimistic concurrency prevents lost updates; it does not establish that a remembered claim is true.

## API reference

-   [`pydantic_ai_harness.memory` source](https://github.com/pydantic/pydantic-ai-harness/tree/main/pydantic_ai_harness/memory/)
-   [Pydantic AI capabilities](https://pydantic.dev/docs/ai/capabilities/overview/)
-   [Pydantic AI hooks](https://pydantic.dev/docs/ai/core-concepts/hooks/)

The public module exports `Memory`, `MemoryToolset`, the bundled stores, the store protocols, mutation and search result models, and conflict exceptions. Import them from `pydantic_ai_harness.memory`.

### Memory

**Bases:** `AbstractCapability[AgentDepsT]`

Persistent agent memory across sessions.

`MEMORY.md` is injected as user-role context and longer topic files are available through `read_memory` and `search_memory`. Automatic snapshot loading is journaled by durability engines that support capability operations.

#### Attributes

##### store

Storage backend. The default persists only for the process lifetime.

**Type:** `MemoryStore` **Default:** `field(default_factory=InMemoryStore)`

##### store\_resolver

Optional per-run store resolver. Resolver failures always propagate.

**Type:** [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]\], `MemoryStore`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### agent\_name

Storage segment that isolates memory within a namespace. Part of the scope key only; never rendered into the model-facing memory block.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'main'`

##### heading

Markdown heading for rendered guidance and the injected memory block, rendered as `## {heading}` when set. The default is empty: the block already sits inside `<memory>` markers, so none is added. Set a distinct value per instance when several `Memory` capabilities share one agent (for example `heading='Team notes'`) so the model can tell the blocks apart.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `field(default='', kw_only=True)`

##### namespace

Static or per-run tenant namespace, never exposed as a tool argument.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)\[\[[`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]\], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `''`

##### inject\_memory

Inject stored memory when true; otherwise inject static tool guidance only.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### max\_tokens

Approximate total token ceiling for the complete injected memory section.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `2000`

##### max\_lines

Maximum number of `MEMORY.md` content lines considered for injection.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `200`

##### max\_memory\_size

Per-file character boundary for backend reads, search, and writes.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `65536`

##### max\_search\_results

Maximum matches returned by one search.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `10`

##### max\_search\_result\_chars

Maximum combined snippet characters returned by one search.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `4000`

##### max\_search\_files

Maximum files scanned by one search.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `1000`

##### guidance

Override injected usage guidance; `''` disables guidance.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### injection\_errors

Whether store failures during automatic injection are ignored or raised.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['ignore', 'raise'\] **Default:** `'ignore'`

#### Methods

##### for\_run

`@async`

```python
def for_run(ctx: RunContext[AgentDepsT]) -> Memory[AgentDepsT]
```

Return a clone with scope resolution isolated to this run.

###### Returns

`Memory`\[`AgentDepsT`\]

##### resolve\_scope

```python
def resolve_scope(ctx: RunContext[AgentDepsT]) -> tuple[MemoryStore, str]
```

Return the cached run scope, or resolve one for direct toolset use.

###### Returns

[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[`MemoryStore`, [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

##### get\_toolset

```python
def get_toolset() -> AgentToolset[AgentDepsT] | None
```

Provide the stable `memory` toolset.

###### Returns

[`AgentToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AgentToolset)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_instructions

```python
def get_instructions() -> AgentInstructions[AgentDepsT] | None
```

Provide trusted static guidance about using memory.

Stored memory is added separately as user-role context by `before_model_request` so model-written content is not placed in the instruction channel.

###### Returns

`AgentInstructions`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### before\_model\_request

`@async`

```python
def before_model_request(
    ctx: RunContext[AgentDepsT],
    request_context: ModelRequestContext,
) -> ModelRequestContext
```

Add a bounded memory snapshot to only the current user request.

###### Returns

[`ModelRequestContext`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ModelRequestContext)

##### from\_spec

`@classmethod`

```python
def from_spec(
    cls,
    *,
    backend: Literal['memory', 'file', 'sqlite'] = 'memory',
    directory: str = '.agent-memory',
    database: str = '.agent-memory.db',
    agent_name: str = 'main',
    heading: str = '',
    namespace: str = '',
    inject_memory: bool = True,
    max_tokens: int = 2000,
    max_lines: int = 200,
    max_memory_size: int = 65536,
    max_search_results: int = 10,
    max_search_result_chars: int = 4000,
    max_search_files: int = 1000,
    guidance: str | None = None,
    injection_errors: Literal['ignore', 'raise'] = 'ignore',
) -> Memory[AgentDepsT]
```

Construct a memory capability from serializable options.

###### Returns

`Memory`\[`AgentDepsT`\]

##### get\_serialization\_name

`@classmethod`

```python
def get_serialization_name(cls) -> str | None
```

Return the name used by custom capability specs.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### MemoryToolset

**Bases:** `FunctionToolset[AgentDepsT]`

Scoped read/write/delete/search tools with CAS and durable idempotency.

The stable `memory` ID lets Temporal and Prefect wrap this static toolset. DBOS does not currently turn an ordinary `FunctionToolset` into a durable step, so applications requiring DBOS durability must provide that wrapper.

#### Methods

##### write\_memory

`@async`

```python
def write_memory(
    ctx: RunContext[AgentDepsT],
    content: str,
    file: str = MAIN_FILENAME,
    old_text: str | None = None,
) -> MemoryWriteResult
```

Write persistent memory by appending or uniquely replacing text.

Omit `old_text` to append, creating the file when necessary. Pass `old_text` to replace exactly one matching passage; use an empty `content` to remove that passage. Keep short durable facts in `MEMORY.md`, and longer or evolving topics in separate files. Update stale entries rather than adding contradictory duplicates.

###### Returns

`MemoryWriteResult`

###### Parameters

**`ctx`** : [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]

Framework-provided run context.

**`content`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Text to append, or replacement text for `old_text`.

**`file`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `MAIN_FILENAME`

Memory filename; defaults to `MEMORY.md`.

**`old_text`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Exact passage to replace, which must occur once.

##### read\_memory

`@async`

```python
def read_memory(ctx: RunContext[AgentDepsT], file: str) -> str
```

Read a bounded prefix of one memory file.

Memory may be stale background context, so verify volatile facts before relying on them.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

###### Parameters

**`ctx`** : [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]

Framework-provided run context.

**`file`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Memory filename returned by injection or search.

##### delete\_memory

`@async`

```python
def delete_memory(ctx: RunContext[AgentDepsT], file: str) -> MemoryDeleteResult
```

Delete a non-main memory file that is no longer useful.

`MEMORY.md` cannot be deleted; remove or correct its text with `write_memory` instead.

###### Returns

`MemoryDeleteResult`

###### Parameters

**`ctx`** : [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]

Framework-provided run context.

**`file`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Memory filename to delete.

##### search\_memory

`@async`

```python
def search_memory(ctx: RunContext[AgentDepsT], query: str) -> MemorySearchResponse
```

Search memory files in the current tenant and agent scope.

Results contain bounded snippets; call `read_memory` when a larger bounded excerpt is relevant.

###### Returns

`MemorySearchResponse`

###### Parameters

**`ctx`** : [`RunContext`](https://pydantic.dev/docs/ai/api/pydantic-ai/tools/#pydantic_ai.tools.RunContext)\[`AgentDepsT`\]

Framework-provided run context.

**`query`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Terms to find in memory filenames and content.

---
