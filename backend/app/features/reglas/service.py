import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.features.agentes import compilador
from app.features.decisiones import auditoria
from app.features.procesos.model import Simbolo, TipoDecision
from app.features.procesos.service import obtener as obtener_proceso
from app.features.reglas.model import Regla
from app.features.reglas.schemas import ReglaDetalle, ReglaIn, ReglaOut


def _out(regla: Regla) -> ReglaOut:
    return ReglaOut.model_validate(regla, from_attributes=True)


def _detalle(regla: Regla) -> ReglaDetalle:
    return ReglaDetalle.model_validate(regla, from_attributes=True)


async def _regla(session: AsyncSession, regla_id: int) -> Regla:
    regla = await session.get(Regla, regla_id)
    if regla is None:
        raise NotFoundError(f"Regla {regla_id} no existe")
    return regla


async def listar(session: AsyncSession, proceso_id: int, estado: str | None) -> list[ReglaOut]:
    consulta = select(Regla).where(Regla.proceso_id == proceso_id).order_by(Regla.id)
    if estado:
        consulta = consulta.where(Regla.estado == estado)
    return [_out(r) for r in await session.scalars(consulta)]


async def obtener(session: AsyncSession, regla_id: int) -> ReglaDetalle:
    return _detalle(await _regla(session, regla_id))


async def crear(session: AsyncSession, proceso_id: int, datos: ReglaIn) -> ReglaDetalle:
    await obtener_proceso(session, proceso_id)
    if not await session.get(TipoDecision, (proceso_id, datos.decision)):
        raise ConflictError(f"{datos.decision!r} no es un tipo de decisión de este proceso")
    regla = Regla(proceso_id=proceso_id, **datos.model_dump())
    session.add(regla)
    await session.commit()
    return _detalle(regla)


async def compilar(session: AsyncSession, regla_id: int) -> ReglaDetalle:
    regla = await _regla(session, regla_id)
    if regla.estado != "borrador":
        raise ConflictError(f"Solo se compila una regla en borrador (está {regla.estado})")
    simbolos = list(
        await session.scalars(select(Simbolo).where(Simbolo.proceso_id == regla.proceso_id))
    )
    resultado = await compilador.compilar(session, regla, simbolos)
    regla.codigo_a, regla.codigo_b = resultado.codigo_a, resultado.codigo_b
    regla.tests_a, regla.tests_b = resultado.tests_a, resultado.tests_b
    regla.informe = resultado.informe
    regla.hash = hashlib.sha256(
        "\0".join([regla.texto, regla.codigo_a, regla.codigo_b]).encode()
    ).hexdigest()
    await session.commit()
    return _detalle(regla)


async def _aplicar(session: AsyncSession, regla: Regla, propuestas: list[Regla]) -> None:
    """Check a rule change against every decision already taken, then adopt it.

    The past is never rewritten. What the change says about it is recorded as findings for
    the responsable to act on outside this system (P14). A change that would contradict a
    decision a person took is refused until they resolve it (P15).
    """
    impacto = await auditoria.comprobar(session, regla.proceso_id, propuestas)
    if impacto.hay_conflictos:
        contradichas = ", ".join(c.nombre for c in impacto.conflictos[:5])
        raise ConflictError(
            f"{len(impacto.conflictos)} decisiones tomadas por una persona cambiarían: "
            f"{contradichas}. Resuélvelas antes de aplicar esta regla"
        )
    await auditoria.registrar_hallazgos(session, regla.proceso_id, impacto, regla)


async def impacto(session: AsyncSession, regla_id: int) -> auditoria.Impacto:
    """What activating (or retiring) this rule would do, without doing it."""
    regla = await _regla(session, regla_id)
    propuestas = (
        await auditoria.propuesta_sin(session, regla)
        if regla.estado == "activa"
        else await auditoria.propuesta_con(session, regla)
    )
    return await auditoria.comprobar(session, regla.proceso_id, propuestas)


async def activar(session: AsyncSession, regla_id: int) -> ReglaDetalle:
    """A rule only enters the process when its validation found no discrepancy (P21)."""
    regla = await _regla(session, regla_id)
    if regla.estado != "borrador":
        raise ConflictError(f"Solo se activa una regla en borrador (está {regla.estado})")
    if not (regla.informe or {}).get("valida"):
        raise ConflictError("La regla tiene discrepancias sin resolver o no está compilada")
    await _aplicar(session, regla, await auditoria.propuesta_con(session, regla))
    regla.estado = "activa"
    regla.activada = datetime.now(UTC)
    await session.commit()
    return _detalle(regla)


async def retirar(session: AsyncSession, regla_id: int) -> ReglaDetalle:
    """Retiring a rule can change a past decision just as adding one can, so it goes
    through the same check."""
    regla = await _regla(session, regla_id)
    if regla.estado != "activa":
        raise ConflictError(f"Solo se retira una regla activa (está {regla.estado})")
    await _aplicar(session, regla, await auditoria.propuesta_sin(session, regla))
    regla.estado = "retirada"
    await session.commit()
    return _detalle(regla)
