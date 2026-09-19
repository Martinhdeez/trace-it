from typing import Literal

from fastapi import APIRouter

from app.core.database import Session
from app.features.alerts import service
from app.features.alerts.schemas import AckIn, AlertOut
from app.features.users.dependencies import CurrentUser

router = APIRouter(tags=["alerts"])


@router.get(
    "/processes/{process_id}/alerts",
    operation_id="listAlerts",
    summary="Past decisions that newer data or rules would decide otherwise",
    description="Raised after a source sync that changes rows and after a process version "
    "is published (ADR 0026). Each alert names the decision flagged, the outcome the engine "
    "would reach now, the trigger (source rows involved, or rule ids) and the reason codes "
    "before and after. The decision itself is never changed: act with `resolve` or "
    "`reprocess`; the later decision marks the alert `resolved`.",
)
async def list_alerts(
    process_id: int,
    session: Session,
    status: Literal["open", "acknowledged", "resolved"] | None = None,
) -> list[AlertOut]:
    return await service.list_alerts(session, process_id, status)


@router.post(
    "/alerts/{alert_id}/ack",
    operation_id="ackAlert",
    summary="The manager has seen the alert; records who and an optional note",
    responses={409: {"description": "Already acknowledged"}},
)
async def ack_alert(
    alert_id: int, session: Session, user: CurrentUser, body: AckIn | None = None
) -> AlertOut:
    return await service.ack(session, alert_id, body.note if body else None, user)
