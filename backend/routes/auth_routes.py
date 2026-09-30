"""
backend/routes/auth_routes.py
==============================
POST /api/register  - create an auth identity + matching profile row
POST /api/login      - exchange email/password for tokens
POST /api/refresh    - exchange a refresh token for a new access token
POST /api/logout     - revoke the current access token
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from cloud.auth_service import AuthError
from cloud.database_service import DuplicateError
from backend.middleware.auth_middleware import get_current_user
from backend.utils.validation import ValidationError, clean_email, clean_password

router = APIRouter(prefix="/api", tags=["auth"])


class RegisterBody(BaseModel):
    name: str = Field(..., examples=["Asha Verma"])
    username: str = Field(..., examples=["asha_v"])
    email: str = Field(..., examples=["asha@example.com"])
    password: str = Field(..., examples=["Str0ngPass!"])


class LoginBody(BaseModel):
    email: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


@router.post("/register", status_code=201)
def register(body: RegisterBody, request: Request):
    services = request.app.state.cloud
    try:
        email = clean_email(body.email)
        password = clean_password(body.password)
        user_id = services.auth.register(email, password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})

    try:
        profile = request.app.state.profile_service.create_profile(
            user_id_from_auth=user_id, name=body.name, username=body.username, email=email)
    except (ValidationError, DuplicateError) as exc:
        # Roll back the orphaned auth identity so a failed registration can be retried cleanly.
        services.auth.delete_user(user_id)
        message = exc.message if isinstance(exc, ValidationError) else "username already taken"
        raise HTTPException(status_code=422, detail={"message": message})

    session = services.auth.login(email, password)
    return {"user": request.app.state.profile_service.to_private_profile(profile), **session}


@router.post("/login")
def login(body: LoginBody, request: Request):
    services = request.app.state.cloud
    try:
        session = services.auth.login(clean_email(body.email), body.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    profile = request.app.state.profile_service.get_profile(session["user_id"])
    user_view = request.app.state.profile_service.to_private_profile(profile) if profile else None
    return {"user": user_view, **session}


@router.post("/refresh")
def refresh(body: RefreshBody, request: Request):
    try:
        return request.app.state.cloud.auth.refresh(body.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("/logout")
def logout(request: Request, user_id: str = Depends(get_current_user)):
    token = request.headers["authorization"].split(" ", 1)[1]
    request.app.state.cloud.auth.logout(token)
    return {"message": "Logged out"}
