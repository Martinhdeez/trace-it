"""One interface for every LLM provider (P22). The model per role lives in `config_llm`."""

import time
from dataclasses import dataclass
from typing import Any

import litellm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.features.llm.model import ConfigLLM


@dataclass(frozen=True)
class Respuesta:
    contenido: str
    modelo: str
    coste: float | None
    latencia_ms: int


async def completar(
    session: AsyncSession,
    papel: str,
    mensajes: list[dict[str, Any]],
    formato: type[BaseModel] | None = None,
) -> Respuesta:
    """Call the model configured for `papel`. With `formato`, the reply is JSON that
    validates against it (`formato.model_validate_json(respuesta.contenido)`)."""
    config = await session.get(ConfigLLM, papel)
    if config is None:
        raise NotFoundError(f"No hay modelo configurado para el papel {papel!r}")
    inicio = time.perf_counter()
    respuesta = await litellm.acompletion(
        model=config.modelo, messages=mensajes, response_format=formato
    )
    latencia_ms = int((time.perf_counter() - inicio) * 1000)
    try:
        coste = litellm.completion_cost(completion_response=respuesta)
    except Exception:  # unknown price for this model: the call still succeeded
        coste = None
    return Respuesta(
        contenido=respuesta.choices[0].message.content or "",
        modelo=config.modelo,
        coste=coste,
        latencia_ms=latencia_ms,
    )
