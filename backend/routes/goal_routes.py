"""
backend/routes/goal_routes.py
==============================
POST /api/goals        - create a goal (optionally with milestones)
PUT  /api/goals/{id}    - update a goal
GET  /api/goals         - list the caller's goals (optional ?skill_id=)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.middleware.auth_middleware import get_current_user
from backend.services.skill_service import NotOwnerError
from backend.utils.validation import ValidationError

router = APIRouter(prefix="/api/goals", tags=["goals"])


class MilestoneBody(BaseModel):
    title: str
    target_value: float


class GoalBody(BaseModel):
    skill_id: str
    title: str
    target_value: float
    unit: str = "hours"
    deadline: str | None = None
    milestones: list[MilestoneBody] = []


class GoalUpdateBody(BaseModel):
    title: str | None = None
    target_value: float | None = None
    status: str | None = None


def _service(request: Request):
    return request.app.state.goal_service


@router.post("", status_code=201)
def create_goal(body: GoalBody, request: Request, user_id: str = Depends(get_current_user)):
    payload = body.model_dump()
    try:
        return _service(request).create_goal(user_id, payload)
    except NotOwnerError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})


@router.get("")
def get_my_goals(request: Request, skill_id: Optional[str] = None,
                  user_id: str = Depends(get_current_user)):
    return _service(request).get_my_goals(user_id, skill_id=skill_id)


@router.put("/{goal_id}")
def update_goal(goal_id: str, body: GoalUpdateBody, request: Request,
                 user_id: str = Depends(get_current_user)):
    try:
        return _service(request).update_goal(user_id, goal_id, body.model_dump(exclude_none=True))
    except NotOwnerError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})
