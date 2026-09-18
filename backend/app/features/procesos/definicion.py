"""A whole process as data: one JSON file under `procesos/` (see `procesos/README.md`).

Loading is idempotent, so the same file can be loaded again after editing it.
"""

from typing import Self

from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.procesos.model import Proceso, Simbolo, TipoDecision
from app.features.procesos.schemas import ProcesoDetalle, ProcesoIn
from app.features.procesos.service import obtener
from app.features.reglas.model import Regla
from app.features.reglas.schemas import ReglaIn
from app.features.usuarios.model import Usuario
from app.features.usuarios.schemas import UsuarioIn


class Definicion(ProcesoIn):
    reglas: list[ReglaIn] = []
    usuarios: list[UsuarioIn] = []

    @model_validator(mode="after")
    def _coherente(self) -> Self:
        tipos = {t.nombre for t in self.tipos_decision}
        if len(tipos) != len(self.tipos_decision):
            raise ValueError("Hay tipos de decisión repetidos")
        if sum(t.por_defecto for t in self.tipos_decision) != 1:
            raise ValueError("Debe haber exactamente un tipo de decisión por defecto")
        if any(t.por_defecto and t.requiere_persona for t in self.tipos_decision):
            raise ValueError("El tipo por defecto no puede requerir persona")
        if len({s.nombre for s in self.simbolos}) != len(self.simbolos):
            raise ValueError("Hay símbolos repetidos")
        if len({r.texto for r in self.reglas}) != len(self.reglas):
            raise ValueError("Hay reglas con el mismo texto")
        for r in self.reglas:
            if r.decision not in tipos:
                raise ValueError(f"{r.decision!r} no es un tipo de decisión: {r.texto[:60]}")
        return self


class Carga(BaseModel):
    proceso: ProcesoDetalle
    reglas_nuevas: int
    usuarios_nuevos: int


async def cargar_definicion(session: AsyncSession, datos: Definicion) -> Carga:
    """Create the process if missing (by name), upsert its decision types and symbols, add each
    rule as a draft unless the process already has one with the same text, and create missing
    users by email. Existing rules are never touched."""
    proceso = await session.scalar(select(Proceso).where(Proceso.nombre == datos.nombre))
    if proceso is None:
        proceso = Proceso(nombre=datos.nombre)
        session.add(proceso)
    proceso.descripcion = datos.descripcion
    await session.flush()

    for t in datos.tipos_decision:
        await session.merge(TipoDecision(proceso_id=proceso.id, **t.model_dump()))
    for s in datos.simbolos:
        await session.merge(Simbolo(proceso_id=proceso.id, **s.model_dump()))

    textos = set(await session.scalars(select(Regla.texto).where(Regla.proceso_id == proceso.id)))
    reglas = [r for r in datos.reglas if r.texto not in textos]
    session.add_all(Regla(proceso_id=proceso.id, **r.model_dump()) for r in reglas)

    emails = set(await session.scalars(select(Usuario.email)))
    usuarios = [u for u in datos.usuarios if u.email not in emails]
    session.add_all(Usuario(**u.model_dump()) for u in usuarios)

    await session.commit()
    return Carga(
        proceso=await obtener(session, proceso.id),
        reglas_nuevas=len(reglas),
        usuarios_nuevos=len(usuarios),
    )
