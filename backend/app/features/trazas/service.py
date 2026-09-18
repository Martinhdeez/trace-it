from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.trazas.model import Evento


def registrar(
    session: AsyncSession,
    paso: str,
    *,
    instancia_id: int | None = None,
    datos: dict[str, Any] | None = None,
    latencia_ms: int | None = None,
    coste: float | None = None,
) -> None:
    """Add a trace event to the session. It is saved with the caller's commit."""
    session.add(
        Evento(
            instancia_id=instancia_id,
            paso=paso,
            datos=datos,
            latencia_ms=latencia_ms,
            coste=coste,
        )
    )
