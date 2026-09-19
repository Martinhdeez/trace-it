from typing import Literal

from fastapi import APIRouter

from app.core.database import Session
from app.features.proposals import service
from app.features.proposals.schemas import ManagerProposalOut, SettleIn
from app.features.users.dependencies import Manager

router = APIRouter(tags=["proposals"])


@router.post(
    "/instances/{instance_id}/proposal",
    status_code=201,
    operation_id="proposeDecision",
    summary="The assistant proposes a decision for an escalated instance; a manager settles it",
    description="Why the case escalated, the options with their consequence, the proposed "
    "one and its evidence, in `payload`. Only a proposal: no decision is taken until a "
    "manager accepts it (or resolves the instance with its `proposal_id`). A new one "
    "supersedes the instance's open proposal.",
    responses={
        409: {"description": "Instance not escalated"},
        502: {"description": "The assistant's model failed"},
    },
)
async def propose_decision(instance_id: int, session: Session, user: Manager) -> ManagerProposalOut:
    return await service.propose_decision(session, instance_id)


@router.get(
    "/processes/{process_id}/proposals",
    operation_id="listProposals",
    summary="Proposals from the escalation assistant, the process chat and learning",
    description="Newest first. `kind` is decision, rule, context, input or source.",
)
async def list_proposals(
    process_id: int,
    session: Session,
    user: Manager,
    status: Literal["open", "accepted", "rejected", "superseded"] | None = None,
) -> list[ManagerProposalOut]:
    return await service.list_for(session, process_id, status)


@router.post(
    "/proposals/{proposal_id}/accept",
    operation_id="acceptProposal",
    summary="The manager accepts a proposal; its channel's own workflow applies it",
    description="decision: resolves the instance with the proposed decision. Chat: accepts "
    "the change in the chat draft (publishing stays `/process-drafts/{id}/prepare` and "
    "`/publish`). Learning rule: adopts the norm's latest valid validation "
    "(`/norm-proposals/{id}/validate` first). Learning context or input: stages it in "
    "the version draft (`/processes/{id}/draft`). Learning source: recorded only.",
    responses={409: {"description": "Not open, stale, or not validated yet"}},
)
async def accept(
    proposal_id: int, session: Session, user: Manager, body: SettleIn | None = None
) -> ManagerProposalOut:
    return await service.accept(session, proposal_id, body.reason if body else "", user)


@router.post(
    "/proposals/{proposal_id}/reject",
    operation_id="rejectProposal",
    summary="The manager rejects a proposal; nothing it proposed is applied",
    responses={409: {"description": "Not open"}},
)
async def reject(
    proposal_id: int, session: Session, user: Manager, body: SettleIn | None = None
) -> ManagerProposalOut:
    return await service.reject(session, proposal_id, body.reason if body else "", user)
