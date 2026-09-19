"""Compiler without network, LLM or database: the models are scripted, the sandbox is faked
with a plain `exec` (acceptable in tests only) and the DB reads are monkeypatched."""

import json
from types import SimpleNamespace

import pytest

from app.features.agents import compiler, llm, sandbox
from tests.support.models import per_role, retry_prompts, user_prompt


class SandboxError(Exception):
    pass


def check(code: str) -> None:
    try:
        compile(code, "<rule>", "exec")
    except SyntaxError as e:
        raise SandboxError(str(e)) from e


def run_batch(code: str, cases: list, timeout_s: float = 10.0) -> list:
    namespace: dict = {}
    exec(code, namespace)
    results = []
    for case in cases:
        try:
            results.append(namespace["evaluate"](*case))
        except Exception as e:
            results.append(SandboxError(repr(e)))
    return results


@pytest.fixture(autouse=True)
def fake_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "SandboxError", SandboxError, raising=False)
    monkeypatch.setattr(sandbox, "check", check, raising=False)
    monkeypatch.setattr(sandbox, "run_batch", run_batch, raising=False)


# "If amount > 1000, escalate" (prohibition)
CODE = """
from decimal import Decimal

def evaluate(instance, sources, others):
    if Decimal(str(instance["amount"])) > Decimal("1000"):
        return {"fires": True, "reason": "HIGH_AMOUNT"}
    return {"fires": False, "reason": "OK"}
"""
# Same rule read as ">=": only differs at exactly 1000.
CODE_GREATER_EQUAL = CODE.replace('> Decimal("1000")', '>= Decimal("1000")')
CODE_BROKEN = CODE.replace('instance["amount"]', 'instance["missing"]')


def _test(name: str, amount: float, fires: bool) -> dict:
    return {
        "name": name,
        "instance": {"amount": amount},
        "sources": {},
        "others": [],
        "fires": fires,
    }


TESTS = [_test("high", 1500, True), _test("low", 10, False)]
HISTORY = [("f1.pdf", {"amount": 50}), ("f2.pdf", {"amount": 2000})]


def test_validate_agree() -> None:
    report = compiler.validate(CODE, CODE, TESTS, TESTS, HISTORY, {}, run_batch)
    assert report["valid"] is True
    assert report["history"] == {"instances": 2, "agree": 2}
    assert report["discrepancies"] == []
    assert len(report["tests"]) == 4 and all(t["passed"] for t in report["tests"])


def test_validate_cross_failure() -> None:
    tests_b = [*TESTS, _test("exactly 1000", 1000, True)]
    report = compiler.validate(CODE, CODE_GREATER_EQUAL, TESTS, tests_b, HISTORY, {}, run_batch)
    assert report["valid"] is False
    [failure] = [t for t in report["tests"] if not t["passed"]]
    assert failure == {
        "author": "B",
        "name": "exactly 1000",
        "expected": True,
        "a": "does not fire",
        "b": "fires (HIGH_AMOUNT)",
        "passed": False,
    }
    assert len(report["discrepancies"]) == 1 and "exactly 1000" in report["discrepancies"][0]


def test_validate_history_discrepancy() -> None:
    history = [*HISTORY, ("f3.pdf", {"amount": 1000})]
    report = compiler.validate(CODE, CODE_GREATER_EQUAL, TESTS, TESTS, history, {}, run_batch)
    assert report["valid"] is False
    assert report["history"] == {"instances": 3, "agree": 2}
    assert report["discrepancies"] == [
        "Instance f3.pdf: A says does not fire; B says fires (HIGH_AMOUNT)"
    ]


def test_validate_run_error() -> None:
    report = compiler.validate(CODE, CODE_BROKEN, TESTS, [], HISTORY, {}, run_batch)
    assert report["valid"] is False
    assert all(t["b"].startswith("error: KeyError") for t in report["tests"])
    assert report["history"]["agree"] == 0
    assert len(report["discrepancies"]) == 4


def test_validate_others_excludes_itself() -> None:
    code = """
def evaluate(instance, sources, others):
    dup = any(o["num"] == instance["num"] for o in others)
    return {"fires": dup, "reason": "DUPLICATE" if dup else "OK"}
"""
    history = [("a", {"num": 1}), ("b", {"num": 1}), ("c", {"num": 2})]
    seen = []

    def spy(code: str, cases: list) -> list:
        seen.extend(cases)
        return run_batch(code, cases)

    report = compiler.validate(code, code, [], [], history, {"p": []}, spy)
    assert report["valid"] is True
    assert seen[0] == (
        {"num": 1},
        {"p": []},
        [{"num": 1, "_instance": "b"}, {"num": 2, "_instance": "c"}],
    )


def proposal(code: str) -> dict:
    """What an agent answers: code plus six tests around the threshold."""
    tests = [
        {
            "name": f"amount {amount}",
            "instance_json": json.dumps({"amount": amount}),
            "sources_json": "{}",
            "others_json": "[]",
            "fires": amount > 1000,
        }
        for amount in (0, 10, 999.99, 1000, 1000.01, 5000)
    ]
    return {"code": code, "tests": tests}


class FakeSession:
    def __init__(self) -> None:
        self.added: list = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


DESCRIPTION = "Amounts in whole cents; if a value is missing, the rule does not fire."
RULE = SimpleNamespace(id=7, process_id=1, text="If amount > 1000, escalate", type="prohibition")
SYMBOLS = [SimpleNamespace(name="amount", type="number", description="invoice total")]


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> dict:
    """The compiler reads the process from a fake, not the database."""

    async def read(session, process_id):
        return DESCRIPTION, {"suppliers": [{"cif": "B1", "iban": "ES1"}]}, HISTORY

    monkeypatch.setattr(compiler, "read_process", read)
    return {}


def script(monkeypatch: pytest.MonkeyPatch, seen: dict, a: list[dict], b: list[dict]) -> None:
    monkeypatch.setattr(llm, "model_for", per_role({"compiler_a": a, "compiler_b": b}, seen))


async def test_compile_end_to_end(monkeypatch: pytest.MonkeyPatch, seen: dict) -> None:
    script(monkeypatch, seen, [proposal(CODE)], [proposal(CODE)])
    session = FakeSession()

    result = await compiler.compile_rule(session, RULE, SYMBOLS)

    assert result.code == CODE
    assert result.report["valid"] is True
    assert len(result.report["tests"]) == 12
    assert result.report["alternative"]["code"] == CODE
    assert result.tests[3] == {
        "name": "amount 1000",
        "instance": {"amount": 1000},
        "sources": {},
        "others": [],
        "fires": False,
    }
    # Both agents got the same context, which carries the rule, symbols and sources.
    [ctx_a], [ctx_b] = (list(map(user_prompt, calls)) for calls in seen.values())
    assert ctx_a == ctx_b
    assert "prohibition" in ctx_a and "amount (number)" in ctx_a
    assert '"iban": "ES1"' in ctx_a
    assert DESCRIPTION in ctx_a
    events = [e for e in session.added if e.step == "compile_rule"]
    assert [e.data["role"] for e in events] == ["compiler_a", "compiler_b"]
    assert all(e.data["retries"] == 0 for e in events)
    assert all(e.data["model"] == "fake/model" and e.data["valid"] for e in events)


async def test_compile_self_repair(monkeypatch: pytest.MonkeyPatch, seen: dict) -> None:
    script(monkeypatch, seen, [proposal("def evaluate(:\n"), proposal(CODE)], [proposal(CODE)])
    session = FakeSession()

    result = await compiler.compile_rule(session, RULE, SYMBOLS)

    a, b = session.added
    assert (a.data["retries"], b.data["retries"]) == (1, 0)
    # A only ever saw its own broken answer and the sandbox error, never B's work.
    repair = seen["compiler_a"][1]
    [complaint] = retry_prompts(repair)
    assert "sandbox" in complaint and "Fix it" in complaint
    assert DESCRIPTION in user_prompt(repair)  # its own context, kept in the repair round
    assert len(seen["compiler_b"]) == 1
    assert result.report["valid"] is True


async def test_compile_without_a_fix_fails(monkeypatch: pytest.MonkeyPatch, seen: dict) -> None:
    script(monkeypatch, seen, [proposal("def evaluate(:\n")] * 3, [proposal(CODE)])

    with pytest.raises(compiler.CompilationError) as e:
        await compiler.compile_rule(FakeSession(), RULE, SYMBOLS)

    assert e.value.status_code == 502 and "compiler_a" in e.value.message
    assert len(seen["compiler_a"]) == 3  # the first answer and two repairs
