"""Escalation assistant: suggests a decision, its reasoning and a new rule (3.4).
Owner: Martín."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotImplementedYetError


@dataclass(frozen=True)
class Sugerencia:
    decision: str
    razonamiento: str
    regla_propuesta: str  # rule text, to be compiled like any other rule if accepted


async def sugerir(session: AsyncSession, instancia_id: int) -> Sugerencia:
    raise NotImplementedYetError("Asistente de escalado pendiente")
