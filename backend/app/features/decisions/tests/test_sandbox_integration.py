"""The engine against the real sandbox, not a fake.

The other engine tests inject a fake executor, so nothing there would notice if the two
sides of the contract drifted apart. This one runs compiled-looking code for real, through
the same `decide` + `sandbox.run_dataset` pair the service uses.
"""

import time

from app.features.agents import sandbox
from app.features.decisions.engine import Outcomes, Verdict, decide
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
# Fails on any instance without an IBAN.
STRICT = CODE.replace('instance["iban"] !=', 'instance["iban"].upper() !=')

SOURCES = {"suppliers": [{"nif": "B96233419", "iban": "ES2100752345670600123456"}]}
OUTCOMES = Outcomes({"ESCALAR": 3, "PAGAR": 1}, default="PAGAR", escalate="ESCALAR")
CLEAN = {"nif": "B96233419", "iban": "ES2100752345670600123456"}
OTHER_IBAN = {"nif": "B96233419", "iban": "ES3900815290070012345678"}
NO_IBAN = {"nif": "B96233419", "iban": None}


def rule(code: str = CODE) -> list[Rule]:
    return [Rule(id=1, text="The IBAN is the master's", decision="ESCALAR", code=code, hash="h")]


def decide_with_sandbox(instances: list[dict], rules: list[Rule] | None = None) -> list[Verdict]:
    dataset = list(enumerate(instances))
    return decide(rules or rule(), OUTCOMES, dataset, SOURCES, dataset, sandbox.run_dataset)


def test_the_engine_talks_to_the_real_sandbox() -> None:
    clean, escalated = decide_with_sandbox([CLEAN, OTHER_IBAN])

    assert clean.decision == "PAGAR"
    assert escalated.decision == "ESCALAR"
    assert escalated.results[0].reason == "IBAN_MISMATCH"


def test_code_the_sandbox_rejects_escalates() -> None:
    """A rule the sandbox refuses to run is a rule the engine cannot decide without."""
    [verdict] = decide_with_sandbox([CLEAN], rule("import os"))

    assert verdict.decision == "ESCALAR"
    assert verdict.reason.startswith("RULE_ERROR 1: SandboxError: Import not allowed")


def test_a_failing_instance_only_affects_itself() -> None:
    verdicts = decide_with_sandbox([CLEAN, NO_IBAN, OTHER_IBAN], rule(STRICT))

    assert [v.decision for v in verdicts] == ["PAGAR", "ESCALAR", "ESCALAR"]
    assert "AttributeError" in verdicts[1].reason


def test_a_whole_batch_failure_escalates_every_instance() -> None:
    loop = "def evaluate(instance, sources, others):\n    while True:\n        pass\n"

    def slow(code: str, instances: list, sources: dict, population: list) -> list:
        return sandbox.run_dataset(code, instances, sources, population, timeout_s=0.5)

    dataset = [(1, CLEAN), (2, OTHER_IBAN)]
    verdicts = decide(rule(loop), OUTCOMES, dataset, SOURCES, dataset, slow)

    assert [v.decision for v in verdicts] == ["ESCALAR", "ESCALAR"]
    assert all("Timed out" in v.reason for v in verdicts)


def test_500_instances_run_each_rule_once() -> None:
    """500 instances x 1 rule: one subprocess, the population crossing to it once."""
    instances = [
        {**(OTHER_IBAN if n % 10 == 0 else CLEAN), "_instance": f"f{n}.pdf"} for n in range(500)
    ]
    calls: list[int] = []

    def counted(code: str, dataset: list, sources: dict, population: list) -> list:
        calls.append(len(dataset))
        return sandbox.run_dataset(code, dataset, sources, population)

    dataset = list(enumerate(instances))
    start = time.perf_counter()
    verdicts = decide(rule(), OUTCOMES, dataset, SOURCES, dataset, counted)
    seconds = time.perf_counter() - start

    assert calls == [500]
    assert [v.decision for v in verdicts].count("ESCALAR") == 50
    assert seconds < 10
