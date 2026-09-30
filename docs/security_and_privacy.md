# Cloud Security, Privacy & Content Moderation

## 1. Authentication

- Passwords are never stored by our own code. In cloud mode, Supabase Auth
  hashes and stores them; in local mode, `LocalAuth` uses PBKDF2-HMAC-SHA256
  with 120,000 iterations and a random 16-byte salt per user
  (`cloud/auth_service.py`).
- Sessions are short-lived signed JWTs (`access_token`, 1 hour by default)
  plus a longer-lived, single-use `refresh_token`. The frontend
  (`frontend/src/services/api.js`) automatically calls `/api/refresh` on a
  `401` and retries the original request once.
- Login failure and "unknown email" both return the same generic `401 Invalid
  email or password`, and `LocalAuth.login` always runs the password hash
  (even for an unknown email, against a dummy salt) so response timing
  cannot be used to enumerate which emails are registered.

## 2. Authorization

Authentication only proves *who* is calling. Every write additionally
checks *what* they're allowed to touch, right next to the data:

```python
# backend/services/skill_service.py
def _owned_skill(self, user_id, skill_id):
    skill = self.db.get("skills", skill_id)
    if not skill:
        raise ValidationError("skill_id", "skill not found")
    if skill["user_id"] != user_id:
        raise NotOwnerError("You can only modify your own skills")
    return skill
```

The same pattern is repeated for goals, posts, comments, and files. A
`GET /api/skills/{id}` for a skill you don't own returns `404`, not `403` —
this avoids confirming to a prober that a given `skill_id` even exists
(see Test 23 in `docs/testing.md`).

A `users.is_moderator` flag allows a small extra permission: moderators can
delete any post/comment (for handling reported content), enforced in
`PostService.delete_own_post` / `SocialService.delete_own_comment`.

## 3. Secure file uploads

`backend/services/file_service.py`:
- **Size limit** enforced before anything touches storage (`MAX_UPLOAD_MB`,
  default 5MB).
- **Type is verified by content, not by trusting the client.** The
  browser-supplied `Content-Type` header and the filename extension are
  both attacker-controlled and are never trusted. Instead, the first bytes
  of the file are checked against the real magic-number signatures for
  JPEG/PNG/GIF/WEBP (`_sniff_image_type`) before upload proceeds.
- **Storage paths are namespaced by owner**
  (`users/<user_id>/profile/...`, `users/<user_id>/skills/<skill_id>/...`,
  `users/<user_id>/posts/...`), and `LocalStorage._resolve()` additionally
  rejects any path that would escape its base directory (blocks `../`
  traversal) even though every path we generate is already safe by
  construction.

## 4. Private files and signed URLs

The Supabase Storage bucket is **private** — nothing is served by public
URL. Every file the frontend displays goes through
`StorageService.signed_url(path, expires_in)`, a time-limited URL that
expires (default: 1 hour). `SupabaseStorage` caches a signed URL in memory
until it's within 5 minutes of expiring, batches URL generation for a whole
feed page in one call (`signed_urls`), and never persists a signed URL to
the database — only the permanent `storage_path` is stored, so URLs are
minted fresh on read and a leaked link naturally stops working.

## 5. Secrets management

- `backend/config.py` reads every credential from environment variables;
  `.env` is listed in `.gitignore` and only `.env.example` (with placeholder
  values) is committed.
- The Supabase **service-role key** (which bypasses Row Level Security) is
  used only in the backend, never sent to the browser. The frontend never
  imports a Supabase SDK or holds any Supabase key at all — it only ever
  talks to our own `/api/*`.
- `Settings.validate()` refuses to start the app in `ENVIRONMENT=production`
  with the default local JWT secret, to stop an accidental unsafe deploy.

## 6. Rate limiting

`backend/middleware/rate_limit.py` applies a simple fixed-window limit
(120 requests/minute per IP by default) to slow down a runaway script or
naive scraper. A production deployment behind multiple backend instances
would move this counter to a shared store (e.g. Redis) — noted in
`docs/scalability_and_reliability.md`.

## 7. Input validation

Every field a user can submit is validated in `backend/utils/validation.py`
before it reaches the database: string length limits, enum membership
(`BEGINNER`/`INTERMEDIATE`/`ADVANCED`, etc.), positive-number checks with a
sane upper bound, email format, username character set, and password
strength (8+ chars, letters + numbers). A `ValidationError` always maps to
HTTP `422` with a `field` name the frontend can highlight.

## 8. Privacy & content moderation

- **Public vs. private profile view.** `ProfileService.to_public_profile()`
  is the *only* representation of a user ever sent to anyone but that user
  — it deliberately omits `email`. `to_private_profile()` (email included)
  is only returned from `/api/profile` (the caller's own).
- **Reporting.** `POST /api/posts/{id}/report` records a report with a
  composite key `"<post_id>:<reporter_id>"`, so one user cannot inflate a
  report count by reporting the same post repeatedly
  (`backend/services/moderation_service.py`).
- **Right to deletion.** `DELETE /api/account` removes the user's profile,
  skills, goals, milestones, practice sessions, posts (and their media),
  comments, likes, follows, and files, then deletes their auth identity —
  verified end-to-end in the integration test in `tests/`. Content other
  people posted (e.g. a comment they left on someone else's post) is not
  touched, since it isn't this user's data to delete.
- **Dummy data only.** Every account used to build/demo/test this project
  is synthetic (`test@example.com`-style addresses); no real personal data
  is stored.

## 9. What a production hardening pass would add

This is a student project and says so honestly: a few things a paid/production
deployment would add on top of the above —
1. A managed rate limiter shared across instances (Redis) instead of
   per-process memory.
2. A Web Application Firewall / managed DDoS protection at the edge.
3. Structured audit logging of moderation actions (who deleted what, when).
4. Automated dependency vulnerability scanning in CI.
5. A dedicated moderation queue UI instead of a raw `reports` table.
