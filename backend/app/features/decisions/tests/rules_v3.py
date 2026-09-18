"""The sixteen Norma_Pagos_v3 rules as the process pack ships them.

The code is not written here: it is read from `processes/rules-v3/`, the same files the
loader installs, so what these tests exercise is exactly what runs. They are hand-written
because the process has to run before any model is configured; the compiler in
`features/agents` is what writes them from the rule text once it can, and this is what its
output can be compared against.
"""

import json
from pathlib import Path

PACK = Path(__file__).resolve().parents[5] / "processes"
DEFINITION = PACK / "invoice-payment.json"


def codes() -> list[str]:
    """Each rule's code, in the order the definition lists them."""
    rules = json.loads(DEFINITION.read_text(encoding="utf-8"))["rules"]
    return [(PACK / r["code"]).read_text(encoding="utf-8") for r in rules]


RULES_V3 = codes()
