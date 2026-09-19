"""Rule compiler: two blind agents turn a rule's text into code + tests (ADR 0003, 0004).

Each agent only ever sees the rule's context and its own mistakes. Every test then runs
against both codes and both codes run over the process history; the rule is valid only when
they agree everywhere. Code A is what runs afterwards; B's work stays in the report.
"""

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import TraceError
from app.core import events
from app.features.agents import llm, sandbox
from app.features.ingestion.model import Instance
from app.features.ingestion.symbols import flatten_symbols
from app.features.processes.model import Process, Symbol
from app.features.rules.model import Rule
from app.features.sources.model import Source

# A test case, as written by an agent from the rule text alone:
# {"name": str, "instance": {...}, "sources": {...}, "others": [...], "fires": bool}
Test = dict[str, Any]
# (instance name, {symbol: value})
History = list[tuple[str, dict[str, Any]]]

ROLES = ("compiler_a", "compiler_b")
MAX_REPAIRS = 2
MIN_TESTS = 6


class CompilationError(TraceError):
    """An agent could not produce valid code + tests (LLM failure or still broken after the
    repair rounds). Nothing is stored."""

    status_code = 502
    code = "compilation_failed"


@dataclass(frozen=True)
class Compilation:
    code: str  # agent A's, the one that runs
    tests: list[Test]  # agent A's
    # {"valid": bool, "tests": [...], "history": {"instances": n, "agree": k},
    #  "discrepancies": [...], "alternative": {"code", "tests", "model"}} (agent B's work)
    # `valid` is True only if both codes pass every test and agree on every past instance.
    report: dict[str, Any]


# Structured output. instance/sources/others travel as JSON strings: free-form objects are
# not representable in strict JSON-schema modes (OpenAI would force them to be empty).
class ProposedTest(BaseModel):
    name: str
    instance_json: str
    sources_json: str
    others_json: str
    fires: bool


class Proposal(BaseModel):
    code: str
    tests: list[ProposedTest]


SYSTEM = """You compile business rules into Python. You turn ONE rule written as text into \
deterministic code and tests, using only the rule's text and the given context.

Code contract (field `code`, Python code only, no markdown):
- Define `def evaluate(instance, sources, others) -> dict` that returns \
{"fires": bool, "reason": str}.
- `instance`: {symbol: value} of the instance being evaluated.
- `sources`: {source_name: [row, ...]}, each row a dict {column: value}.
- `others`: list of the other instances of the process, each {symbol: value} plus the key \
"_instance" (its name). Use it only if the rule talks about other instances \
(duplicates, totals across instances...).
- Pure, deterministic function: no network, disk, clock, randomness or global state. \
Only these imports are allowed: decimal, datetime, re, math, unicodedata.
- Rule type: `requirement` = something that must hold; it fires when it does NOT hold. \
`prohibition` = something that must not happen; it fires when it DOES happen.
- Amounts and other decimals: compare with Decimal(str(value)). Use a tolerance only if the \
rule states one.
- Values may be missing or None: handle that explicitly and as the rule says.
- `reason`: short code in UPPER_CASE_WITH_UNDERSCORES (e.g. "VALUE_MISMATCH", \
"LIMIT_EXCEEDED"). When it does not fire, a reason such as "OK".

Process description: when the context includes it, it holds conventions that apply to every \
rule of the process (key normalisation, amount units, tolerances, what to do when a value is \
missing...). Always apply them, before your own assumptions. If they contradict the rule's \
text, the rule's text wins.

Tests (field `tests`, at least 6): each with `name`, `instance_json` (JSON object), \
`sources_json` (JSON object), `others_json` (JSON list) and `fires` (what the rule must \
return). Cover cases where it fires and where it does not, and the limits and exceptions the \
rule's text mentions. The tests must pass with your own code."""

compiler = Agent(
    None, output_type=Proposal, instructions=SYSTEM, name="compiler", retries=MAX_REPAIRS
)


def context(
    rule: Rule,
    symbols: list[Symbol],
    sources: dict[str, list[dict[str, Any]]],
    description: str,
) -> str:
    """What both agents see: the rule, the process conventions, the symbols and a sample of
    each source. Never the other agent's work."""
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


def tests_of(proposal: Proposal) -> list[Test]:
    """The proposal's tests with their JSON decoded. Raises ValueError when malformed."""
    if len(proposal.tests) < MIN_TESTS:
        raise ValueError(f"At least {MIN_TESTS} tests are needed; there are {len(proposal.tests)}")
    tests = []
    for t in proposal.tests:
        try:
            tests.append(
                {
                    "name": t.name,
                    "instance": json.loads(t.instance_json),
                    "sources": json.loads(t.sources_json),
                    "others": json.loads(t.others_json),
                    "fires": t.fires,
                }
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Test {t.name!r}: invalid JSON ({e})") from e
    return tests


def _cases(tests: list[Test]) -> list[tuple[dict, dict, list]]:
    return [(t["instance"], t["sources"], t["others"]) for t in tests]


def _describe(result: Any) -> str:
    if isinstance(result, dict) and isinstance(result.get("fires"), bool):
        return f"fires ({result.get('reason')})" if result["fires"] else "does not fire"
    return f"error: {result}"


def _fires(result: Any) -> bool | None:
    """The verdict, or None if the run failed or returned something malformed."""
    if isinstance(result, dict) and isinstance(result.get("fires"), bool):
        return result["fires"]
    return None


def own_errors(code: str, tests: list[Test]) -> str | None:
    """What is wrong with an agent's own code against its own tests, or None."""
    try:
        sandbox.check(code)
        results = sandbox.run_batch(code, _cases(tests))
    except sandbox.SandboxError as e:
        return f"The code does not pass the sandbox check: {e}"
    failures = [
        f"- {t['name']}: expected {'fires' if t['fires'] else 'does not fire'}, got {_describe(r)}"
        for t, r in zip(tests, results, strict=True)
        if _fires(r) is not t["fires"]
    ]
    return "Your code fails your own tests:\n" + "\n".join(failures) if failures else None


@compiler.output_validator
async def _self_consistent(_ctx: RunContext[None], proposal: Proposal) -> Proposal:
    """An agent's answer is only accepted when its code passes the sandbox check and its own
    tests; otherwise it gets its errors back and another try (up to MAX_REPAIRS)."""
    try:
        tests = tests_of(proposal)
    except ValueError as e:
        raise ModelRetry(f"Malformed reply: {e}") from e
    # The sandbox is a subprocess that may take seconds: off the event loop.
    error = await asyncio.to_thread(own_errors, proposal.code, tests)
    if error:
        raise ModelRetry(
            f"{error}\n\nFix it and return the whole proposal (code and tests) in the same format."
        )
    return proposal


def validate(
    code_a: str,
    code_b: str,
    tests_a: list[Test],
    tests_b: list[Test],
    history: History,
    sources: dict[str, list[dict[str, Any]]],
    run_batch: Callable[..., list[Any]],
) -> dict[str, Any]:
    """Cross-check: every test on both codes, both codes on the whole history (ADR 0004)."""
    tests = [("A", t) for t in tests_a] + [("B", t) for t in tests_b]
    # O(n²) `others` per instance; fine for a process history of hundreds.
    cases = _cases([t for _, t in tests]) + [
        (symbols, sources, [dict(s, _instance=n) for j, (n, s) in enumerate(history) if j != i])
        for i, (_, symbols) in enumerate(history)
    ]

    def run_all(code: str) -> list[Any]:
        try:
            return run_batch(code, cases)
        except Exception as e:  # the whole batch failed: every case reports it
            return [e] * len(cases)

    ra, rb = run_all(code_a), run_all(code_b)
    test_report, discrepancies = [], []
    for (author, t), a, b in zip(tests, ra, rb, strict=False):
        passed = _fires(a) is t["fires"] and _fires(b) is t["fires"]
        test_report.append(
            {
                "author": author,
                "name": t["name"],
                "expected": t["fires"],
                "a": _describe(a),
                "b": _describe(b),
                "passed": passed,
            }
        )
        if not passed:
            expected = "fires" if t["fires"] else "does not fire"
            discrepancies.append(
                f"Test {author} «{t['name']}» (expected: {expected}): "
                f"A says {_describe(a)}; B says {_describe(b)}"
            )
    agree = 0
    for (name, _), a, b in zip(history, ra[len(tests) :], rb[len(tests) :], strict=True):
        if _fires(a) is not None and _fires(a) is _fires(b):
            agree += 1
        else:
            discrepancies.append(f"Instance {name}: A says {_describe(a)}; B says {_describe(b)}")
    return {
        "valid": all(t["passed"] for t in test_report) and agree == len(history),
        "tests": test_report,
        "history": {"instances": len(history), "agree": agree},
        "discrepancies": discrepancies,
    }


async def read_process(
    session: AsyncSession, process_id: int
) -> tuple[str, dict[str, list[dict[str, Any]]], History]:
    """The process description, the current sources (latest load per name) and the history
    of instances with their symbols as rule code sees them."""
    description = await session.scalar(select(Process.description).where(Process.id == process_id))
    loads = await session.scalars(
        select(Source)
        .where(Source.process_id == process_id)
        .order_by(Source.name, Source.loaded_at.desc())
        .distinct(Source.name)
    )
    sources = {s.name: s.rows for s in loads}
    rows = await session.execute(
        select(Instance.name, Instance.symbols)
        .where(Instance.process_id == process_id)
        .order_by(Instance.id)
    )
    history = [(name, flatten_symbols(symbols)) for name, symbols in rows if symbols]
    return description or "", sources, history


async def _agent(role: str, prompt: str) -> tuple[Proposal, llm.Trace]:
    try:
        return await llm.run(compiler, role, prompt)
    except llm.AgentError as e:
        raise CompilationError(e.message) from e


async def compile_rule(session: AsyncSession, rule: Rule, symbols: list[Symbol]) -> Compilation:
    """Agents A and B each write, blind to the other, a function

        def evaluate(instance: dict, sources: dict[str, list[dict]], others: list[dict]) -> dict
            # returns {"fires": bool, "reason": str}

    plus tests. Then every test runs against both codes, and both codes run on the
    process history. The result is reported, never silently accepted."""
    description, sources, history = await read_process(session, rule.process_id)
    prompt = context(rule, symbols, sources, description)
    (a, trace_a), (b, trace_b) = await asyncio.gather(*(_agent(role, prompt) for role in ROLES))
    tests_a, tests_b = tests_of(a), tests_of(b)
    report = await asyncio.to_thread(
        validate, a.code, b.code, tests_a, tests_b, history, sources, sandbox.run_batch
    )
    report["alternative"] = {"code": b.code, "tests": tests_b, "model": trace_b.model}
    for trace in (trace_a, trace_b):
        events.record(
            session,
            "compile_rule",
            process_id=rule.process_id,
            data={"rule_id": rule.id, "valid": report["valid"], **trace.as_data()},
            latency_ms=trace.latency_ms,
            cost=trace.cost,
        )
    return Compilation(a.code, tests_a, report)
