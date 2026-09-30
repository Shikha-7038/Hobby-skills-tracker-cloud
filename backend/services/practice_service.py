"""
backend/services/practice_service.py
=====================================
PURPOSE
    Logging a practice session is the heart of the app: it feeds goal
    progress, milestones, streaks, and the community feed all at once.

STREAK CALCULATION (brief section 8 - "explain streak calculation carefully")
    A user's "current streak" is the number of consecutive CALENDAR DAYS,
    ending today or yesterday, on which they logged at least one practice
    session (across ANY skill - the goal is to reward showing up, not to
    fragment a person's motivation per-hobby).

    Algorithm:
      1. Collect the DISTINCT set of practice dates for the user.
      2. If today is not in that set AND yesterday is not in that set,
         the streak is 0 (it was broken - a gap of 2+ days occurred).
      3. Otherwise walk backwards one day at a time from the most recent
         practiced day, counting while each day is present in the set.

    Example: dates = {Mon, Tue, Wed, Fri} and today = Fri
      -> Fri present -> count 1, check Thu -> absent -> stop. Streak = 1.
      (Wed/Tue/Mon formed an earlier, now-broken streak of 3.)

    "Longest streak" reruns the same walk over the whole history and keeps
    the maximum run length seen, so a broken streak from three months ago
    still shows up as a personal best.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from cloud.database_service import DatabaseService
from backend.models.schemas import new_practice_session
from backend.services.goal_service import GoalService
from backend.services.skill_service import NotOwnerError
from backend.utils.validation import ValidationError, clean_date, clean_positive_number, clean_str


def _parse(d: str) -> date:
    return datetime.strptime(d, "%Y-%m-%d").date()


def compute_streaks(practice_dates: list[str], *, today: Optional[date] = None) -> dict:
    """Pure function (no DB access) so it is trivially unit-testable."""
    today = today or date.today()
    unique_days = sorted({_parse(d) for d in practice_dates}, reverse=True)
    day_set = set(unique_days)

    current = 0
    if today in day_set or (today - timedelta(days=1)) in day_set:
        cursor = today if today in day_set else today - timedelta(days=1)
        while cursor in day_set:
            current += 1
            cursor -= timedelta(days=1)

    longest = 0
    run = 0
    prev: Optional[date] = None
    for day in sorted(day_set):  # ascending, so consecutive days are adjacent
        if prev is not None and (day - prev).days == 1:
            run += 1
        else:
            run = 1
        longest = max(longest, run)
        prev = day

    return {"current_streak": current, "longest_streak": longest}


class PracticeService:
    def __init__(self, db: DatabaseService, goal_service: GoalService):
        self.db = db
        self.goals = goal_service

    def log_session(self, user_id: str, payload: dict) -> dict:
        skill_id = clean_str(payload.get("skill_id"), "skill_id")
        skill = self.db.get("skills", skill_id)
        if not skill:
            raise ValidationError("skill_id", "skill not found")
        if skill["user_id"] != user_id:
            raise NotOwnerError("You can only log practice for your own skills")

        duration = clean_positive_number(payload.get("duration_minutes"), "duration_minutes", allow_zero=False)
        session = new_practice_session(
            user_id=user_id,
            skill_id=skill_id,
            duration_minutes=duration,
            activity=clean_str(payload.get("activity", ""), "activity", max_len=120, required=False),
            notes=clean_str(payload.get("notes", ""), "notes", max_len=1000, required=False),
            practiced_at=clean_date(payload.get("practiced_at") or date.today().isoformat(), "practiced_at"),
        )
        session = self.db.insert("practice_sessions", session)

        # duration is logged in minutes but goals are usually set in hours -
        # apply progress in the SAME unit the goal was created with.
        hours = duration / 60
        achieved = self.goals.apply_progress(skill_id, hours)

        return {"session": session, "milestones_achieved": achieved,
                "streaks": self.get_streaks(user_id)}

    def get_my_sessions(self, user_id: str, *, skill_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        filters = {"user_id": user_id}
        if skill_id:
            filters["skill_id"] = skill_id
        return self.db.select("practice_sessions", filters, order_by=[("practiced_at", True)], limit=limit)

    def get_streaks(self, user_id: str) -> dict:
        sessions = self.db.select("practice_sessions", {"user_id": user_id})
        return compute_streaks([s["practiced_at"] for s in sessions])

    def total_minutes(self, user_id: str, *, since: Optional[date] = None) -> float:
        sessions = self.db.select("practice_sessions", {"user_id": user_id})
        if since:
            sessions = [s for s in sessions if _parse(s["practiced_at"]) >= since]
        return sum(s["duration_minutes"] for s in sessions)
