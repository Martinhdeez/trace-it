from fastapi import APIRouter

from app.common.exceptions import PermissionDeniedError
from app.core.database import Session
from app.features.use_cases import service
from app.features.use_cases.schemas import (
    AgentConfigIn,
    AgentConfigOut,
    Role,
    UseCaseDetail,
    UseCaseOut,
)
from app.features.users.dependencies import CurrentUser

router = APIRouter(tags=["use cases"])


def _manager_only(user: CurrentUser) -> None:
    if user.role != "manager":
        raise PermissionDeniedError("Only a manager can change how the agents work")


@router.get("/use-cases", operation_id="listUseCases", summary="All use cases")
async def list_use_cases(session: Session) -> list[UseCaseOut]:
    return await service.list_all(session)


@router.get(
    "/use-cases/{use_case_id}",
    operation_id="getUseCase",
    summary="A use case with the active configuration of each agent role",
)
async def get_use_case(use_case_id: int, session: Session) -> UseCaseDetail:
    return await service.get(session, use_case_id)


@router.get(
    "/use-cases/{use_case_id}/agents/{role}/versions",
    operation_id="listAgentConfigVersions",
    summary="Every version of an agent role's configuration, oldest first",
)
async def list_versions(use_case_id: int, role: Role, session: Session) -> list[AgentConfigOut]:
    return await service.versions(session, use_case_id, role)


@router.put(
    "/use-cases/{use_case_id}/agents/{role}",
    operation_id="configureAgent",
    summary="Save a new version of an agent role's configuration and activate it",
    responses={403: {"description": "Not a manager"}},
)
async def configure(
    use_case_id: int, role: Role, body: AgentConfigIn, session: Session, user: CurrentUser
) -> AgentConfigOut:
    _manager_only(user)
    return await service.configure(session, use_case_id, role, body.config, user.name, body.note)


@router.post(
    "/agent-configs/{config_id}/activate",
    operation_id="activateAgentConfig",
    summary="Activate an existing version (rollback, or adopt one loaded from the pack)",
    responses={403: {"description": "Not a manager"}, 409: {"description": "Already active"}},
)
async def activate(config_id: int, session: Session, user: CurrentUser) -> AgentConfigOut:
    _manager_only(user)
    return await service.activate(session, config_id)
