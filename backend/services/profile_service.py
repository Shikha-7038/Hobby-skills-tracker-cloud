"""
backend/services/profile_service.py
====================================
PURPOSE
    Everything about the USERS table: registration bootstrap, profile
    updates, and public-vs-private views.

    SECURITY NOTE (see docs "Privacy & Content Moderation"):
    ``to_public_profile`` is the ONLY view of a user ever sent to anyone other
    than that user. Email is intentionally never included in it.
"""
from __future__ import annotations

from typing import Optional

from cloud.database_service import DatabaseService
from cloud.storage_service import StorageService
from backend.models.schemas import new_user
from backend.utils.validation import clean_str, clean_username, clean_email, ValidationError


class ProfileService:
    def __init__(self, db: DatabaseService, storage: StorageService):
        self.db = db
        self.storage = storage

    def create_profile(self, *, user_id_from_auth: str, name: str, username: str, email: str) -> dict:
        """Called right after a successful auth registration to create the
        matching application-level profile row."""
        name = clean_str(name, "name", max_len=100)
        username = clean_username(username)
        email = clean_email(email)
        row = new_user(username=username, email=email, name=name)
        row["user_id"] = user_id_from_auth  # keep auth id and profile id identical
        return self.db.insert("users", row)

    def get_profile(self, user_id: str) -> Optional[dict]:
        return self.db.get("users", user_id)

    def update_profile(self, user_id: str, changes: dict) -> dict:
        allowed = {}
        if "name" in changes:
            allowed["name"] = clean_str(changes["name"], "name", max_len=100)
        if "bio" in changes:
            allowed["bio"] = clean_str(changes["bio"], "bio", max_len=500, required=False)
        if "interests" in changes:
            interests = changes["interests"] or []
            if not isinstance(interests, list) or len(interests) > 20:
                raise ValidationError("interests", "must be a list of at most 20 items")
            allowed["interests"] = [clean_str(i, "interests", max_len=40) for i in interests]
        from backend.models.schemas import now_iso
        allowed["updated_at"] = now_iso()
        updated = self.db.update("users", user_id, allowed)
        if not updated:
            raise ValidationError("user_id", "profile not found")
        return updated

    def set_profile_picture(self, user_id: str, storage_path: str) -> dict:
        old = self.db.get("users", user_id)
        if old and old.get("profile_picture"):
            self.storage.delete(old["profile_picture"])  # clean up the previous image
        from backend.models.schemas import now_iso
        return self.db.update("users", user_id, {"profile_picture": storage_path, "updated_at": now_iso()})

    def to_public_profile(self, user: dict) -> dict:
        """NEVER include email or other private fields here."""
        picture_url = self.storage.signed_url(user["profile_picture"]) if user.get("profile_picture") else None
        return {
            "user_id": user["user_id"],
            "name": user["name"],
            "username": user["username"],
            "profile_picture": picture_url,
            "bio": user.get("bio", ""),
            "interests": user.get("interests", []),
            "created_at": user["created_at"],
        }

    def to_private_profile(self, user: dict) -> dict:
        """Full view returned only to the profile's own owner."""
        pub = self.to_public_profile(user)
        pub["email"] = user["email"]
        return pub
