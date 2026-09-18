"""The sixteen Norma_Pagos_v3 rules as the process pack ships them.

The code is not written here: it is read from `procesos/reglas-v3/`, the same files the
loader installs, so what these tests exercise is exactly what runs. They are hand-written
because the process has to run before any model is configured; the compiler in
`features/agentes` is what writes them from the rule text once it can, and this is what its
output can be compared against.
"""

import json
from pathlib import Path

PAQUETE = Path(__file__).resolve().parents[5] / "procesos"
DEFINICION = PAQUETE / "pago-facturas.json"


def codigos() -> list[str]:
    """Each rule's code, in the order the definition lists them."""
    reglas = json.loads(DEFINICION.read_text(encoding="utf-8"))["reglas"]
    return [(PAQUETE / r["codigo"]).read_text(encoding="utf-8") for r in reglas]


REGLAS_V3 = codigos()
