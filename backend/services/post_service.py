"""
backend/services/post_service.py
=================================
PURPOSE
    createPost / getCommunityFeed / deleteOwnPost from the brief, plus the
    file upload plumbing a post's image goes through.

    The feed uses simple OFFSET pagination, which is fine at hobby-project
    scale; docs/scalability.md explains why this stops working past roughly
    a million rows and what replaces it (keyset pagination + fan-out writes).
"""
from __future__ import annotations

from typing import Optional

from cloud.database_service import DatabaseService
from cloud.storage_service import StorageService
from backend.models.schemas import POST_VISIBILITY, new_post
from backend.utils.validation import ValidationError, clean_choice, clean_str


class NotOwnerError(Exception):
    pass


class PostService:
    def __init__(self, db: DatabaseService, storage: StorageService):
        self.db = db
        self.storage = storage

    def create_post(self, user_id: str, payload: dict) -> dict:
        content = clean_str(payload.get("content", ""), "content", max_len=500, required=False)
        media_path = payload.get("media_path")  # set by a prior /api/files/upload call
        if not content and not media_path:
            raise ValidationError("content", "a post needs text, an image, or both")
        skill_id = payload.get("skill_id") or None
        if skill_id:
            skill = self.db.get("skills", skill_id)
            if not skill or skill["user_id"] != user_id:
                raise ValidationError("skill_id", "skill not found for this user")
        post = new_post(
            user_id=user_id,
            content=content,
            skill_id=skill_id,
            media_path=media_path,
            visibility=clean_choice(payload.get("visibility", "PUBLIC"), "visibility", POST_VISIBILITY),
        )
        return self.db.insert("posts", post)

    def _hydrate(self, post: dict, *, viewer_id: Optional[str]) -> dict:
        author = self.db.get("users", post["user_id"]) or {}
        media_url = self.storage.signed_url(post["media_path"]) if post.get("media_path") else None
        avatar_url = self.storage.signed_url(author["profile_picture"]) if author.get("profile_picture") else None
        liked_by_me = False
        if viewer_id:
            liked_by_me = self.db.get("likes", f"{post['post_id']}:{viewer_id}") is not None
        return {
            "post_id": post["post_id"],
            "content": post["content"],
            "media_url": media_url,
            "skill_id": post.get("skill_id"),
            "visibility": post["visibility"],
            "created_at": post["created_at"],
            "like_count": post["like_count"],
            "comment_count": post["comment_count"],
            "liked_by_me": liked_by_me,
            "author": {
                "user_id": author.get("user_id", post["user_id"]),
                "username": author.get("username", "unknown"),
                "name": author.get("name", "Unknown user"),
                "profile_picture": avatar_url,
            },
        }

    def get_feed(self, *, viewer_id: Optional[str], following_only: bool = False,
                 category_skill_ids: Optional[list[str]] = None,
                 sort: str = "recent", page: int = 1, page_size: int = 20) -> dict:
        filters: dict = {"visibility": "PUBLIC"}
        if following_only and viewer_id:
            follows = self.db.select("follows", {"follower_id": viewer_id})
            following_ids = [f["following_id"] for f in follows]
            filters["user_id"] = ("in", following_ids)
        if category_skill_ids is not None:
            filters["skill_id"] = ("in", category_skill_ids)

        order_col = "like_count" if sort == "top" else "created_at"
        posts = self.db.select("posts", filters, order_by=[(order_col, True)])
        total = len(posts)
        start = (page - 1) * page_size
        page_rows = posts[start:start + page_size]
        return {
            "posts": [self._hydrate(p, viewer_id=viewer_id) for p in page_rows],
            "page": page, "page_size": page_size, "total": total,
            "has_more": start + page_size < total,
        }

    def get_post(self, post_id: str, *, viewer_id: Optional[str]) -> Optional[dict]:
        post = self.db.get("posts", post_id)
        return self._hydrate(post, viewer_id=viewer_id) if post else None

    def delete_own_post(self, user_id: str, post_id: str) -> None:
        post = self.db.get("posts", post_id)
        if not post:
            raise ValidationError("post_id", "post not found")
        user = self.db.get("users", user_id)
        is_owner = post["user_id"] == user_id
        is_moderator = bool(user and user.get("is_moderator"))
        if not (is_owner or is_moderator):
            raise NotOwnerError("You can only delete your own posts")
        if post.get("media_path"):
            self.storage.delete(post["media_path"])
        self.db.delete_where("likes", {"post_id": post_id})
        self.db.delete_where("comments", {"post_id": post_id})
        self.db.delete("posts", post_id)
