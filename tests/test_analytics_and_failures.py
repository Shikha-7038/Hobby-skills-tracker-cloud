"""
tests/test_analytics_and_failures.py
=====================================
Covers Test IDs:
  22 Analytics calculation
  23 User-data isolation (a user cannot read another user's private skills)
  24 Cloud-storage failure (simulated) -> graceful 503, not a crash
  25 Database failure (simulated) -> graceful 503, not a crash
"""
from tests.conftest import auth_headers, register_user


def test_22_analytics_calculation(client):
    session = register_user(client, email="analytics1@example.com", username="analyticsuser1")
    headers = auth_headers(session)
    skill = client.post("/api/skills", json={
        "skill_name": "Painting", "category": "Art", "current_level": "BEGINNER",
        "target_level": "ADVANCED", "start_date": "2026-01-01"}, headers=headers).json()
    client.post("/api/practice", json={"skill_id": skill["skill_id"], "duration_minutes": 120,
                                        "activity": "Watercolor"}, headers=headers)
    dashboard = client.get("/api/analytics/dashboard", headers=headers).json()
    assert dashboard["total_practice_minutes"] == 120
    assert dashboard["active_skills"] == 1
    assert "practice_minutes_by_skill" in dashboard["charts"]


def test_23_skill_details_isolated_between_users(client):
    owner = register_user(client, email="isolate1@example.com", username="isolateuser1")
    other = register_user(client, email="isolate2@example.com", username="isolateuser2")
    skill = client.post("/api/skills", json={
        "skill_name": "Private Skill", "category": "Other", "current_level": "BEGINNER",
        "target_level": "ADVANCED", "start_date": "2026-01-01"}, headers=auth_headers(owner)).json()
    resp = client.get(f"/api/skills/{skill['skill_id']}", headers=auth_headers(other))
    assert resp.status_code == 404  # not 403 - existence is not revealed either


def test_24_storage_failure_returns_graceful_error(client, app):
    """Simulates cloud object storage being unreachable."""
    fastapi_app, test_client = app
    session = register_user(test_client, email="storagefail@example.com", username="storagefailuser")
    headers = auth_headers(session)

    from cloud.storage_service import StorageError

    class BrokenStorage:
        def upload(self, *a, **k):
            raise StorageError("simulated storage outage")

        def delete(self, *a, **k):
            raise StorageError("simulated storage outage")

        def signed_url(self, *a, **k):
            raise StorageError("simulated storage outage")

    fastapi_app.state.cloud.storage = BrokenStorage()
    fastapi_app.state.file_service.storage = BrokenStorage()

    import io
    resp = test_client.post(
        "/api/files/upload",
        files={"file": ("photo.jpg", io.BytesIO(b"\xff\xd8\xff\xdb" + b"0" * 50), "image/jpeg")},
        data={"kind": "POST_MEDIA"}, headers=headers)
    assert resp.status_code == 503
    assert "try again" in resp.json()["message"].lower()


def test_25_database_failure_returns_graceful_error(client, app):
    """Simulates the cloud database being unreachable."""
    fastapi_app, test_client = app
    session = register_user(test_client, email="dbfail@example.com", username="dbfailuser")
    headers = auth_headers(session)

    from cloud.database_service import DatabaseError

    class BrokenDB:
        def select(self, *a, **k):
            raise DatabaseError("simulated database outage")

        def get(self, *a, **k):
            raise DatabaseError("simulated database outage")

    fastapi_app.state.skill_service.db = BrokenDB()
    resp = test_client.get("/api/skills", headers=headers)
    assert resp.status_code == 503
    assert "try again" in resp.json()["message"].lower()
