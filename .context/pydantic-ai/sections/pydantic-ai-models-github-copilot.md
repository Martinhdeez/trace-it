# [pydantic_ai.models.github_copilot](https://pydantic.dev/docs/ai/api/models/github_copilot/)

# pydantic\_ai.models.github\_copilot

## Setup

For details on how to set up authentication with this model, see [model configuration for GitHub Copilot](https://pydantic.dev/docs/ai/models/github-copilot/).

GitHub Copilot model implementation using OpenAI-compatible API.

### GitHubCopilotModel

**Bases:** `OpenAIChatModel`

A model that uses GitHub Copilot's OpenAI-compatible Chat Completions API.

Copilot serves Anthropic, OpenAI, Google, xAI and MoonshotAI models behind one endpoint, so the model family -- and with it the profile [`GitHubCopilotProvider`](https://pydantic.dev/docs/ai/api/pydantic-ai/providers/#pydantic_ai.providers.github_copilot.GitHubCopilotProvider) resolves -- is derived from the prefix of the bare model id (`claude-`, `gpt-`, `gemini-`, ...). Ids go out on the wire exactly as given.

Apart from `__init__`, all methods are private or match those of the base class.

#### Methods

##### \_\_init\_\_

```python
def __init__(
    model_name: GitHubCopilotModelName,
    *,
    provider: Literal['github-copilot'] | Provider[AsyncOpenAI] = 'github-copilot',
    profile: ModelProfileSpec | None = None,
    settings: ModelSettings | None = None,
)
```

Initialize a GitHub Copilot model.

###### Parameters

**`model_name`** : `GitHubCopilotModelName`

The name of the Copilot model to use, e.g. `'claude-haiku-4.5'`.

**`provider`** : [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)\['github-copilot'\] | `Provider`\[`AsyncOpenAI`\] _Default:_ `'github-copilot'`

The provider to use. Defaults to `'github-copilot'`.

**`profile`** : [`ModelProfileSpec`](https://pydantic.dev/docs/ai/api/pydantic-ai/profiles/#pydantic_ai.profiles.ModelProfileSpec) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

The model profile to use. Defaults to a profile picked by the provider based on the model name.

**`settings`** : [`ModelSettings`](https://pydantic.dev/docs/ai/api/pydantic-ai/settings/#pydantic_ai.settings.ModelSettings) | [`None`](https://docs.python.org/3/builtins/constants.html#None) _Default:_ `None`

Model-specific settings that will be used as defaults for this model.

### GitHubCopilotModelName

Possible GitHub Copilot model names.

Copilot's catalog varies by subscription and changes often -- an id one plan serves returns `400 model_not_supported` on another -- so no known-model list is shipped and any name is allowed. List the ids your own plan serves with `GET https://api.githubcopilot.com/models`.

**Default:** `str`

---
