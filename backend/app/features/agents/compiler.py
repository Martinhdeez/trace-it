"""Rule compiler: a coder writes a rule's code against tests a blind tester wrote (ADR 0004).

The tester sees only the rule's text and the process context, never any code, so its tests
are an oracle the coder cannot bend. The coder iterates on its own failures; a test it
believes contradicts the rule text goes back to the tester, who keeps or corrects it from
the text alone. The loop ends green (valid), or not valid with every open failure in the
report. Nothing here decides an instance: the stored code does, deterministically.
"""

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


SHARED = """The rule is evaluated by a Python function
`evaluate(instance, sources, others) -> {"fires": bool, "reason": str}`:
- `instance`: {symbol: value} of the instance being evaluated.
- `sources`: {source_name: [row, ...]}, each row a dict {column: value}.
- `others`: the other instances of the process, each {symbol: value} plus "_instance" (its \
name). Relevant only if the rule talks about other instances (duplicates, totals...).
- Rule type: `requirement` = something that must hold; it fires when it does NOT hold. \
`prohibition` = something that must not happen; it fires when it DOES happen.
- A value the rule needs may be missing or None. If the rule text or the process \
description says what to do then, that is what happens. Otherwise the function raises, \
and the engine sends the instance to a person: it never guesses.

Process description: conventions that apply to every rule of the process (normalisation, \
units, tolerances...). Apply them before your own assumptions. If they contradict the \
rule's text, the rule's text wins.

If the rule needs data that is neither a symbol nor a source column, answer with \
NeedsData (what is missing and why) instead of inventing a field."""

TESTER = f"""You write the tests for ONE business rule, from its text and the process \
context only. You never see the code: your tests are the reference it must meet.

{SHARED}

Write at least {MIN_TESTS} tests: each with `name` (unique), `instance_json` (JSON \
object), `sources_json` (JSON object), `others_json` (JSON list) and `fires` (what the \
rule must return). Cover cases where it fires and where it does not, and the limits and \
exceptions the rule's text mentions. Use only the given symbol names as instance keys and \
only the given source names. Do not test a missing value unless the text or the \
description says what happens then."""

CODER = f"""You compile ONE business rule into deterministic Python.

{SHARED}

Code contract (field `code`, Python code only, no markdown):
- Define `evaluate(instance, sources, others)` returning {{"fires": bool, "reason": str}}.
- Pure, deterministic function: no network, disk, clock, randomness or global state. \
Only these imports are allowed: decimal, datetime, re, math, unicodedata.
- Amounts and other decimals: compare with Decimal(str(value)). Use a tolerance only if \
the rule or the description states one.
- `reason`: short code in UPPER_CASE_WITH_UNDERSCORES (e.g. "VALUE_MISMATCH"). When it \
does not fire, a reason such as "OK".

You get tests written from the rule text by someone who never saw your code. Make them \
pass. If you are sure a test contradicts the rule text, list it in `disputes` with your \
argument (quote the text); it goes back to its author. Never special-case a test's data."""

REVIEWER = f"""You wrote tests for a business rule. The person who implements it \
disputes some of them. Re-read the rule text and the process context and, for each \
disputed test, give the result the rule really requires (`fires`) and why. Change a test \
only if the text supports the objection; otherwise keep it.

{SHARED}"""

tester = Agent(
    None,
    deps_type=set[str],  # the symbol names: the only valid instance keys
    output_type=[TestSuite, NeedsData],
    instructions=TESTER,
    name="tester",
    retries=MAX_REPAIRS,
)
coder = Agent(
    None,
    output_type=[Proposal, NeedsData],
    instructions=CODER,
    name="compiler",
    retries=MAX_REPAIRS,
)
reviewer = Agent(None, output_type=Review, instructions=REVIEWER, name="reviewer")


def context(rule: Rule, symbols: list[Symbol], sources: Sources, description: str) -> str:
    """What every agent sees: the rule, the process conventions, the symbols and a sample
    of each source."""
    lines = [
        "Process description (conventions shared by all its rules):",
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


def tests_of(suite: TestSuite) -> list[Test]:
    """The suite's tests with their JSON decoded. Raises ValueError when malformed."""
    if len(suite.tests) < MIN_TESTS:
        raise ValueError(f"At least {MIN_TESTS} tests are needed; there are {len(suite.tests)}")
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
def _well_formed(ctx: RunContext[set[str]], output: TestSuite | NeedsData) -> Any:
    if isinstance(output, NeedsData):
        return output
    try:
        tests = tests_of(output)
    except ValueError as e:
        raise ModelRetry(f"Malformed tests: {e}") from e
    unknown = {k for t in tests for k in t["instance"]} - ctx.deps
    if unknown:
        raise ModelRetry(
            f"Unknown instance keys {sorted(unknown)}: use only the symbols given. If the "
            "rule needs other data, answer with NeedsData."
        )
    return output


@coder.output_validator
def _allowed(_ctx: RunContext[None], output: Proposal | NeedsData) -> Any:
    if isinstance(output, Proposal):
        try:
            sandbox.check(output.code)
        except sandbox.SandboxError as e:
            raise ModelRetry(f"The code does not pass the sandbox check: {e}") from e
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


class Runs:
    """The agent runs of one compilation, and their traces."""

    def __init__(self) -> None:
        self.traces: list[llm.Trace] = []

    async def __call__(self, agent: Agent, role: str, prompt: str, deps: Any = None) -> Any:
        try:
            output, trace = await llm.run(agent, role, prompt, deps=deps)
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
    review = await runs(reviewer, "tester", f"{ctx}\n\nDisputed tests:\n{question}")
    asked = {d.test for d in disputed}
    return [v for v in review.verdicts if v.test in asked]


async def compile_text(
    rule: Rule, symbols: list[Symbol], sources: Sources, description: str, runs: Runs
) -> Compilation:
    """The compile loop, without the database: the tester's tests, then the coder against
    them until they pass or the attempts run out."""
    ctx = context(rule, symbols, sources, description)
    suite = await runs(tester, "tester", ctx, deps={s.name for s in symbols})
    if isinstance(suite, NeedsData):
        return _needs_data(suite, "tester")
    tests = tests_of(suite)
    by_name = {t["name"]: t for t in tests}

    reviews: list[dict[str, Any]] = []
    review_rounds = 0
    feedback = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = f"{ctx}\n\nTests your code must pass (JSON):\n{_as_json(tests)}{feedback}"
        proposal = await runs(coder, "compiler", prompt)
        if isinstance(proposal, NeedsData):
            return _needs_data(proposal, "compiler")
        results = await asyncio.to_thread(run_tests, proposal.code, tests)
        failures = [r for r in results if not r["passed"]]
        if not failures or attempt == MAX_ATTEMPTS:
            break
        feedback = "\n\nYour previous code:\n" + proposal.code + "\n\nIt fails these tests:\n"
        feedback += "\n".join(f"- {_failure(f)}" for f in failures)
        failing = {f["name"] for f in failures}
        disputed = [d for d in proposal.disputes if d.test in failing]
        if disputed and review_rounds < MAX_REVIEWS:
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


async def read_process(session: AsyncSession, process_id: int) -> tuple[str, Sources]:
    """The process description and the current sources (latest load per name)."""
    description = await session.scalar(select(Process.description).where(Process.id == process_id))
    loads = await session.scalars(
        select(Source)
        .where(Source.process_id == process_id)
        .order_by(Source.name, Source.loaded_at.desc())
        .distinct(Source.name)
    )
    return description or "", {s.name: s.rows for s in loads}


async def compile_rule(session: AsyncSession, rule: Rule, symbols: list[Symbol]) -> Compilation:
    """The tester writes tests from the text, the coder writes

        def evaluate(instance: dict, sources: dict[str, list[dict]], others: list[dict]) -> dict
            # returns {"fires": bool, "reason": str}

    against them. The result is reported, never silently accepted."""
    description, sources = await read_process(session, rule.process_id)
    runs = Runs()
    result = await compile_text(rule, symbols, sources, description, runs)
    for trace in runs.traces:
        events.record(
            session,
            "compile_rule",
            data={"rule_id": rule.id, "valid": result.report["valid"], **trace.as_data()},
            latency_ms=trace.latency_ms,
            cost=trace.cost,
        )
    return result
