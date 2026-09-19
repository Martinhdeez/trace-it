from fastapi import APIRouter, Query

from app.common.exceptions import PermissionDeniedError
from app.core.database import Session
from app.features.learning import service
from app.features.learning.schemas import (
    AdoptionOut,
    AnalysisIn,
    AnalysisOut,
    ApproveIn,
    ProposalOut,
    RejectIn,
    ValidationOut,
)
from app.features.users.dependencies import CurrentUser

router = APIRouter(tags=["learning"])


def manager(user: CurrentUser) -> str:
    if user.role != "manager":
        raise PermissionDeniedError("Only a manager can review and adopt norms")
    return user.name


@router.post(
    "/processes/{process_id}/learning",
    status_code=201,
    summary="Analyze past cases and propose norms; changes no decisions or rules",
)
async def analyze(
    process_id: int, body: AnalysisIn, session: Session, user: CurrentUser
) -> AnalysisOut:
    return await service.analyze(session, process_id, body.case_limit, manager(user))


@router.get("/processes/{process_id}/learning")
async def list_analyses(
    process_id: int, session: Session, user: CurrentUser, limit: int = Query(20, ge=1, le=100)
) -> list[AnalysisOut]:
    manager(user)
    return await service.list_all(session, process_id, limit)


@router.get("/learning/{analysis_id}")
async def get_analysis(analysis_id: int, session: Session, user: CurrentUser) -> AnalysisOut:
    manager(user)
    return await service.get(session, analysis_id)


@router.get("/norm-proposals/{proposal_id}")
async def get_proposal(proposal_id: int, session: Session, user: CurrentUser) -> ProposalOut:
    manager(user)
    return await service.get_proposal(session, proposal_id)


@router.post(
    "/norm-proposals/{proposal_id}/validate",
    status_code=201,
    summary="Prepare isolated code/tests or paired guidance previews; waits up to five minutes",
)
async def validate(proposal_id: int, session: Session, user: CurrentUser) -> ValidationOut:
    return await service.validate(session, proposal_id, manager(user))


@router.post(
    "/norm-proposals/{proposal_id}/approve",
    status_code=201,
    summary="Publish the exact latest validated norm after checking for stale evidence",
)
async def approve(
    proposal_id: int, body: ApproveIn, session: Session, user: CurrentUser
) -> AdoptionOut:
    return await service.approve(
        session, proposal_id, body.validation_id, body.reason, manager(user)
    )


@router.post("/norm-proposals/{proposal_id}/reject", status_code=201)
async def reject(
    proposal_id: int, body: RejectIn, session: Session, user: CurrentUser
) -> AdoptionOut:
    return await service.reject(session, proposal_id, body.reason, manager(user))
