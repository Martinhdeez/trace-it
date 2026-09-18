"""The decision engine: every active rule runs, nobody chooses which (P7).

Pure function. No database, no LLM, no clock, no network: the same inputs always give the
same verdict, so a past decision can be replayed from its stored symbols.
"""

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from app.features.reglas.model import Regla

# Martín's sandbox: runs `evaluar(instancia, fuentes, otras, contexto)` from `codigo` and
# returns {"salta": bool, "motivo": str}. Raises on any error, timeout or malformed result.
Ejecutar = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class ResultadoRegla:
    """What one rule answered. `salta` is None when the rule could not be evaluated."""

    regla_id: int
    hash: str | None
    salta: bool | None
    motivo: str


@dataclass(frozen=True)
class Veredicto:
    decision: str
    motivo: str
    resultados: list[ResultadoRegla]
    reglas_hash: str


def hash_reglas(reglas: Sequence[Regla]) -> str:
    """Identifies the rule set a decision was taken with."""
    partes = sorted(f"{r.id}:{r.hash}" for r in reglas)
    return hashlib.sha256("\0".join(partes).encode()).hexdigest()


def decidir(
    reglas: Sequence[Regla],
    prioridades: dict[str, int],
    por_defecto: str,
    escalar: str,
    instancia: dict[str, Any],
    fuentes: dict[str, list[dict[str, Any]]],
    otras: list[dict[str, Any]],
    contexto: dict[str, Any],
    ejecutar: Ejecutar,
) -> Veredicto:
    """Apply every rule in `reglas` to one instance.

    No rule fires -> `por_defecto`. Several fire -> the outcome with the highest priority.
    A rule that fails, or a tie between two different outcomes, is sent to a person as
    `escalar`: the engine never decides without a rule it could not evaluate.
    """
    resultados: list[ResultadoRegla] = []
    fallos: list[str] = []
    saltan: list[Regla] = []

    for regla in reglas:
        try:
            respuesta = ejecutar(regla.codigo_a, instancia, fuentes, otras, contexto)
            salta, motivo = bool(respuesta["salta"]), str(respuesta.get("motivo", ""))
        except Exception as error:  # noqa: BLE001 - any failure is the same to the engine
            fallo = f"ERROR_REGLA {regla.id}: {type(error).__name__}: {error}"
            resultados.append(ResultadoRegla(regla.id, regla.hash, None, fallo))
            fallos.append(fallo)
            continue

        resultados.append(ResultadoRegla(regla.id, regla.hash, salta, motivo))
        if salta:
            saltan.append(regla)

    reglas_hash = hash_reglas(reglas)

    def veredicto(decision: str, motivo: str) -> Veredicto:
        return Veredicto(decision, motivo, resultados, reglas_hash)

    if fallos:
        return veredicto(escalar, " | ".join(fallos))

    desconocidas = [r.decision for r in saltan if r.decision not in prioridades]
    if desconocidas:
        return veredicto(escalar, f"DECISION_DESCONOCIDA: {', '.join(sorted(desconocidas))}")

    if not saltan:
        return veredicto(por_defecto, "")

    maxima = max(prioridades[r.decision] for r in saltan)
    ganadoras = [r for r in saltan if prioridades[r.decision] == maxima]
    decisiones = {r.decision for r in ganadoras}
    if len(decisiones) > 1:
        return veredicto(
            escalar, f"CONFLICTO_REGLAS: {', '.join(sorted(decisiones))} con la misma prioridad"
        )

    return veredicto(ganadoras[0].decision, " | ".join(r.texto for r in ganadoras))
