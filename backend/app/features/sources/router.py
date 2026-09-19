from fastapi import APIRouter

from app.common.exceptions import NotFoundError
from app.core.database import Session
from app.features.processes.model import Process
from app.features.sources import service
from app.features.sources.service import Diff, SyncResult

router = APIRouter(prefix="/processes", tags=["sources"])


@router.post(
    "/{process_id}/sources/{name}/sync",
    operation_id="syncSource",
    summary="Download an HTTP source (e.g. the ERP) into a new snapshot",
    description="Reads the source's configuration from the process pack's `sources.json` on "
    "every call. Writes one new snapshot only if the whole download succeeds; otherwise "
    "answers 502 and the previous snapshot stays current. Returns the counts, the retries "
    "and the diff against the previous snapshot.",
    responses={502: {"description": "The source failed; nothing was stored"}},
)
async def sync_source(process_id: int, name: str, session: Session) -> SyncResult:
    return await service.sync_process(session, process_id, name)


@router.get(
    "/{process_id}/sources/{name}/diff",
    operation_id="diffSource",
    summary="The latest snapshot of a source against the one before it",
)
async def diff_source(process_id: int, name: str, session: Session) -> Diff:
    process = await session.get(Process, process_id)
    if process is None:
        raise NotFoundError(f"Process {process_id} does not exist")
    config = service.load_config(service.pack_sources_file(service.find_pack(process.name)), name)
    return await service.diff_latest(session, process_id, name, config.key)
