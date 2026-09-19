from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.features.processes.model import DecisionType, Process, Symbol
from app.features.processes.schemas import (
    DecisionTypeIO,
    ProcessDetail,
    ProcessOut,
    SymbolIO,
)
from app.features.use_cases.model import UseCase


async def list_all(session: AsyncSession) -> list[ProcessOut]:
    ids = await session.scalars(select(Process.id).order_by(Process.id))
    return [ProcessOut.model_validate((await get(session, key)).model_dump()) for key in ids]


async def get(session: AsyncSession, process_id: int) -> ProcessDetail:
    process = await session.get(Process, process_id)
    if process is None:
        raise NotFoundError(f"Process {process_id} does not exist")
    if process.active_version_id:
        from app.features.versions.model import ProcessVersion

        version = await session.get(ProcessVersion, process.active_version_id)
        return ProcessDetail.model_validate(
            {**version.snapshot["process"], "active_version_id": version.id}
        )
    types = await session.scalars(
        select(DecisionType)
        .where(DecisionType.process_id == process_id)
        .order_by(DecisionType.priority.desc())
    )
    symbols = await session.scalars(
        select(Symbol).where(Symbol.process_id == process_id).order_by(Symbol.name)
    )
    return ProcessDetail(
        id=process.id,
        name=process.name,
        use_case_id=process.use_case_id,
        description=(await session.get(UseCase, process.use_case_id)).description,
        decision_review=process.decision_review,
        decision_types=[DecisionTypeIO.model_validate(t, from_attributes=True) for t in types],
        symbols=[SymbolIO.model_validate(s, from_attributes=True) for s in symbols],
    )
