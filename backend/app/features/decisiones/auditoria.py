"""What a change to the rules would do to the decisions already taken.

Runs the proposed rule set over the symbols already stored, never re-reading a PDF or the
ERP: the check is fast, free and always gives the same answer. It never changes a past
decision (P14). Adding a rule and retiring one are the same question, asked of a different
proposed set.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.agentes import sandbox
from app.features.decisiones.model import Hallazgo
from app.features.decisiones.motor import decidir
from app.features.decisiones.service import (
    _fuentes_vigentes,
    _instancias,
    _salidas,
    _ultimas_decisiones,
)
from app.features.reglas.model import Regla


@dataclass(frozen=True)
class Cambio:
    instancia_id: int
    nombre: str
    antes: str
    despues: str
    autor_anterior: str
    motivo: str
    decision_id: int


@dataclass(frozen=True)
class Impacto:
    """Three groups, because they need three different answers from the responsable."""

    sin_cambio: int
    cambios: list[Cambio]  # the engine decided it, and would now decide otherwise
    conflictos: list[Cambio]  # a person decided it, and the rules would now contradict them

    @property
    def hay_conflictos(self) -> bool:
        return bool(self.conflictos)


async def reglas_activas(session: AsyncSession, proceso_id: int) -> list[Regla]:
    return list(
        await session.scalars(
            select(Regla)
            .where(Regla.proceso_id == proceso_id, Regla.estado == "activa")
            .order_by(Regla.id)
        )
    )


async def propuesta_con(session: AsyncSession, regla: Regla) -> list[Regla]:
    """The rule set as it would be if `regla` were activated."""
    activas = await reglas_activas(session, regla.proceso_id)
    return sorted([*activas, regla], key=lambda r: r.id)


async def propuesta_sin(session: AsyncSession, regla: Regla) -> list[Regla]:
    """The rule set as it would be if `regla` were retired. Retiring a rule can change a
    past decision exactly as adding one can, so it is checked the same way."""
    activas = await reglas_activas(session, regla.proceso_id)
    return [r for r in activas if r.id != regla.id]


async def comprobar(session: AsyncSession, proceso_id: int, propuestas: list[Regla]) -> Impacto:
    """Decide every already-decided instance again under `propuestas` and compare."""
    salidas = await _salidas(session, proceso_id)
    fuentes = await _fuentes_vigentes(session, proceso_id)
    instancias = await _instancias(session, proceso_id)
    ultimas = await _ultimas_decisiones(session, instancias)
    simbolos = {
        i.id: {**i.simbolos, "_instancia": i.nombre} for i in instancias if i.simbolos is not None
    }

    sin_cambio = 0
    cambios: list[Cambio] = []
    conflictos: list[Cambio] = []
    for instancia in instancias:
        anterior = ultimas.get(instancia.id)
        if anterior is None or instancia.simbolos is None:
            continue  # nothing decided yet, or nothing to decide it with
        veredicto = decidir(
            propuestas,
            salidas.prioridades,
            salidas.por_defecto,
            salidas.escalar,
            instancia.simbolos,
            fuentes,
            [s for iid, s in simbolos.items() if iid != instancia.id],
            sandbox.ejecutar,
        )
        if veredicto.decision == anterior.decision:
            sin_cambio += 1
            continue
        cambio = Cambio(
            instancia_id=instancia.id,
            nombre=instancia.nombre,
            antes=anterior.decision,
            despues=veredicto.decision,
            autor_anterior=anterior.autor,
            motivo=veredicto.motivo,
            decision_id=anterior.id,
        )
        # A person's decision is not overruled by a rule, and a rule is not silently
        # dropped because a person disagreed: the responsable resolves it (P15).
        (conflictos if anterior.autor != "motor" else cambios).append(cambio)

    return Impacto(sin_cambio=sin_cambio, cambios=cambios, conflictos=conflictos)


async def registrar_hallazgos(
    session: AsyncSession, proceso_id: int, impacto: Impacto, regla: Regla
) -> list[Hallazgo]:
    """Record the past decisions the adopted change says were wrong.

    Only for outcomes nobody was asked to look at: an instance that sat in the human queue
    harmed nothing, whereas one the engine concluded by itself was acted on. The finding is
    a notice, never a correction — the past is not edited, and what to do about it (claim
    the money back, pay what is owed) happens outside this system (P14).
    """
    salidas = await _salidas(session, proceso_id)
    hallazgos = [
        Hallazgo(
            decision_id=cambio.decision_id,
            regla_id=regla.id,
            tipo="decision_distinta",
            detalle=f"{cambio.antes} -> {cambio.despues}: {cambio.motivo}",
        )
        for cambio in impacto.cambios
        if cambio.antes not in salidas.humanas
    ]
    session.add_all(hallazgos)
    return hallazgos
