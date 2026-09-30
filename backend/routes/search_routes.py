"""
backend/routes/search_routes.py
================================
GET /api/search?q=...        - search hobbies/skills and users by name
GET /api/community/trending  - most-practiced categories this week (for the
                                Community Dashboard's "Trending Skills" panel)
"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
def search(request: Request, q: str = Query(..., min_length=1, max_length=60)):
    db = request.app.state.cloud.db
    needle = q.strip().lower()

    skills = [s for s in db.select("skills") if needle in s["skill_name"].lower()
              or needle in s["category"].lower()]
    users = [u for u in db.select("users") if needle in u["username"].lower()
             or needle in u["name"].lower()]

    profile_service = request.app.state.profile_service
    return {
        "skills": [{"skill_id": s["skill_id"], "skill_name": s["skill_name"],
                    "category": s["category"]} for s in skills[:20]],
        "users": [profile_service.to_public_profile(u) for u in users[:20]],
    }


@router.get("/community/trending")
def trending(request: Request):
    db = request.app.state.cloud.db
    since = (date.today() - timedelta(days=7)).isoformat()
    recent_sessions = db.select("practice_sessions", {"practiced_at": ("gte", since)})

    category_by_skill: dict[str, str] = {s["skill_id"]: s["category"] for s in db.select("skills")}
    minutes_by_category: Counter = Counter()
    for session in recent_sessions:
        category = category_by_skill.get(session["skill_id"], "Other")
        minutes_by_category[category] += session["duration_minutes"]

    return {"trending_categories": [
        {"category": category, "practice_minutes": minutes}
        for category, minutes in minutes_by_category.most_common(10)
    ]}
