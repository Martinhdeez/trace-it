from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select

from app.common.exceptions import PermissionDeniedError, UnauthenticatedError
from app.core.api_auth import API_USER_EMAIL, BearerIdentity
from app.core.database import Session
from app.features.users.model import User


# Bearer callers always use the reserved manager. The public demo browser selects its identity.
async def current_user(
    session: Session,
    authenticated: BearerIdentity,
    x_user_id: Annotated[int | None, Header()] = None,
) -> User:
    """Resolve the API manager or the demo browser's chosen user."""
    if authenticated:
        user = await session.scalar(select(User).where(User.email == API_USER_EMAIL))
        if user is None or user.role != "manager":
            raise HTTPException(503, "API manager is unavailable; run database migrations")
        return user
    user = None if x_user_id is None else await session.get(User, x_user_id)
    if user is None:
        raise UnauthenticatedError(
            "Send X-User-Id with the id POST /login returns"
            if x_user_id is None
            else f"User {x_user_id} does not exist"
        )
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def manager_user(user: CurrentUser) -> User:
    """The app's user is the manager: only a manager runs, syncs, configures and resolves."""
    if user.role != "manager":
        raise PermissionDeniedError("Only a manager can do this")
    return user


Manager = Annotated[User, Depends(manager_user)]


async def optional_user(
    session: Session,
    authenticated: BearerIdentity,
    x_user_id: Annotated[int | None, Header()] = None,
) -> User | None:
    """The caller when it says who it is: for the author of a step anyone may take."""
    if not authenticated and x_user_id is None:
        return None
    return await current_user(session, authenticated, x_user_id)


OptionalUser = Annotated[User | None, Depends(optional_user)]
