from fastapi import APIRouter
from sqlalchemy import select

from app.common.exceptions import NotFoundError
from app.core.database import Session
from app.features.llm.model import LLMConfig
from app.features.llm.schemas import LLMConfigIn, LLMConfigOut

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/config", operation_id="listLlmConfig", summary="Model per role")
async def list_config(session: Session) -> list[LLMConfigOut]:
    rows = await session.scalars(select(LLMConfig).order_by(LLMConfig.role))
    return [LLMConfigOut(role=r.role, model=r.model) for r in rows]


@router.put("/config/{role}", operation_id="updateLlmConfig", summary="Change a role's model")
async def update_config(role: str, body: LLMConfigIn, session: Session) -> LLMConfigOut:
    config = await session.get(LLMConfig, role)
    if config is None:
        raise NotFoundError(f"Unknown role: {role!r}")
    config.model = body.model
    await session.commit()
    return LLMConfigOut(role=role, model=config.model)
