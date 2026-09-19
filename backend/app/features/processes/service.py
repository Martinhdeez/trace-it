from sqlalchemy import delete as sql_delete
from sqlalchemy import exists, or_, select, update
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


async def delete_process(session: AsyncSession, process_id: int) -> None:
    """Permanently remove a process and every row owned by its history."""
    from app.core.events import Event
    from app.features.alerts.model import Alert
    from app.features.decisions.model import Decision, DecisionReview, Finding
    from app.features.ingestion.model import File, Instance
    from app.features.learning.model import (
        Adoption,
        Analysis,
        Validation,
    )
    from app.features.learning.model import (
        Proposal as NormProposal,
    )
    from app.features.mail_ingestion.model import (
        MailAccount,
        MailActivity,
        MailActivityRead,
        MailAttachment,
        MailMessage,
        RunOperation,
    )
    from app.features.processes.model import DiscoveryRevision, DiscoverySession
    from app.features.proposals.model import ManagerProposal
    from app.features.rules.model import NormRule, Rule
    from app.features.sources.model import Source
    from app.features.versions.model import Execution, ProcessDraft, ProcessVersion

    process = await session.scalar(
        select(Process)
        .where(Process.id == process_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if process is None:
        raise NotFoundError(f"Process {process_id} does not exist")

    instance_ids = list(
        await session.scalars(select(Instance.id).where(Instance.process_id == process_id))
    )
    execution_ids = list(
        await session.scalars(select(Execution.id).where(Execution.process_id == process_id))
    )
    version_ids = list(
        await session.scalars(
            select(ProcessVersion.id).where(ProcessVersion.process_id == process_id)
        )
    )
    decision_ids = list(
        await session.scalars(
            select(Decision.id).where(
                or_(
                    Decision.instance_id.in_(instance_ids),
                    Decision.execution_id.in_(execution_ids),
                    Decision.version_id.in_(version_ids),
                )
            )
        )
    )
    rule_ids = list(await session.scalars(select(Rule.id).where(Rule.process_id == process_id)))
    norm_rule_ids = list(
        await session.scalars(select(NormRule.id).where(NormRule.process_id == process_id))
    )
    analysis_ids = list(
        await session.scalars(select(Analysis.id).where(Analysis.process_id == process_id))
    )
    norm_proposal_ids = list(
        await session.scalars(
            select(NormProposal.id).where(NormProposal.analysis_id.in_(analysis_ids))
        )
    )
    validation_ids = list(
        await session.scalars(
            select(Validation.id).where(Validation.proposal_id.in_(norm_proposal_ids))
        )
    )
    discovery_session_ids = list(
        await session.scalars(
            select(DiscoverySession.id).where(
                or_(
                    DiscoverySession.process_id == process_id,
                    DiscoverySession.published_process_id == process_id,
                )
            )
        )
    )
    account_ids = list(
        await session.scalars(select(MailAccount.id).where(MailAccount.process_id == process_id))
    )
    message_ids = list(
        await session.scalars(select(MailMessage.id).where(MailMessage.account_id.in_(account_ids)))
    )
    message_ids.extend(
        await session.scalars(
            select(MailActivity.message_id).where(MailActivity.process_id == process_id)
        )
    )
    message_ids = list(set(message_ids))

    attachment_filters = []
    if message_ids:
        attachment_filters.append(MailAttachment.message_id.in_(message_ids))
    if instance_ids:
        attachment_filters.append(MailAttachment.instance_id.in_(instance_ids))
    if execution_ids:
        attachment_filters.append(MailAttachment.execution_id.in_(execution_ids))
    if decision_ids:
        attachment_filters.append(MailAttachment.decision_id.in_(decision_ids))
    activity_attachment_ids = list(
        await session.scalars(
            select(MailActivity.attachment_id).where(
                MailActivity.process_id == process_id,
                MailActivity.attachment_id.is_not(None),
            )
        )
    )
    if activity_attachment_ids:
        attachment_filters.append(MailAttachment.id.in_(activity_attachment_ids))
    attachment_ids = (
        list(await session.scalars(select(MailAttachment.id).where(or_(*attachment_filters))))
        if attachment_filters
        else []
    )
    file_hashes = set(
        await session.scalars(select(Instance.file_hash).where(Instance.id.in_(instance_ids)))
    )
    file_hashes.update(
        file_hash
        for file_hash in await session.scalars(
            select(MailAttachment.file_hash).where(
                MailAttachment.id.in_(attachment_ids),
                MailAttachment.file_hash.is_not(None),
            )
        )
        if file_hash is not None
    )

    # Events have no foreign keys, so remove their links before removing the rows they describe.
    event_filters = [Event.process_id == process_id]
    if instance_ids:
        event_filters.append(Event.instance_id.in_(instance_ids))
    if rule_ids:
        event_filters.append(Event.rule_id.in_(rule_ids))
    if norm_rule_ids:
        event_filters.append(Event.norm_rule_id.in_(norm_rule_ids))
    await session.execute(sql_delete(Event).where(or_(*event_filters)))

    # Delete leaf rows first, then the rows that own them.
    await session.execute(
        sql_delete(MailActivityRead).where(MailActivityRead.process_id == process_id)
    )
    await session.execute(sql_delete(MailActivity).where(MailActivity.process_id == process_id))
    await session.execute(sql_delete(MailAttachment).where(MailAttachment.id.in_(attachment_ids)))
    await session.execute(sql_delete(MailMessage).where(MailMessage.id.in_(message_ids)))
    if account_ids:
        await session.execute(sql_delete(MailAccount).where(MailAccount.id.in_(account_ids)))

    await session.execute(sql_delete(Alert).where(Alert.process_id == process_id))
    await session.execute(
        sql_delete(DecisionReview).where(DecisionReview.decision_id.in_(decision_ids))
    )
    await session.execute(
        sql_delete(Finding).where(
            or_(Finding.decision_id.in_(decision_ids), Finding.rule_id.in_(rule_ids))
        )
    )
    await session.execute(sql_delete(Decision).where(Decision.id.in_(decision_ids)))
    await session.execute(
        sql_delete(ManagerProposal).where(ManagerProposal.process_id == process_id)
    )

    await session.execute(
        sql_delete(Adoption).where(
            or_(
                Adoption.proposal_id.in_(norm_proposal_ids),
                Adoption.validation_id.in_(validation_ids),
            )
        )
    )
    await session.execute(sql_delete(Validation).where(Validation.id.in_(validation_ids)))
    await session.execute(sql_delete(NormProposal).where(NormProposal.id.in_(norm_proposal_ids)))
    await session.execute(sql_delete(Analysis).where(Analysis.id.in_(analysis_ids)))

    await session.execute(sql_delete(RunOperation).where(RunOperation.process_id == process_id))
    await session.execute(sql_delete(ProcessDraft).where(ProcessDraft.process_id == process_id))
    await session.execute(
        update(ProcessDraft)
        .where(ProcessDraft.base_version_id.in_(version_ids))
        .values(base_version_id=None)
    )
    await session.execute(sql_delete(Execution).where(Execution.process_id == process_id))
    await session.execute(sql_delete(Instance).where(Instance.process_id == process_id))
    if file_hashes:
        await session.execute(
            sql_delete(File).where(
                File.hash.in_(file_hashes),
                ~exists().where(Instance.file_hash == File.hash),
                ~exists().where(MailAttachment.file_hash == File.hash),
            )
        )

    await session.execute(
        update(ProcessVersion)
        .where(ProcessVersion.parent_id.in_(version_ids))
        .values(parent_id=None)
    )
    await session.execute(
        update(Process).where(Process.id == process_id).values(active_version_id=None)
    )
    process.active_version_id = None
    await session.execute(sql_delete(ProcessVersion).where(ProcessVersion.process_id == process_id))

    await session.execute(sql_delete(Rule).where(Rule.process_id == process_id))
    await session.execute(sql_delete(NormRule).where(NormRule.process_id == process_id))
    await session.execute(sql_delete(Symbol).where(Symbol.process_id == process_id))
    await session.execute(sql_delete(DecisionType).where(DecisionType.process_id == process_id))
    await session.execute(sql_delete(Source).where(Source.process_id == process_id))

    await session.execute(
        sql_delete(DiscoveryRevision).where(DiscoveryRevision.draft_id.in_(discovery_session_ids))
    )
    await session.execute(
        sql_delete(DiscoverySession).where(DiscoverySession.id.in_(discovery_session_ids))
    )

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
