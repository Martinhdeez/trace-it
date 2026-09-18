"""Rule compiler: two independent agents turn a rule's text into code + tests (P9).

Owner: Martín. Contract used by `reglas.service.compilar`.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotImplementedYetError
from app.features.procesos.model import Simbolo
from app.features.reglas.model import Regla

# A test case, as written by an agent from the rule text alone:
# {"nombre": str, "instancia": {...}, "fuentes": {...}, "otras": [...], "salta": bool}
Test = dict[str, Any]


@dataclass(frozen=True)
class Compilacion:
    codigo_a: str
    codigo_b: str
    tests_a: list[Test]
    tests_b: list[Test]
    # {"valida": bool, "tests": [...], "historico": [...], "discrepancias": [...]}
    # `valida` is True only if both codes pass every test and agree on every past instance.
    informe: dict[str, Any]


async def compilar(session: AsyncSession, regla: Regla, simbolos: list[Simbolo]) -> Compilacion:
    """Agents A and B each write, blind to the other, a function

        def evaluar(instancia: dict, fuentes: dict[str, list[dict]], otras: list[dict]) -> dict
            # returns {"salta": bool, "motivo": str}

    plus tests. Then every test runs against both codes, and both codes run on the
    process history. The result is reported, never silently accepted."""
    raise NotImplementedYetError("Compilador de reglas pendiente")
