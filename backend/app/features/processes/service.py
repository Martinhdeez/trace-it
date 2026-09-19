from sqlalchemy import delete as sql_delete
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
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


async def delete_process(session: AsyncSession, process_id: int) -> None:
    """Remove a process that has not entered the append-only runtime history."""
    from app.features.ingestion.model import Instance
    from app.features.learning.model import Analysis
    from app.features.mail_ingestion.model import (
        MailAccount,
        MailActivity,
        MailActivityRead,
        MailMessage,
        RunOperation,
    )
    from app.features.processes.model import DiscoverySession
    from app.features.proposals.model import ManagerProposal
    from app.features.rules.model import NormRule, Rule
    from app.features.sources.model import Source
    from app.features.versions.model import ProcessDraft, ProcessVersion

    process = await session.scalar(
        select(Process)
        .where(Process.id == process_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if process is None:
        raise NotFoundError(f"Process {process_id} does not exist")

    history = (
        ("cases", select(Instance.id).where(Instance.process_id == process_id)),
        ("source loads", select(Source.id).where(Source.process_id == process_id)),
        (
            "published versions",
            select(ProcessVersion.id).where(ProcessVersion.process_id == process_id),
        ),
        (
            "agent proposals",
            select(ManagerProposal.id).where(ManagerProposal.process_id == process_id),
        ),
        ("learning analyses", select(Analysis.id).where(Analysis.process_id == process_id)),
        (
            "discovery revisions",
            select(DiscoverySession.id).where(
                or_(
                    DiscoverySession.process_id == process_id,
                    DiscoverySession.published_process_id == process_id,
                )
            ),
        ),
        ("run history", select(RunOperation.id).where(RunOperation.process_id == process_id)),
        ("mail history", select(MailActivity.id).where(MailActivity.process_id == process_id)),
    )
    for label, statement in history:
        if await session.scalar(statement.limit(1)) is not None:
            raise ConflictError(f"Cannot delete a process with {label}; its history is append-only")

    account_ids = list(
        await session.scalars(select(MailAccount.id).where(MailAccount.process_id == process_id))
    )
    if account_ids:
        message = await session.scalar(
            select(MailMessage.id).where(MailMessage.account_id.in_(account_ids)).limit(1)
        )
        if message is not None:
            raise ConflictError(
                "Cannot delete a process with mail messages; its history is append-only"
            )
    await session.execute(
        sql_delete(MailActivityRead).where(MailActivityRead.process_id == process_id)
    )
    if account_ids:
        await session.execute(sql_delete(MailAccount).where(MailAccount.id.in_(account_ids)))

    await session.execute(sql_delete(ProcessDraft).where(ProcessDraft.process_id == process_id))
    await session.execute(sql_delete(Rule).where(Rule.process_id == process_id))
    await session.execute(sql_delete(NormRule).where(NormRule.process_id == process_id))
    await session.execute(sql_delete(Symbol).where(Symbol.process_id == process_id))
    await session.execute(sql_delete(DecisionType).where(DecisionType.process_id == process_id))

    # Events have no foreign key by design, so their audit rows can remain as the record of
    # the deleted process.
    process.active_version_id = None
    await session.delete(process)
    await session.commit()


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
