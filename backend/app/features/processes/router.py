from fastapi import APIRouter

from app.core.database import Session
from app.features.processes import service
from app.features.processes.definition import Definition, LoadResult, load_definition
from app.features.processes.schemas import ProcessDetail, ProcessOut
from app.features.users.dependencies import Manager

router = APIRouter(prefix="/processes", tags=["processes"])


@router.get("", operation_id="listProcesses", summary="All processes")
async def list_processes(session: Session) -> list[ProcessOut]:
    return await service.list_all(session)


@router.post(
    "/definition",
    operation_id="loadDefinition",
    summary="Create or update a whole process from its JSON definition (idempotent)",
    description="Same format as the files under `processes/`. New rules enter as drafts; "
    "rules whose text already exists, and users whose email exists, are left as they are.",
)
async def load(body: Definition, session: Session, _: Manager) -> LoadResult:
    return await load_definition(session, body)


@router.get("/{process_id}", operation_id="getProcess", summary="A process with its setup")
async def get_process(process_id: int, session: Session) -> ProcessDetail:
    return await service.get(session, process_id)
