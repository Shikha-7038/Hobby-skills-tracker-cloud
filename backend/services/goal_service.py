"""
backend/services/goal_service.py
=================================
PURPOSE
    Goals ("practice 30 hours of guitar") and their milestones
    (5h / 10h / 20h / 30h). Progress is always derived, never stored twice:

        progress_percent = min(100, current_value / target_value * 100)

    Capping at 100 (see brief section 7) means a user who overshoots a goal
    still sees a clean "100% - goal complete", not 137%.
"""
from __future__ import annotations

from typing import Optional

from cloud.database_service import DatabaseService
from backend.models.schemas import new_goal, new_milestone, now_iso
from backend.services.skill_service import NotOwnerError
from backend.utils.validation import ValidationError, clean_date, clean_positive_number, clean_str


def progress_percent(current_value: float, target_value: float) -> float:
    if target_value <= 0:
        return 0.0
    return round(min(100.0, (current_value / target_value) * 100), 1)


class GoalService:
    def __init__(self, db: DatabaseService):
        self.db = db

    # -- goals --------------------------------------------------------- #
    def create_goal(self, user_id: str, payload: dict) -> dict:
        skill_id = clean_str(payload.get("skill_id"), "skill_id")
        skill = self.db.get("skills", skill_id)
        if not skill or skill["user_id"] != user_id:
            raise NotOwnerError("You can only create goals for your own skills")
        goal = new_goal(
            skill_id=skill_id,
            user_id=user_id,
            title=clean_str(payload.get("title"), "title", max_len=120),
            target_value=clean_positive_number(payload.get("target_value"), "target_value", allow_zero=False),
            unit=clean_str(payload.get("unit", "hours"), "unit", max_len=20),
            deadline=clean_date(payload.get("deadline"), "deadline", required=False) or None,
        )
        goal = self.db.insert("goals", goal)
        for m in payload.get("milestones", []):
            self.db.insert("milestones", new_milestone(
                goal_id=goal["goal_id"],
                title=clean_str(m.get("title"), "milestone.title", max_len=60),
                target_value=clean_positive_number(m.get("target_value"), "milestone.target_value", allow_zero=False),
            ))
        return self.with_progress(goal)

    def get_my_goals(self, user_id: str, *, skill_id: Optional[str] = None) -> list[dict]:
        filters = {"user_id": user_id}
        if skill_id:
            filters["skill_id"] = skill_id
        goals = self.db.select("goals", filters, order_by=[("created_at", True)])
        return [self.with_progress(g) for g in goals]

    def with_progress(self, goal: dict) -> dict:
        goal = dict(goal)
        goal["progress_percent"] = progress_percent(goal["current_value"], goal["target_value"])
        goal["milestones"] = self.db.select("milestones", {"goal_id": goal["goal_id"]},
                                             order_by=[("target_value", False)])
        return goal

    def update_goal(self, user_id: str, goal_id: str, payload: dict) -> dict:
        goal = self.db.get("goals", goal_id)
        if not goal:
            raise ValidationError("goal_id", "goal not found")
        if goal["user_id"] != user_id:
            raise NotOwnerError("You can only modify your own goals")
        changes = {"updated_at": now_iso()}
        if "title" in payload:
            changes["title"] = clean_str(payload["title"], "title", max_len=120)
        if "target_value" in payload:
            changes["target_value"] = clean_positive_number(payload["target_value"], "target_value", allow_zero=False)
        if "status" in payload:
            from backend.models.schemas import GOAL_STATUSES
            from backend.utils.validation import clean_choice
            changes["status"] = clean_choice(payload["status"], "status", GOAL_STATUSES)
        updated = self.db.update("goals", goal_id, changes)
        return self.with_progress(updated)

    # -- progress + milestone application (called from practice_service) - #
    def apply_progress(self, skill_id: str, added_value: float) -> list[dict]:
        """Adds ``added_value`` to every ACTIVE goal for this skill and marks
        any milestone that has now been reached. Returns newly achieved
        milestones so the caller can surface a celebratory response."""
        newly_achieved: list[dict] = []
        goals = self.db.select("goals", {"skill_id": skill_id, "status": "ACTIVE"})
        for goal in goals:
            new_value = goal["current_value"] + added_value
            changes = {"current_value": new_value, "updated_at": now_iso()}
            if new_value >= goal["target_value"]:
                changes["status"] = "COMPLETED"
            self.db.update("goals", goal["goal_id"], changes)
            for milestone in self.db.select("milestones", {"goal_id": goal["goal_id"], "achieved": False}):
                if new_value >= milestone["target_value"]:
                    self.db.update("milestones", milestone["milestone_id"],
                                    {"achieved": True, "achieved_at": now_iso()})
                    newly_achieved.append(milestone)
        return newly_achieved
