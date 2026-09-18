from fastapi import APIRouter, status
from sqlalchemy import select

from app.common.exceptions import ConflictError, NotFoundError
from app.core.database import Session
from app.features.users.dependencies import CurrentUser
from app.features.users.model import User
from app.features.users.schemas import LoginIn, UserIn, UserOut

router = APIRouter(tags=["users"])


def _out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, role=user.role)


@router.get("/users", operation_id="listUsers", summary="All users")
async def list_users(session: Session) -> list[UserOut]:
    return [_out(u) for u in await session.scalars(select(User).order_by(User.id))]


@router.post(
    "/users",
    operation_id="createUser",
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
    responses={409: {"description": "Email already in use"}},
)
async def create_user(body: UserIn, session: Session) -> UserOut:
    if await session.scalar(select(User).where(User.email == body.email)):
        raise ConflictError(f"A user with email {body.email} already exists")
    user = User(**body.model_dump())
    session.add(user)
    await session.commit()
    return _out(user)


@router.post(
    "/login",
    operation_id="login",
    summary="Find the user by email. Send its id as `X-User-Id` afterwards",
)
async def login(body: LoginIn, session: Session) -> UserOut:
    user = await session.scalar(select(User).where(User.email == body.email))
    if user is None:
        raise NotFoundError(f"No user with email {body.email}")
    return _out(user)


@router.get("/me", operation_id="me", summary="The current user")
async def me(user: CurrentUser) -> UserOut:
    return _out(user)
