"""
sample_data/seed_local_data.py
===============================
Populates the LOCAL simulation store with a handful of dummy/synthetic
users, hobbies, goals, practice sessions, and community posts, so the app
has something to look at immediately after cloning the repo.

This never touches a real cloud account — it only works against
CLOUD_PROVIDER=local, and it clears any existing local store first.

Run:  python sample_data/seed_local_data.py
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("CLOUD_PROVIDER", "local")
os.environ.setdefault("LOCAL_PERSIST", "true")
os.environ.setdefault("LOCAL_JWT_SECRET", "seed-script-secret")

from backend.config import settings  # noqa: E402
from cloud.auth_service import LocalAuth  # noqa: E402
from cloud.database_service import LocalDatabase  # noqa: E402
from cloud.storage_service import LocalStorage  # noqa: E402
from backend.services.goal_service import GoalService  # noqa: E402
from backend.services.post_service import PostService  # noqa: E402
from backend.services.practice_service import PracticeService  # noqa: E402
from backend.services.profile_service import ProfileService  # noqa: E402
from backend.services.skill_service import SkillService  # noqa: E402
from backend.services.social_service import SocialService  # noqa: E402

DUMMY_USERS = [
    {"name": "Asha Verma", "username": "asha_v", "email": "asha@example.com"},
    {"name": "Diego Martins", "username": "diego_m", "email": "diego@example.com"},
    {"name": "Priya Nair", "username": "priya_n", "email": "priya@example.com"},
]
PASSWORD = "Demo1234"


def main():
    data_dir = Path(settings.local_data_dir)
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    auth = LocalAuth(settings.local_jwt_secret, path=str(data_dir / "auth.json"))
    db = LocalDatabase(path=str(data_dir / "db.json"))
    storage = LocalStorage(str(data_dir / "storage"), settings.public_api_url)

    profiles = ProfileService(db, storage)
    skills_svc = SkillService(db)
    goals_svc = GoalService(db)
    practice_svc = PracticeService(db, goals_svc)
    posts_svc = PostService(db, storage)
    social_svc = SocialService(db)

    users = []
    for u in DUMMY_USERS:
        uid = auth.register(u["email"], PASSWORD)
        profiles.create_profile(user_id_from_auth=uid, name=u["name"], username=u["username"], email=u["email"])
        users.append(uid)
    print(f"Created {len(users)} dummy users (password for all: {PASSWORD})")

    asha, diego, priya = users

    guitar = skills_svc.create_skill(asha, {
        "skill_name": "Guitar", "category": "Music", "current_level": "BEGINNER",
        "target_level": "ADVANCED", "start_date": "2026-06-01", "target_date": None,
        "description": "Learning acoustic fingerstyle."})
    goals_svc.create_goal(asha, {
        "skill_id": guitar["skill_id"], "title": "Practice 30 hours", "target_value": 30,
        "unit": "hours", "deadline": None,
        "milestones": [{"title": "5 hours", "target_value": 5}, {"title": "15 hours", "target_value": 15},
                        {"title": "30 hours", "target_value": 30}]})

    today = date.today()
    for i, minutes in enumerate([45, 30, 60, 20, 90]):
        practice_svc.log_session(asha, {
            "skill_id": guitar["skill_id"], "duration_minutes": minutes,
            "activity": "Chord practice", "notes": "Worked on transitions.",
            "practiced_at": (today - timedelta(days=i)).isoformat()})

    chess = skills_svc.create_skill(diego, {
        "skill_name": "Chess", "category": "Strategy", "current_level": "INTERMEDIATE",
        "target_level": "ADVANCED", "start_date": "2026-03-01", "target_date": None,
        "description": "Studying the Sicilian Defense."})
    practice_svc.log_session(diego, {
        "skill_id": chess["skill_id"], "duration_minutes": 40, "activity": "Puzzle rush",
        "notes": "Tactics practice.", "practiced_at": today.isoformat()})

    painting = skills_svc.create_skill(priya, {
        "skill_name": "Watercolor Painting", "category": "Art", "current_level": "BEGINNER",
        "target_level": "INTERMEDIATE", "start_date": "2026-07-15", "target_date": None,
        "description": "Landscapes and light."})
    practice_svc.log_session(priya, {
        "skill_id": painting["skill_id"], "duration_minutes": 75, "activity": "Sky studies",
        "notes": "Wet-on-wet technique.", "practiced_at": today.isoformat()})

    post1 = posts_svc.create_post(asha, {
        "content": "Five days of guitar practice in a row! 🎸 Chord transitions finally feel smooth.",
        "skill_id": guitar["skill_id"], "media_path": None, "visibility": "PUBLIC"})
    social_svc.like_post(diego, post1["post_id"])
    social_svc.like_post(priya, post1["post_id"])
    social_svc.add_comment(diego, post1["post_id"], "Nice consistency! What are you learning next?")

    post2 = posts_svc.create_post(priya, {
        "content": "First watercolor sky study of the week. Loving the wet-on-wet technique.",
        "skill_id": painting["skill_id"], "media_path": None, "visibility": "PUBLIC"})
    social_svc.like_post(asha, post2["post_id"])

    social_svc.follow_user(diego, asha)
    social_svc.follow_user(priya, asha)

    print("Seed data created. Log in with any of these emails and password 'Demo1234':")
    for u in DUMMY_USERS:
        print(f"  - {u['email']}")


if __name__ == "__main__":
    main()
