from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.features.processes.model import DecisionType, Process, Symbol
from app.features.processes.schemas import (
    DecisionTypeIO,
    ProcessDetail,
    ProcessIn,
    ProcessOut,
    SymbolIO,
)


async def list_all(session: AsyncSession) -> list[ProcessOut]:
    processes = await session.scalars(select(Process).order_by(Process.id))
    return [ProcessOut(id=p.id, name=p.name, description=p.description) for p in processes]


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
        decision_types=[
            DecisionTypeIO(
                name=t.name,
                priority=t.priority,
                is_default=t.is_default,
                requires_human=t.requires_human,
            )
            for t in types
        ],
        symbols=[SymbolIO(name=s.name, type=s.type, description=s.description) for s in symbols],
    )


async def create(session: AsyncSession, data: ProcessIn) -> ProcessDetail:
    if sum(t.is_default for t in data.decision_types) != 1:
        raise ConflictError("There must be exactly one default decision type")
    if any(t.is_default and t.requires_human for t in data.decision_types):
        raise ConflictError("The default decision type cannot require a human")
    if await session.scalar(select(Process).where(Process.name == data.name)):
        raise ConflictError(f"A process named {data.name!r} already exists")
    process = Process(name=data.name, description=data.description)
    session.add(process)
    await session.flush()
    session.add_all(
        DecisionType(process_id=process.id, **t.model_dump()) for t in data.decision_types
    )
    session.add_all(Symbol(process_id=process.id, **s.model_dump()) for s in data.symbols)
    await session.commit()
    return await get(session, process.id)


async def replace_symbols(
    session: AsyncSession, process_id: int, symbols: list[SymbolIO]
) -> ProcessDetail:
    await get(session, process_id)
    await session.execute(delete(Symbol).where(Symbol.process_id == process_id))
    session.add_all(Symbol(process_id=process_id, **s.model_dump()) for s in symbols)
    await session.commit()
    return await get(session, process_id)
