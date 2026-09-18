from typing import Literal

from fastapi import APIRouter, status

from app.common.exceptions import PermissionDeniedError
from app.core.database import Session
from app.features.decisions.schemas import ImpactOut
from app.features.rules import service
from app.features.rules.schemas import RuleDetail, RuleIn, RuleOut
from app.features.users.dependencies import CurrentUser

router = APIRouter(tags=["rules"])

Status = Literal["draft", "rejected", "active", "retired"]


def _manager_only(user: CurrentUser) -> None:
    if user.role != "manager":
        raise PermissionDeniedError("Only a manager can activate or retire rules")


@router.get("/processes/{process_id}/rules", operation_id="listRules", summary="Rules")
async def list_rules(
    process_id: int, session: Session, status: Status | None = None
) -> list[RuleOut]:
    return await service.list_all(session, process_id, status)


@router.post(
    "/processes/{process_id}/rules",
    operation_id="createRule",
    status_code=status.HTTP_201_CREATED,
    summary="Add a rule as text. It starts as a draft",
)
async def create_rule(process_id: int, body: RuleIn, session: Session) -> RuleDetail:
    return await service.create(session, process_id, body)


@router.get("/rules/{rule_id}", operation_id="getRule", summary="A rule with its code")
async def get_rule(rule_id: int, session: Session) -> RuleDetail:
    return await service.get(session, rule_id)


@router.post(
    "/rules/{rule_id}/compile",
    operation_id="compileRule",
    summary="Generate code + tests with two agents and validate them",
)
async def compile_rule(rule_id: int, session: Session) -> RuleDetail:
    return await service.compile_rule(session, rule_id)


@router.get(
    "/rules/{rule_id}/impact",
    operation_id="getImpact",
    summary="What activating (or retiring) this rule would change, without doing it",
)
async def get_impact(rule_id: int, session: Session) -> ImpactOut:
    return ImpactOut.model_validate(await service.impact(session, rule_id), from_attributes=True)


@router.post(
    "/rules/{rule_id}/activate",
    operation_id="activateRule",
    summary="Activate a validated draft",
    responses={
        409: {
            "description": "Not compiled, discrepancies unresolved, or it would "
            "contradict a decision a person took"
        }
    },
)
async def activate_rule(rule_id: int, session: Session, user: CurrentUser) -> RuleDetail:
    _manager_only(user)
    return await service.activate(session, rule_id)


@router.post(
    "/rules/{rule_id}/retire",
    operation_id="retireRule",
    summary="Retire a rule. Checked against past decisions exactly like activating one",
    responses={409: {"description": "It would contradict a decision a person took"}},
)
async def retire_rule(rule_id: int, session: Session, user: CurrentUser) -> RuleDetail:
    _manager_only(user)
    return await service.retire(session, rule_id)
