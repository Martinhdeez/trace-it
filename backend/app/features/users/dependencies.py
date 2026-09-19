from typing import Annotated

from fastapi import Depends, Header

from app.common.exceptions import PermissionDeniedError, UnauthenticatedError
from app.core.database import Session
from app.features.users.model import User


# ponytail: identity by header, no password or token. Add real auth if the app leaves the
# hackathon; every endpoint already goes through this one dependency.
async def current_user(
    session: Session, x_user_id: Annotated[int | None, Header()] = None
) -> User:
    """401 when the caller does not say who it is, or names a user that does not exist."""
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
    session: Session, x_user_id: Annotated[int | None, Header()] = None
) -> User | None:
    """The caller when it says who it is: for the author of a step anyone may take."""
    return None if x_user_id is None else await current_user(session, x_user_id)


OptionalUser = Annotated[User | None, Depends(optional_user)]
