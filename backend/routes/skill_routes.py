"""
backend/routes/skill_routes.py
===============================
POST   /api/skills          - createSkill
GET    /api/skills          - getMySkills (optional ?status= filter)
GET    /api/skills/{id}     - getSkillDetails (only the owner may view)
PUT    /api/skills/{id}     - updateSkill
DELETE /api/skills/{id}     - deleteSkill
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.middleware.auth_middleware import get_current_user
from backend.services.skill_service import NotOwnerError
from backend.utils.validation import ValidationError

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillBody(BaseModel):
    skill_name: str
    category: str
    current_level: str = "BEGINNER"
    target_level: str = "ADVANCED"
    start_date: str
    target_date: str | None = None
    description: str = ""


class SkillUpdateBody(BaseModel):
    skill_name: str | None = None
    category: str | None = None
    current_level: str | None = None
    target_level: str | None = None
    status: str | None = None
    target_date: str | None = None
    description: str | None = None


def _service(request: Request):
    return request.app.state.skill_service


@router.post("", status_code=201)
def create_skill(body: SkillBody, request: Request, user_id: str = Depends(get_current_user)):
    try:
        return _service(request).create_skill(user_id, body.model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})


@router.get("")
def get_my_skills(request: Request, status: Optional[str] = None,
                   user_id: str = Depends(get_current_user)):
    try:
        return _service(request).get_my_skills(user_id, status=status)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})


@router.get("/{skill_id}")
def get_skill_details(skill_id: str, request: Request, user_id: str = Depends(get_current_user)):
    skill = _service(request).get_skill_details(skill_id)
    if not skill or skill["user_id"] != user_id:
        # 404 (not 403) so a probing request cannot learn that a skill_id exists.
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.put("/{skill_id}")
def update_skill(skill_id: str, body: SkillUpdateBody, request: Request,
                  user_id: str = Depends(get_current_user)):
    try:
        return _service(request).update_skill(user_id, skill_id, body.model_dump(exclude_none=True))
    except NotOwnerError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})


@router.delete("/{skill_id}", status_code=204)
def delete_skill(skill_id: str, request: Request, user_id: str = Depends(get_current_user)):
    try:
        _service(request).delete_skill(user_id, skill_id)
    except NotOwnerError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})
