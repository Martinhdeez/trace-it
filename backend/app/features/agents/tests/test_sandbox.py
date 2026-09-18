import time

import pytest

from app.features.agents.sandbox import SandboxError, check, run, run_batch

VALID = """
from decimal import Decimal

def evaluate(instance, sources, others):
    total = Decimal(str(instance["total"]))
    return {"fires": total > Decimal("100.00"), "reason": f"total {total}"}
"""


def rule(body: str) -> str:
    return f"def evaluate(instance, sources, others):\n    {body}\n"


def test_valid_rule_returns_its_result():
    assert run(VALID, {"total": "150.50"}, {}, []) == {
        "fires": True,
        "reason": "total 150.50",
    }


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
