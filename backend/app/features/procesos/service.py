from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.features.procesos.model import Proceso, Simbolo, TipoDecision
from app.features.procesos.schemas import (
    ProcesoDetalle,
    ProcesoIn,
    ProcesoOut,
    SimboloIO,
    TipoDecisionIO,
)


async def listar(session: AsyncSession) -> list[ProcesoOut]:
    procesos = await session.scalars(select(Proceso).order_by(Proceso.id))
    return [ProcesoOut(id=p.id, nombre=p.nombre, descripcion=p.descripcion) for p in procesos]


async def obtener(session: AsyncSession, proceso_id: int) -> ProcesoDetalle:
    proceso = await session.get(Proceso, proceso_id)
    if proceso is None:
        raise NotFoundError(f"Proceso {proceso_id} no existe")
    tipos = await session.scalars(
        select(TipoDecision)
        .where(TipoDecision.proceso_id == proceso_id)
        .order_by(TipoDecision.prioridad.desc())
    )
    simbolos = await session.scalars(
        select(Simbolo).where(Simbolo.proceso_id == proceso_id).order_by(Simbolo.nombre)
    )
    return ProcesoDetalle(
        id=proceso.id,
        nombre=proceso.nombre,
        descripcion=proceso.descripcion,
        tipos_decision=[
            TipoDecisionIO(nombre=t.nombre, prioridad=t.prioridad, por_defecto=t.por_defecto)
            for t in tipos
        ],
        simbolos=[
            SimboloIO(nombre=s.nombre, tipo=s.tipo, descripcion=s.descripcion) for s in simbolos
        ],
    )


async def crear(session: AsyncSession, datos: ProcesoIn) -> ProcesoDetalle:
    if sum(t.por_defecto for t in datos.tipos_decision) != 1:
        raise ConflictError("Debe haber exactamente un tipo de decisión por defecto")
    if await session.scalar(select(Proceso).where(Proceso.nombre == datos.nombre)):
        raise ConflictError(f"Ya existe un proceso llamado {datos.nombre!r}")
    proceso = Proceso(nombre=datos.nombre, descripcion=datos.descripcion)
    session.add(proceso)
    await session.flush()
    session.add_all(
        TipoDecision(proceso_id=proceso.id, **t.model_dump()) for t in datos.tipos_decision
    )
    session.add_all(Simbolo(proceso_id=proceso.id, **s.model_dump()) for s in datos.simbolos)
    await session.commit()
    return await obtener(session, proceso.id)


async def reemplazar_simbolos(
    session: AsyncSession, proceso_id: int, simbolos: list[SimboloIO]
) -> ProcesoDetalle:
    await obtener(session, proceso_id)
    await session.execute(delete(Simbolo).where(Simbolo.proceso_id == proceso_id))
    session.add_all(Simbolo(proceso_id=proceso_id, **s.model_dump()) for s in simbolos)
    await session.commit()
    return await obtener(session, proceso_id)
