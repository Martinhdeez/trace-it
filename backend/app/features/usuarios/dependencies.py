from typing import Annotated

from fastapi import Depends, Header

from app.common.exceptions import NotFoundError
from app.core.database import Session
from app.features.usuarios.model import Usuario


# ponytail: identity by header, no password or token. Add real auth if the app leaves the
# hackathon; every endpoint already goes through this one dependency.
async def usuario_actual(session: Session, x_usuario_id: Annotated[int, Header()]) -> Usuario:
    usuario = await session.get(Usuario, x_usuario_id)
    if usuario is None:
        raise NotFoundError(f"Usuario {x_usuario_id} no existe")
    return usuario


UsuarioActual = Annotated[Usuario, Depends(usuario_actual)]
