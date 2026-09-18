from fastapi import APIRouter, status

from app.core.database import Session
from app.features.processes import service
from app.features.processes.definition import Definition, LoadResult, load_definition
from app.features.processes.schemas import ProcessDetail, ProcessIn, ProcessOut, SymbolIO

router = APIRouter(prefix="/processes", tags=["processes"])


@router.get("", operation_id="listProcesses", summary="All processes")
async def list_processes(session: Session) -> list[ProcessOut]:
    return await service.list_all(session)


@router.post(
    "",
    operation_id="createProcess",
    status_code=status.HTTP_201_CREATED,
    summary="Create a process with its decision types and symbols",
    responses={409: {"description": "Name taken, or not exactly one default decision"}},
)
async def create_process(body: ProcessIn, session: Session) -> ProcessDetail:
    return await service.create(session, body)


@router.post(
    "/definition",
    operation_id="loadDefinition",
    summary="Create or update a whole process from its JSON definition (idempotent)",
    description="Same format as the files under `processes/`. New rules enter as drafts; "
    "rules whose text already exists, and users whose email exists, are left as they are.",
)
async def load(body: Definition, session: Session) -> LoadResult:
    return await load_definition(session, body)


@router.get("/{process_id}", operation_id="getProcess", summary="A process with its setup")
async def get_process(process_id: int, session: Session) -> ProcessDetail:
    return await service.get(session, process_id)


@router.put(
    "/{process_id}/symbols",
    operation_id="replaceSymbols",
    summary="Replace the symbol list of a process",
)
async def replace_symbols(process_id: int, body: list[SymbolIO], session: Session) -> ProcessDetail:
    return await service.replace_symbols(session, process_id, body)
