"""
backend/models/schemas.py
==========================
PURPOSE
    Defines the shape of every row we store, as plain dictionaries (works
    identically against Supabase PostgreSQL and the local JSON store - no ORM
    lock-in). Each ``new_*`` function stamps defaults + a fresh UUID so
    services never construct raw dicts by hand.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# --------------------------------------------------------------------------- #
# Enumerations (kept as plain string constants -> portable to any database)
# --------------------------------------------------------------------------- #
SKILL_LEVELS = ("BEGINNER", "INTERMEDIATE", "ADVANCED")
SKILL_STATUSES = ("ACTIVE", "PAUSED", "COMPLETED")
GOAL_STATUSES = ("ACTIVE", "COMPLETED", "ABANDONED")
POST_VISIBILITY = ("PUBLIC", "FOLLOWERS")
FILE_KINDS = ("PROFILE_IMAGE", "ACHIEVEMENT_IMAGE", "POST_MEDIA")


def new_user(*, username: str, email: str, name: str) -> dict:
    return {
        "user_id": new_id("usr"),
        "name": name,
        "username": username,
        "email": email,
        "profile_picture": None,
        "bio": "",
        "interests": [],
        "is_moderator": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def new_skill(*, user_id: str, skill_name: str, category: str, current_level: str,
              target_level: str, start_date: str, target_date: Optional[str],
              description: str) -> dict:
    return {
        "skill_id": new_id("skl"),
        "user_id": user_id,
        "skill_name": skill_name,
        "category": category,
        "current_level": current_level,
        "target_level": target_level,
        "start_date": start_date,
        "target_date": target_date,
        "status": "ACTIVE",
        "description": description,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def new_goal(*, skill_id: str, user_id: str, title: str, target_value: float,
             unit: str, deadline: Optional[str]) -> dict:
    return {
        "goal_id": new_id("gol"),
        "skill_id": skill_id,
        "user_id": user_id,
        "title": title,
        "target_value": target_value,
        "current_value": 0.0,
        "unit": unit,
        "deadline": deadline,
        "status": "ACTIVE",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def new_milestone(*, goal_id: str, title: str, target_value: float) -> dict:
    return {
        "milestone_id": new_id("mil"),
        "goal_id": goal_id,
        "title": title,
        "target_value": target_value,
        "achieved": False,
        "achieved_at": None,
    }


def new_practice_session(*, user_id: str, skill_id: str, duration_minutes: float,
                          activity: str, notes: str, practiced_at: str) -> dict:
    return {
        "session_id": new_id("ses"),
        "user_id": user_id,
        "skill_id": skill_id,
        "duration_minutes": duration_minutes,
        "activity": activity,
        "notes": notes,
        "practiced_at": practiced_at,  # date the practice happened (YYYY-MM-DD)
        "created_at": now_iso(),
    }


def new_post(*, user_id: str, content: str, skill_id: Optional[str],
             media_path: Optional[str], visibility: str) -> dict:
    return {
        "post_id": new_id("pst"),
        "user_id": user_id,
        "skill_id": skill_id,
        "content": content,
        "media_path": media_path,
        "visibility": visibility,
        "like_count": 0,
        "comment_count": 0,
        "created_at": now_iso(),
    }


def new_comment(*, post_id: str, user_id: str, text: str) -> dict:
    return {
        "comment_id": new_id("cmt"),
        "post_id": post_id,
        "user_id": user_id,
        "text": text,
        "created_at": now_iso(),
    }


def new_like(*, post_id: str, user_id: str) -> dict:
    return {
        "like_id": f"{post_id}:{user_id}",  # composite key -> DB rejects duplicate likes
        "post_id": post_id,
        "user_id": user_id,
        "created_at": now_iso(),
    }


def new_follow(*, follower_id: str, following_id: str) -> dict:
    return {
        "follow_id": f"{follower_id}:{following_id}",
        "follower_id": follower_id,
        "following_id": following_id,
        "created_at": now_iso(),
    }


def new_file(*, owner_id: str, kind: str, storage_path: str, content_type: str,
             size_bytes: int) -> dict:
    return {
        "file_id": new_id("fil"),
        "owner_id": owner_id,
        "kind": kind,
        "storage_path": storage_path,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "created_at": now_iso(),
    }


def new_report(*, post_id: str, reporter_id: str, reason: str) -> dict:
    return {
        "report_id": f"{post_id}:{reporter_id}",
        "post_id": post_id,
        "reporter_id": reporter_id,
        "reason": reason,
        "status": "OPEN",
        "created_at": now_iso(),
    }
