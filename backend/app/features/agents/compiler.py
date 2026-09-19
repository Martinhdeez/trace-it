"""Rule compiler: a coder writes a rule's code against tests a blind tester wrote (ADR 0004).

The tester sees only the rule's text and the process context, never any code, so its tests
are an oracle the coder cannot bend. The coder iterates on its own failures; a test it
believes contradicts the rule text goes back to the tester, who keeps or corrects it from
the text alone. The loop ends green (valid), or not valid with every open failure in the
report. Nothing here decides an instance: the stored code does, deterministically.
"""

import ast
import asyncio
import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import TraceError
from app.core import events
from app.features.agents import llm, sandbox
from app.features.processes.model import Process, Symbol
from app.features.rules.model import Rule
from app.features.sources.model import Source
from app.features.use_cases import service as use_cases
from app.features.use_cases.model import UseCase

# A test case, as written by the tester from the rule text alone:
# {"name": str, "instance": {...}, "sources": {...}, "others": [...], "fires": bool}
Test = dict[str, Any]
Sources = dict[str, list[dict[str, Any]]]

ROLES = ("compiler", "tester")
MAX_REPAIRS = 2  # malformed answers an agent may fix inside one run
MAX_ATTEMPTS = 4  # coder runs against the tests
MAX_REVIEWS = 2  # times the tester is asked to reconsider disputed tests
MIN_TESTS = 6


class CompilationError(TraceError):
    """An agent gave nothing usable (LLM failure, or still malformed after the repair
    rounds). Nothing is stored."""

    status_code = 502
    code = "compilation_failed"


@dataclass(frozen=True)
class Compilation:
    code: str | None  # None when the rule needs data the process does not have
    tests: list[Test]
    # {"valid", "tests": [{name, expected, got, passed}], "discrepancies": [...],
    #  "attempts", "reviews": [...]} or {"valid": False, "needs_data": {...}, ...}
    report: dict[str, Any]


# Structured output. instance/sources/others travel as JSON strings: free-form objects are
# not representable in strict JSON-schema modes (OpenAI would force them to be empty).
class ProposedTest(BaseModel):
    name: str
    instance_json: str
    sources_json: str
    others_json: str
    fires: bool


class TestSuite(BaseModel):
    tests: list[ProposedTest]


class Dispute(BaseModel):
    test: str  # name of a test the coder believes contradicts the rule text
    argument: str


class Proposal(BaseModel):
    code: str
    disputes: list[Dispute] = []


class NeedsData(BaseModel):
    """The rule cannot be written with the symbols and sources the process has."""

    missing: list[str]  # e.g. "symbol: delivery_date"
    explanation: str


class Verdict(BaseModel):
    test: str
    fires: bool  # the expected result after re-reading the rule text
    reason: str


class Review(BaseModel):
    verdicts: list[Verdict]


@dataclass(frozen=True)
class TesterDeps:
    symbols: set[str]  # the only valid instance keys
    min_tests: int


@dataclass(frozen=True)
class CoderDeps:
    symbols: set[str]  # the only keys the code may read from `instance`
    sources: set[str]  # the only keys the code may read from `sources`


# Instructions are not here: the platform prompts are files (`prompts/`), and each use case
# adds its own guidance, model and limits (ADR 0011).
tester = Agent(
    None,
    deps_type=TesterDeps,
    output_type=[TestSuite, NeedsData],
    name="tester",
    retries=MAX_REPAIRS,
)
coder = Agent(
    None,
    deps_type=CoderDeps,
    output_type=[Proposal, NeedsData],
    name="compiler",
    retries=MAX_REPAIRS,
)
reviewer = Agent(None, output_type=Review, name="reviewer")


def context(rule: Rule, symbols: list[Symbol], sources: Sources, description: str) -> str:
    """What every agent sees: the rule, the process conventions, the symbols and a sample
    of each source."""
    lines = [
        "Use case description (conventions shared by all its rules):",
        description or "(no description)",
        "",
        f"Rule ({rule.type}): {rule.text}",
        "",
        "Symbols of each instance (name, type, description):",
        *(f"- {s.name} ({s.type}): {s.description}" for s in symbols),
        "",
        "Available sources of truth (columns and 3 sample rows):",
    ]
    for name, rows in sources.items():
        columns = list(dict.fromkeys(c for r in rows for c in r))
        lines.append(f"- {name}: columns {columns}")
        lines += [f"    {json.dumps(r, ensure_ascii=False, default=str)}" for r in rows[:3]]
    if not sources:
        lines.append("- (none)")
    return "\n".join(lines)


def tests_of(suite: TestSuite, min_tests: int = MIN_TESTS) -> list[Test]:
    """The suite's tests with their JSON decoded. Raises ValueError when malformed."""
    if len(suite.tests) < min_tests:
        raise ValueError(f"At least {min_tests} tests are needed; there are {len(suite.tests)}")
    tests = []
    for t in suite.tests:
        try:
            test = {
                "name": t.name,
                "instance": json.loads(t.instance_json),
                "sources": json.loads(t.sources_json),
                "others": json.loads(t.others_json),
                "fires": t.fires,
            }
        except json.JSONDecodeError as e:
            raise ValueError(f"Test {t.name!r}: invalid JSON ({e})") from e
        if not isinstance(test["instance"], dict):
            raise ValueError(f"Test {t.name!r}: the instance must be a JSON object")
        tests.append(test)
    if len({t["name"] for t in tests}) < len(tests):
        raise ValueError("Test names must be unique")
    if len({t["fires"] for t in tests}) < 2:
        raise ValueError("Tests must include cases where the rule fires and where it does not")
    return tests


@tester.output_validator
def _well_formed(ctx: RunContext[TesterDeps], output: TestSuite | NeedsData) -> Any:
    if isinstance(output, NeedsData):
        return output
    try:
        tests = tests_of(output, ctx.deps.min_tests)
    except ValueError as e:
        raise ModelRetry(f"Malformed tests: {e}") from e
    unknown = {k for t in tests for k in t["instance"]} - ctx.deps.symbols
    if unknown:
        raise ModelRetry(
            f"Unknown instance keys {sorted(unknown)}: use only the symbols given. If the "
            "rule needs other data, answer with NeedsData."
        )
    return output


def read_keys(code: str) -> tuple[set[str], set[str]]:
    """The literal keys `evaluate` reads from its first two parameters, whatever their
    names: `x["k"]` and `x.get("k")`. A computed key is not a literal and is not listed."""
    function = next(
        (
            n
            for n in ast.walk(ast.parse(code))
            if isinstance(n, ast.FunctionDef) and n.name == "evaluate"
        ),
        None,
    )
    if function is None:
        return set(), set()
    params = [a.arg for a in function.args.args[:2]] + [None, None]
    keys: dict[str, set[str]] = {p: set() for p in params if p}
    for node in ast.walk(function):
        if isinstance(node, ast.Subscript):
            target, key = node.value, node.slice
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != "get" or not node.args:
                continue
            target, key = node.func.value, node.args[0]
        else:
            continue
        literal = isinstance(key, ast.Constant) and isinstance(key.value, str)
        if isinstance(target, ast.Name) and target.id in keys and literal:
            keys[target.id].add(key.value)
    return keys.get(params[0], set()), keys.get(params[1], set())


@coder.output_validator
def _allowed(ctx: RunContext[CoderDeps], output: Proposal | NeedsData) -> Any:
    if isinstance(output, NeedsData):
        return output
    try:
        sandbox.check(output.code)
    except sandbox.SandboxError as e:
        raise ModelRetry(f"The code does not pass the sandbox check: {e}") from e
    instance, sources = read_keys(output.code)
    unknown = sorted(instance - ctx.deps.symbols) + sorted(sources - ctx.deps.sources)
    if unknown:
        raise ModelRetry(
            f"The code reads unknown keys {unknown}. Read from the instance only the symbols "
            f"{sorted(ctx.deps.symbols)} and from the sources only {sorted(ctx.deps.sources)}. "
            "If the rule needs other data, answer with NeedsData."
        )
    return output


def _expect(fires: bool) -> str:
    return "fires" if fires else "does not fire"


def _describe(result: Any) -> str:
    if isinstance(result, dict) and isinstance(result.get("fires"), bool):
        return f"fires ({result.get('reason')})" if result["fires"] else "does not fire"
    return f"error: {result}"


def _fires(result: Any) -> bool | None:
    """The verdict, or None if the run failed or returned something malformed."""
    if isinstance(result, dict) and isinstance(result.get("fires"), bool):
        return result["fires"]
    return None


def run_tests(code: str, tests: list[Test]) -> list[dict[str, Any]]:
    """Every test on `code` in the sandbox: [{name, expected, got, passed}]."""
    cases = [(t["instance"], t["sources"], t["others"]) for t in tests]
    try:
        results: list[Any] = sandbox.run_batch(code, cases)
    except sandbox.SandboxError as e:  # the whole batch failed: every case reports it
        results = [e] * len(tests)
    return [
        {
            "name": t["name"],
            "expected": t["fires"],
            "got": _describe(r),
            "passed": _fires(r) is t["fires"],
        }
        for t, r in zip(tests, results, strict=True)
    ]


def _as_json(tests: list[Test]) -> str:
    return json.dumps(tests, ensure_ascii=False, default=str)


def _failure(f: dict[str, Any]) -> str:
    return f"{f['name']}: expected {_expect(f['expected'])}, got {f['got']}"


Setups = dict[str, llm.Setup]  # role -> how it runs in the rule's use case


class Runs:
    """The agent runs of one compilation, with the use case's setups, and their traces."""

    def __init__(self, setups: Setups | None = None) -> None:
        self.setups = setups or {}
        self.traces: list[llm.Trace] = []

    def setup(self, role: str) -> llm.Setup:
        return self.setups.get(role) or llm.Setup()

    async def __call__(
        self, agent: Agent, role: str, prompt: str, instructions: str, deps: Any = None
    ) -> Any:
        try:
            output, trace = await llm.run(
                agent, role, prompt, instructions=instructions, setup=self.setup(role), deps=deps
            )
        except llm.AgentError as e:
            raise CompilationError(e.message) from e
        self.traces.append(trace)
        return output


def _needs_data(output: NeedsData, role: str) -> Compilation:
    report = {
        "valid": False,
        "needs_data": {"by": role, **output.model_dump()},
        "discrepancies": [f"Needs data: {', '.join(output.missing)}. {output.explanation}"],
    }
    return Compilation(None, [], report)


async def _review(
    runs: Runs, ctx: str, disputed: list[Dispute], by_name: dict[str, Test]
) -> list[Verdict]:
    """The tester re-reads the rule text for each disputed test: keep it or correct it."""
    question = "\n".join(
        f"- Test {d.test!r}, you expected: {_expect(by_name[d.test]['fires'])}\n"
        f"  {_as_json([by_name[d.test]])}\n  Objection: {d.argument}"
        for d in disputed
    )
    review = await runs(
        reviewer,
        "tester",
        f"{ctx}\n\nDisputed tests:\n{question}",
        llm.prompt("reviewer", "shared"),
    )
    asked = {d.test for d in disputed}
    return [v for v in review.verdicts if v.test in asked]


def _examples(setup: llm.Setup, rule: Rule) -> str:
    """The use case's approved rule/code pairs, never the rule being compiled: an example
    of the rule itself would hand the model its answer."""
    examples = [e for e in setup.settings.examples if e.text.strip() != rule.text.strip()]
    if not examples:
        return ""
    return (
        "\n\n## Approved code of other rules of this use case (follow their conventions)\n"
        + "\n".join(
            f"\nRule ({e.type}): {e.text}\n```python\n{e.code.strip()}\n```" for e in examples
        )
    )


async def compile_text(
    rule: Rule, symbols: list[Symbol], sources: Sources, description: str, runs: Runs
) -> Compilation:
    """The compile loop, without the database: the tester's tests, then the coder against
    them until they pass or the attempts run out."""
    ctx = context(rule, symbols, sources, description)
    min_tests = int(runs.setup("tester").limit("min_tests", MIN_TESTS))
    max_reviews = int(runs.setup("tester").limit("max_reviews", MAX_REVIEWS))
    max_attempts = int(runs.setup("compiler").limit("max_attempts", MAX_ATTEMPTS))
    tester_instructions = llm.prompt("tester", "shared") + f"\n\nWrite at least {min_tests} tests."
    deps = TesterDeps({s.name for s in symbols}, min_tests)
    suite = await runs(tester, "tester", ctx, tester_instructions, deps=deps)
    if isinstance(suite, NeedsData):
        return _needs_data(suite, "tester")
    tests = tests_of(suite, min_tests)
    by_name = {t["name"]: t for t in tests}
    coder_instructions = llm.prompt("coder", "shared") + _examples(runs.setup("compiler"), rule)
    coder_deps = CoderDeps(deps.symbols, set(sources))

    reviews: list[dict[str, Any]] = []
    review_rounds = 0
    feedback = ""
    for attempt in range(1, max_attempts + 1):
        prompt = f"{ctx}\n\nTests your code must pass (JSON):\n{_as_json(tests)}{feedback}"
        with events.span("coder_attempt", attempt=attempt) as span:
            proposal = await runs(coder, "compiler", prompt, coder_instructions, deps=coder_deps)
            if isinstance(proposal, NeedsData):
                span.set(needs_data=proposal.missing)
                return _needs_data(proposal, "compiler")
            with events.span("run_tests", cases=len(tests)) as run:
                results = await asyncio.to_thread(run_tests, proposal.code, tests)
                run.set(passed=sum(r["passed"] for r in results))
            failures = [r for r in results if not r["passed"]]
            span.set(failures=len(failures), disputes=len(proposal.disputes))
        if not failures or attempt == max_attempts:
            break
        feedback = "\n\nYour previous code:\n" + proposal.code + "\n\nIt fails these tests:\n"
        feedback += "\n".join(f"- {_failure(f)}" for f in failures)
        failing = {f["name"] for f in failures}
        disputed = [d for d in proposal.disputes if d.test in failing]
        if disputed and review_rounds < max_reviews:
            review_rounds += 1
            verdicts = await _review(runs, ctx, disputed, by_name)
            for v in verdicts:
                reviews.append({"before": by_name[v.test]["fires"], **v.model_dump()})
                by_name[v.test]["fires"] = v.fires
            feedback += "\n\nThe tests' author reviewed your objections:\n" + "\n".join(
                f"- {v.test}: {_expect(v.fires)} ({v.reason})" for v in verdicts
            )
        feedback += "\n\nFix the code. The test list above is the current one."

    report = {
        "valid": not failures,
        "tests": results,
        "discrepancies": [f"Test {_failure(f)}" for f in failures],
        "attempts": attempt,
        "reviews": reviews,
    }
    return Compilation(proposal.code, tests, report)


async def read_process(session: AsyncSession, process_id: int) -> tuple[str, Sources, Setups]:
    """The use case's description and agent setups, and the process's current sources
    (latest load per name)."""
    process = await session.get(Process, process_id)
    use_case = await session.get(UseCase, process.use_case_id)
    loads = await session.scalars(
        select(Source)
        .where(Source.process_id == process_id)
        .order_by(Source.name, Source.loaded_at.desc())
        .distinct(Source.name)
    )
    from app.features.versions.configuration import setups as pinned_setups
    from app.features.versions.model import ProcessDraft, ProcessVersion

    draft = await session.get(ProcessDraft, process_id)
    if draft:
        return (
            draft.snapshot["process"]["description"],
            {s.name: s.rows for s in loads},
            pinned_setups(draft.snapshot),
        )
    if process.active_version_id:
        version = await session.get(ProcessVersion, process.active_version_id)
        return (
            version.snapshot["process"]["description"],
            {s.name: s.rows for s in loads},
            pinned_setups(version.snapshot),
        )
    setups = await use_cases.setups(session, use_case.id)
    return use_case.description, {s.name: s.rows for s in loads}, setups


async def compile_rule(session: AsyncSession, rule: Rule, symbols: list[Symbol]) -> Compilation:
    """The tester writes tests from the text, the coder writes

        def evaluate(instance: dict, sources: dict[str, list[dict]], others: list[dict]) -> dict
            # returns {"fires": bool, "reason": str}

    against them. The result is reported, never silently accepted."""
    from app.features.versions.model import ProcessDraft

    draft = await session.get(ProcessDraft, rule.process_id)
    if draft:
        symbols = [Symbol(**s) for s in draft.snapshot["process"]["symbols"]]
    description, sources, setups = await read_process(session, rule.process_id)
    return await compile_text(rule, symbols, sources, description, Runs(setups))
