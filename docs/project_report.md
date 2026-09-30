# Project Report: Online Hobby & Skills Tracker with Community Sharing on Cloud

## Abstract
This project is a cloud-backed web application that helps individuals build
and maintain hobbies and skills by logging practice sessions, tracking goals
and milestones, visualizing progress through streaks and analytics, and
sharing achievements with a community feed. It is implemented as a React
single-page frontend and a Python FastAPI backend, built against a
provider-agnostic cloud abstraction layer that runs identically against a
fully offline local simulation and against managed cloud services
(Supabase Authentication, PostgreSQL database, and object storage). The
project demonstrates, in working code rather than only in theory, the core
concepts of a Cloud Computing course: managed authentication and
authorization, a cloud-hosted relational database, cloud object storage
with signed URLs, a REST API, stateless/scalable backend design, structured
error handling for cloud-dependency failures, and a deployable, tested,
version-controlled codebase.

## Introduction
Hobby and skill development is a long-tail, self-directed activity with no
built-in structure — unlike a class or a job, there is no external deadline
forcing consistency. This project treats "showing up regularly" as the
central design problem and builds the smallest set of features that
directly support it: a place to log a session in under 30 seconds, a
visible number (a streak, a percentage) that rewards consistency, and a
low-friction way to share progress with other people, which research on
habit formation consistently shows increases follow-through.

## Problem Statement
People starting a new hobby or skill frequently abandon it within the first
few weeks, not from lack of interest but from lack of structure,
measurable progress, and social accountability. Existing solutions are
either too broad (general note-taking apps, with no notion of streaks or
goals) or too narrow (single-purpose trackers for one activity, like a
running app that cannot track piano practice). There is no lightweight,
general-purpose, cloud-accessible tool for logging practice across
*any* hobby and sharing that progress with others.

## Objectives
1. Let a user register, create hobbies/skills, set measurable goals with
   milestones, and log practice sessions against them.
2. Automatically calculate progress percentage, practice streaks, and
   time-based totals (weekly/monthly) from raw session logs.
3. Let users upload proof (images) of achievements to cloud object storage.
4. Provide a community feed where users can share updates and interact via
   likes and comments, with basic moderation (reporting, deletion).
5. Provide a personal analytics dashboard summarizing progress visually.
6. Demonstrate managed cloud authentication, a managed cloud database, and
   cloud object storage, accessed exclusively through a REST API.
7. Ship a fully working **local-simulation mode** requiring no cloud account,
   for development, grading, and offline demoing.
8. Deploy the application for real, on free-tier cloud infrastructure.
9. Cover the system with automated tests and document it thoroughly enough
   for another developer (or a reviewer) to understand it without the
   original author present.

## Existing System
Manual tracking (a paper journal, a personal spreadsheet, or scattered
notes-app entries) is the status quo for most hobbyists. It has no
streaks, no progress visualization, no cross-device access, and no social
accountability loop. General-purpose habit-tracker apps exist, but are
typically closed-source, mobile-only, and not built as an educational
demonstration of cloud architecture — a gap this project fills for a
student audience specifically.

## Proposed System
A cloud-backed system with a clear three-tier separation: a React frontend
that only ever calls a REST API; a FastAPI backend that owns all business
logic, validation, and authorization; and a swappable cloud-services layer
(`cloud/`) providing authentication, database, and storage behind small
abstract interfaces, with two implementations each — a managed cloud
provider (Supabase) and a fully local, dependency-free simulation. This
design was chosen specifically so the *same application code* is what a
student runs locally to develop and what actually gets deployed, rather
than maintaining a separate "demo mode."

## Industry Relevance
See `README.md` §2 for the full comparison table. In short: this
architecture — managed auth, managed relational database, object storage
referenced by path (not embedded as blobs), a REST API mediating all
client access, and a community feed with engagement metrics — is the same
shape used by learning platforms (Coursera, LinkedIn Learning), fitness
trackers (Strava), and employee learning-and-development portals. The
skills demonstrated here (designing a normalized schema, enforcing
ownership at the API layer, handling file uploads securely, building an
analytics aggregation layer) transfer directly to those domains.

## Cloud Computing Concepts
See `README.md` §3 and `docs/architecture.md` for the concept-by-concept
mapping to specific files and functions. The project deliberately touches
every concept a first cloud-computing course expects to see demonstrated:
authentication vs. authorization, cloud database vs. object storage,
REST APIs, client-server architecture, statelessness/elasticity, CDN and
load balancing (provided by the hosting platform), environment-variable-based
secrets management, structured logging, and CI/CD.

## Technology Stack
**Frontend:** React 18 (Vite), a small hand-written hash router (no
external routing dependency), Recharts for the analytics dashboard.
**Backend:** Python 3.12, FastAPI, Pydantic for request validation,
PyJWT for local-mode token signing.
**Cloud services:** Supabase (Auth, PostgreSQL, Storage) in cloud mode; an
in-memory/JSON-backed simulation in local mode — see `cloud/factory.py`.
**Testing:** pytest + FastAPI's `TestClient`.
**CI/CD:** GitHub Actions.
**Deployment:** a free-tier PaaS host for the backend (Render/Railway/Fly.io)
and static hosting with CDN for the frontend (Vercel/Netlify).
Full option comparison (A/B/C) is in `README.md` §4.

## System Architecture
See `docs/architecture.md` for the full diagram set (high-level component
diagram, a request-lifecycle sequence diagram for logging a practice
session, the cloud-provider abstraction class diagram, and the deployment
topology diagram).

## Database Design
See `docs/er_diagram.md` (entity-relationship diagram, both as a Mermaid
diagram and a plain-text diagram) and `docs/schema.sql` (the actual
PostgreSQL DDL, including indexes and Row Level Security policies). Eleven
tables: `users`, `skills`, `goals`, `milestones`, `practice_sessions`,
`posts`, `comments`, `likes`, `follows`, `files`, `reports`. Composite
primary keys (e.g. `likes.like_id = "<post_id>:<user_id>"`) are used
deliberately to turn business rules ("one like per user per post") into
database-level constraints rather than application-only logic.

## Cloud Storage Design
Files are never stored in the database — only a `storage_path` reference
is. The actual bytes live in a private Supabase Storage bucket, organized
as `users/<user_id>/{profile,skills/<skill_id>,posts}/<file_id>.<ext>`.
Every read goes through a time-limited signed URL
(`StorageService.signed_url`), and every upload is validated by
inspecting the file's real magic bytes rather than trusting the
client-supplied MIME type or file extension. See
`docs/security_and_privacy.md` §3–4 for the full explanation.

## Authentication
Managed by Supabase Auth in cloud mode (passwords hashed and stored by the
provider) or by a from-scratch PBKDF2 + signed-JWT implementation in local
mode (`cloud/auth_service.py`) — both behind the same `AuthService`
interface so the rest of the app is provider-agnostic. Sessions use a
short-lived access token plus a rotating refresh token; the frontend
transparently refreshes an expired token once and retries the failed
request.

## Hobby & Skill Tracking
`backend/services/skill_service.py` implements `createSkill`,
`updateSkill`, `deleteSkill`, `getMySkills`, `getSkillDetails`, each
enforcing that only the owning user can read or modify their own rows
(non-owner access to skill details returns `404`, not `403`, to avoid
confirming a given ID exists).

## Practice Tracking
`backend/services/practice_service.py` logs sessions and, in the same
request, updates goal progress and checks for newly achieved milestones.
The **streak calculation algorithm is explained in full, with a worked
example, in that file's module docstring** — summarized: the current
streak is the number of consecutive calendar days, ending today or
yesterday, with at least one logged session across any skill.

## Goal Management
`backend/services/goal_service.py` implements the exact formula from the
brief: `progress_percent = min(100, current_value / target_value * 100)`,
capped at 100% so overshooting a goal still displays cleanly. Milestones
are checked and marked `achieved` automatically every time practice is
logged.

## Community Sharing
`backend/services/post_service.py` and `social_service.py` implement
`createPost`, a paginated `getCommunityFeed` (with `recent`/`top` sort and
an optional "following only" filter), `deleteOwnPost` (owner or moderator
only), like/unlike with database-enforced duplicate prevention, comments,
and an optional follow graph.

## Analytics
`analytics/progress_service.py` aggregates practice totals (all-time,
weekly, monthly), practice time by skill and by category, a weekly/monthly
trend series for charting, goal-completion counts, streaks, and community
engagement (likes/comments received) into one dashboard payload consumed by
the React frontend's Recharts visualizations.

## API Design
A resource-oriented REST API — see `docs/api_reference.md` for the full
endpoint table. Every endpoint returns JSON; errors follow a consistent
`{"message": ..., "field": ...}` shape mapped to a meaningful HTTP status
code (`401`/`403`/`404`/`422`/`429`/`503`).

## Implementation
The codebase is organized into four layers with a strict dependency
direction: `cloud/` (no knowledge of the app's domain — pure
auth/db/storage interfaces) → `backend/services/` (business logic +
authorization, depends only on `cloud/` interfaces) → `backend/routes/`
(HTTP concerns only — parsing requests, calling a service, mapping
exceptions to status codes) → `backend/app.py` (wiring). This makes each
layer independently testable and keeps a route handler from ever
containing business logic that would need duplicating if a second client
(e.g. a mobile app) were added later.

## Testing
27 test-ID scenarios covering authentication, authorization, CRUD
operations, progress/streak calculation, file validation, community
interactions, analytics, data isolation, and simulated cloud-dependency
failures — see `docs/testing.md` for the full matrix and
`tests/` for the automated pytest suite that implements it, run
automatically in CI on every push.

## Cloud Deployment
Documented step by step in `docs/deployment_guide.md`: provisioning
Supabase (database + storage + auth), deploying the FastAPI backend to a
free-tier PaaS host, and deploying the React build to a free static host
with CDN, including the exact environment variables each step requires.

## Security
See `docs/security_and_privacy.md` for the full write-up: password
handling, JWT-based sessions with refresh rotation, per-request
authorization checks colocated with the data they protect, content-based
(not extension-based) file-type validation, private storage with
short-lived signed URLs, environment-variable secrets management, and
basic rate limiting.

## Privacy
Public profile views deliberately exclude email; a full right-to-deletion
flow (`DELETE /api/account`) removes every row a user owns across every
table before deleting their auth identity; content reporting is available
with database-enforced duplicate-report prevention.

## Scalability
See `docs/scalability_and_reliability.md`: the backend is stateless and
scales horizontally without code changes; current pagination and
rate-limiting choices are appropriate at student-project scale, with an
explicit table of what would need to change (keyset pagination, a shared
rate-limit store, precomputed analytics rollups) at real-world scale.

## Results
The system successfully implements the full MVP flow described in the
brief — register, create a hobby, set a goal with milestones, log
practice, watch progress and streaks update automatically, upload an
achievement image, share a community post, and receive likes/comments
from another account — with all 27 defined test scenarios passing, and
runs identically in a fully offline local-simulation mode and against a
real managed cloud backend.

## Advantages
Runs entirely free on managed-service free tiers; the local-simulation mode
means the whole project is gradable/demoable with zero setup friction and
zero cost; the cloud abstraction layer means moving to a different
provider (or to Option C's AWS/Azure/GCP stack) later is a contained change,
not a rewrite; ownership checks are centralized and consistently applied,
reducing the chance of an authorization bug.

## Limitations
Single-region free-tier database (no geographic redundancy); rate limiting
is per-process rather than shared across instances; no real-time
(WebSocket) updates — the feed is refreshed on demand, not pushed; no
automated content-moderation (reports are surfaced to a human moderator
role, not auto-actioned); analytics are computed on read rather than
precomputed, which would need to change well before this reached
production scale.

## Future Scope
Real-time feed updates via WebSockets or Supabase Realtime; push
notifications for milestone achievements and new followers; a mobile app
built on the same REST API; badges/achievements as a first-class feature
beyond milestones; an AI-based hobby-suggestion microservice (scaffolded
as an optional Cloud Run-style service in the original brief); precomputed
analytics rollups for scale; a proper moderation queue UI.

## Conclusion
This project demonstrates that a small, well-structured application can
cover the full breadth of an introductory cloud computing curriculum —
authentication, authorization, a managed database, object storage, REST
APIs, deployment, security, and testing — without requiring a paid cloud
account, while still being architected so that every one of those pieces
could be swapped for a more advanced (e.g. AWS-based) implementation with
contained, well-isolated code changes rather than a rewrite.
