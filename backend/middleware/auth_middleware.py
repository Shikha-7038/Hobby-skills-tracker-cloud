"""
backend/middleware/auth_middleware.py
======================================
PURPOSE
    Turns the raw ``Authorization: Bearer <token>`` header into a verified
    user id. FastAPI runs this as a dependency, so any route that needs a
    logged-in user just adds ``user_id: str = Depends(get_current_user)``.

    AUTHENTICATION happens here (are you who you say you are?).
    AUTHORIZATION (are you allowed to touch THIS row?) happens per-service,
    right next to the data it protects - see services/*.py "ownership check".
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cloud.auth_service import AuthError

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    services = request.app.state.cloud
    try:
        return services.auth.verify_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str | None:
    """Same as get_current_user but returns None instead of 401 - used for
    endpoints (like the public feed) that behave differently when logged in
    but do not require it."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        return request.app.state.cloud.auth.verify_token(credentials.credentials)
    except AuthError:
        return None
