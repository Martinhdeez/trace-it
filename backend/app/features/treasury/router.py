from fastapi import APIRouter

from app.core.database import Session
from app.features.treasury.schemas import TreasuryPlanIn, TreasuryPlanOut
from app.features.treasury.service import plan

router = APIRouter(tags=["treasury"])


@router.post(
    "/processes/{process_id}/treasury/preview",
    operation_id="previewTreasuryPlan",
    response_model=TreasuryPlanOut,
    summary="Preview a deterministic, read-only payment plan",
    description=(
        "Plans current final decisions with the approved invoice payable outcome. "
        "The preview uses recorded instance and execution snapshots; it never executes "
        "or persists payments."
    ),
)
async def preview_treasury_plan(
    process_id: int, body: TreasuryPlanIn, session: Session
) -> TreasuryPlanOut:
    return await plan(session, process_id, body)
