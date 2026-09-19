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


async def publish_fixture(session: AsyncSession, process_id: int):
    """Install seeded/fake artifacts as a published fixture, not a production approval path."""
    from app.features.versions import configuration, service
    from app.features.versions.model import ProcessDraft

    row = await service.lock(session, process_id)
    snapshot = await configuration.workspace(session, process_id)
    # Legacy fake fixtures use injected readers and scripted role models.
    # Execution-configuration tests publish through the real draft endpoints.
    snapshot.pop("execution", None)
    # Scripted tests resolve their role models through llm.model_for.
    for config in snapshot["agents"].values():
        config["settings"]["model"] = None
    result = await service.publish_snapshot(
        session, row, snapshot, "fixture manager", "Test setup", {}
    )
    draft = await session.get(ProcessDraft, process_id)
    if draft:
        await session.delete(draft)
    await session.commit()
    return result
