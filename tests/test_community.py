"""
tests/test_community.py
========================
Covers Test IDs:
  13 File upload
  14 Invalid file
  15 Create community post
  16 Retrieve feed
  17 Like post
  18 Duplicate like prevention
  19 Unlike post
  20 Add comment
  21 Unauthorized content deletion
"""
import io

from tests.conftest import auth_headers, register_user

REAL_JPEG_BYTES = b"\xff\xd8\xff\xdb" + b"0" * 100


def test_13_file_upload(client):
    session = register_user(client, email="file1@example.com", username="fileuser1")
    headers = auth_headers(session)
    resp = client.post("/api/files/upload",
                        files={"file": ("photo.jpg", io.BytesIO(REAL_JPEG_BYTES), "image/jpeg")},
                        data={"kind": "POST_MEDIA"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["storage_path"].endswith(".jpg")


def test_14_invalid_file_rejected(client):
    session = register_user(client, email="file2@example.com", username="fileuser2")
    headers = auth_headers(session)
    resp = client.post("/api/files/upload",
                        files={"file": ("notes.txt", io.BytesIO(b"just text"), "text/plain")},
                        data={"kind": "POST_MEDIA"}, headers=headers)
    assert resp.status_code == 422


def test_15_create_community_post(client):
    session = register_user(client, email="post1@example.com", username="postuser1")
    headers = auth_headers(session)
    resp = client.post("/api/posts", json={"content": "Completed 30 hours of guitar practice!"},
                        headers=headers)
    assert resp.status_code == 201


def test_16_retrieve_feed(client):
    session = register_user(client, email="post2@example.com", username="postuser2")
    headers = auth_headers(session)
    client.post("/api/posts", json={"content": "Hello community"}, headers=headers)
    resp = client.get("/api/feed")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_17_like_post(client):
    author = register_user(client, email="post3@example.com", username="postuser3")
    liker = register_user(client, email="liker1@example.com", username="likeruser1")
    post = client.post("/api/posts", json={"content": "Like me"},
                        headers=auth_headers(author)).json()
    resp = client.post(f"/api/posts/{post['post_id']}/like", headers=auth_headers(liker))
    assert resp.status_code == 201
    assert resp.json()["like_count"] == 1


def test_18_duplicate_like_prevented(client):
    author = register_user(client, email="post4@example.com", username="postuser4")
    liker = register_user(client, email="liker2@example.com", username="likeruser2")
    post = client.post("/api/posts", json={"content": "Like me twice?"},
                        headers=auth_headers(author)).json()
    headers = auth_headers(liker)
    client.post(f"/api/posts/{post['post_id']}/like", headers=headers)
    resp = client.post(f"/api/posts/{post['post_id']}/like", headers=headers)
    assert resp.status_code == 422


def test_19_unlike_post(client):
    author = register_user(client, email="post5@example.com", username="postuser5")
    liker = register_user(client, email="liker3@example.com", username="likeruser3")
    post = client.post("/api/posts", json={"content": "Unlike me"},
                        headers=auth_headers(author)).json()
    headers = auth_headers(liker)
    client.post(f"/api/posts/{post['post_id']}/like", headers=headers)
    resp = client.delete(f"/api/posts/{post['post_id']}/like", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["like_count"] == 0


def test_20_add_comment(client):
    author = register_user(client, email="post6@example.com", username="postuser6")
    commenter = register_user(client, email="commenter1@example.com", username="commenteruser1")
    post = client.post("/api/posts", json={"content": "Comment on this"},
                        headers=auth_headers(author)).json()
    resp = client.post(f"/api/posts/{post['post_id']}/comments", json={"text": "Nice job!"},
                        headers=auth_headers(commenter))
    assert resp.status_code == 201
    comments = client.get(f"/api/posts/{post['post_id']}/comments").json()
    assert len(comments) == 1


def test_21_unauthorized_post_deletion_rejected(client):
    author = register_user(client, email="post7@example.com", username="postuser7")
    intruder = register_user(client, email="intruder1@example.com", username="intruderuser1")
    post = client.post("/api/posts", json={"content": "Do not delete me"},
                        headers=auth_headers(author)).json()
    resp = client.delete(f"/api/posts/{post['post_id']}", headers=auth_headers(intruder))
    assert resp.status_code == 403
