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
