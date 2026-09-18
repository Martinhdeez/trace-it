from typing import Literal

from fastapi import APIRouter, status

from app.common.exceptions import PermissionDeniedError
from app.core.database import Session
from app.features.decisiones.schemas import ImpactoOut
from app.features.reglas import service
from app.features.reglas.schemas import ReglaDetalle, ReglaIn, ReglaOut
from app.features.usuarios.dependencies import UsuarioActual

router = APIRouter(tags=["reglas"])

Estado = Literal["borrador", "rechazada", "activa", "retirada"]


def _solo_responsable(usuario: UsuarioActual) -> None:
    if usuario.rol != "responsable":
        raise PermissionDeniedError("Solo un responsable puede activar o retirar reglas")


@router.get("/procesos/{proceso_id}/reglas", operation_id="listReglas", summary="Rules")
async def list_reglas(
    proceso_id: int, session: Session, estado: Estado | None = None
) -> list[ReglaOut]:
    return await service.listar(session, proceso_id, estado)


@router.post(
    "/procesos/{proceso_id}/reglas",
    operation_id="createRegla",
    status_code=status.HTTP_201_CREATED,
    summary="Add a rule as text. It starts as a draft",
)
async def create_regla(proceso_id: int, body: ReglaIn, session: Session) -> ReglaDetalle:
    return await service.crear(session, proceso_id, body)


@router.get("/reglas/{regla_id}", operation_id="getRegla", summary="A rule with its code")
async def get_regla(regla_id: int, session: Session) -> ReglaDetalle:
    return await service.obtener(session, regla_id)


@router.post(
    "/reglas/{regla_id}/compilar",
    operation_id="compileRegla",
    summary="Generate code + tests with two agents and validate them",
)
async def compile_regla(regla_id: int, session: Session) -> ReglaDetalle:
    return await service.compilar(session, regla_id)


@router.get(
    "/reglas/{regla_id}/impacto",
    operation_id="getImpacto",
    summary="What activating (or retiring) this rule would change, without doing it",
)
async def get_impacto(regla_id: int, session: Session) -> ImpactoOut:
    return ImpactoOut.model_validate(await service.impacto(session, regla_id), from_attributes=True)


@router.post(
    "/reglas/{regla_id}/activar",
    operation_id="activateRegla",
    summary="Activate a validated draft",
    responses={
        409: {
            "description": "Not compiled, discrepancies unresolved, or it would "
            "contradict a decision a person took"
        }
    },
)
async def activate_regla(regla_id: int, session: Session, usuario: UsuarioActual) -> ReglaDetalle:
    _solo_responsable(usuario)
    return await service.activar(session, regla_id)


@router.post(
    "/reglas/{regla_id}/retirar",
    operation_id="retireRegla",
    summary="Retire a rule. Checked against past decisions exactly like activating one",
    responses={409: {"description": "It would contradict a decision a person took"}},
)
async def retire_regla(regla_id: int, session: Session, usuario: UsuarioActual) -> ReglaDetalle:
    _solo_responsable(usuario)
    return await service.retirar(session, regla_id)
