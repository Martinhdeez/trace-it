"""Approved process guidance, shared by live reviews and proposal previews."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.model import Adoption, Analysis, Proposal


async def approved(session: AsyncSession, process_id: int) -> dict[str, str]:
    rows = await session.execute(
        select(Adoption.id, Proposal.text)
        .join(Proposal, Adoption.proposal_id == Proposal.id)
        .join(Analysis, Proposal.analysis_id == Analysis.id)
        .where(
            Analysis.process_id == process_id,
            Proposal.kind == "guidance",
            Adoption.approved.is_(True),
        )
        .order_by(Adoption.id)
    )
    return {f"norm:{key}": text for key, text in rows}
