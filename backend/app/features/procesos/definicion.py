"""A whole process as data: one JSON file under `procesos/` (see `procesos/README.md`).

Loading is idempotent, so the same file can be loaded again after editing it.

A rule is text; the compiler turns it into code. A rule may also point at a file holding
code already written, which is how a process runs before any model is configured, and what
a compiled rule can be compared against.
"""

import hashlib
from pathlib import Path
from typing import Self

from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError
from app.features.agentes import sandbox
from app.features.procesos.model import Proceso, Simbolo, TipoDecision
from app.features.procesos.schemas import ProcesoDetalle, ProcesoIn
from app.features.procesos.service import obtener
from app.features.reglas.model import Regla
from app.features.reglas.schemas import ReglaIn
from app.features.usuarios.model import Usuario
from app.features.usuarios.schemas import UsuarioIn


class ReglaDefinicion(ReglaIn):
    # Path to a file with the rule's code, relative to the definition file. The file must
    # define `evaluar(instancia, fuentes, otras)` and pass the sandbox's static check.
    codigo: str | None = None


class Definicion(ProcesoIn):
    reglas: list[ReglaDefinicion] = []
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


def _regla(datos: ReglaDefinicion, proceso_id: int, base: Path | None) -> Regla:
    """A rule with code arrives ready to activate; one without it waits for the compiler."""
    regla = Regla(proceso_id=proceso_id, **datos.model_dump(exclude={"codigo"}))
    if datos.codigo:
        if base is None:
            # `codigo` names a file next to the definition, so it only means something when
            # the definition is being read from disk. Resolving a client-supplied path
            # server-side would hand out any file the backend can read.
            raise ConflictError(
                f"Rule {datos.texto[:40]!r} carries its code in a file ({datos.codigo}): "
                f"load it with `python -m app.cli cargar`, not over HTTP"
            )
        codigo = (base / datos.codigo).read_text(encoding="utf-8")
        sandbox.comprobar(codigo)
        regla.codigo_a = regla.codigo_b = codigo
        regla.hash = hashlib.sha256("\0".join([regla.texto, codigo, codigo]).encode()).hexdigest()
        # Nothing to disagree about: one text, one implementation, written by a person.
        regla.informe = {"valida": True, "origen": "escrita a mano", "fichero": datos.codigo}
    return regla


async def cargar_definicion(
    session: AsyncSession, datos: Definicion, base: Path | None = None
) -> Carga:
    """Create the process if missing (by name), upsert its decision types and symbols, add each
    rule as a draft unless the process already has one with the same text, and create missing
    users by email. Existing rules are never touched. `base` is the folder a rule's `codigo`
    path is resolved from; without it, a rule that names a code file is refused."""
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
    session.add_all(_regla(r, proceso.id, base) for r in reglas)

    emails = set(await session.scalars(select(Usuario.email)))
    usuarios = [u for u in datos.usuarios if u.email not in emails]
    session.add_all(Usuario(**u.model_dump()) for u in usuarios)

    await session.commit()
    return Carga(
        proceso=await obtener(session, proceso.id),
        reglas_nuevas=len(reglas),
        usuarios_nuevos=len(usuarios),
    )
