"""
tests/test_auth_and_profile.py
===============================
Covers Test IDs:
  1  User registration
  2  Duplicate registration
  3  Valid login
  4  Invalid login
  5  Profile update
  26 Authentication-token expiry (rejection of a garbage/expired token)
  27 Logout
"""
from tests.conftest import auth_headers, register_user


def test_01_user_registration(client):
    session = register_user(client)
    assert session["user"]["username"] == "testuser"
    assert "access_token" in session and "refresh_token" in session


def test_02_duplicate_registration_rejected(client):
    register_user(client, email="dup@example.com", username="dupuser")
    resp = client.post("/api/register", json={
        "name": "Someone Else", "username": "dupuser2",
        "email": "dup@example.com", "password": "password123"})
    assert resp.status_code in (409, 422)


def test_03_valid_login(client):
    register_user(client, email="login@example.com", username="loginuser", password="password123")
    resp = client.post("/api/login", json={"email": "login@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["user"]["username"] == "loginuser"


def test_04_invalid_login_rejected(client):
    register_user(client, email="login2@example.com", username="loginuser2", password="password123")
    resp = client.post("/api/login", json={"email": "login2@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_05_profile_update(client):
    session = register_user(client, email="profile@example.com", username="profileuser")
    resp = client.put("/api/profile", json={"bio": "I love photography and chess."},
                       headers=auth_headers(session))
    assert resp.status_code == 200
    assert resp.json()["bio"] == "I love photography and chess."


def test_23_user_data_isolation_on_private_fields(client):
    session = register_user(client, email="private@example.com", username="privateuser")
    public = client.get("/api/users/privateuser")
    assert public.status_code == 200
    assert "email" not in public.json()


def test_26_garbage_token_rejected(client):
    resp = client.get("/api/profile", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_27_logout_revokes_token(client):
    session = register_user(client, email="logout@example.com", username="logoutuser")
    headers = auth_headers(session)
    assert client.get("/api/profile", headers=headers).status_code == 200
    assert client.post("/api/logout", headers=headers).status_code == 200
    assert client.get("/api/profile", headers=headers).status_code == 401
