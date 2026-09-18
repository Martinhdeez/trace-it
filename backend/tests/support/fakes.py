"""Stand-ins for the sandbox, for tests of the engine and the API that are not about the
sandbox itself. A rule is a plain function of (instance, sources, others) -> fires."""

from collections.abc import Callable
from typing import Any

RuleFn = Callable[[dict[str, Any], dict[str, Any], list[dict[str, Any]]], bool]
Case = tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]


def dataset_runner(rules: dict[str, RuleFn], seen: list[Case] | None = None) -> Callable:
    """`sandbox.run_dataset` with `code` naming a function in `rules`. Like the real one, a
    failing instance comes back as its exception instead of raising, and each instance's
    `others` is the population minus itself. `seen` records what each rule was handed."""

    def run_dataset(code: str, instances: list, sources: dict, population: list) -> list:
        answers: list[Any] = []
        for key, symbols in instances:
            others = [s for k, s in population if k != key]
            if seen is not None:
                seen.append((symbols, sources, others))
            try:
                fires = rules[code](symbols, sources, others)
                answers.append({"fires": fires, "reason": code if fires else ""})
            except Exception as error:  # noqa: BLE001 - the engine reads it as a rule error
                answers.append(error)
        return answers

    return run_dataset
