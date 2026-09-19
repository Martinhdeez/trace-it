from fastapi import APIRouter

from app.core.database import Session
from app.features.sources import service
from app.features.sources.service import Diff, SourceDetail, SourceOut, SyncResult

router = APIRouter(prefix="/processes", tags=["sources"])


@router.get(
    "/{process_id}/sources",
    operation_id="listSources",
    summary="The current load of each source of truth",
)
async def list_sources(process_id: int, session: Session) -> list[SourceOut]:
    return await service.list_sources(session, process_id)


@router.get(
    "/{process_id}/sources/{name}",
    operation_id="getSource",
    summary="The current load of one source, rows included",
)
async def get_source(process_id: int, name: str, session: Session) -> SourceDetail:
    return await service.get_source(session, process_id, name)


@router.post(
    "/{process_id}/sources/{name}/sync",
    operation_id="syncSource",
    summary="Download an HTTP source (e.g. the ERP) into a new snapshot",
    description="Reads the source's configuration from the `sources.json` of the process's "
    "use case on every call. Writes one new snapshot only if the whole download succeeds; "
    "otherwise answers 502 and the previous snapshot stays current. Returns the counts, the "
    "retries and the diff against the previous snapshot.",
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
    config = await service.process_config(session, process_id, name)
    return await service.diff_latest(session, process_id, name, config.key)
