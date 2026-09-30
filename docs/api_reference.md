# REST API Reference

Base URL (local): `http://localhost:8000`. All request/response bodies are
JSON unless noted. Authenticated endpoints require `Authorization: Bearer
<access_token>`. FastAPI also serves interactive docs at `/docs`
(Swagger UI) and `/redoc` once the server is running.

## Conventions

- **Errors** are always `{"message": "...", "field": "..."}` (field omitted
  when not applicable) with an appropriate status code: `401` not
  authenticated, `403` authenticated but not allowed, `404` not found,
  `422` validation error, `429` rate limited, `503` a cloud dependency is
  unavailable, `500` unexpected.
- **Pagination** uses `page` (1-indexed) and `page_size` query params where
  it appears; paginated responses include `total` and `has_more`.

## Auth — `backend/routes/auth_routes.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/register` | — | Create an account. Body: `name, username, email, password`. Returns `{user, access_token, refresh_token, expires_in}` |
| POST | `/api/login` | — | Body: `email, password`. Same response shape as register |
| POST | `/api/refresh` | — | Body: `refresh_token`. Returns a fresh `access_token` |
| POST | `/api/logout` | ✓ | Revokes the current access token |

## Profile — `backend/routes/profile_routes.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/profile` | ✓ | Your own full profile (includes email) |
| PUT | `/api/profile` | ✓ | Update `name`, `bio`, `interests` |
| GET | `/api/users/{username}` | — | Anyone's **public** profile (no email) |
| DELETE | `/api/account` | ✓ | Permanently delete your account and all owned data |

## Skills — `backend/routes/skill_routes.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/skills` | ✓ | Create a skill/hobby |
| GET | `/api/skills?status=` | ✓ | List your skills, optional status filter |
| GET | `/api/skills/{id}` | ✓ (owner) | Skill details — 404 for non-owners |
| PUT | `/api/skills/{id}` | ✓ (owner) | Update a skill |
| DELETE | `/api/skills/{id}` | ✓ (owner) | Delete a skill and cascade its goals/sessions |

## Goals — `backend/routes/goal_routes.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/goals` | ✓ | Create a goal, optionally with milestones |
| GET | `/api/goals?skill_id=` | ✓ | List your goals, each with `progress_percent` and `milestones` |
| PUT | `/api/goals/{id}` | ✓ (owner) | Update title/target/status |

## Practice — `backend/routes/practice_routes.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/practice` | ✓ | Log a session. Returns `{session, milestones_achieved, streaks}` |
| GET | `/api/practice?skill_id=` | ✓ | Your practice sessions |
| GET | `/api/skills/{id}/practice` | ✓ (owner) | Sessions for one skill |

## Posts & feed — `backend/routes/post_routes.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/posts` | ✓ | Create a post (text and/or `media_path` from a prior upload) |
| GET | `/api/feed?page=&page_size=&sort=&following_only=&category_skill_id=` | optional | Public feed; richer (`liked_by_me`) when logged in |
| DELETE | `/api/posts/{id}` | ✓ (owner or moderator) | Delete a post |
| POST | `/api/posts/{id}/report` | ✓ | Report a post. Body: `reason` |

## Social — `backend/routes/social_routes.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/posts/{id}/like` | ✓ | Like a post (second like → `422`) |
| DELETE | `/api/posts/{id}/like` | ✓ | Unlike a post |
| POST | `/api/posts/{id}/comments` | ✓ | Add a comment. Body: `text` |
| GET | `/api/posts/{id}/comments?page=` | — | List comments |
| DELETE | `/api/comments/{id}` | ✓ (owner or moderator) | Delete a comment |
| POST | `/api/users/{id}/follow` | ✓ | Follow a user |
| DELETE | `/api/users/{id}/follow` | ✓ | Unfollow a user |
| GET | `/api/users/{id}/followers` | — | List a user's followers |
| GET | `/api/users/{id}/following` | — | List who a user follows |

## Files — `backend/routes/file_routes.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/files/upload` | ✓ | Multipart form: `file`, `kind` (`PROFILE_IMAGE`\|`ACHIEVEMENT_IMAGE`\|`POST_MEDIA`), optional `skill_id`. Returns `{storage_path, url, ...}` |
| DELETE | `/api/files/{id}` | ✓ (owner) | Delete a file you own |

## Analytics — `backend/routes/analytics_routes.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/analytics/dashboard` | ✓ | Totals, streaks, and chart-ready data — see `analytics/progress_service.py` |

## Search & discovery — `backend/routes/search_routes.py`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/search?q=` | — | Search skills and users by name |
| GET | `/api/community/trending` | — | Most-practiced categories in the last 7 days |

## Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | — | `{"status": "ok", "cloud_provider": "..."}` — used by deploy-platform health checks |

## Example: end-to-end curl session

```bash
# Register
curl -s -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Asha Verma","username":"asha_v","email":"asha@example.com","password":"Str0ngPass1"}' \
  | tee /tmp/session.json

TOKEN=$(python3 -c "import json;print(json.load(open('/tmp/session.json'))['access_token'])")

# Create a skill
curl -s -X POST http://localhost:8000/api/skills \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"skill_name":"Guitar","category":"Music","current_level":"BEGINNER","target_level":"ADVANCED","start_date":"2026-01-01"}'

# Log practice
curl -s -X POST http://localhost:8000/api/practice \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"skill_id":"<skill_id from above>","duration_minutes":45,"activity":"Chords"}'
```
