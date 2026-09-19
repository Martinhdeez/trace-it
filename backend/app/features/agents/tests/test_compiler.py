"""Compiler without network, LLM or database: the models are scripted, the sandbox is faked
with a plain `exec` (acceptable in tests only) and the DB reads are monkeypatched."""

import json
from types import SimpleNamespace

import pytest

from app.core import events
from app.features.agents import compiler, llm, sandbox
from app.features.use_cases.schemas import AgentSettings, Example
from tests.support.models import instructions, per_role, retry_prompts, user_prompt


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
AMOUNTS = (0, 10, 999.99, 1000, 1000.01, 5000)


def suite(at_1000: bool = False, **extra: object) -> dict:
    """What the tester answers: six tests around the threshold. `at_1000` is what it
    expects at exactly 1000 (the text says '>', so False is the right reading)."""
    tests = [
        {
            "name": f"amount {amount}",
            "instance_json": json.dumps({"amount": amount, **extra}),
            "sources_json": "{}",
            "others_json": "[]",
            "fires": at_1000 if amount == 1000 else amount > 1000,
        }
        for amount in AMOUNTS
    ]
    return {"tests": tests}


def proposal(code: str, disputes: list[dict] | None = None) -> dict:
    return {"code": code, "disputes": disputes or []}


NEEDS_DATA = {
    "_output": "NeedsData",
    "missing": ["symbol: delivery_date"],
    "explanation": "The rule compares with the delivery date",
}


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
        return DESCRIPTION, {"suppliers": [{"cif": "B1", "iban": "ES1"}]}, {}

    monkeypatch.setattr(compiler, "read_process", read)
    return {}


def script(monkeypatch: pytest.MonkeyPatch, seen: dict, tester: list, coder: list) -> None:
    monkeypatch.setattr(llm, "model_for", per_role({"tester": tester, "compiler": coder}, seen))


async def compile_(session: FakeSession | None = None) -> compiler.Compilation:
    return await compiler.compile_rule(session or FakeSession(), RULE, SYMBOLS)


async def test_green_on_the_first_attempt(monkeypatch: pytest.MonkeyPatch, seen: dict) -> None:
    script(monkeypatch, seen, [suite()], [proposal(CODE)])
    session = FakeSession()

    result = await compile_(session)

    assert result.code == CODE
    assert result.report["valid"] is True and result.report["attempts"] == 1
    assert all(t["passed"] for t in result.report["tests"])
    assert result.tests[3] == {
        "name": "amount 1000",
        "instance": {"amount": 1000},
        "sources": {},
        "others": [],
        "fires": False,
    }
    # The tester works from the text alone; the coder gets the same context plus the tests.
    [tester_ctx] = map(user_prompt, seen["tester"])
    [coder_ctx] = map(user_prompt, seen["compiler"])
    assert "prohibition" in tester_ctx and "amount (number)" in tester_ctx
    assert DESCRIPTION in tester_ctx and '"iban": "ES1"' in tester_ctx
    assert "def evaluate" not in tester_ctx
    assert coder_ctx.startswith(tester_ctx) and '"name": "amount 1000"' in coder_ctx


def tree(rows: list[dict], parent: str | None = None) -> list:
    """The spans as nested (step, data, children), children in the order they ended."""
    return [
        (r["step"], r["data"], tree(rows, r["span_id"])) for r in rows if r["parent_id"] == parent
    ]


async def test_the_coder_iterates_on_failing_tests(
    monkeypatch: pytest.MonkeyPatch, seen: dict
) -> None:
    script(monkeypatch, seen, [suite()], [proposal(CODE_GREATER_EQUAL), proposal(CODE)])
    written: list[dict] = []
    monkeypatch.setattr(events, "_write", written.extend)

    with events.span("compile_rule", rule_id=7):
        result = await compile_()

    # One trace, written once: the tester's run, then each attempt with its test run.
    [(root, _, [tester, first, second])] = tree(written)
    assert root == "compile_rule" and {r["rule_id"] for r in written} == {7}
    assert tester[0] == "llm_run" and tester[1]["agent"] == "tester"
    assert tester[1]["model"] == "fake/model" and tester[1]["input_tokens"] > 0
    for (step, _, [run, tests]), passed in zip((first, second), (5, 6), strict=True):
        assert step == "coder_attempt" and run[1]["agent"] == "compiler"
        assert tests[:2] == ("run_tests", {"cases": 6, "passed": passed})
    assert first[1]["attempt"] == 1 and first[1]["failures"] == 1
    # Each run keeps what the model saw and answered.
    assert "## Guidance" not in tester[1]["instructions"] and tester[1]["instructions"]
    assert tester[1]["user_prompt"] == user_prompt(seen["tester"][0])
    assert len(tester[1]["output"]["tests"]) == 6 and tester[1]["retry_prompts"] == []
    retry = second[2][0][1]
    assert CODE_GREATER_EQUAL in retry["user_prompt"] and retry["output"]["code"] == CODE

    assert result.code == CODE and result.report["valid"] is True
    assert result.report["attempts"] == 2
    second = user_prompt(seen["compiler"][1])
    assert CODE_GREATER_EQUAL in second
    assert "amount 1000: expected does not fire, got fires (HIGH_AMOUNT)" in second


async def test_a_disputed_test_is_corrected_by_the_tester(
    monkeypatch: pytest.MonkeyPatch, seen: dict
) -> None:
    """The tester misread '>' as '>='. The coder objects; the tester re-reads and fixes it."""
    dispute = {"test": "amount 1000", "argument": "The text says 'amount > 1000'"}
    verdict = {"test": "amount 1000", "fires": False, "reason": "'>' excludes 1000"}
    script(
        monkeypatch,
        seen,
        [suite(at_1000=True), {"verdicts": [verdict]}],
        [proposal(CODE, [dispute]), proposal(CODE)],
    )

    result = await compile_()

    assert result.report["valid"] is True and result.report["attempts"] == 2
    assert result.report["reviews"] == [{"before": True, **verdict}]
    assert result.tests[3]["fires"] is False
    review_prompt = user_prompt(seen["tester"][1])
    assert "The text says 'amount > 1000'" in review_prompt and "def evaluate" not in review_prompt
    assert "'>' excludes 1000" in user_prompt(seen["compiler"][1])


async def test_without_agreement_the_rule_is_not_valid(
    monkeypatch: pytest.MonkeyPatch, seen: dict
) -> None:
    """The tester keeps its reading and the coder keeps its code: nothing is activated,
    the open failure is in the report."""
    dispute = {"test": "amount 1000", "argument": "The text says 'amount > 1000'"}
    keep = {"verdicts": [{"test": "amount 1000", "fires": True, "reason": "keep"}]}
    attempts = compiler.MAX_ATTEMPTS
    script(
        monkeypatch,
        seen,
        [suite(at_1000=True), keep, keep],
        [proposal(CODE, [dispute])] * attempts,
    )

    result = await compile_()

    assert result.report["valid"] is False
    assert result.report["attempts"] == attempts
    assert len(seen["tester"]) == 1 + compiler.MAX_REVIEWS
    assert result.report["discrepancies"] == ["Test amount 1000: expected fires, got does not fire"]


@pytest.mark.parametrize("who", ["tester", "compiler"])
async def test_needs_data_stops_without_code(
    monkeypatch: pytest.MonkeyPatch, seen: dict, who: str
) -> None:
    if who == "tester":
        script(monkeypatch, seen, [NEEDS_DATA], [])
    else:
        script(monkeypatch, seen, [suite()], [NEEDS_DATA])

    result = await compile_()

    assert result.code is None and result.report["valid"] is False
    assert result.report["needs_data"]["by"] == who
    assert result.report["needs_data"]["missing"] == ["symbol: delivery_date"]


async def test_the_tester_may_only_use_known_symbols(
    monkeypatch: pytest.MonkeyPatch, seen: dict
) -> None:
    script(monkeypatch, seen, [suite(currency="EUR"), suite()], [proposal(CODE)])

    result = await compile_()

    assert result.report["valid"] is True
    [complaint] = retry_prompts(seen["tester"][1])
    assert "Unknown instance keys ['currency']" in complaint


UNKNOWN_KEYS = CODE.replace(
    "    if Decimal",
    '    if instance.get("currency") == "USD" or sources["rates"]:\n'
    '        return {"fires": True, "reason": "FOREIGN"}\n'
    "    if Decimal",
)


async def test_the_coder_may_only_read_known_symbols_and_sources(
    monkeypatch: pytest.MonkeyPatch, seen: dict
) -> None:
    script(monkeypatch, seen, [suite()], [proposal(UNKNOWN_KEYS), proposal(CODE)])

    result = await compile_()

    assert result.code == CODE and result.report["valid"] is True
    [complaint] = retry_prompts(seen["compiler"][1])
    assert "unknown keys ['currency', 'rates']" in complaint
    assert "['amount']" in complaint and "['suppliers']" in complaint
    assert "NeedsData" in complaint


def test_computed_keys_and_any_parameter_names_are_allowed() -> None:
    code = """
def evaluate(inv, src, others):
    key = "amo" + "unt"
    rows = src.get("suppliers") or src[key]
    return {"fires": inv[key] > 1 and bool(inv.get("amount")), "reason": ""}
"""
    assert compiler.read_keys(code) == ({"amount"}, {"suppliers"})


async def test_tests_on_one_side_only_are_rejected() -> None:
    one_sided = compiler.TestSuite.model_validate(suite())
    for t in one_sided.tests:
        t.fires = True
    with pytest.raises(ValueError, match="fires and where it does not"):
        compiler.tests_of(one_sided)


async def test_code_the_sandbox_rejects_is_repaired_in_the_run(
    monkeypatch: pytest.MonkeyPatch, seen: dict
) -> None:
    script(monkeypatch, seen, [suite()], [proposal("def evaluate(:\n"), proposal(CODE)])

    result = await compile_()

    assert result.report["valid"] is True and result.report["attempts"] == 1
    [complaint] = retry_prompts(seen["compiler"][1])
    assert "sandbox check" in complaint


async def test_still_malformed_after_the_repairs_fails(
    monkeypatch: pytest.MonkeyPatch, seen: dict
) -> None:
    script(monkeypatch, seen, [suite()], [proposal("def evaluate(:\n")] * 3)

    with pytest.raises(compiler.CompilationError) as e:
        await compile_()

    assert e.value.status_code == 502 and "compiler" in e.value.message
    assert len(seen["compiler"]) == 3  # the first answer and two repairs


def use_case(monkeypatch: pytest.MonkeyPatch, **settings: AgentSettings) -> None:
    """The rule's use case configures its agents with `settings` (role -> settings)."""
    setups = {role: llm.Setup(s) for role, s in settings.items()}

    async def read(session, process_id):
        return DESCRIPTION, {}, setups

    monkeypatch.setattr(compiler, "read_process", read)


async def test_the_coder_sees_examples_of_other_rules_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    examples = [
        Example(text=RULE.text, type="prohibition", code="OWN_EXAMPLE_CODE"),
        Example(text="If supplier is empty, escalate", type="prohibition", code="OTHER_CODE"),
    ]
    use_case(monkeypatch, compiler=AgentSettings(examples=examples))
    seen: dict = {}
    script(monkeypatch, seen, [suite()], [proposal(CODE)])

    await compile_()

    coder = instructions(seen["compiler"][0])
    assert "OTHER_CODE" in coder and "If supplier is empty" in coder
    assert "OWN_EXAMPLE_CODE" not in coder


async def test_the_use_case_limits_are_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case(
        monkeypatch,
        tester=AgentSettings(limits={"min_tests": 7}),
        compiler=AgentSettings(limits={"max_attempts": 1}),
    )
    seven = suite()
    seven["tests"].append({**seven["tests"][0], "name": "amount 0 again"})
    seen: dict = {}
    script(monkeypatch, seen, [suite(), seven], [proposal(CODE_GREATER_EQUAL)])

    result = await compile_()

    [complaint] = retry_prompts(seen["tester"][1])
    assert "At least 7 tests" in complaint
    assert result.report["valid"] is False and result.report["attempts"] == 1
