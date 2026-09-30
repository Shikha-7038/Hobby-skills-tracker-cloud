"""
analytics/progress_service.py
==============================
PURPOSE
    Turns raw rows (sessions, goals, posts, likes) into the numbers the
    dashboard shows (brief sections 14 and 26). Kept as its own module,
    separate from backend/services, because analytics reads across many
    tables at once rather than owning a single one.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

from cloud.database_service import DatabaseService
from backend.services.goal_service import progress_percent
from backend.services.practice_service import compute_streaks


class AnalyticsService:
    def __init__(self, db: DatabaseService):
        self.db = db

    def dashboard(self, user_id: str) -> dict:
        sessions = self.db.select("practice_sessions", {"user_id": user_id})
        skills = self.db.select("skills", {"user_id": user_id})
        goals = self.db.select("goals", {"user_id": user_id})
        posts = self.db.select("posts", {"user_id": user_id})

        skill_names = {s["skill_id"]: s["skill_name"] for s in skills}
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_prefix = today.strftime("%Y-%m")

        total_minutes = sum(s["duration_minutes"] for s in sessions)
        weekly_minutes = sum(s["duration_minutes"] for s in sessions
                              if date.fromisoformat(s["practiced_at"]) >= week_start)
        monthly_minutes = sum(s["duration_minutes"] for s in sessions
                               if s["practiced_at"].startswith(month_prefix))

        minutes_by_skill: Counter = Counter()
        for s in sessions:
            minutes_by_skill[skill_names.get(s["skill_id"], "Unknown")] += s["duration_minutes"]
        most_practiced = minutes_by_skill.most_common(1)[0][0] if minutes_by_skill else None

        weekly_trend: defaultdict = defaultdict(float)  # ISO week label -> minutes
        for s in sessions:
            d = date.fromisoformat(s["practiced_at"])
            iso_year, iso_week, _ = d.isocalendar()
            weekly_trend[f"{iso_year}-W{iso_week:02d}"] += s["duration_minutes"]

        monthly_trend: defaultdict = defaultdict(float)
        for s in sessions:
            monthly_trend[s["practiced_at"][:7]] += s["duration_minutes"]

        streaks = compute_streaks([s["practiced_at"] for s in sessions])

        goals_with_progress = [
            {**g, "progress_percent": progress_percent(g["current_value"], g["target_value"])}
            for g in goals
        ]
        milestones_achieved = 0
        for g in goals:
            milestones_achieved += self.db.count("milestones", {"goal_id": g["goal_id"], "achieved": True})

        likes_received = sum(p["like_count"] for p in posts)
        comments_received = sum(p["comment_count"] for p in posts)

        return {
            "active_skills": sum(1 for s in skills if s["status"] == "ACTIVE"),
            "total_practice_minutes": total_minutes,
            "total_practice_hours": round(total_minutes / 60, 1),
            "weekly_practice_minutes": weekly_minutes,
            "monthly_practice_minutes": monthly_minutes,
            "most_practiced_skill": most_practiced,
            "current_streak": streaks["current_streak"],
            "longest_streak": streaks["longest_streak"],
            "goals_completed": sum(1 for g in goals if g["status"] == "COMPLETED"),
            "active_goals": sum(1 for g in goals if g["status"] == "ACTIVE"),
            "milestones_achieved": milestones_achieved,
            "posts_count": len(posts),
            "likes_received": likes_received,
            "comments_received": comments_received,
            "charts": {
                "practice_minutes_by_skill": dict(minutes_by_skill),
                "weekly_practice_trend": dict(sorted(weekly_trend.items())),
                "monthly_practice_trend": dict(sorted(monthly_trend.items())),
                "skill_distribution": dict(Counter(s["category"] for s in skills)),
                "goal_completion": {
                    "completed": sum(1 for g in goals if g["status"] == "COMPLETED"),
                    "active": sum(1 for g in goals if g["status"] == "ACTIVE"),
                    "abandoned": sum(1 for g in goals if g["status"] == "ABANDONED"),
                },
            },
            "goals": goals_with_progress,
        }
