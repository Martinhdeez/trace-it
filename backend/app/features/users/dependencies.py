from typing import Annotated

from fastapi import Depends, Header

from app.common.exceptions import NotFoundError
from app.core.database import Session
from app.features.users.model import User


# ponytail: identity by header, no password or token. Add real auth if the app leaves the
# hackathon; every endpoint already goes through this one dependency.
async def current_user(session: Session, x_user_id: Annotated[int, Header()]) -> User:
    user = await session.get(User, x_user_id)
    if user is None:
        raise NotFoundError(f"User {x_user_id} does not exist")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def optional_user(
    session: Session, x_user_id: Annotated[int | None, Header()] = None
) -> User | None:
    """The caller when it says who it is: for the author of a step anyone may take."""
    return None if x_user_id is None else await current_user(session, x_user_id)


OptionalUser = Annotated[User | None, Depends(optional_user)]
