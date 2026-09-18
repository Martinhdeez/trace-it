# [pydantic_evals.online_capability](https://pydantic.dev/docs/ai/api/pydantic_evals/online_capability/)

# pydantic\_evals.online\_capability

Online evaluation capability for pydantic-ai agents.

Provides an `OnlineEvaluation` capability that attaches evaluators to agent runs, dispatching them asynchronously in the background after each run completes.

### OnlineEvaluation

**Bases:** `AbstractCapability[AgentDepsT]`

Capability that runs online evaluators on agent run results.

Dispatches evaluators asynchronously in the background after each completed agent run. Non-blocking -- the agent run returns without waiting for evaluators to finish.

Note

[`OnlineEvaluation`](https://pydantic.dev/docs/ai/api/pydantic_evals/online_capability/#pydantic_evals.online_capability.OnlineEvaluation) wraps [`agent.run()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run), [`agent.run_stream()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.AbstractAgent.run_stream), and [`agent.iter()`](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.Agent.iter) when the run reaches a final result. For streaming runs, evaluators are dispatched only after the final result is available and the surrounding context manager exits.

Example:

```python
from dataclasses import dataclass

from pydantic_ai import Agent
from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.online_capability import OnlineEvaluation


@dataclass
class OutputNotEmpty(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return bool(ctx.output)


agent = Agent(
    'openai:gpt-5.2',
    name='assistant',
    capabilities=[OnlineEvaluation(evaluators=[OutputNotEmpty()])],
)
```

#### Attributes

##### evaluators

Evaluators to run after each agent run.

**Type:** [`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)\[`Evaluator` | `OnlineEvaluator`\]

##### config

Optional config override. Defaults to the global `DEFAULT_CONFIG`.

**Type:** `OnlineEvalConfig` | [`None`](https://docs.python.org/3/builtins/constants.html#None) **Default:** `None`

---
