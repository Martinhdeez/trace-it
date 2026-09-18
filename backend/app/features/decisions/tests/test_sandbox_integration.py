"""The engine against the real sandbox, not a fake.

The other engine tests inject a fake executor, so nothing there would notice if the two
sides of the contract drifted apart. This one runs compiled-looking code for real.
"""

from app.features.agents import sandbox
from app.features.decisions.engine import decide
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

SOURCES = {"suppliers": [{"nif": "B96233419", "iban": "ES2100752345670600123456"}]}
PRIORITIES = {"ESCALAR": 3, "PAGAR": 1}
RULES = [Rule(id=1, text="The IBAN is the master's", decision="ESCALAR", code_a=CODE)]


def decide_with_sandbox(instance: dict) -> str:
    verdict = decide(RULES, PRIORITIES, "PAGAR", "ESCALAR", instance, SOURCES, [], sandbox.run)
    return verdict.decision


def test_the_engine_talks_to_the_real_sandbox() -> None:
    clean = {"nif": "B96233419", "iban": "ES2100752345670600123456"}
    other_iban = {"nif": "B96233419", "iban": "ES3900815290070012345678"}

    assert decide_with_sandbox(clean) == "PAGAR"
    assert decide_with_sandbox(other_iban) == "ESCALAR"


def test_code_the_sandbox_rejects_escalates() -> None:
    """A rule the sandbox refuses to run is a rule the engine cannot decide without."""
    malicious = [Rule(id=1, text="reads the disk", decision="ESCALAR", code_a="import os")]

    verdict = decide(
        malicious, PRIORITIES, "PAGAR", "ESCALAR", {"nif": "x"}, SOURCES, [], sandbox.run
    )

    assert verdict.decision == "ESCALAR"
    assert "RULE_ERROR 1" in verdict.reason
