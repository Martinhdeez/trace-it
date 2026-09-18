from fastapi import APIRouter, status
from sqlalchemy import select

from app.common.exceptions import ConflictError, NotFoundError
from app.core.database import Session
from app.features.usuarios.dependencies import UsuarioActual
from app.features.usuarios.model import Usuario
from app.features.usuarios.schemas import LoginIn, UsuarioIn, UsuarioOut

router = APIRouter(tags=["usuarios"])


def _out(usuario: Usuario) -> UsuarioOut:
    return UsuarioOut(id=usuario.id, nombre=usuario.nombre, email=usuario.email, rol=usuario.rol)


@router.get("/usuarios", operation_id="listUsuarios", summary="All users")
async def list_usuarios(session: Session) -> list[UsuarioOut]:
    return [_out(u) for u in await session.scalars(select(Usuario).order_by(Usuario.id))]


@router.post(
    "/usuarios",
    operation_id="createUsuario",
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
    responses={409: {"description": "Email already in use"}},
)
async def create_usuario(body: UsuarioIn, session: Session) -> UsuarioOut:
    if await session.scalar(select(Usuario).where(Usuario.email == body.email)):
        raise ConflictError(f"Ya existe un usuario con email {body.email}")
    usuario = Usuario(**body.model_dump())
    session.add(usuario)
    await session.commit()
    return _out(usuario)


@router.post(
    "/login",
    operation_id="login",
    summary="Find the user by email. Send its id as `X-Usuario-Id` afterwards",
)
async def login(body: LoginIn, session: Session) -> UsuarioOut:
    usuario = await session.scalar(select(Usuario).where(Usuario.email == body.email))
    if usuario is None:
        raise NotFoundError(f"No hay usuario con email {body.email}")
    return _out(usuario)


@router.get("/yo", operation_id="me", summary="The current user")
async def yo(usuario: UsuarioActual) -> UsuarioOut:
    return _out(usuario)
