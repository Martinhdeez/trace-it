# [Modal Sandbox](https://pydantic.dev/docs/ai/harness/modal-sandbox/)

> Give a Pydantic AI agent a per-run Modal sandbox with command and file tools.

# Modal Sandbox

`ModalSandbox` gives an agent an isolated cloud container for running commands and working with files. Use it for coding, data processing, and other tasks that should not execute model-generated commands on the application host.

The capability adds shell and file tools backed by a [Modal sandbox](https://modal.com/docs/guide/sandbox). By default, every agent run gets a fresh sandbox created from a container image. The capability requests termination when the run ends. You can also attach an existing sandbox or reuse one across several runs.

> While Pydantic AI Harness is on 0.x releases, the API may change between minor releases; when it does, deprecation warnings and release-note migration guidance tell you (or your agent) exactly how to upgrade. See the [version policy](https://pydantic.dev/docs/ai/harness/#version-policy).

## Quick start

Install the `modal` extra and authenticate with the Modal CLI. In CI, set `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` instead.

-   [pip](#tab-panel-138)
-   [uv](#tab-panel-139)
-   [pip](#tab-panel-140)
-   [uv](#tab-panel-141)

Terminal

```bash
pip install "pydantic-ai-harness[modal]"
```

Terminal

```bash
uv add "pydantic-ai-harness[modal]"
```

Terminal

```bash
 modal token new                # writes ~/.modal.toml
```

Terminal

```bash
uv run modal token new                # writes ~/.modal.toml
```

In CI, use environment variables instead of interactive authentication:

Terminal

```bash
export MODAL_TOKEN_ID=...
export MODAL_TOKEN_SECRET=...
```

Add `ModalSandbox` to the agent:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import ModalSandbox

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[ModalSandbox(image='python:3.12-slim')],
)

result = agent.run_sync('Create a Python script and run its tests.')
print(result.output)
```

During the run, the agent can create files, inspect its working directory, run commands, and react to command failures. The sandbox is separate from the host filesystem and process space.

The capability contributes four tools:

Tool

Purpose

`run_command`

Run a shell command through `sh -c`.

`read_file`

Read a UTF-8 text file with bounded output and line paging.

`write_file`

Write a UTF-8 text file and create parent directories.

`list_directory`

List directory entries, marking directories with `/`.

Command output labels stdout and stderr and reports non-zero exit codes to the model. It keeps the tail when truncating, so later diagnostics remain visible. File reads keep the head and return the next line offset when more content is available.

## Lifecycle

By default, each agent run creates an owned sandbox and requests its termination when the run exits, so expect a cold-start cost per run. Teardown waits for confirmation for a bounded period; if the control plane does not respond, `sandbox_timeout` remains the server-side cleanup backstop. The sandbox is provisioned when the run enters the capability toolset, even if no sandbox tool is called. Deferred tool loading controls which tool definitions reach the model; it does not defer toolset lifecycle.

Attach to a sandbox managed elsewhere by ID:

```python
from pydantic_ai_harness import ModalSandbox

ModalSandbox(sandbox_id='sb-abc123')
```

To share a sandbox across runs while controlling its lifetime, create and enter a `ModalSandboxSession` yourself:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import ModalSandbox
from pydantic_ai_harness.modal_sandbox import ModalSandboxSession

async with ModalSandboxSession(image='python:3.12-slim', sandbox_timeout=1800) as session:
    agent = Agent(
        'anthropic:claude-sonnet-4-6',
        capabilities=[ModalSandbox(session=session, max_command_timeout=600)],
    )
    await agent.run('Install the project dependencies.')
    await agent.run('Run the test suite in the same sandbox.')
```

Size the session's `sandbox_timeout` to the whole workload; the default 300s would expire partway through a multi-run session. The capability cannot see a reused sandbox's real lifetime, so each command there is capped at 300s unless `max_command_timeout` raises the ceiling.

Attached and injected sandboxes are left running when an agent run ends. They share a filesystem and process space, so do not use the same sandbox for overlapping runs that need isolation.

## Timeouts and output limits

Every model-facing command receives a finite deadline. `default_command_timeout` supplies the default and `max_command_timeout` caps model-supplied values. Modal accepts whole-second deadlines, so fractional values round up without exceeding the configured integer ceiling.

Modal does not expose a per-command kill operation. Cancelling the client wait does not stop the remote command immediately; it continues until its command deadline or the sandbox is terminated.

Each command stream retains the last `max_output_bytes` after every transport chunk, and each stream's payload is also truncated separately by `max_output_bytes` and `max_output_lines` in the tool output, so a large stderr cannot crowd out stdout and the `[stdout]` / `[stderr]` labels always survive. Any cut is marked. Labels, truncation or continuation notes, and command status add a small amount beyond those payload limits. One transport chunk can temporarily be larger than the byte limit. Invalid UTF-8 is decoded with replacement characters.

`read_file` checks file metadata before reading and checks the returned byte count again. A file that grows between those operations can temporarily exceed `max_read_bytes` in client memory before being rejected. Modal's filesystem API does not expose a bounded read, so use a bounded shell command for virtual files or other paths whose reported size may be misleading.

`list_directory` materializes the complete directory listing before truncating it. Listing a directory with many entries therefore uses memory proportional to the number of entries; use a narrowed shell command for unusually large directories.

Modal's SDK is asyncio-native. The capability requires an asyncio event loop and does not run under trio.

## Errors and composition

Recoverable command and filesystem failures become model retry prompts. A terminated sandbox raises `ModalSandboxUnavailableError` and rejected Modal credentials raise `ModalSandboxAuthError` (both `ModalSandboxTerminalError` subclasses) instead of retrying against the same unusable sandbox.

The toolset is an implementation detail. The public lower-level API consists of `ModalSandboxSession`, `ModalSandboxExecResult`, and the typed sandbox error classes.

Do not combine this capability with another unprefixed capability that registers `run_command`, `read_file`, `write_file`, or `list_directory` (e.g. the Shell or FileSystem capabilities). Pydantic AI rejects duplicate tool names. Prefix the capability before composing it with another capability that uses the same names:

```python
from pydantic_ai.capabilities import PrefixTools

from pydantic_ai_harness import ModalSandbox

sandbox = PrefixTools(
    wrapped=ModalSandbox(
        instructions=(
            'You have a Modal cloud sandbox. Use the modal_-prefixed tools to run '
            'shell commands and manage files in it.'
        )
    ),
    prefix='modal',
)
```

Prefixing renames the tools (`modal_run_command`, ...) but does not rewrite the capability's default instructions, which name the unprefixed tools -- pass `instructions` with text that matches the prefixed names.

## Configuration

```python
from pydantic_ai_harness import ModalSandbox

ModalSandbox(
    image='python:3.12-slim',
    sandbox_id=None,
    session=None,
    app_name='pydantic-ai-harness',
    create_app_if_missing=True,
    sandbox_timeout=300,
    workdir=None,
    env=None,
    default_command_timeout=60.0,
    max_command_timeout=None,
    max_output_bytes=50 * 1024,
    max_output_lines=2000,
    max_read_bytes=5 * 1024 * 1024,
    instructions=None,
)
```

The default instructions state the tools, the command timeout, and its ceiling. Set `instructions=''` to add none, or pass your own text to replace the default.

Settings used only when creating a sandbox cannot be combined with `sandbox_id` or an injected `session`. These conflicts fail at construction instead of being ignored.

## Not yet supported

-   Streaming command output: `run_command` returns once the command finishes (or hits its deadline), not incrementally.
-   Custom-built images, mounts, or `modal.Secret`: `image` takes a registry tag, and `env` takes plain environment variables. For anything richer, create the sandbox yourself with the Modal SDK and pass it via `sandbox_id` or `session`.
-   Spilling full output to a file: truncated file reads end with the next `offset` to page from and oversized files get a shell-slice hint; truncated command output gets a truncation marker. Nothing is written to a file in the sandbox for the model to open.

## Agent specs

Register `ModalSandbox` as a custom capability type when loading an agent spec:

```yaml
model: anthropic:claude-sonnet-4-6
capabilities:
  - ModalSandbox:
      image: python:3.12-slim
      sandbox_timeout: 600
```

```python
from pydantic_ai import Agent
from pydantic_ai_harness import ModalSandbox

agent = Agent.from_file('agent.yaml', custom_capability_types=[ModalSandbox])
```

## API reference

-   [Pydantic AI capabilities](https://pydantic.dev/docs/ai/capabilities/overview/)
-   [Pydantic AI toolsets](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/)
-   [Modal sandboxes](https://modal.com/docs/guide/sandbox)
-   [Modal Sandbox source code](https://github.com/pydantic/pydantic-ai-harness/tree/main/pydantic_ai_harness/modal_sandbox/)
-   [Pydantic AI Harness version policy](https://pydantic.dev/docs/ai/harness/#version-policy)

### ModalSandbox

**Bases:** `AbstractCapability[AgentDepsT]`

Access to an isolated cloud sandbox powered by [Modal](https://modal.com/).

Gives the agent tools to run commands and manage files inside a Modal sandbox, a place to execute untrusted or model-generated code without touching the host. By default each run gets a fresh sandbox created from `image`. When the run ends, the capability requests termination and waits for a bounded period; `sandbox_timeout` is the server-side cleanup backstop. To keep one sandbox across runs, either set `sandbox_id` to attach to a sandbox you manage elsewhere, or pass a `session` you own (an open `ModalSandboxSession`) so you control its lifetime and can read its `sandbox_id`. The capability never opens or terminates a `session` you pass.

Requires the `modal` extra (`uv add "pydantic-ai-harness[modal]"`) and Modal credentials, configured as for the Modal CLI: run `modal token new` once, or set `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` in the environment.

```python
from pydantic_ai import Agent
from pydantic_ai_harness.modal_sandbox import ModalSandbox

agent = Agent('anthropic:claude-sonnet-4-6', capabilities=[ModalSandbox()])
result = agent.run_sync('Write a Python script that prints the first 10 primes and run it.')
print(result.output)
```

#### Attributes

##### image

Container image for owned sandboxes, as a registry tag (e.g. `python:3.12-slim`).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `_DEFAULT_IMAGE`

##### sandbox\_id

Attach to an existing sandbox by id instead of creating one. Attached sandboxes are not terminated.

Use this to reuse a sandbox created elsewhere (e.g. via the Modal CLI). The settings that only apply when creating a sandbox (`image`, `app_name`, `create_app_if_missing`, `sandbox_timeout`, `workdir`, `env`) cannot be combined with `sandbox_id`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### session

Use a sandbox session you own and keep open across runs, instead of a per-run one.

Pass an already-entered `ModalSandboxSession` to reuse one sandbox across runs while controlling its lifetime yourself: the capability uses it but never opens or terminates it. Cannot be combined with `sandbox_id` or the owned-sandbox creation settings (the session already owns those). Like `sandbox_id`, a shared session is not concurrency-safe across overlapping runs.

**Type:** `ModalSandboxSession` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### app\_name

Modal app the owned sandbox is created under.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `_DEFAULT_APP_NAME`

##### create\_app\_if\_missing

If True, create the Modal app when it does not already exist.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### sandbox\_timeout

Maximum lifetime in seconds of an owned sandbox before Modal shuts it down.

This bounds the whole sandbox; `default_command_timeout` bounds a single command.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `_DEFAULT_SANDBOX_TIMEOUT`

##### workdir

Working directory for commands inside an owned sandbox (Modal's default when None).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### env

Environment variables to set in an owned sandbox.

Owned sandboxes only. To inject secrets or env into an attached or injected sandbox, set them when you create that sandbox yourself (e.g. with `modal.Secret`).

**Type:** [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### default\_command\_timeout

Default timeout in seconds for one `run_command`, used when the model omits one.

This bounds a single command; `sandbox_timeout` bounds the whole sandbox's lifetime. Modal enforces whole-second deadlines, so fractional values are rounded up (0.5 behaves as 1).

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) **Default:** `60.0`

##### max\_command\_timeout

Hard ceiling in seconds for any single `run_command`, including a model-supplied `timeout_seconds`. None falls back to `sandbox_timeout`.

Modal has no per-command kill, so a cancelled command keeps running until its deadline; this caps how long that worst case can be. An owned command cannot outlive `sandbox_timeout` anyway, so the default ceiling is exact for owned sandboxes.

For an attached or injected sandbox the fallback is still `sandbox_timeout`, which is pinned to its default (300s) in those modes because the capability does not know the real lifetime of a sandbox it did not create. So every command there is capped at 300s unless you set `max_command_timeout` to the value the sandbox actually allows.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### max\_output\_bytes

Maximum payload retained per command stream or file read, measured in UTF-8 bytes.

For commands the cap applies to stdout and stderr separately, both client-side (each stream retains at most this many bytes after Modal delivers each transport chunk) and in the tool output, so a large stderr cannot crowd out stdout. Labels, truncation notes, continuation offsets, timeouts, and exit codes add a small amount beyond this payload limit. Whichever of `max_output_bytes` and `max_output_lines` is reached first wins.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `DEFAULT_MAX_BYTES`

##### max\_output\_lines

Maximum payload lines retained per command stream or file read, alongside `max_output_bytes`.

A second cap so many short lines cannot pile up under the byte budget. Whichever cap is reached first wins. Labels and truncation or status notes can add lines beyond this payload limit. Both caps proxy a context budget; a future token-based cap would be additive.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `DEFAULT_MAX_LINES`

##### max\_read\_bytes

Largest file `read_file` will read whole; larger files are refused with a hint to use shell tools.

Modal has no bounded file-read API. The tool checks metadata before reading and checks the returned byte count again, but a file that grows between those operations can briefly exceed this value in client memory before it is rejected.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `_DEFAULT_MAX_READ_BYTES`

##### instructions

Instructions telling the model how to use the sandbox, added to the system prompt.

Leave as `None` for a default that matches the mode (fresh sandbox per run, or a reused one that can carry files from earlier runs) and states the command timeout and its ceiling. Set `''` to add no instructions, or pass your own text -- e.g. when wrapping with `PrefixTools`, so the tool names in the text match the prefixed ones.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

#### Methods

##### \_\_post\_init\_\_

```python
def __post_init__() -> None
```

Reject settings that the chosen mode would ignore, so a dead value can't mislead.

There are three modes: owned (the default), attach (`sandbox_id`), and injected (`session`). Attach and injected both reuse an existing sandbox, so the owned-only creation settings have no effect there; `session` also subsumes `sandbox_id`. Rather than ignore a conflicting value, fail at construction with the names to remove.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_instructions

```python
def get_instructions() -> str | None
```

Explain the sandbox to the model, unless overridden or disabled via `instructions`.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_toolset

```python
def get_toolset() -> AgentToolset[AgentDepsT]
```

Build and return the Modal sandbox toolset.

###### Returns

[`AgentToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AgentToolset)\[`AgentDepsT`\]

### ModalSandboxSession

Async context manager that owns or attaches to a Modal sandbox.

In _owned_ mode (the default) it creates a fresh sandbox from `image` on enter. On exit it requests termination and waits for a bounded period; `sandbox_timeout` is the server-side cleanup backstop. In _attach_ mode (`sandbox_id` set) it looks up an existing sandbox and leaves it running on exit, so a sandbox you manage elsewhere can be reused across runs.

Modal's SDK is asyncio-native, so this session drives its `.aio` coroutine API directly and requires an asyncio event loop. It authenticates the way the Modal CLI and SDK do: from the config written by `modal token new`, or from the `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` environment variables (which take precedence).

```python
from pydantic_ai_harness.modal_sandbox import ModalSandboxSession

async with ModalSandboxSession(image='python:3.12-slim') as session:
    result = await session.exec(['echo', 'hello'])
```

#### Attributes

##### sandbox\_id

The id of the running sandbox, or None when it is not running.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_aenter\_\_

`@async`

```python
def __aenter__() -> Self
```

Create or attach to the sandbox.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self)

##### \_\_aexit\_\_

`@async`

```python
def __aexit__(*args: object) -> None
```

Request termination when owned, then attempt to detach within bounded waits.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### exec

`@async`

```python
def exec(
    argv: Sequence[str],
    *,
    timeout: float | None = None,
    max_output_bytes: int | None = None,
) -> ModalSandboxExecResult
```

Run an argument vector in the sandbox (without a shell) and return its result.

Modal does not currently expose a per-exec kill, so cancelling this coroutine stops us waiting for the command but does not stop the command: it keeps running until its `timeout` deadline (or until the sandbox itself is terminated). Pass a finite `timeout` so a cancelled or abandoned command cannot run on indefinitely; `timeout=None` leaves it unbounded, which is why the toolset always sets one.

###### Returns

`ModalSandboxExecResult`

###### Parameters

**`argv`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\]

The command and its arguments.

**`timeout`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Per-command deadline in seconds, enforced server-side by Modal. None means no deadline (the command can outlive a cancellation).

**`max_output_bytes`** : [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Cap on how much of each stream is retained in client memory. A command can print far more than the caller will ever show the model, so with this set only the last `max_output_bytes` bytes of each stream are kept exactly. A retained byte suffix can begin inside a multi-byte character and is decoded with replacement. None reads each stream in full -- fine for the small outputs of a direct session caller, but the toolset always sets it.

##### file\_size

`@async`

```python
def file_size(path: str) -> int
```

Return a file's size in bytes via Modal's filesystem API, without reading it.

Lets a caller check size before reading the whole file. A relative `path` is resolved against the sandbox working directory (see `_resolve`).

###### Returns

[`int`](https://docs.python.org/3/builtins/functions.html#int)

###### Raises

-   `ModalSandboxError` -- if the file cannot be stat-ed (missing, a directory, ...).

##### read\_bytes

`@async`

```python
def read_bytes(path: str) -> bytes
```

Read a file's raw bytes from the sandbox via Modal's filesystem API.

The session deals in bytes so each tool layer can decode (or not) as it needs; text handling lives above the session, not here. A relative `path` is resolved against the sandbox working directory (see `_resolve`).

###### Returns

[`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes)

###### Raises

-   `ModalSandboxError` -- if the file cannot be read (missing, a directory, ...).

##### write\_bytes

`@async`

```python
def write_bytes(path: str, data: bytes) -> None
```

Write raw bytes to a file in the sandbox, creating parent directories.

A relative `path` is resolved against the sandbox working directory (see `_resolve`). Unlike shelling out, Modal's filesystem API streams the content, so the size is not bounded by the argument-length limit of a command, and it creates missing parent directories itself.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Raises

-   `ModalSandboxError` -- if the file cannot be written (bad path, permissions, ...).

##### list\_files

`@async`

```python
def list_files(path: str) -> list[tuple[str, bool]]
```

List a sandbox directory as `(name, is_dir)` pairs.

A relative `path` is resolved against the sandbox working directory (see `_resolve`). The Modal-native `FileInfo` entries are normalized to plain tuples here so the provider type does not leak past the session.

###### Returns

[`list`](https://docs.python.org/3/glossary.html#term-list)\[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`bool`](https://docs.python.org/3/builtins/functions.html#bool)\]\]

###### Raises

-   `ModalSandboxError` -- if the directory cannot be listed.

### ModalSandboxExecResult

The outcome of running a command in the sandbox.

#### Attributes

##### stdout

The command's standard output, tail-truncated when `max_output_bytes` was set.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### stderr

The command's standard error, tail-truncated when `max_output_bytes` was set.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### returncode

The exit status: 0-255 for a real exit (128+n for signal n), or Modal's `-1` deadline sentinel.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int)

##### stdout\_truncated

True when `max_output_bytes` dropped earlier stdout bytes; `stdout` is the retained tail.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### stderr\_truncated

True when `max_output_bytes` dropped earlier stderr bytes; `stderr` is the retained tail.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### timed\_out

True when a deadline was applied and the command was killed by it.

Modal reports a client-side deadline kill as returncode `-1`; a server-side kill at the same deadline surfaces as the plain SIGKILL exit (137), so that exit is also read as a timeout when the command consumed its whole deadline window.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### applied\_timeout

The whole-second deadline Modal enforced for this command, or None if unbounded.

This is the quantized value actually sent to Modal, not the (possibly fractional) timeout the caller requested, so the caller can report the exact deadline.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

### ModalSandboxError

**Bases:** [`RuntimeError`](https://docs.python.org/3/builtins/exceptions.html#RuntimeError)

Base class for failures reported by the Modal sandbox integration.

The toolset turns direct instances into `ModelRetry`. Terminal subclasses propagate because retrying cannot restore a missing sandbox or credentials.

### ModalSandboxTerminalError

**Bases:** `ModalSandboxError`

A sandbox failure that retrying cannot fix, so the run should end, not loop.

The toolset lets this propagate out of the tool (ending the run) instead of turning it into a `ModelRetry`: re-issuing the command would hit the same wall. Raised as `ModalSandboxUnavailableError` for a sandbox that no longer exists and `ModalSandboxAuthError` for rejected credentials.

### ModalSandboxAuthError

**Bases:** `ModalSandboxTerminalError`

Modal rejected the credentials, so no sandbox operation can succeed.

Fixing this is an operator action (configure credentials), not something a retry or a new run can do, which is why it is terminal.

### ModalSandboxUnavailableError

**Bases:** `ModalSandboxTerminalError`

The sandbox no longer exists: terminated, or expired at its `sandbox_timeout`.

Every later command against it would fail the same way, so it is terminal. In owned mode this is what a run outliving the sandbox lifetime looks like; raise `sandbox_timeout` (or shorten the work) if runs legitimately need longer.

---
