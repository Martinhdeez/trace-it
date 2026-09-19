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


async def list_all(session: AsyncSession) -> list[ProcessOut]:
    processes = await session.scalars(select(Process).order_by(Process.id))
    return [ProcessOut.model_validate(p, from_attributes=True) for p in processes]


async def get(session: AsyncSession, process_id: int) -> ProcessDetail:
    process = await session.get(Process, process_id)
    if process is None:
        raise NotFoundError(f"Process {process_id} does not exist")
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
        description=process.description,
        decision_types=[DecisionTypeIO.model_validate(t, from_attributes=True) for t in types],
        symbols=[SymbolIO.model_validate(s, from_attributes=True) for s in symbols],
    )
