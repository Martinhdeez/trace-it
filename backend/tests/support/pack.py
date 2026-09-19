"""The invoice process pack as the engine consumes it, without a database."""

import json
from pathlib import Path
from typing import Any

from app.features.decisions.engine import Outcomes
from app.features.rules.model import Rule
from app.features.rules.service import rule_hash
from app.features.use_cases import service as use_cases
from app.features.use_cases.schemas import UseCaseDefinition

REPO = Path(__file__).resolve().parents[3]
PACK = REPO / "processes"
PROCESS_FILE = PACK / "invoice-payment.json"


USE_CASE_FILE = PACK / "invoice-payment" / "use-case.json"


def definition() -> dict[str, Any]:
    return json.loads(PROCESS_FILE.read_text(encoding="utf-8"))


def use_case() -> UseCaseDefinition:
    """The invoice use case: description and agent settings, examples' code read in."""
    return use_cases.read_file(USE_CASE_FILE)


def codes(defn: dict[str, Any] | None = None) -> list[str]:
    """Each rule's hand-written code, in the order the definition lists them."""
    defn = defn or definition()
    return [(PACK / r["code"]).read_text(encoding="utf-8") for r in defn["rules"]]


def rules(defn: dict[str, Any] | None = None) -> list[Rule]:
    """Rule rows as the loader would install them, numbered 1..16 like the files."""
    defn = defn or definition()
    return [
        Rule(
            id=n,
            text=r["text"],
            type=r["type"],
            decision=r["decision"],
            code=code,
            hash=rule_hash(r["text"], code),
        )
        for n, (r, code) in enumerate(zip(defn["rules"], codes(defn), strict=True), 1)
    ]


def outcomes(defn: dict[str, Any] | None = None) -> Outcomes:
    types = (defn or definition())["decision_types"]
    return Outcomes(
        priorities={t["name"]: t["priority"] for t in types},
        default=next(t["name"] for t in types if t.get("is_default")),
        escalate=max((t for t in types if t.get("requires_human")), key=lambda t: t["priority"])[
            "name"
        ],
        required=tuple(s["name"] for s in (defn or definition())["symbols"] if s.get("required")),
    )
