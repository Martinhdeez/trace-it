from typing import Literal

from fastapi import APIRouter, BackgroundTasks

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
    "supersedes the instance's open proposal. If the case gets another decision while the "
    "model answers, nothing is stored (409).",
    responses={
        409: {"description": "Instance not escalated, or it changed while the model answered"},
        502: {"description": "The assistant's model failed"},
    },
)
async def propose_decision(instance_id: int, session: Session, user: Manager) -> ManagerProposalOut:
    return await service.propose_decision(session, instance_id)


@router.post(
    "/instances/{instance_id}/rule-proposal",
    status_code=201,
    operation_id="proposeRule",
    summary="After a person resolved an escalated case, the reviewer agent amends the rule that "
    "escalated it so similar cases get that decision; a manager accepts or rejects it",
    description="Only when one escalation rule fired and, without it, the other rules give "
    "the person's decision; otherwise 409 with the reason in Spanish, and no model is "
    "called. `kind: rule`, `channel: escalation`; `payload`: `{decision_id` (the "
    "resolution), `engine_decision_id, replaces` (the rule it amends), `text` (English, "
    "compiled on accept), `summary, type, decision, resolved_as, version_id}`. Accepting "
    "stages it in the process draft in place of `replaces` and compiles it in the "
    "background; publishing stays `/processes/{id}/draft/validate` and `/publish`. Left "
    "open, it ends `superseded` with `outcome.cause`: `ignored` (another case resolved), "
    "`version_published`, `case_changed` or `superseded` (a newer suggestion).",
    responses={
        409: {"description": "Not resolved, not learnable (reason in Spanish), or stale"},
        502: {"description": "The assistant's model failed"},
    },
)
async def propose_rule(instance_id: int, session: Session, user: Manager) -> ManagerProposalOut:
    return await service.propose_rule(session, instance_id)


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
    description="decision: resolves the instance with the proposed decision. Escalation "
    "rule: creates the amended rule in the process draft, retires `replaces` there and "
    "compiles it in the background; `outcome` is `{rule_id, retired, draft_revision}`. "
    "Chat: accepts "
    "the change in the chat draft (publishing stays `/process-drafts/{id}/prepare` and "
    "`/publish`). Learning rule: adopts the norm's latest valid validation "
    "(`/norm-proposals/{id}/validate` first). Learning context or input: stages it in "
    "the version draft (`/processes/{id}/draft`). Learning source: recorded only.",
    responses={409: {"description": "Not open, stale, or not validated yet"}},
)
async def accept(
    proposal_id: int,
    session: Session,
    user: Manager,
    background: BackgroundTasks,
    body: SettleIn | None = None,
) -> ManagerProposalOut:
    return await service.accept(session, proposal_id, body.reason if body else "", user, background)


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
