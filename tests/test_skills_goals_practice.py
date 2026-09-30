"""
tests/test_skills_goals_practice.py
====================================
Covers Test IDs:
  6  Add skill
  7  Update skill
  8  Delete skill
  9  Create goal
  10 Log practice session
  11 Progress calculation
  12 Milestone completion
"""
from tests.conftest import auth_headers, register_user


def _make_skill(client, headers, **overrides):
    payload = {"skill_name": "Guitar", "category": "Music", "current_level": "BEGINNER",
               "target_level": "ADVANCED", "start_date": "2026-01-01",
               "target_date": None, "description": "Learn guitar"}
    payload.update(overrides)
    resp = client.post("/api/skills", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_06_add_skill(client):
    session = register_user(client, email="skills1@example.com", username="skillsuser1")
    headers = auth_headers(session)
    skill = _make_skill(client, headers)
    assert skill["skill_name"] == "Guitar"
    assert skill["status"] == "ACTIVE"


def test_07_update_skill(client):
    session = register_user(client, email="skills2@example.com", username="skillsuser2")
    headers = auth_headers(session)
    skill = _make_skill(client, headers)
    resp = client.put(f"/api/skills/{skill['skill_id']}", json={"status": "PAUSED"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAUSED"


def test_08_delete_skill(client):
    session = register_user(client, email="skills3@example.com", username="skillsuser3")
    headers = auth_headers(session)
    skill = _make_skill(client, headers)
    resp = client.delete(f"/api/skills/{skill['skill_id']}", headers=headers)
    assert resp.status_code == 204
    assert client.get(f"/api/skills/{skill['skill_id']}", headers=headers).status_code == 404


def test_09_create_goal_with_milestones(client):
    session = register_user(client, email="goals1@example.com", username="goalsuser1")
    headers = auth_headers(session)
    skill = _make_skill(client, headers)
    resp = client.post("/api/goals", json={
        "skill_id": skill["skill_id"], "title": "Practice 30 hours", "target_value": 30,
        "unit": "hours", "milestones": [{"title": "5 Hours", "target_value": 5},
                                         {"title": "30 Hours", "target_value": 30}]},
        headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["target_value"] == 30
    assert len(body["milestones"]) == 2


def test_10_log_practice_session(client):
    session = register_user(client, email="practice1@example.com", username="practiceuser1")
    headers = auth_headers(session)
    skill = _make_skill(client, headers)
    resp = client.post("/api/practice", json={
        "skill_id": skill["skill_id"], "duration_minutes": 60,
        "activity": "Chord practice", "notes": "Worked on transitions"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["session"]["duration_minutes"] == 60


def test_11_progress_calculation_via_api(client):
    session = register_user(client, email="progress1@example.com", username="progressuser1")
    headers = auth_headers(session)
    skill = _make_skill(client, headers)
    client.post("/api/goals", json={"skill_id": skill["skill_id"], "title": "20 hours",
                                     "target_value": 20, "unit": "hours"}, headers=headers)
    client.post("/api/practice", json={"skill_id": skill["skill_id"], "duration_minutes": 600,
                                        "activity": "Practice"}, headers=headers)  # 10 hours
    goals = client.get("/api/goals", params={"skill_id": skill["skill_id"]}, headers=headers).json()
    assert goals[0]["progress_percent"] == 50.0


def test_12_milestone_completion(client):
    session = register_user(client, email="milestone1@example.com", username="milestoneuser1")
    headers = auth_headers(session)
    skill = _make_skill(client, headers)
    client.post("/api/goals", json={"skill_id": skill["skill_id"], "title": "10 hours",
                                     "target_value": 10, "unit": "hours",
                                     "milestones": [{"title": "First hour", "target_value": 1}]},
                headers=headers)
    resp = client.post("/api/practice", json={"skill_id": skill["skill_id"], "duration_minutes": 90,
                                               "activity": "Practice"}, headers=headers)
    achieved = resp.json()["milestones_achieved"]
    assert any(m["title"] == "First hour" for m in achieved)
