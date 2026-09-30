"""
backend/routes/profile_routes.py
=================================
GET  /api/profile          - the logged-in user's own full profile
PUT  /api/profile          - update name / bio / interests
GET  /api/users/{username} - anyone's PUBLIC profile (no email)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.middleware.auth_middleware import get_current_user
from backend.utils.validation import ValidationError

router = APIRouter(prefix="/api", tags=["profile"])


class ProfileUpdateBody(BaseModel):
    name: str | None = None
    bio: str | None = None
    interests: list[str] | None = None


@router.get("/profile")
def get_my_profile(request: Request, user_id: str = Depends(get_current_user)):
    profile = request.app.state.profile_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return request.app.state.profile_service.to_private_profile(profile)


@router.put("/profile")
def update_my_profile(body: ProfileUpdateBody, request: Request, user_id: str = Depends(get_current_user)):
    try:
        updated = request.app.state.profile_service.update_profile(
            user_id, body.model_dump(exclude_none=True))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})
    return request.app.state.profile_service.to_private_profile(updated)


@router.get("/users/{username}")
def get_public_profile(username: str, request: Request):
    db = request.app.state.cloud.db
    matches = db.select("users", {"username": username.lower()})
    if not matches:
        raise HTTPException(status_code=404, detail="User not found")
    return request.app.state.profile_service.to_public_profile(matches[0])


@router.delete("/account", status_code=204)
def delete_my_account(request: Request, user_id: str = Depends(get_current_user)):
    """Permanently deletes this user's profile, skills, goals, posts, likes,
    comments, follows, files, and auth identity. Irreversible."""
    request.app.state.moderation_service.delete_account(user_id)
