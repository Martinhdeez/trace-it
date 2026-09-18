from fastapi import APIRouter
from sqlalchemy import select

from app.common.exceptions import NotFoundError
from app.core.database import Session
from app.features.llm.model import ConfigLLM
from app.features.llm.schemas import ConfigLLMIn, ConfigLLMOut

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/config", operation_id="listLlmConfig", summary="Model per role")
async def list_config(session: Session) -> list[ConfigLLMOut]:
    filas = await session.scalars(select(ConfigLLM).order_by(ConfigLLM.papel))
    return [ConfigLLMOut(papel=f.papel, modelo=f.modelo) for f in filas]


@router.put("/config/{papel}", operation_id="updateLlmConfig", summary="Change a role's model")
async def update_config(papel: str, body: ConfigLLMIn, session: Session) -> ConfigLLMOut:
    config = await session.get(ConfigLLM, papel)
    if config is None:
        raise NotFoundError(f"Papel desconocido: {papel!r}")
    config.modelo = body.modelo
    await session.commit()
    return ConfigLLMOut(papel=papel, modelo=config.modelo)
