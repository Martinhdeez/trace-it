"""Shared Bearer authentication for the application and database administration API."""

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

API_USER_EMAIL = "trace-it-api@localhost"
bearer = HTTPBearer(
    auto_error=False,
    scheme_name="TraceItBearer",
    description="The deployment's Trace-it API token. Acts as the dedicated API manager.",
)


def bearer_identity(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> bool:
    """Basic/browser callers keep their existing identity; invalid Bearers never fall back."""
    authorization = request.headers.get("authorization", "")
    parts = authorization.split(maxsplit=1)
    if not parts or parts[0].lower() != "bearer":
        return False
    expected = settings.api_token.get_secret_value()
    if (
        not expected
        or credentials is None
        or not secrets.compare_digest(credentials.credentials.encode(), expected.encode())
    ):
        raise HTTPException(401, "Invalid API token", headers={"WWW-Authenticate": "Bearer"})
    return True


BearerIdentity = Annotated[bool, Depends(bearer_identity)]


def require_bearer(authenticated: BearerIdentity) -> None:
    if not authenticated:
        raise HTTPException(401, "API token required", headers={"WWW-Authenticate": "Bearer"})
