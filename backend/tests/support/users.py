import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient, Response

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


async def anonymous(method: str, url: str, **kwargs) -> Response:
    """One request that says nobody: no `X-User-Id`."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        return await api.request(method, url, **kwargs)


@asynccontextmanager
async def manager_client(base_url: str = "http://test") -> AsyncIterator[AsyncClient]:
    """A client of the app acting as a new manager, the console's user (Q5)."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=base_url) as api:
        await manager(api)
        yield api
