# [Repo Context](https://pydantic.dev/docs/ai/harness/repo-context/)

> Discover and load a repo's accumulated coding-assistant context engineering -- instruction files, skills, sub-agents, and hooks.

# Repo Context

`RepoContext` discovers and loads a repo's accumulated coding-assistant context engineering (CE): the instruction files (`CLAUDE.md`/`AGENTS.md`) scattered across the tree and the assets under `.claude`/`.agents`/`.codex`/`.grok` (skills, sub-agents, hooks).

[Source](https://github.com/pydantic/pydantic-ai-harness/tree/main/pydantic_ai_harness/repo_context/)

> While Pydantic AI Harness is on 0.x releases, the API may change between minor releases; when it does, deprecation warnings and release-note migration guidance tell you (or your agent) exactly how to upgrade. See the [version policy](https://pydantic.dev/docs/ai/harness/#version-policy).

## The problem

A repo accumulates CE for whatever coding assistant worked in it: instruction files (`CLAUDE.md`/`AGENTS.md`) scattered across the tree, and assets under `.claude`/`.agents`/`.codex`/`.grok` (skills, sub-agents, hooks). An agent that loads only the top-level instruction file misses the ancestor context and has no idea the rest of the setup exists, so it can neither honor it nor translate it.

## The solution

`RepoContext` bundles three strategies, each independently toggleable. Construct it with `RepoContext(...)` in an `Agent`'s `capabilities`, anchored at the deepest directory the agent works in:

```python
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai_harness import RepoContext

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[RepoContext(workspace_dir=Path('.'), home_dir=Path.home())],
)

result = agent.run_sync('Summarize the coding-assistant setup in this repo.')
print(result.output)
```

### 1\. Walk-up instruction autoload (on by default)

Loads `CLAUDE.md`/`AGENTS.md` from `workspace_dir` and every ancestor up to `home_dir` (inclusive). Precedence is ancestor-first, workspace-last: broadest context first, most specific last. Files are deduped by resolved real path and by content hash, so a symlinked `AGENTS.md -> CLAUDE.md` or two ancestors sharing identical content load once.

When `home_dir` is `None` (the default), only `workspace_dir` is scanned -- no walk-up. Pass `home_dir=Path.home()` to walk up to your home directory.

### 2\. Asset inventory (on by default)

Exposes one tool, `inventory_agent_context()`, that reports where the repo's CE assets live -- the `.claude`/`.agents`/`.codex`/`.grok` roots and, within each, the `skills/` (`SKILL.md`), `agents/` (`.md`), and `settings.json` (hooks) it contains. It returns a structured `AgentContextInventory`; it locates assets and does not parse them, leaving translation to the orchestrator.

Rename the tool with `inventory_tool_name`, or scope which roots it scans with `asset_roots`.

### 3\. Nested-on-traversal (off by default)

When the model lists or reads a directory, surface that directory's `CLAUDE.md`/`AGENTS.md`. This strategy subscribes to `FileReadEvent` and `DirectoryListedEvent`, so it receives normalized, containment-checked paths instead of inspecting raw tool arguments. It remains opt-in:

```python
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai_harness import FileSystem, RepoContext

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[
        FileSystem(root_dir='.'),
        RepoContext(
            workspace_dir=Path('.'),
            nested_traversal=True,
            nested_inject='pointer',  # or 'contents'
        )
    ],
)
```

`nested_inject='pointer'` (default) enqueues a one-line note pointing at the file; `'contents'` enqueues the file body. The note reaches message history before the next model request. Each directory is surfaced at most once per run.

`FileSystem` emits these events directly. Hosts with other file tools can emit the same types by importing `FileReadEvent` and `DirectoryListedEvent` from `pydantic_ai_harness.filesystem`; set `root_dir` to the directory the event's `path` is relative to.

The traversed location is `root_dir / path`, so a `FileSystem` rooted at a subdirectory of `workspace_dir` still surfaces the right directory. A traversal that resolves outside `workspace_dir` is ignored: it is not nested in the workspace, so there is no nested context to surface.

`traversal_tool_names` and `traversal_path_arg` are deprecated. Setting either to a non-default value emits `HarnessDeprecationWarning` and keeps the old tool-name and argument sniffing path active for hosts that do not emit events. With the defaults, sniffing is disabled, so a `FileSystem` event cannot deliver the same note twice.

## Cache cost

Injecting file contents into the system prompt costs prompt-cache stability: a changed prefix re-bills the whole cached region. `RepoContext` keeps the two cache-relevant paths separate:

-   Strategy 1 reads its files once at run start and injects them as static system instructions, so the cached prefix stays byte-identical across turns.
-   Strategy 3 is volatile (it depends on which directory was just touched), so its note is enqueued in the message tail, never in the system prompt, and cannot invalidate the cached prefix.

## Configuration

```python
RepoContext(
    workspace_dir,                  # Path -- the deepest dir the agent works in (required)
    home_dir=None,                  # Path | None -- shallowest dir to stop walk-up at, inclusive
    filenames=('CLAUDE.md', 'AGENTS.md'),
    autoload_instructions=True,     # Strategy 1
    expose_inventory_tool=True,     # Strategy 2
    inventory_tool_name='inventory_agent_context',
    nested_traversal=False,         # Strategy 3
    nested_inject='pointer',        # 'pointer' | 'contents'
    traversal_tool_names=frozenset({'list_directory', 'read_file'}),  # deprecated fallback
    traversal_path_arg='path',                                       # deprecated fallback
    asset_roots=('.claude', '.agents', '.codex', '.grok'),
)
```

## Scope

`RepoContext` locates and loads CE; it does not parse skill/sub-agent frontmatter or hook bodies, and it does not rewrite or translate assets. Strategy 1 reads its files once per run, so mid-run edits to those files are not reloaded.

## Further reading

-   [Pydantic AI capabilities](https://pydantic.dev/docs/ai/capabilities/overview/)
-   [Pydantic AI hooks](https://pydantic.dev/docs/ai/core-concepts/hooks/)

## API reference

### RepoContext

**Bases:** `AbstractCapability[AgentDepsT]`

Discover and load a repo's accumulated coding-assistant context engineering.

Three strategies, each independently toggleable:

1.  Walk-up instruction autoload (`autoload_instructions`, on by default): load `CLAUDE.md`/`AGENTS.md` from `workspace_dir` and every ancestor up to `home_dir`, deduped, ancestor-first. These are read once at run start and injected as **static system instructions** via `get_instructions`, so they stay in the cached prefix and never re-read per turn.
    
2.  Asset inventory (`expose_inventory_tool`, on by default): a tool that reports where the repo's CE assets live (`.claude`/`.agents`/`.codex`/ `.grok` and their `skills/`, `agents/`, `settings.json`). It locates assets; it does not parse them.
    
3.  Nested-on-traversal (`nested_traversal`, off by default): when the model lists or reads a directory through a filesystem capability event, surface that directory's `CLAUDE.md`/`AGENTS.md`. The note is enqueued in the message tail, not added to system instructions, so it does not invalidate the cached prefix. `nested_inject='pointer'` (default) enqueues a one-line pointer; `'contents'` inlines the file body.
    

Cache note: injecting file contents into the system prompt costs prompt-cache stability. Strategy 1 is safe because its files are static; the volatile Strategy 3 content rides in the message tail instead.

```python
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai_harness.repo_context import RepoContext

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[RepoContext(workspace_dir=Path('.'), home_dir=Path.home())],
)
```

#### Attributes

##### workspace\_dir

The deepest directory the agent works in. The walk-up and asset scan are anchored here.

**Type:** `Path`

##### home\_dir

The shallowest directory to stop the walk-up at, inclusive. `None` (the default) scans only `workspace_dir` -- no walk-up.

**Type:** `Path` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### filenames

Instruction filenames to look for, in within-directory precedence order.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `('CLAUDE.md', 'AGENTS.md')`

##### autoload\_instructions

Strategy 1: load instruction files into the system prompt.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### expose\_inventory\_tool

Strategy 2: expose the asset-inventory tool.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### inventory\_tool\_name

Name of the inventory tool exposed to the model.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'inventory_agent_context'`

##### nested\_traversal

Strategy 3: surface a directory's instruction file when the model lists or reads that directory. Off by default -- it couples to the list/read tools.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### nested\_inject

For Strategy 3: append a one-line `pointer`, or inline the file `contents`.

**Type:** [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['pointer', 'contents'\] **Default:** `'pointer'`

##### traversal\_tool\_names

Deprecated tool names used by the compatibility traversal detector.

**Type:** [`frozenset`](https://docs.python.org/3/builtins/stdtypes.html#frozenset)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `_DEFAULT_TRAVERSAL_TOOL_NAMES`

##### traversal\_path\_arg

Deprecated path argument used by the compatibility traversal detector.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `_DEFAULT_TRAVERSAL_PATH_ARG`

##### asset\_roots

Root directories the inventory tool scans, relative to `workspace_dir`.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `('.claude', '.agents', '.codex', '.grok')`

#### Methods

##### for\_run

`@async`

```python
def for_run(ctx: RunContext[AgentDepsT]) -> RepoContext[AgentDepsT]
```

Return a fresh per-run instance with isolated traversal/cache state.

###### Returns

`RepoContext`\[`AgentDepsT`\]

##### get\_instructions

```python
def get_instructions() -> AgentInstructions[AgentDepsT] | None
```

Static, cache-stable instructions: loaded files plus the inventory hint.

###### Returns

`AgentInstructions`\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_toolset

```python
def get_toolset() -> AgentToolset[AgentDepsT] | None
```

The asset-inventory toolset, or `None` when the tool is disabled.

###### Returns

[`AgentToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AgentToolset)\[`AgentDepsT`\] | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### after\_tool\_execute

`@async`

```python
def after_tool_execute(
    ctx: RunContext[AgentDepsT],
    *,
    call: ToolCallPart,
    tool_def: ToolDefinition,
    args: dict[str, Any],
    result: Any,
) -> Any
```

Support customized legacy traversal tool and argument names.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### get\_serialization\_name

`@classmethod`

```python
def get_serialization_name(cls) -> str | None
```

Serialization name for agent-spec support.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### AgentContextInventory

**Bases:** `BaseModel`

A map of where a repo's CE assets live, for an orchestrator to read or translate.

### AssetRoot

**Bases:** `BaseModel`

Where CE assets live under a single root directory (e.g. `.claude`).

---
