# [StackOne](https://pydantic.dev/docs/ai/harness/stackone/)

> Let a Pydantic AI agent use actions from one of the user's linked business applications through StackOne.

# StackOne

Use `StackOne` when an agent needs to work with one of a user's linked business applications, such as BambooHR, Salesforce, or Zendesk. Each instance is scoped to one linked account, which is one authenticated connection between [StackOne](https://www.stackone.com/) and a provider.

[Source](https://github.com/pydantic/pydantic-ai-harness/tree/main/pydantic_ai_harness/stackone/)

> While Pydantic AI Harness is on 0.x releases, the API may change between minor releases; when it does, deprecation warnings and release-note migration guidance tell you (or your agent) exactly how to upgrade. See the [version policy](https://pydantic.dev/docs/ai/harness/#version-policy).

## Before you start

Follow the [StackOne docs](https://docs.stackone.com/) to:

1.  Configure a connector and link an account. For your first test, enable only the read actions you need.
2.  Copy the linked account ID from the StackOne dashboard.
3.  Create a StackOne API key that can execute actions.

You also need an API key for the model your agent uses.

## Installation

-   [pip](#tab-panel-154)
-   [uv](#tab-panel-155)

Terminal

```bash
pip install "pydantic-ai-harness[stackone]" "pydantic-ai-slim[openai,spec]"
```

Terminal

```bash
uv add "pydantic-ai-harness[stackone]" "pydantic-ai-slim[openai,spec]"
```

The `openai` and `spec` extras support the model and agent-spec examples below. Install the provider extra for a different model provider instead.

Set the credentials in the shell where you will run the example:

Terminal

```bash
export STACKONE_API_KEY='your-stackone-api-key'
export STACKONE_ACCOUNT_ID='your-linked-account-id'
export OPENAI_API_KEY='your-openai-api-key'
```

`StackOne` reads `STACKONE_API_KEY` automatically. The example reads `STACKONE_ACCOUNT_ID` explicitly so the account ID is not hard-coded. You can pass `api_key=` directly instead, but keep secrets out of source control.

## Run your first agent

```python
import os

from pydantic_ai import Agent
from pydantic_ai_harness import StackOne

agent = Agent(
    'openai:gpt-5',
    capabilities=[
        StackOne(account_id=os.environ['STACKONE_ACCOUNT_ID']),
    ],
)
result = agent.run_sync('List the first 5 employees')
print(result.output)
```

By default, the model receives two tools. It searches for an action that matches the request, then executes the returned action ID. The final output depends on the linked provider and its data.

## Control available actions

StackOne controls which actions are enabled for the linked account. Treat that configuration as the primary access control.

Use `actions` when you also want to limit which tools the model sees. Patterns use Python [`fnmatch`](https://docs.python.org/3/library/fnmatch.html) syntax, where `*` is a wildcard. They ignore case and match the full `{connector}_{action}_{entity}` tool name:

```python
from pydantic_ai_harness import StackOne

StackOne(account_id='your-linked-account-id', actions=['*_list_*'])            # All matching list tools
StackOne(account_id='your-linked-account-id', actions=['workday_get_worker'])  # One exact tool
```

Passing `actions` selects `individual` mode automatically. Explicitly combining `actions` with `tool_mode='search_execute'` raises an error because that mode registers only the search and execute tools.

## Choose a tool mode

Mode

What the model receives

Use it when

`search_execute`

Two tools: search for an action, then execute it by ID

The account has many enabled actions. This is the default when `actions` is omitted.

`individual`

One tool and schema per enabled action

You need to select exact actions or add per-tool behavior. Passing `actions` selects this mode.

In `search_execute` mode, action IDs are returned by the search tool at runtime and should not be guessed. In `individual` mode, all selected tool schemas are sent to the model, so filter large action sets with `actions`.

To keep StackOne tools out of the model context until they are needed, pass `defer_loading=True`. The capability needs an `id` to be loaded on demand, and derives one from the linked account -- `StackOne(account_id='45320')` is `stackone-45320` -- so one agent can reach several accounts without naming each one:

```python
from pydantic_ai_harness import StackOne

StackOne(account_id='your-linked-account-id', defer_loading=True)
```

Two capabilities on the _same_ account share that id and are rejected at agent construction, which is what you want: one linked account is one connection. Pass an explicit `id=` if you need to override the derived one.

### Two accounts on one agent

Distinct ids keep the two capabilities apart, but they do not rename their tools. StackOne's server names the tools after the connector and action (`bamboohr_list_employees`), so two accounts on the same provider list the same names and the run fails on the tool name rather than the id:

```
UserError: StackOneToolset 'stackone-crm-account' defines a tool whose name conflicts with
existing tool from StackOneToolset: 'bamboohr_list_employees'
```

Namespace them with [`PrefixTools`](https://pydantic.dev/docs/ai/capabilities/overview/), which is what it is for:

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import PrefixTools

from pydantic_ai_harness import StackOne

agent = Agent(
    'openai:gpt-5.6-sol',
    capabilities=[
        PrefixTools(StackOne(account_id='hr-account'), prefix='hr'),
        PrefixTools(StackOne(account_id='crm-account'), prefix='crm'),
    ],
)
```

The model sees `hr_bamboohr_list_employees` and `crm_bamboohr_list_employees`, and each routes to its own linked account. Two accounts on _different_ providers list different tool names already, so they need no prefix.

### Bound large tool results

Provider actions can return large exports. Combine StackOne with the [Tool Output Limits](https://pydantic.dev/docs/ai/harness/tool-output-limits/) capability to reduce oversized tool returns agent-wide:

```python
from pydantic_ai import Agent
from pydantic_ai_harness import StackOne, ToolOutputLimits

agent = Agent(
    'openai:gpt-5',
    capabilities=[
        StackOne(account_id='your-linked-account-id'),
        ToolOutputLimits(),
    ],
)
```

### Require approval

Approval is not enabled automatically. For operations that need human confirmation, use the public `StackOneToolset` with Pydantic AI's [tool approval](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/#requiring-tool-approval):

```python
import os

from pydantic_ai import Agent
from pydantic_ai_harness.stackone import StackOneToolset

stackone_tools = StackOneToolset(
    account_id=os.environ['STACKONE_ACCOUNT_ID'],
    actions=['workday_create_worker'],
).approval_required()

agent = Agent('openai:gpt-5', toolsets=[stackone_tools])
```

Handle the resulting deferred approval requests as described in the linked guide.

## Define the agent in YAML or JSON

The capability also works with Pydantic AI's [agent spec](https://pydantic.dev/docs/ai/core-concepts/agent-spec/) format for YAML or JSON. Keep the API key in `STACKONE_API_KEY` rather than storing it in the file:

```yaml
# agent.yaml
model: openai:gpt-5
capabilities:
  - StackOne:
      account_id: 'your-linked-account-id'
      actions: ['*_list_*']
```

```python
from pydantic_ai import Agent
from pydantic_ai_harness import StackOne

agent = Agent.from_file('agent.yaml', custom_capability_types=[StackOne])
```

Pass `custom_capability_types` so the spec loader knows how to instantiate `StackOne`.

Use the lower-level `StackOneToolset` directly when you need [`Agent(toolsets=[...])`](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/) or other toolset wrappers.

Custom `base_url` and URL-valued `client` values must use HTTPS. The toolset adds auth headers and appends the `tool-mode` query parameter for URL values when it is absent. It raises an error when the URL's `tool-mode` conflicts with the configured mode because rewriting would invalidate signed URLs. When using `search_execute` with a signed URL, include `tool-mode=search_execute` before signing. Prebuilt clients are used as-is; configure their HTTPS transport, auth, account selection, and tool mode yourself.

## API reference

### StackOne

**Bases:** `AbstractCapability[AgentDepsT]`

Actions on the user's SaaS account (HRIS, ATS, CRM, and more) via StackOne.

Connects an agent to one linked account's actions over StackOne's MCP endpoint, with authentication, tool filtering, and usage instructions.

#### Attributes

##### account\_id

The linked account to act on (one account is one provider connection).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### id

Stable capability and toolset ID, derived from `account_id` when not given.

One account is one provider connection, so the account is what identifies this capability -- the same way an MCP server is identified by its URL. Deriving it rather than fixing it to `'stackone'` is what lets one agent reach two linked accounts: their ids differ, so they stay two capabilities. Two under the _same_ account are a mistake, and collide.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### description

Routing description used when the capability is loaded on demand.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `_DEFAULT_DESCRIPTION`

##### api\_key

StackOne API key. Defaults to the `STACKONE_API_KEY` environment variable.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, repr=False)`

##### base\_url

HTTPS StackOne API host. Point at a regional or staging host if needed.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `STACKONE_BASE_URL`

##### actions

`fnmatch` globs over full tool names (case-insensitive), e.g. `['*_list_*']`. Giving `actions` switches the default `tool_mode` to `individual`, where the globs apply.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `()`

##### tool\_mode

`individual` registers one tool per enabled action; `search_execute` registers two server-side meta-tools (search the catalog, execute an action by id) whose prompt footprint stays constant however large the catalog is. `None` picks `search_execute`, or `individual` when `actions` are given.

**Type:** `ToolMode` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### include\_instructions

Inject StackOne usage instructions into the system prompt.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

##### metadata

Metadata merged onto every tool, available to tool-selection machinery such as `CodeMode(tools={'code_mode': True})` or custom `prepare_tools` hooks.

**Type:** [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`object`](https://docs.python.org/3/glossary.html#term-object)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### client

Replacement for the default `{base_url}/mcp` connection. URL values must use HTTPS; prebuilt clients keep their own transport, auth, and account selection, so `account_id` is not applied to them.

**Type:** `MCPToolsetClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `field(default=None, repr=False)`

#### Methods

##### get\_toolset

```python
def get_toolset() -> StackOneToolset[AgentDepsT]
```

Build the StackOne toolset.

###### Returns

`StackOneToolset`\[`AgentDepsT`\]

##### get\_instructions

```python
def get_instructions() -> str | None
```

StackOne usage guidance; the underlying MCP toolset provides none itself.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### from\_spec

`@classmethod`

```python
def from_spec(
    cls,
    account_id: str,
    *,
    id: str | None = None,
    description: str | None = _DEFAULT_DESCRIPTION,
    defer_loading: bool = False,
    api_key: str | None = None,
    base_url: str = STACKONE_BASE_URL,
    actions: str | Sequence[str] = (),
    tool_mode: ToolMode | None = None,
    include_instructions: bool = True,
    metadata: Mapping[str, object] | None = None,
) -> StackOne[AgentDepsT]
```

Construct from serializable options, excluding the runtime-only `client`.

###### Returns

`StackOne`\[`AgentDepsT`\]

##### get\_serialization\_name

`@classmethod`

```python
def get_serialization_name(cls) -> str
```

Return the agent-spec capability name.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### StackOneToolset

**Bases:** `MCPToolset[AgentDepsT]`

StackOne actions on one linked SaaS account, as an agent toolset.

An `MCPToolset` connected to StackOne's MCP endpoint. URL clients receive StackOne auth and account headers. Action filtering and metadata merging apply to the tools listed by the server. Prebuilt clients keep their own transport configuration. Instances support the full `MCPToolset` surface.

Use the `StackOne` capability for usage instructions and agent-spec support. Use this class for toolset combinators such as `approval_required()`.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    *,
    account_id: str,
    api_key: str | None = None,
    base_url: str = STACKONE_BASE_URL,
    actions: Sequence[str] = (),
    tool_mode: ToolMode | None = None,
    metadata: Mapping[str, object] | None = None,
    client: MCPToolsetClient | None = None,
    id: str = 'stackone',
) -> None
```

Build a StackOne MCP toolset.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

###### Parameters

**`account_id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

Linked account used for StackOne requests.

**`api_key`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

API key, or `STACKONE_API_KEY` when omitted.

**`base_url`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `STACKONE_BASE_URL`

HTTPS StackOne API host.

**`actions`** : [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] _Default:_ `()`

Case-insensitive globs over individual action tool names. Selects `individual`; incompatible with explicit `search_execute`.

**`tool_mode`** : `ToolMode` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Individual tools or the search/execute pair. Inferred when omitted.

**`metadata`** : [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`object`](https://docs.python.org/3/glossary.html#term-object)\] | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Metadata merged onto each tool definition.

**`client`** : `MCPToolsetClient` | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

URL, `FastMCP`, or prebuilt client accepted by `MCPToolset`. Non-URL clients keep their own transport, auth, and account selection, so `account_id` is not applied to them.

**`id`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) _Default:_ `'stackone'`

Toolset ID; use distinct values for multiple accounts.

---
