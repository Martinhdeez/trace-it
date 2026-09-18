# [LocalStack](https://pydantic.dev/docs/ai/harness/localstack/)

> Give a Pydantic AI agent access to an emulated AWS environment through the AWS CLI, with an optional Docker-managed LocalStack container lifecycle.

# LocalStack

`LocalStack` gives an agent access to an emulated AWS environment, so it can provision and exercise AWS services without touching a real account. It wires the AWS CLI to a running [LocalStack](https://www.localstack.cloud/) instance -- injecting the endpoint, region, and credentials -- and can optionally start and stop the LocalStack Docker container for each run.

[Source](https://github.com/pydantic/pydantic-ai-harness/tree/main/pydantic_ai_harness/localstack/)

> While Pydantic AI Harness is on 0.x releases, the API may change between minor releases; when it does, deprecation warnings and release-note migration guidance tell you (or your agent) exactly how to upgrade. See the [version policy](https://pydantic.dev/docs/ai/harness/#version-policy).

## The problem

Agents that build or test cloud infrastructure need somewhere to create buckets, tables, queues, and functions. Pointing them at real AWS is slow, costs money, risks leaking credentials, and is hard to reset between runs. LocalStack emulates the AWS APIs locally, but wiring an agent to it means repeating the same boilerplate: injecting the endpoint URL, supplying dummy credentials, shelling out to the AWS CLI, and checking which services are up.

## Usage

`LocalStack` exposes AWS tooling wired to a running LocalStack instance. The agent issues plain AWS CLI commands; the capability injects the endpoint, region, and credentials, and adds a health check for the emulated services.

```python
from pydantic_ai import Agent
from pydantic_ai_harness import LocalStack

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[LocalStack()],
)

result = agent.run_sync('Create an S3 bucket called reports and list all buckets.')
print(result.output)
```

By default the agent connects to a LocalStack instance you started separately -- for example with the [`localstack` CLI](https://docs.localstack.cloud/aws/tooling/localstack-cli/) (`localstack start`). The defaults match LocalStack's conventions: the edge endpoint `http://localhost.localstack.cloud:4566` (which resolves to `127.0.0.1`) and `test` / `test` credentials. Set `manage_container=True` to have the capability start and stop a fresh Docker container per run.

## Tools

Tool

Purpose

`aws_cli`

Run an AWS CLI command against LocalStack. Pass the command **without** the leading `aws` and **without** `--endpoint-url` -- both are injected. Returns labelled stdout/stderr plus an exit code on failure.

`localstack_health`

Query LocalStack's health endpoint and return the JSON of which services (s3, dynamodb, sqs, etc.) are available.

Commands run as an argument vector (no shell), so shell operators and redirection in the command string have no effect. Output is labelled with `[stdout]` / `[stderr]` markers and an `[exit code: N]` line on non-zero exit. When it exceeds `max_output_chars` the **tail** is kept (the head is dropped), so errors survive truncation.

The AWS CLI can read from and write to local files through arguments such as `--body`, `file://`, `fileb://`, and `s3 cp`. Treat this capability as both AWS-emulator access and AWS CLI access to the process's filesystem.

## Service controls

Field

Effect

`allowed_services`

If non-empty, only these AWS services may be used (allowlist), e.g. `['s3', 'dynamodb']`.

`denied_services`

These AWS services are always rejected (denylist).

`allowed_services` and `denied_services` are mutually exclusive -- set one, not both. The service is the first non-flag token of the command (`s3` in `s3 ls`).

Best-effort, not a security boundary

These checks gate which commands the agent issues, not what it can reach. For hard guarantees, configure LocalStack itself with the narrowest service and IAM behavior the run needs, and run the agent under OS-level isolation.

## Managing the container

Set `manage_container=True` and the capability starts a LocalStack Docker container for each run and stops it when the run ends, so the agent always gets a fresh, isolated environment. Docker must be installed and running.

```python
from pydantic_ai_harness import LocalStack

LocalStack(
    manage_container=True,
    image='localstack/localstack',
    container_env={'DEBUG': '1', 'PERSISTENCE': '1'},
    startup_timeout=120.0,
)
```

The container's edge port (`4566`) is published on the host port from `endpoint_url`, and the capability waits for the health endpoint before the run starts, then stops the container when it ends (even if the run raises). Each run gets its own container, so concurrent runs of one agent need distinct host ports or an externally managed instance (`manage_container=False`).

Since LocalStack 2026.03.0 the default `localstack/localstack` image is a single image that requires an auth token to start (a free Hobby/OSS token covers community usage). When `LOCALSTACK_AUTH_TOKEN` is set in the current process it is forwarded to the container automatically; a legacy `LOCALSTACK_API_KEY` value is forwarded when no auth token is set. Auth values are forwarded through the Docker CLI environment rather than embedded in the `docker run` arguments. The default `localstack/localstack` image requires a token to start, so a managed run needs one configured. To run tokenless, set `image` to a tag from before the account requirement, such as a `localstack/localstack:4.x` release.

Docker-backed services such as Lambda need the Docker socket mounted, and some services expose ports outside the gateway (LocalStack reserves `4510-4559`). Enable those explicitly when a service you test requires them:

```python
from pydantic_ai_harness import LocalStack

LocalStack(manage_container=True, service_port_range='4510-4559', mount_docker_socket=True)
```

Mounting the Docker socket gives the container host-level Docker control. Keep `mount_docker_socket=False` unless the emulated service requires it and the run environment is already trusted.

The same lifecycle is available standalone as an async context manager:

```python
import asyncio

from pydantic_ai_harness.localstack import LocalStackContainer


async def main() -> None:
    async with LocalStackContainer(environment={'DEBUG': '1'}) as localstack:
        ...  # talk to localstack.endpoint_url


asyncio.run(main())
```

## Configuration

```python
from pydantic_ai_harness import LocalStack

LocalStack(
    endpoint_url='http://localhost.localstack.cloud:4566',  # edge endpoint (host port reused when managed)
    region='us-east-1',                    # region for the CLI and environment
    access_key_id='test',                  # LocalStack accepts any value
    secret_access_key='test',              # LocalStack accepts any value
    allowed_services=[],                   # allowlist (mutually exclusive with denied)
    denied_services=[],                    # denylist
    default_timeout=60.0,                  # seconds, per command and health check
    max_output_chars=50_000,               # output cap returned to the model
    aws_cli_path='aws',                    # CLI executable (e.g. 'aws' or 'awslocal')
    manage_container=False,                # start/stop a Docker container per run
    image='localstack/localstack',         # image used when managing the container
    host_address='127.0.0.1',              # host address for Docker port publishing
    service_port_range=None,               # e.g. '4510-4559' for non-gateway service ports
    mount_docker_socket=False,             # required by Docker-backed services such as Lambda
    container_name=None,                   # optional name for the managed container
    container_env={},                      # env vars for the managed container
    docker_path='docker',                  # Docker executable
    startup_timeout=120.0,                 # seconds to wait for the container to be ready
    include_instructions=True,             # add usage instructions to the prompt
)
```

The AWS CLI must be installed and on `PATH` (or point `aws_cli_path` at it). If the binary is missing, `aws_cli` returns a clear error instead of aborting the run. Set `include_instructions=False` to omit the capability's prompt text when you supply your own.

## Agent spec (YAML/JSON)

`LocalStack` works with Pydantic AI's [agent spec](https://pydantic.dev/docs/ai/core-concepts/agent-spec/):

```yaml
# agent.yaml
model: anthropic:claude-sonnet-4-6
capabilities:
  - LocalStack:
      endpoint_url: http://localhost.localstack.cloud:4566
      allowed_services: ['s3', 'dynamodb', 'sqs']
```

```python
from pydantic_ai import Agent
from pydantic_ai_harness import LocalStack

agent = Agent.from_file('agent.yaml', custom_capability_types=[LocalStack])
```

Pass `custom_capability_types` so the spec loader knows how to instantiate `LocalStack`.

## Further reading

-   [LocalStack documentation](https://docs.localstack.cloud/)
-   [Pydantic AI capabilities](https://pydantic.dev/docs/ai/capabilities/overview/)
-   [Toolsets](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/)

## API reference

### LocalStack

**Bases:** `AbstractCapability[AgentDepsT]`

Access to an emulated AWS environment via LocalStack.

Gives the agent AWS CLI tooling wired to a running LocalStack instance, so it can provision and interact with AWS services (S3, DynamoDB, SQS, Lambda, ...) without touching real AWS. Start LocalStack separately (`localstack start` or its Docker image) before running the agent.

```python
from pydantic_ai import Agent
from pydantic_ai_harness.localstack import LocalStack

agent = Agent('anthropic:claude-sonnet-4-6', capabilities=[LocalStack()])
result = agent.run_sync('Create an S3 bucket called reports and list all buckets.')
print(result.output)
```

#### Attributes

##### endpoint\_url

Base URL of the running LocalStack instance.

Defaults to LocalStack's `localhost.localstack.cloud` domain (which resolves to `127.0.0.1`) for compatibility with AWS SDKs that need subdomain-style hosts.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'http://localhost.localstack.cloud:4566'`

##### region

AWS region passed to the CLI and exported to the environment.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'us-east-1'`

##### access\_key\_id

AWS access key id. LocalStack accepts any value; defaults to its `test` convention.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'test'`

##### secret\_access\_key

AWS secret access key. LocalStack accepts any value; defaults to its `test` convention.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'test'`

##### allowed\_services

If non-empty, only these AWS services may be used (allowlist), e.g. `['s3', 'dynamodb']`.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(list[str]))`

##### denied\_services

These AWS services are always rejected (denylist).

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(list[str]))`

##### default\_timeout

Default timeout in seconds for AWS CLI commands and the health check.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) **Default:** `60.0`

##### max\_output\_chars

Maximum characters of output returned to the model. Must be positive.

**Type:** [`int`](https://docs.python.org/3/builtins/functions.html#int) **Default:** `50000`

##### aws\_cli\_path

Path or name of the AWS CLI executable (e.g. `aws` or `awslocal`).

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'aws'`

##### manage\_container

If True, start a LocalStack Docker container for each run and stop it when the run ends.

Requires Docker. When False (default), the agent connects to a LocalStack instance you started separately at `endpoint_url`.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### image

Docker image to run when `manage_container` is True.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'localstack/localstack'`

##### host\_address

Host address Docker publishes the LocalStack edge port on.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'127.0.0.1'`

##### service\_port\_range

Optional host/container port range for services that expose their own ports, e.g. `4510-4559`.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### mount\_docker\_socket

If True, mount `/var/run/docker.sock` into the managed container for Docker-backed services like Lambda.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `False`

##### container\_name

Optional name for the managed container. Leave None to let Docker assign one.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

##### container\_env

Environment variables passed to the managed container, e.g. `{'DEBUG': '1'}`.

**Type:** [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)\[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)\] **Default:** `field(default_factory=(dict[str, str]))`

##### docker\_path

Path or name of the Docker executable used to manage the container.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) **Default:** `'docker'`

##### startup\_timeout

Seconds to wait for the managed container to become ready before failing.

**Type:** [`float`](https://docs.python.org/3/builtins/functions.html#float) **Default:** `120.0`

##### include\_instructions

If True, add instructions telling the model how to use the emulated environment.

**Type:** [`bool`](https://docs.python.org/3/builtins/functions.html#bool) **Default:** `True`

#### Methods

##### get\_instructions

```python
def get_instructions() -> str | None
```

Explain the emulated environment to the model, unless disabled.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

##### get\_toolset

```python
def get_toolset() -> AgentToolset[AgentDepsT]
```

Build and return the LocalStack toolset.

###### Returns

[`AgentToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AgentToolset)\[`AgentDepsT`\]

### LocalStackToolset

**Bases:** `FunctionToolset[AgentDepsT]`

Gives an agent the ability to drive an emulated AWS environment.

Wraps the AWS CLI: `aws_cli` runs a command against a running LocalStack instance with the endpoint, region, and credentials injected, while `localstack_health` reports which emulated services are available.

Commands are executed as an argument vector (no shell), so shell operators and redirection in the command string have no effect.

#### Methods

##### for\_run

`@async`

```python
def for_run(ctx: RunContext[AgentDepsT]) -> AbstractToolset[AgentDepsT]
```

Return a fresh instance per run so a managed container is isolated and torn down.

`get_toolset` builds one shared instance at agent construction. When this toolset manages a Docker container it holds per-run lifecycle state, so each run gets its own instance (and its own container) that `__aexit__` can stop.

###### Returns

[`AbstractToolset`](https://pydantic.dev/docs/ai/api/pydantic-ai/toolsets/#pydantic_ai.toolsets.AbstractToolset)\[`AgentDepsT`\]

##### call\_tool

`@async`

```python
def call_tool(
    name: str,
    tool_args: dict[str, Any],
    ctx: RunContext[AgentDepsT],
    tool: ToolsetTool[AgentDepsT],
) -> Any
```

Enforce the model-visible output cap at the tool dispatch seam.

Only `str` results are capped; a future tool returning rich content (e.g. `ToolReturn`) needs this seam extended.

###### Returns

[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

##### \_\_aenter\_\_

`@async`

```python
def __aenter__() -> Self
```

Start the managed LocalStack container, if configured, before tools run.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self)

##### \_\_aexit\_\_

`@async`

```python
def __aexit__(*args: object) -> None
```

Stop the managed LocalStack container, if one was started.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

##### aws\_cli

`@async`

```python
def aws_cli(command: str, *, timeout_seconds: float | None = None) -> str
```

Run an AWS CLI command against the emulated AWS environment.

Pass the command without the leading `aws` and without `--endpoint-url`; the endpoint, region, and credentials are injected automatically. For example `s3 mb s3://my-bucket`, `s3 ls`, or `dynamodb list-tables`.

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) -- Labelled stdout/stderr output, with an exit code on non-zero exit.

###### Parameters

**`command`** : [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

The AWS CLI command to run (e.g. `s3 ls`).

**`timeout_seconds`** : [`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Maximum seconds to wait (default: the configured timeout).

##### localstack\_health

`@async`

```python
def localstack_health() -> str
```

Report the health and availability of the emulated AWS services.

Queries LocalStack's health endpoint and returns the raw JSON, which maps each service (s3, dynamodb, sqs, ...) to its state (available, running, ...).

###### Returns

[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) -- The health JSON, or an error message if LocalStack is unreachable.

### LocalStackContainer

Async context manager that starts and stops a LocalStack Docker container.

Drives the `docker` CLI, so Docker must be installed and running. On enter it launches the container, polls the health endpoint until LocalStack is ready, and exposes `endpoint_url`. On exit it stops the container -- it is started with `--rm`, so stopping also removes it.

```python
async with LocalStackContainer() as localstack:
    ...  # talk to localstack.endpoint_url
```

#### Attributes

##### endpoint\_url

URL of the container's edge endpoint.

For the default loopback publish addresses (`127.0.0.1` and the bind-all `0.0.0.0`, both reachable at `127.0.0.1`), uses LocalStack's `localhost.localstack.cloud` domain, which resolves to `127.0.0.1` and supports the subdomain-style hosts some AWS SDKs need. For any other `host_address`, uses that address literally, since `localhost.localstack.cloud` does not resolve there.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

##### container\_id

The running container's id, or None when it is not running.

**Type:** [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

#### Methods

##### \_\_aenter\_\_

`@async`

```python
def __aenter__() -> Self
```

Start the container and wait for it to become ready.

###### Returns

[`Self`](https://docs.python.org/3/library/typing.html#typing.Self)

##### \_\_aexit\_\_

`@async`

```python
def __aexit__(*args: object) -> None
```

Stop and remove the container.

###### Returns

[`None`](https://docs.python.org/3/builtins/constants.html#None)

---
