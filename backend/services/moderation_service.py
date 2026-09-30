"""
backend/services/moderation_service.py
=======================================
PURPOSE
    Covers brief section 24 (Privacy & Content Moderation): reporting a post,
    and a user deleting their own account and all of its data.

    Reports use a composite key "<post_id>:<reporter_id>" so one user cannot
    spam-report the same post to inflate its report count.
"""
from __future__ import annotations

from cloud.auth_service import AuthService
from cloud.database_service import DatabaseService, DuplicateError
from cloud.storage_service import StorageService
from backend.models.schemas import new_report
from backend.utils.validation import ValidationError, clean_str


class ModerationService:
    def __init__(self, db: DatabaseService, storage: StorageService, auth: AuthService):
        self.db = db
        self.storage = storage
        self.auth = auth

    def report_post(self, reporter_id: str, post_id: str, reason: str) -> None:
        if not self.db.get("posts", post_id):
            raise ValidationError("post_id", "post not found")
        try:
            self.db.insert("reports", new_report(
                post_id=post_id, reporter_id=reporter_id,
                reason=clean_str(reason, "reason", max_len=300)))
        except DuplicateError:
            raise ValidationError("post_id", "you have already reported this post")

    def list_open_reports(self) -> list[dict]:
        """Moderator-only view (checked in the route)."""
        return self.db.select("reports", {"status": "OPEN"}, order_by=[("created_at", True)])

    def delete_account(self, user_id: str) -> None:
        """Removes the user's own data across every table, then their auth
        record. Community content (posts/comments left by OTHERS) is
        untouched; only what this user owns is deleted."""
        user = self.db.get("users", user_id)
        if user and user.get("profile_picture"):
            self.storage.delete(user["profile_picture"])

        for skill in self.db.select("skills", {"user_id": user_id}):
            for goal in self.db.select("goals", {"skill_id": skill["skill_id"]}):
                self.db.delete_where("milestones", {"goal_id": goal["goal_id"]})
            self.db.delete_where("goals", {"skill_id": skill["skill_id"]})
        self.db.delete_where("skills", {"user_id": user_id})
        self.db.delete_where("practice_sessions", {"user_id": user_id})

        for post in self.db.select("posts", {"user_id": user_id}):
            if post.get("media_path"):
                self.storage.delete(post["media_path"])
            self.db.delete_where("likes", {"post_id": post["post_id"]})
            self.db.delete_where("comments", {"post_id": post["post_id"]})
        self.db.delete_where("posts", {"user_id": user_id})
        self.db.delete_where("comments", {"user_id": user_id})
        self.db.delete_where("likes", {"user_id": user_id})
        self.db.delete_where("follows", {"follower_id": user_id})
        self.db.delete_where("follows", {"following_id": user_id})
        self.db.delete_where("files", {"owner_id": user_id})

        self.db.delete("users", user_id)
        self.auth.delete_user(user_id)
