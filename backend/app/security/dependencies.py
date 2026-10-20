from typing import Any

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.errors import AppError

bearer_scheme = HTTPBearer(auto_error=False)


def get_token_claims(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Validate a signed Bearer JWT; account and role checks follow in Phase 3."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(401, "missing_token", "A Bearer token is required")
    secret = request.app.state.settings.jwt_secret_key
    if not secret:
        raise AppError(401, "auth_unconfigured", "Authentication is not configured")
    try:
        return jwt.decode(credentials.credentials, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AppError(401, "invalid_token", "The access token is invalid or expired") from exc
