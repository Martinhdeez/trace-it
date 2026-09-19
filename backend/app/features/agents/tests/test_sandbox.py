import time

import pytest

from app.features.agents.sandbox import (
    MissingValidationSymbol,
    SandboxError,
    check,
    run_batch,
    run_dataset,
)

VALID = """
from decimal import Decimal

def evaluate(instance, sources, others):
    total = Decimal(str(instance["total"]))
    return {"fires": total > Decimal("100.00"), "reason": f"total {total}"}
"""


def rule(body: str) -> str:
    return f"def evaluate(instance, sources, others):\n    {body}\n"


def run(code: str, instance: dict, sources: dict, others: list, timeout_s: float = 2.0) -> dict:
    """One case; raises the case's SandboxError like the whole batch would."""
    [result] = run_batch(code, [(instance, sources, others)], timeout_s)
    if isinstance(result, SandboxError):
        raise result
    return result


def test_valid_rule_returns_its_result():
    assert run(VALID, {"total": "150.50"}, {}, []) == {
        "fires": True,
        "reason": "total 150.50",
    }


def test_validation_marks_only_actual_missing_symbol_access():
    missing = {1: ["new_field"], 2: ["new_field"]}
    population = [(1, {"old": 0}), (2, {"old": 2})]
    code = (
        "def evaluate(instance, sources, others):\n"
        "    if instance['old'] == 0:\n"
        "        raise ZeroDivisionError('independent failure')\n"
        "    return {'fires': instance.get('new_field') == 1, 'reason': 'OK'}\n"
    )
    results = run_dataset(code, population, {}, population, validation_missing=missing)
    assert isinstance(results[0], SandboxError) and not isinstance(
        results[0], MissingValidationSymbol
    )
    assert "ZeroDivisionError" in str(results[0])
    assert isinstance(results[1], MissingValidationSymbol)
    assert results[1].name == "new_field"
    other_code = (
        "def evaluate(instance, sources, others):\n"
        "    return {'fires': 'new_field' in others[0], 'reason': 'OTHER'}\n"
    )
    [other] = run_dataset(other_code, [(3, {"old": 3})], {}, population, validation_missing=missing)
    assert isinstance(other, MissingValidationSymbol) and other.name == "new_field"


@pytest.mark.parametrize(
    "body",
    [
        'return {"fires": 1, "reason": "x"}',
        'return {"fires": "yes", "reason": "x"}',
        'return {"fires": True}',
        'return {"fires": True, "reason": "x", "decision": "PAGAR"}',
        'return {"fires": True, "reason": 3}',
        "return [True]",
        "return object()",
        "raise ValueError('bad')",
        "raise SystemExit(0)",
    ],
)
def test_invalid_result_or_exception(body):
    with pytest.raises(SandboxError):
        run(rule(body), {}, {}, [])


@pytest.mark.parametrize(
    "code",
    [
        "import os\n" + rule("return {}"),
        "import socket\n" + rule("return {}"),
        "from subprocess import run\n" + rule("return {}"),
        "from . import x\n" + rule("return {}"),
        rule("open('/etc/passwd')"),
        rule("__import__('os')"),
        rule("return ().__class__.__bases__[0].__subclasses__()"),
        rule("return (x for x in []).gi_frame.f_back"),
        rule("getattr(1, 'real')"),
        "def other():\n    pass\n",
        "def evaluate(:\n",
    ],
)
def test_forbidden_code_rejected_before_running(code):
    with pytest.raises(SandboxError):
        check(code)
    with pytest.raises(SandboxError):
        run(code, {}, {}, [])


def test_allowed_module_does_not_expose_other_modules():
    with pytest.raises(SandboxError, match="AttributeError"):
        run(rule("import re\n    re.enum.sys.modules"), {}, {}, [])


def test_infinite_loop_times_out():
    start = time.monotonic()
    with pytest.raises(SandboxError, match="Timed out"):
        run(rule("while True:\n        pass"), {}, {}, [], timeout_s=0.5)
    assert time.monotonic() - start < 2


def test_one_bad_case_in_a_batch_only_fails_that_case():
    cases = [({"total": "50"}, {}, []), ({}, {}, []), ({"total": "500"}, {}, [])]
    ok1, bad, ok2 = run_batch(VALID, cases)
    assert ok1 == {"fires": False, "reason": "total 50"}
    assert isinstance(bad, SandboxError) and "KeyError" in bad.message
    assert ok2 == {"fires": True, "reason": "total 500"}


def test_dataset_derives_others_without_sending_them_per_case():
    code = rule(
        'return {"fires": len(others) == 2 and all(o["id"] != instance["id"] for o in others), '
        '"reason": ",".join(o["name"] for o in others)}'
    )
    population = [
        (1, {"id": 1, "name": "a"}),
        (2, {"id": 2, "name": "b"}),
        (3, {"id": 3, "name": "c"}),
    ]

    results = run_dataset(code, [(2, {"id": 2})], {}, population)

    assert results == [{"fires": True, "reason": "a,c"}]
