"""
backend/routes/practice_routes.py
==================================
POST /api/practice                 - log a practice session
GET  /api/practice                 - list the caller's sessions
GET  /api/skills/{id}/practice     - list sessions for one skill
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.middleware.auth_middleware import get_current_user
from backend.services.skill_service import NotOwnerError
from backend.utils.validation import ValidationError

router = APIRouter(prefix="/api", tags=["practice"])


class PracticeBody(BaseModel):
    skill_id: str
    duration_minutes: float
    activity: str = ""
    notes: str = ""
    practiced_at: str | None = None  # defaults to today server-side


def _service(request: Request):
    return request.app.state.practice_service


@router.post("/practice", status_code=201)
def log_practice(body: PracticeBody, request: Request, user_id: str = Depends(get_current_user)):
    try:
        return _service(request).log_session(user_id, body.model_dump())
    except NotOwnerError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})


@router.get("/practice")
def get_my_practice(request: Request, skill_id: Optional[str] = None,
                     user_id: str = Depends(get_current_user)):
    return _service(request).get_my_sessions(user_id, skill_id=skill_id)


@router.get("/skills/{skill_id}/practice")
def get_skill_practice(skill_id: str, request: Request, user_id: str = Depends(get_current_user)):
    skill = request.app.state.skill_service.get_skill_details(skill_id)
    if not skill or skill["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Skill not found")
    return _service(request).get_my_sessions(user_id, skill_id=skill_id)
