# [Pydantic Model](https://pydantic.dev/docs/ai/examples/getting-started/pydantic-model/)

# Pydantic Model

Simple example of using Pydantic AI to construct a Pydantic model from a text input.

Demonstrates:

-   [structured `output_type`](https://pydantic.dev/docs/ai/core-concepts/output/#structured-output)

## Running the Example

With [dependencies installed and environment variables set](https://pydantic.dev/docs/ai/examples/setup/#usage), run:

-   [pip](#tab-panel-44)
-   [uv](#tab-panel-45)

Terminal

```bash
python -m pydantic_ai_examples.pydantic_model
```

Terminal

```bash
uv run -m pydantic_ai_examples.pydantic_model
```

This example uses `openai:gpt-5` by default, but it works well with other models. For example, run it with Gemini:

-   [pip](#tab-panel-46)
-   [uv](#tab-panel-47)

Terminal

```bash
PYDANTIC_AI_MODEL=gemini-3-pro-preview python -m pydantic_ai_examples.pydantic_model
```

Terminal

```bash
PYDANTIC_AI_MODEL=gemini-3-pro-preview uv run -m pydantic_ai_examples.pydantic_model
```

(or `PYDANTIC_AI_MODEL=gemini-3-flash-preview ...`)

## Example Code

pydantic\_model.py

```py
import os

import logfire
from pydantic import BaseModel

from pydantic_ai import Agent

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_pydantic_ai()


class MyModel(BaseModel):
    city: str
    country: str


model = os.getenv('PYDANTIC_AI_MODEL', 'openai:gpt-5.2')
print(f'Using model: {model}')
agent = Agent(model, output_type=MyModel)

if __name__ == '__main__':
    result = agent.run_sync('The windy city in the US of A.')
    print(result.output)
    print(result.usage)
```

---
