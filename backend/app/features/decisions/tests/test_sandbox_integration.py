"""The engine against the real sandbox, not a fake.

The other engine tests inject a fake executor, so nothing there would notice if the two
sides of the contract drifted apart. This one runs compiled-looking code for real.
"""

import time

from app.features.agents import sandbox
from app.features.decisions.engine import Verdict, decide, decide_batch
from app.features.rules.model import Rule

CODE = """
def evaluate(instance, sources, others):
    approved = None
    for row in sources["suppliers"]:
        if row["nif"] == instance["nif"]:
            approved = row["iban"]
    if approved is None:
        return {"fires": True, "reason": "SUPPLIER_NOT_FOUND"}
    if instance["iban"] != approved:
        return {"fires": True, "reason": "IBAN_MISMATCH"}
    return {"fires": False, "reason": ""}
"""
# Same rule, written by the other agent: same answer, its own wording.
CODE_B = CODE.replace('"IBAN_MISMATCH"', '"IBAN_NOT_IN_MASTER"')
# A misreading: it never fires.
NEVER = 'def evaluate(instance, sources, others):\n    return {"fires": False, "reason": ""}\n'
# Fails on any instance without an IBAN.
STRICT = CODE.replace('instance["iban"] !=', 'instance["iban"].upper() !=')

SOURCES = {"suppliers": [{"nif": "B96233419", "iban": "ES2100752345670600123456"}]}
PRIORITIES = {"ESCALAR": 3, "PAGAR": 1}
CLEAN = {"nif": "B96233419", "iban": "ES2100752345670600123456"}
OTHER_IBAN = {"nif": "B96233419", "iban": "ES3900815290070012345678"}
NO_IBAN = {"nif": "B96233419", "iban": None}


def rule(code_a: str = CODE, code_b: str = CODE_B) -> list[Rule]:
    return [
        Rule(
            id=1, text="The IBAN is the master's", decision="ESCALAR", code_a=code_a, code_b=code_b
        )
    ]


def decide_with_sandbox(instance: dict, rules: list[Rule] | None = None) -> Verdict:
    return decide(rules or rule(), PRIORITIES, "PAGAR", instance, SOURCES, [], sandbox.run_batch)


def test_the_engine_talks_to_the_real_sandbox() -> None:
    assert decide_with_sandbox(CLEAN).decision == "PAGAR"
    escalated = decide_with_sandbox(OTHER_IBAN)
    assert escalated.decision == "ESCALAR"
    # A's reason is the record; B's is kept next to it.
    [result] = escalated.results
    assert (result.reason, result.reason_b) == ("IBAN_MISMATCH", "IBAN_NOT_IN_MASTER")


def test_code_the_sandbox_rejects_goes_to_review() -> None:
    """A rule the sandbox refuses to run is a rule the engine cannot decide without."""
    verdict = decide_with_sandbox({"nif": "x"}, rule(code_b="import os"))

    assert verdict.decision is None
    assert "RULE_ERROR 1" in verdict.reason


def test_codes_a_and_b_disagreeing_goes_to_review() -> None:
    verdict = decide_with_sandbox(OTHER_IBAN, rule(code_b=NEVER))

    assert verdict.decision is None
    assert "CODES_DISAGREE 1" in verdict.reason
    # Where they agree, the rule is trusted.
    assert decide_with_sandbox(CLEAN, rule(code_b=NEVER)).decision == "PAGAR"


def test_one_code_raising_goes_to_review_never_to_the_default() -> None:
    verdict = decide_with_sandbox(NO_IBAN, rule(code_a=STRICT))

    assert verdict.decision is None
    assert "RULE_ERROR 1" in verdict.reason
    assert "AttributeError" in verdict.reason


def test_a_failing_case_only_affects_its_own_instance() -> None:
    cases = [(CLEAN, SOURCES, []), (NO_IBAN, SOURCES, []), (OTHER_IBAN, SOURCES, [])]

    verdicts = decide_batch(rule(code_a=STRICT), PRIORITIES, "PAGAR", cases, sandbox.run_batch)

    assert [v.decision for v in verdicts] == ["PAGAR", None, "ESCALAR"]


def test_a_whole_batch_failure_sends_every_instance_to_review() -> None:
    loop = "def evaluate(instance, sources, others):\n    while True:\n        pass\n"

    def slow(code: str, cases: list) -> list:
        return sandbox.run_batch(code, cases, timeout_s=0.5)

    cases = [(CLEAN, SOURCES, []), (OTHER_IBAN, SOURCES, [])]
    verdicts = decide_batch(rule(code_b=loop), PRIORITIES, "PAGAR", cases, slow)

    assert [v.decision for v in verdicts] == [None, None]
    assert all("Timed out" in v.reason for v in verdicts)


def test_500_instances_run_each_code_once() -> None:
    """500 instances x 1 rule x 2 codes: two subprocesses, each case seeing the other 499
    instances as the service passes them."""
    instances = [
        {**(OTHER_IBAN if n % 10 == 0 else CLEAN), "_instance": f"f{n}.pdf"} for n in range(500)
    ]
    cases = [(i, SOURCES, [o for o in instances if o is not i]) for i in instances]
    batches: list[int] = []

    def counted(code: str, cases: list) -> list:
        batches.append(len(cases))
        return sandbox.run_batch(code, cases)

    start = time.perf_counter()
    verdicts = decide_batch(rule(), PRIORITIES, "PAGAR", cases, counted)
    seconds = time.perf_counter() - start

    print(f"\n500 instances x 1 rule x 2 codes: {seconds:.2f}s")
    assert batches == [500, 500]
    assert [v.decision for v in verdicts].count("ESCALAR") == 50
    assert seconds < 30
