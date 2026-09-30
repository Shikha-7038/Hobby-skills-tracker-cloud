"""
backend/routes/post_routes.py
==============================
POST   /api/posts          - createPost
GET    /api/feed           - getCommunityFeed (public; richer when logged in)
DELETE /api/posts/{id}     - deleteOwnPost
POST   /api/posts/{id}/report - report inappropriate content
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from backend.middleware.auth_middleware import get_current_user, get_optional_user
from backend.services.post_service import NotOwnerError
from backend.utils.validation import ValidationError

router = APIRouter(prefix="/api", tags=["posts"])


class PostBody(BaseModel):
    content: str = ""
    media_path: str | None = None
    skill_id: str | None = None
    visibility: str = "PUBLIC"


class ReportBody(BaseModel):
    reason: str


@router.post("/posts", status_code=201)
def create_post(body: PostBody, request: Request, user_id: str = Depends(get_current_user)):
    try:
        return request.app.state.post_service.create_post(user_id, body.model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})


@router.get("/feed")
def get_feed(request: Request, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
             following_only: bool = False, category_skill_id: Optional[str] = None,
             sort: str = "recent", user_id: Optional[str] = Depends(get_optional_user)):
    category_ids = [category_skill_id] if category_skill_id else None
    return request.app.state.post_service.get_feed(
        viewer_id=user_id, following_only=following_only, category_skill_ids=category_ids,
        sort=sort, page=page, page_size=page_size)


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: str, request: Request, user_id: str = Depends(get_current_user)):
    try:
        request.app.state.post_service.delete_own_post(user_id, post_id)
    except NotOwnerError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})


@router.post("/posts/{post_id}/report", status_code=201)
def report_post(post_id: str, body: ReportBody, request: Request,
                 user_id: str = Depends(get_current_user)):
    try:
        request.app.state.moderation_service.report_post(user_id, post_id, body.reason)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})
    return {"message": "Report submitted. Our team will review this post."}
