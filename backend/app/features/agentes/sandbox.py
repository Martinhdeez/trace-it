"""Isolated execution of generated rule code (P8). Owner: Martín."""

from typing import Any

from app.common.exceptions import NotImplementedYetError


def ejecutar(
    codigo: str,
    instancia: dict[str, Any],
    fuentes: dict[str, list[dict[str, Any]]],
    otras: list[dict[str, Any]],
    timeout_s: float = 2.0,
) -> dict[str, Any]:
    """Run `evaluar(instancia, fuentes, otras)` from `codigo` in a separate process with no
    network or disk and a time limit. Returns {"salta": bool, "motivo": str}; raises on any
    error, timeout or malformed result. Callers must never decide without the result."""
    raise NotImplementedYetError("Sandbox pendiente")
