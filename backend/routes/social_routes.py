"""
backend/routes/social_routes.py
================================
POST   /api/posts/{id}/like         - likePost
DELETE /api/posts/{id}/like         - unlikePost
POST   /api/posts/{id}/comments     - addComment
GET    /api/posts/{id}/comments     - getComments
DELETE /api/comments/{id}           - deleteOwnComment
POST   /api/users/{id}/follow       - followUser
DELETE /api/users/{id}/follow       - unfollowUser
GET    /api/users/{id}/followers    - getFollowers
GET    /api/users/{id}/following    - getFollowing
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.middleware.auth_middleware import get_current_user
from backend.services.social_service import NotOwnerError
from backend.utils.validation import ValidationError

router = APIRouter(prefix="/api", tags=["social"])


class CommentBody(BaseModel):
    text: str


def _svc(request: Request):
    return request.app.state.social_service


@router.post("/posts/{post_id}/like", status_code=201)
def like_post(post_id: str, request: Request, user_id: str = Depends(get_current_user)):
    try:
        return _svc(request).like_post(user_id, post_id)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})


@router.delete("/posts/{post_id}/like", status_code=200)
def unlike_post(post_id: str, request: Request, user_id: str = Depends(get_current_user)):
    try:
        return _svc(request).unlike_post(user_id, post_id)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})


@router.post("/posts/{post_id}/comments", status_code=201)
def add_comment(post_id: str, body: CommentBody, request: Request,
                 user_id: str = Depends(get_current_user)):
    try:
        return _svc(request).add_comment(user_id, post_id, body.text)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})


@router.get("/posts/{post_id}/comments")
def get_comments(post_id: str, request: Request, page: int = 1):
    return _svc(request).get_comments(post_id, page=page)


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: str, request: Request, user_id: str = Depends(get_current_user)):
    try:
        _svc(request).delete_own_comment(user_id, comment_id)
    except NotOwnerError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})


@router.post("/users/{target_id}/follow", status_code=201)
def follow_user(target_id: str, request: Request, user_id: str = Depends(get_current_user)):
    try:
        _svc(request).follow_user(user_id, target_id)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})
    return {"message": "Now following"}


@router.delete("/users/{target_id}/follow", status_code=204)
def unfollow_user(target_id: str, request: Request, user_id: str = Depends(get_current_user)):
    _svc(request).unfollow_user(user_id, target_id)


@router.get("/users/{target_id}/followers")
def get_followers(target_id: str, request: Request):
    return _svc(request).get_followers(target_id)


@router.get("/users/{target_id}/following")
def get_following(target_id: str, request: Request):
    return _svc(request).get_following(target_id)
