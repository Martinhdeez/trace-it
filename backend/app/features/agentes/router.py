from dataclasses import asdict

from fastapi import APIRouter

from app.core.database import Session
from app.features.agentes import asistente
from app.features.agentes.schemas import SugerenciaOut

router = APIRouter(tags=["agentes"])


@router.get(
    "/instancias/{instancia_id}/sugerencia",
    operation_id="getSugerencia",
    summary=(
        "Assistant's suggested decision, reasoning and new rule for an escalated case. "
        "Only a suggestion: the person resolves the instance and creates the rule "
        "(POST /procesos/{id}/reglas) themselves"
    ),
    responses={
        409: {"description": "Instance not escalated nor in REVISION"},
        502: {"description": "The assistant's model failed"},
    },
)
async def get_sugerencia(instancia_id: int, session: Session) -> SugerenciaOut:
    return SugerenciaOut(**asdict(await asistente.sugerir(session, instancia_id)))
