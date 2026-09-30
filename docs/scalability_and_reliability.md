# Scalability, Cloud Analytics & Failure Handling

## 1. Scalability

**Stateless backend.** `backend/app.py` keeps zero per-user state in process
memory (every service reads/writes through `app.state.cloud`, backed by the
managed database) except the rate limiter's request counters. That means a
PaaS host can run 1 instance or 20 identical instances of the FastAPI
container behind a load balancer with no code change — this is what "the
backend scales horizontally" means concretely here.

**Elasticity in practice on the free tier.** Most student-friendly hosts
(Render, Railway, Fly.io) scale a free-tier service to zero when idle and
spin a new instance up on the next request (with a cold-start delay). That
*is* elasticity — the same mechanism a paid autoscaling group uses, just
tuned for "close to $0" instead of "handle a traffic spike."

**Where this design would need to change at real scale:**

| Bottleneck at scale | Current approach (fine up to ~thousands of users) | What replaces it |
|---|---|---|
| Feed pagination | `OFFSET`-based (`post_service.py`) — `OFFSET 100000` gets slow | Keyset/cursor pagination (`WHERE created_at < :cursor`) |
| Fan-out on a like/comment | Synchronous counter update in the same request | Async event (queue) updates a denormalized counter |
| Rate limiting | In-process memory, per backend instance | Shared store (Redis) so limits apply across all instances |
| Signed URL generation | Called per-request, cached in memory per instance | A CDN in front of storage + longer-lived signed URLs |
| Analytics dashboard | Recomputed from raw rows on every request | Precomputed/materialized daily rollups, refreshed on a schedule |
| Practice-session writes | Single-region managed Postgres | Read replicas for the dashboard's read-heavy queries |

**Database indexing** (see `docs/er_diagram.md`) is what keeps the current
design fast well past a "class project" scale: every list query the app
makes (a user's skills, a user's sessions, the public feed sorted by date)
hits an index, not a full table scan.

## 2. Cloud analytics

`analytics/progress_service.py` is a separate module from
`backend/services/` on purpose: analytics reads *across* several tables at
once (sessions, skills, goals, posts) rather than owning one table, so it
doesn't belong inside any single-resource service.

What it computes, and how:
- **Total / weekly / monthly practice time** — sums `practice_sessions.duration_minutes`, filtered by date range computed in Python (ISO week boundaries, calendar-month prefix match).
- **Practice hours by skill / skill category distribution** — `collections.Counter` grouped by `skill_id`/`category`.
- **Weekly and monthly trend lines** — minutes bucketed by ISO week (`YYYY-Www`) and by month (`YYYY-MM`), used directly as chart X-axis labels.
- **Streaks** — delegates to `PracticeService.compute_streaks` (see its docstring for the full algorithm) so the "current streak" logic exists in exactly one place.
- **Goal completion breakdown** — counts goals by `status` for a pie chart.
- **Community engagement** — sums `like_count`/`comment_count` across the user's own posts.

At real scale this endpoint would move from "compute on every request" to
"read a precomputed summary row, refreshed by a scheduled job" — the
function signatures wouldn't need to change, only what's inside them.

## 3. Failure handling

Every external dependency this app has (the auth provider, the database,
object storage) can be unreachable, and the app is written to fail
*gracefully*, not crash:

```python
# cloud/database_service.py
class DatabaseError(Exception): ...

# backend/app.py
@app.exception_handler(DatabaseError)
def handle_database_error(request, exc):
    logger.error("Database error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=503, content={
        "message": "We couldn't reach the database. Please try again in a moment."})
```

The same pattern exists for `StorageError` and `AuthError`. This is
deliberately tested, not just asserted in prose: `tests/test_analytics_and_failures.py`
swaps in a fake storage/database object that always raises, then asserts
the API returns a clean `503` with a user-readable message instead of a
raw stack trace or a `500`.

**Retry behavior on the client.** `frontend/src/services/api.js`'s
`apiRequest` treats a `401` specially — it transparently refreshes the
access token once and retries the original request — so a token expiring
mid-session doesn't interrupt the user's flow with a confusing error.

**What a production deployment would add on top:**
- Automatic retries with exponential backoff for transient (not
  permanent) database errors.
- A circuit breaker so a fully-down dependency fails fast instead of
  letting every request hang until it times out.
- An incident-status page fed by the `/api/health` check.
