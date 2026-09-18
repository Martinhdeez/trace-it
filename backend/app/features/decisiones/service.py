import json
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.features.agentes import sandbox
from app.features.decisiones.model import Decision
from app.features.decisiones.motor import decidir
from app.features.decisiones.schemas import (
    DecisionOut,
    EventoOut,
    InstanciaDetalle,
    InstanciaOut,
    ResolverIn,
    ResumenEjecucion,
)
from app.features.fuentes.model import Fuente
from app.features.ingesta.model import Instancia
from app.features.procesos.model import TipoDecision
from app.features.procesos.service import obtener as obtener_proceso
from app.features.reglas.model import Regla
from app.features.trazas import service as trazas
from app.features.trazas.model import Evento
from app.features.usuarios.model import Usuario


async def _instancia(session: AsyncSession, instancia_id: int) -> Instancia:
    instancia = await session.get(Instancia, instancia_id)
    if instancia is None:
        raise NotFoundError(f"Instancia {instancia_id} no existe")
    return instancia


@dataclass(frozen=True)
class Salidas:
    """What a process can conclude: the priorities, the outcome when no rule fires, and the
    outcomes that send the case to a person."""

    prioridades: dict[str, int]
    por_defecto: str
    humanas: list[str]

    @property
    def escalar(self) -> str:
        """Where the engine puts a case it could not decide: the highest-priority outcome
        that needs a person."""
        return max(self.humanas, key=lambda nombre: self.prioridades[nombre])


async def _salidas(session: AsyncSession, proceso_id: int) -> Salidas:
    tipos = list(
        await session.scalars(select(TipoDecision).where(TipoDecision.proceso_id == proceso_id))
    )
    if not tipos:
        raise ConflictError("El proceso no tiene tipos de decisión")
    por_defecto = next((t.nombre for t in tipos if t.por_defecto), None)
    if por_defecto is None:
        raise ConflictError("El proceso no tiene un tipo de decisión por defecto")
    humanas = [t.nombre for t in tipos if t.requiere_persona]
    if not humanas:
        raise ConflictError(
            "El proceso no tiene ningún tipo de decisión con `requiere_persona`: "
            "el motor no tendría dónde dejar un caso que no puede decidir"
        )
    return Salidas({t.nombre: t.prioridad for t in tipos}, por_defecto, humanas)


async def _fuentes_vigentes(
    session: AsyncSession, proceso_id: int
) -> dict[str, list[dict[str, Any]]]:
    """The latest load of each source of truth. Every load is kept; only the last one is used."""
    cargas = await session.scalars(
        select(Fuente).where(Fuente.proceso_id == proceso_id).order_by(Fuente.id)
    )
    return {carga.nombre: carga.filas for carga in cargas}


async def _instancias(session: AsyncSession, proceso_id: int) -> list[Instancia]:
    return list(
        await session.scalars(
            select(Instancia).where(Instancia.proceso_id == proceso_id).order_by(Instancia.id)
        )
    )


async def _ultimas_decisiones(
    session: AsyncSession, instancias: list[Instancia]
) -> dict[int, Decision]:
    """An instance's current decision is its latest row (the history only ever grows)."""
    if not instancias:
        return {}
    filas = await session.scalars(
        select(Decision)
        .where(Decision.instancia_id.in_([i.id for i in instancias]))
        .order_by(Decision.id)
    )
    return {fila.instancia_id: fila for fila in filas}


def _out(instancia: Instancia, decision: Decision | None) -> InstanciaOut:
    return InstanciaOut(
        id=instancia.id,
        nombre=instancia.nombre,
        estado=instancia.estado,
        decision=decision.decision if decision else None,
    )


async def ejecutar(session: AsyncSession, proceso_id: int) -> ResumenEjecucion:
    """Decide every PENDIENTE instance that already has its symbols.

    Runs against the rules active now and the latest load of each source. A rule never
    reads the clock: anything like a cut-off date is a row in a source of truth.
    """
    await obtener_proceso(session, proceso_id)
    salidas = await _salidas(session, proceso_id)
    reglas = list(
        await session.scalars(
            select(Regla)
            .where(Regla.proceso_id == proceso_id, Regla.estado == "activa")
            .order_by(Regla.id)
        )
    )
    fuentes = await _fuentes_vigentes(session, proceso_id)
    instancias = await _instancias(session, proceso_id)
    # Each entry of `otras` carries `_instancia` so a rule can name the duplicate it found.
    simbolos = {
        i.id: {**i.simbolos, "_instancia": i.nombre} for i in instancias if i.simbolos is not None
    }

    cuenta: Counter[str] = Counter()
    for instancia in instancias:
        if instancia.estado != "PENDIENTE" or instancia.simbolos is None:
            continue
        otras = [s for iid, s in simbolos.items() if iid != instancia.id]
        veredicto = decidir(
            reglas,
            salidas.prioridades,
            salidas.por_defecto,
            salidas.escalar,
            instancia.simbolos,
            fuentes,
            otras,
            sandbox.ejecutar,
        )
        session.add(
            Decision(
                instancia_id=instancia.id,
                decision=veredicto.decision,
                resultados=[asdict(r) for r in veredicto.resultados],
                reglas_hash=veredicto.reglas_hash,
                autor="motor",
                motivo=veredicto.motivo or None,
            )
        )
        instancia.estado = "DECIDIDA"
        trazas.registrar(
            session,
            "decision",
            instancia_id=instancia.id,
            datos={"decision": veredicto.decision, "reglas_hash": veredicto.reglas_hash},
        )
        cuenta[veredicto.decision] += 1

    await session.commit()
    return ResumenEjecucion(decididas=sum(cuenta.values()), por_decision=dict(cuenta))


async def listar_instancias(
    session: AsyncSession, proceso_id: int, estado: str | None
) -> list[InstanciaOut]:
    await obtener_proceso(session, proceso_id)
    instancias = await _instancias(session, proceso_id)
    ultimas = await _ultimas_decisiones(session, instancias)
    return [_out(i, ultimas.get(i.id)) for i in instancias if estado is None or i.estado == estado]


async def cola(session: AsyncSession, proceso_id: int, tipo: str | None) -> list[InstanciaOut]:
    """Everything waiting for a person: by default, every outcome marked `requiere_persona`."""
    await obtener_proceso(session, proceso_id)
    salidas = await _salidas(session, proceso_id)
    buscados = {tipo} if tipo else set(salidas.humanas)
    instancias = await _instancias(session, proceso_id)
    ultimas = await _ultimas_decisiones(session, instancias)
    return [
        _out(i, ultimas[i.id])
        for i in instancias
        if i.id in ultimas and ultimas[i.id].decision in buscados
    ]


async def obtener_instancia(session: AsyncSession, instancia_id: int) -> InstanciaDetalle:
    instancia = await _instancia(session, instancia_id)
    decisiones = list(
        await session.scalars(
            select(Decision).where(Decision.instancia_id == instancia_id).order_by(Decision.id)
        )
    )
    eventos = await session.scalars(
        select(Evento).where(Evento.instancia_id == instancia_id).order_by(Evento.id)
    )
    return InstanciaDetalle(
        **_out(instancia, decisiones[-1] if decisiones else None).model_dump(),
        fichero_hash=instancia.fichero_hash,
        simbolos=instancia.simbolos,
        decisiones=[DecisionOut.model_validate(d, from_attributes=True) for d in decisiones],
        eventos=[EventoOut.model_validate(e, from_attributes=True) for e in eventos],
    )


async def resolver(
    session: AsyncSession, instancia_id: int, datos: ResolverIn, usuario: Usuario
) -> InstanciaDetalle:
    """A person's decision is a new row, never an edit of the engine's (P14)."""
    instancia = await _instancia(session, instancia_id)
    salidas = await _salidas(session, instancia.proceso_id)
    if datos.decision not in salidas.prioridades:
        raise ConflictError(f"{datos.decision!r} no es un tipo de decisión de este proceso")

    ultimas = await _ultimas_decisiones(session, [instancia])
    anterior = ultimas.get(instancia.id)
    session.add(
        Decision(
            instancia_id=instancia.id,
            decision=datos.decision,
            resultados=[],  # a person decides on the evidence, not by running the rules
            reglas_hash=anterior.reglas_hash if anterior else "",
            autor=usuario.nombre,
            motivo=datos.motivo,
        )
    )
    instancia.estado = "DECIDIDA"
    trazas.registrar(
        session,
        "resolucion",
        instancia_id=instancia.id,
        datos={"decision": datos.decision, "autor": usuario.nombre},
    )
    await session.commit()
    return await obtener_instancia(session, instancia_id)


async def exportar(session: AsyncSession, proceso_id: int) -> str:
    """`outcomes.jsonl` for the challenge: one line per instance, nothing else.

    `file_id` is the filename exactly as it was supplied, accents included.
    """
    await obtener_proceso(session, proceso_id)
    instancias = await _instancias(session, proceso_id)
    ultimas = await _ultimas_decisiones(session, instancias)
    sin_decidir = [i.nombre for i in instancias if i.id not in ultimas]
    if sin_decidir:
        raise ConflictError(
            f"{len(sin_decidir)} instancias sin decidir: {', '.join(sin_decidir[:5])}"
        )
    return "\n".join(
        json.dumps(
            {"file_id": i.nombre, "result": ultimas[i.id].decision},
            ensure_ascii=False,
        )
        for i in instancias
    )
