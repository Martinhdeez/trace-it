from fastapi import APIRouter, status

from app.core.database import Session
from app.features.procesos import service
from app.features.procesos.definicion import Carga, Definicion, cargar_definicion
from app.features.procesos.schemas import ProcesoDetalle, ProcesoIn, ProcesoOut, SimboloIO

router = APIRouter(prefix="/procesos", tags=["procesos"])


@router.get("", operation_id="listProcesos", summary="All processes")
async def list_procesos(session: Session) -> list[ProcesoOut]:
    return await service.listar(session)


@router.post(
    "",
    operation_id="createProceso",
    status_code=status.HTTP_201_CREATED,
    summary="Create a process with its decision types and symbols",
    responses={409: {"description": "Name taken, or not exactly one default decision"}},
)
async def create_proceso(body: ProcesoIn, session: Session) -> ProcesoDetalle:
    return await service.crear(session, body)


@router.post(
    "/definicion",
    operation_id="loadDefinicion",
    summary="Create or update a whole process from its JSON definition (idempotent)",
    description="Same format as the files under `procesos/`. New rules enter as drafts; "
    "rules whose text already exists, and users whose email exists, are left as they are.",
)
async def load_definicion(body: Definicion, session: Session) -> Carga:
    return await cargar_definicion(session, body)


@router.get("/{proceso_id}", operation_id="getProceso", summary="A process with its setup")
async def get_proceso(proceso_id: int, session: Session) -> ProcesoDetalle:
    return await service.obtener(session, proceso_id)


@router.put(
    "/{proceso_id}/simbolos",
    operation_id="replaceSimbolos",
    summary="Replace the symbol list of a process",
)
async def replace_simbolos(
    proceso_id: int, body: list[SimboloIO], session: Session
) -> ProcesoDetalle:
    return await service.reemplazar_simbolos(session, proceso_id, body)
