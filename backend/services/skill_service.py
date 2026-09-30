"""
backend/services/skill_service.py
==================================
PURPOSE
    createSkill / updateSkill / deleteSkill / getMySkills / getSkillDetails
    from the brief. Every write path re-checks ``user_id == owner`` even
    though the frontend also hides other users' edit buttons - the backend
    ownership check is the one that actually matters (see docs/security.md).
"""
from __future__ import annotations

from typing import Optional

from cloud.database_service import DatabaseService
from backend.models.schemas import SKILL_LEVELS, SKILL_STATUSES, new_skill, now_iso
from backend.utils.validation import ValidationError, clean_choice, clean_date, clean_str


class NotOwnerError(Exception):
    """Raised when a user tries to modify a row they do not own -> HTTP 403."""


class SkillService:
    def __init__(self, db: DatabaseService):
        self.db = db

    def create_skill(self, user_id: str, payload: dict) -> dict:
        row = new_skill(
            user_id=user_id,
            skill_name=clean_str(payload.get("skill_name"), "skill_name", max_len=60),
            category=clean_str(payload.get("category"), "category", max_len=40),
            current_level=clean_choice(payload.get("current_level", "BEGINNER"), "current_level", SKILL_LEVELS),
            target_level=clean_choice(payload.get("target_level", "ADVANCED"), "target_level", SKILL_LEVELS),
            start_date=clean_date(payload.get("start_date"), "start_date"),
            target_date=clean_date(payload.get("target_date"), "target_date", required=False) or None,
            description=clean_str(payload.get("description", ""), "description", max_len=1000, required=False),
        )
        return self.db.insert("skills", row)

    def get_skill_details(self, skill_id: str) -> Optional[dict]:
        return self.db.get("skills", skill_id)

    def get_my_skills(self, user_id: str, *, status: Optional[str] = None) -> list[dict]:
        filters = {"user_id": user_id}
        if status:
            filters["status"] = clean_choice(status, "status", SKILL_STATUSES)
        return self.db.select("skills", filters, order_by=[("created_at", True)])

    def _owned_skill(self, user_id: str, skill_id: str) -> dict:
        skill = self.db.get("skills", skill_id)
        if not skill:
            raise ValidationError("skill_id", "skill not found")
        if skill["user_id"] != user_id:
            raise NotOwnerError("You can only modify your own skills")
        return skill

    def update_skill(self, user_id: str, skill_id: str, payload: dict) -> dict:
        self._owned_skill(user_id, skill_id)
        changes = {"updated_at": now_iso()}
        if "skill_name" in payload:
            changes["skill_name"] = clean_str(payload["skill_name"], "skill_name", max_len=60)
        if "category" in payload:
            changes["category"] = clean_str(payload["category"], "category", max_len=40)
        if "current_level" in payload:
            changes["current_level"] = clean_choice(payload["current_level"], "current_level", SKILL_LEVELS)
        if "target_level" in payload:
            changes["target_level"] = clean_choice(payload["target_level"], "target_level", SKILL_LEVELS)
        if "status" in payload:
            changes["status"] = clean_choice(payload["status"], "status", SKILL_STATUSES)
        if "target_date" in payload:
            changes["target_date"] = clean_date(payload["target_date"], "target_date", required=False) or None
        if "description" in payload:
            changes["description"] = clean_str(payload["description"], "description", max_len=1000, required=False)
        return self.db.update("skills", skill_id, changes)

    def delete_skill(self, user_id: str, skill_id: str) -> None:
        self._owned_skill(user_id, skill_id)
        # Cascade: goals/milestones/sessions tied to this skill no longer make sense on their own.
        for goal in self.db.select("goals", {"skill_id": skill_id}):
            self.db.delete_where("milestones", {"goal_id": goal["goal_id"]})
            self.db.delete("goals", goal["goal_id"])
        self.db.delete_where("practice_sessions", {"skill_id": skill_id})
        self.db.delete("skills", skill_id)
