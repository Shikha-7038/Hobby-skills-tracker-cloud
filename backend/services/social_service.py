"""
backend/services/social_service.py
===================================
PURPOSE
    likePost / unlikePost / addComment / deleteOwnComment / getComments and
    the optional follow graph.

    DUPLICATE-LIKE PREVENTION (brief section 12): the ``likes`` primary key is
    the composite string "<post_id>:<user_id>" (see models/schemas.py). A
    second like insert therefore hits the SAME primary key and raises
    DuplicateError before any counter is touched - the database itself
    enforces "one like per user per post", not application logic that could
    be bypassed by a race condition.
"""
from __future__ import annotations

from typing import Optional

from cloud.database_service import DatabaseService, DuplicateError
from backend.models.schemas import new_comment, new_follow, new_like
from backend.utils.validation import ValidationError, clean_str


class NotOwnerError(Exception):
    pass


class SocialService:
    def __init__(self, db: DatabaseService):
        self.db = db

    # -- likes ----------------------------------------------------------- #
    def like_post(self, user_id: str, post_id: str) -> dict:
        post = self.db.get("posts", post_id)
        if not post:
            raise ValidationError("post_id", "post not found")
        try:
            self.db.insert("likes", new_like(post_id=post_id, user_id=user_id))
        except DuplicateError:
            raise ValidationError("post_id", "you already liked this post")
        updated = self.db.update("posts", post_id, {"like_count": post["like_count"] + 1})
        return updated

    def unlike_post(self, user_id: str, post_id: str) -> dict:
        post = self.db.get("posts", post_id)
        if not post:
            raise ValidationError("post_id", "post not found")
        removed = self.db.delete("likes", f"{post_id}:{user_id}")
        if not removed:
            raise ValidationError("post_id", "you have not liked this post")
        new_count = max(0, post["like_count"] - 1)
        return self.db.update("posts", post_id, {"like_count": new_count})

    # -- comments ---------------------------------------------------------#
    def add_comment(self, user_id: str, post_id: str, text: str) -> dict:
        post = self.db.get("posts", post_id)
        if not post:
            raise ValidationError("post_id", "post not found")
        comment = self.db.insert("comments", new_comment(
            post_id=post_id, user_id=user_id, text=clean_str(text, "text", max_len=500)))
        self.db.update("posts", post_id, {"comment_count": post["comment_count"] + 1})
        return comment

    def delete_own_comment(self, user_id: str, comment_id: str) -> None:
        comment = self.db.get("comments", comment_id)
        if not comment:
            raise ValidationError("comment_id", "comment not found")
        user = self.db.get("users", user_id)
        is_owner = comment["user_id"] == user_id
        is_moderator = bool(user and user.get("is_moderator"))
        if not (is_owner or is_moderator):
            raise NotOwnerError("You can only delete your own comments")
        post = self.db.get("posts", comment["post_id"])
        self.db.delete("comments", comment_id)
        if post:
            self.db.update("posts", post["post_id"], {"comment_count": max(0, post["comment_count"] - 1)})

    def get_comments(self, post_id: str, *, page: int = 1, page_size: int = 20) -> list[dict]:
        comments = self.db.select("comments", {"post_id": post_id}, order_by=[("created_at", False)])
        start = (page - 1) * page_size
        rows = comments[start:start + page_size]
        for c in rows:
            author = self.db.get("users", c["user_id"]) or {}
            c["author_username"] = author.get("username", "unknown")
            c["author_name"] = author.get("name", "Unknown user")
        return rows

    # -- follows (optional) ------------------------------------------------#
    def follow_user(self, follower_id: str, following_id: str) -> None:
        if follower_id == following_id:
            raise ValidationError("following_id", "you cannot follow yourself")
        if not self.db.get("users", following_id):
            raise ValidationError("following_id", "user not found")
        try:
            self.db.insert("follows", new_follow(follower_id=follower_id, following_id=following_id))
        except DuplicateError:
            pass  # already following - treat as a no-op success

    def unfollow_user(self, follower_id: str, following_id: str) -> None:
        self.db.delete("follows", f"{follower_id}:{following_id}")

    def get_followers(self, user_id: str) -> list[dict]:
        return self.db.select("follows", {"following_id": user_id})

    def get_following(self, user_id: str) -> list[dict]:
        return self.db.select("follows", {"follower_id": user_id})
