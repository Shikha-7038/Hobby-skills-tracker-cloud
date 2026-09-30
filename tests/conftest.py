"""
tests/conftest.py
==================
Every test gets a FRESH, in-memory local cloud (no shared state between
tests, no real network calls) via the ``app`` and ``client`` fixtures.
"""
from __future__ import annotations

import os

os.environ["CLOUD_PROVIDER"] = "local"
os.environ["LOCAL_PERSIST"] = "false"
os.environ["LOCAL_JWT_SECRET"] = "test-secret-not-for-production"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app():
    """A freshly-built FastAPI app per test, so in-memory data never leaks
    between tests (importantly: an in-process, non-persistent LocalDatabase)."""
    from backend import app as app_module
    import importlib
    importlib.reload(app_module)  # rebuild app.state cleanly for isolation
    with TestClient(app_module.app) as client:
        yield app_module.app, client


@pytest.fixture()
def client(app):
    return app[1]


def register_user(client, *, name="Test User", username="testuser", email="test@example.com",
                   password="password123"):
    resp = client.post("/api/register", json={
        "name": name, "username": username, "email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()


def auth_headers(session: dict) -> dict:
    return {"Authorization": f"Bearer {session['access_token']}"}
