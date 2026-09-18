from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core.database import Session
from app.features.decisiones import service
from app.features.decisiones.schemas import (
    HallazgoOut,
    InstanciaDetalle,
    InstanciaOut,
    ResolverIn,
    ResumenEjecucion,
)
from app.features.usuarios.dependencies import UsuarioActual

router = APIRouter(tags=["decisiones"])


@router.post(
    "/procesos/{proceso_id}/ejecutar",
    operation_id="runProceso",
    summary="Decide every pending instance with the active rules",
)
async def run_proceso(proceso_id: int, session: Session) -> ResumenEjecucion:
    return await service.ejecutar(session, proceso_id)


@router.get("/procesos/{proceso_id}/instancias", operation_id="listInstancias", summary="Instances")
async def list_instancias(
    proceso_id: int, session: Session, estado: str | None = None
) -> list[InstanciaOut]:
    return await service.listar_instancias(session, proceso_id, estado)


@router.get(
    "/procesos/{proceso_id}/cola",
    operation_id="getCola",
    summary="Instances waiting for a person (by default, the escalated ones)",
)
async def get_cola(
    proceso_id: int, session: Session, tipo: str | None = None
) -> list[InstanciaOut]:
    return await service.cola(session, proceso_id, tipo)


@router.get(
    "/instancias/{instancia_id}",
    operation_id="getInstancia",
    summary="An instance with its symbols, decision history and trace",
)
async def get_instancia(instancia_id: int, session: Session) -> InstanciaDetalle:
    return await service.obtener_instancia(session, instancia_id)


@router.post(
    "/instancias/{instancia_id}/resolver",
    operation_id="resolveInstancia",
    summary="A person decides. Adds a decision, never edits the engine's",
    responses={409: {"description": "Not a decision type of this process"}},
)
async def resolve_instancia(
    instancia_id: int, body: ResolverIn, session: Session, usuario: UsuarioActual
) -> InstanciaDetalle:
    return await service.resolver(session, instancia_id, body, usuario)


@router.get(
    "/procesos/{proceso_id}/exportar",
    operation_id="exportOutcomes",
    summary="outcomes.jsonl, one line per instance",
    response_class=PlainTextResponse,
    responses={
        200: {"content": {"application/x-ndjson": {}}},
        409: {"description": "Some instance has no decision yet"},
    },
)
async def export_outcomes(proceso_id: int, session: Session) -> PlainTextResponse:
    return PlainTextResponse(
        await service.exportar(session, proceso_id), media_type="application/x-ndjson"
    )


@router.get(
    "/procesos/{proceso_id}/hallazgos",
    operation_id="listHallazgos",
    summary="Past decisions a later rule says were wrong",
)
async def list_hallazgos(proceso_id: int, session: Session) -> list[HallazgoOut]:
    return await service.listar_hallazgos(session, proceso_id)
