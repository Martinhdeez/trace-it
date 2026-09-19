"""Rows tests insert directly, bypassing the loaders."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.processes.model import Process
from app.features.use_cases import service as use_cases


async def process(session: AsyncSession, name: str, description: str = "") -> Process:
    """A process with a use case of its own (same name), as a definition without
    `use_case` gets."""
    use_case = await use_cases.ensure(session, name, description)
    row = Process(name=name, use_case_id=use_case.id)
    session.add(row)
    await session.flush()
    return row
