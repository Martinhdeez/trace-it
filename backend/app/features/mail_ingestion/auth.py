import hashlib
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.common.exceptions import PermissionDeniedError, UnauthenticatedError
from app.core.database import Session
from app.features.processes.model import Process

from .model import MailAccount

bearer = HTTPBearer(auto_error=False, scheme_name="MailIngestionBearer")


async def service_account(
    process_id: int,
    session: Session,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> MailAccount:
    if credentials is None:
        raise UnauthenticatedError("A mail service credential is required")
    digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    account = await session.scalar(select(MailAccount).where(MailAccount.token_hash == digest))
    if account is None:
        raise UnauthenticatedError("Invalid mail service credential")
    if account.process_id != process_id:
        raise PermissionDeniedError("Mail credential is not scoped to this process")
    process = await session.get(Process, process_id)
    if process is None or process.gathering_email != account.username:
        raise PermissionDeniedError("The process gathering email does not match this mailbox")
    return account


MailIdentity = Annotated[MailAccount, Depends(service_account)]
