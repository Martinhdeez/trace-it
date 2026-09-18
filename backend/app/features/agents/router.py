from dataclasses import asdict

from fastapi import APIRouter

from app.core.database import Session
from app.features.agents import assistant
from app.features.agents.schemas import SuggestionOut

router = APIRouter(tags=["agents"])


@router.get(
    "/instances/{instance_id}/suggestion",
    operation_id="getSuggestion",
    summary=(
        "Assistant's suggested decision, reasoning and new rule for an escalated case. "
        "Only a suggestion: the person resolves the instance and creates the rule "
        "(POST /processes/{id}/rules) themselves"
    ),
    responses={
        409: {"description": "Instance not escalated nor in REVIEW"},
        502: {"description": "The assistant's model failed"},
    },
)
async def get_suggestion(instance_id: int, session: Session) -> SuggestionOut:
    return SuggestionOut(**asdict(await assistant.suggest(session, instance_id)))
