import uuid

from httpx import AsyncClient

from app.core.database import session_factory
from app.features.users.model import User


async def manager(api: AsyncClient | None = None, name: str = "Manager") -> dict[str, str]:
    """A new manager, inserted directly (`POST /users` itself needs one). With `api`, the
    client sends its `X-User-Id` from now on; a request's own headers still win."""
    async with session_factory() as session:
        user = User(name=name, email=f"manager-{uuid.uuid4().hex[:8]}@test", role="manager")
        session.add(user)
        await session.flush()
        headers = {"X-User-Id": str(user.id)}
        await session.commit()
    if api is not None:
        api.headers.update(headers)
    return headers
