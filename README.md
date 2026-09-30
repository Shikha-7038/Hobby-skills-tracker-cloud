# Practice Log — Online Hobby & Skills Tracker with Community Sharing on Cloud

A cloud-backed web app for tracking hobbies and skills: log practice sessions,
set goals with milestones, build streaks, and share progress with a
community feed (likes, comments, optional follows).

Built as a **Cloud Computing course project** — the point isn't just "a
social app," it's demonstrating a working cloud architecture: managed
authentication, a managed database, object storage, a REST API, and a
deployable cloud service, with a **local-simulation mode** that runs the
exact same code offline for development and grading.

---

## 1. Project Explanation

### A. Simple explanation
Most people quit a hobby not because they lose interest, but because there's
no record of progress and no one to be accountable to. Practice Log fixes
that: every time you practice, you log it. The app turns those logs into
streaks, percentage progress toward goals, and a dashboard you can look back
on. You can also post an update — "completed 30 hours of guitar practice!" —
and people following your hobby can like and comment on it.

## 🔗 Live Demo
- **App:** https://hobby-skills-tracker-cloud.vercel.app

### B. Technical explanation
The frontend (React) never talks to the database or file storage directly.
Every action goes through a REST API (FastAPI) which:
1. verifies the caller's identity via a bearer token (**cloud authentication**),
2. checks the caller **owns** the row they're trying to change (**authorization**),
3. reads/writes structured data in a **cloud database** (Supabase PostgreSQL),
4. reads/writes files in **cloud object storage** (Supabase Storage), and
5. returns JSON.

Because the frontend only ever calls `https://your-api/api/...`, a user's
data is available the moment they log in on a **different device** — nothing
is stored only in the browser. The same `backend/` and `frontend/` code runs
against a `local` cloud provider (in-memory database, disk-based storage, a
locally-issued JWT) so the whole app is fully testable with **no internet
connection and no cloud account**.

### Data flow (also see `docs/architecture.md` for the diagram)
```
User → Register/Login → Cloud Authentication → Create Hobby/Skill → Set Goal
     → Record Practice → Cloud Database → Progress Calculation
     → Upload Achievement Proof → Cloud Object Storage
     → Share Community Post → Community Feed → Likes/Comments/Interaction
```

---

## 2. Industry relevance

The same architecture (managed auth + managed DB + object storage + REST API
+ community feed + analytics) powers:

| Industry example | What it shares with this project |
|---|---|
| Duolingo, language apps | streaks, daily-practice logging, progress % |
| Strava, fitness trackers | session logging, personal analytics, social feed |
| LinkedIn Learning, Coursera | skill tracking, course/goal progress, certificates as uploaded proof |
| GitHub, portfolio platforms | user-generated content, profile pages, public sharing |
| Employee L&D portals | per-user learning goals, manager-visible progress dashboards |
| Any EdTech / LMS | centralized user data, cross-device access, analytics |

**Business benefits this architecture gives you for free:** centralized
user data (one source of truth instead of per-device storage), cross-device
access, community engagement (feed + likes/comments drive retention),
storage that scales independently of the app server, user-generated content
without you hosting files on your own disk, built-in analytics, and a
codebase that can move from a free tier to a paid cloud tier without a
rewrite.

---

## 3. Cloud computing concepts demonstrated

| Concept | Where it appears in this project |
|---|---|
| Cloud computing | The whole app runs against managed, internet-hosted services (Supabase) rather than a server you maintain yourself |
| SaaS | Supabase itself — you consume auth/DB/storage as a service, no server admin |
| PaaS | The backend is deployed to a platform (Render/Railway/Fly.io) that runs your code without you managing the OS |
| IaaS (where applicable) | Not used directly (see `docs/architecture.md` for how Option C would use it) |
| Cloud database | `cloud/database_service.py` → `SupabaseDatabase` (managed PostgreSQL) |
| Object storage | `cloud/storage_service.py` → `SupabaseStorage` (S3-compatible bucket) |
| Authentication | `cloud/auth_service.py` → `SupabaseAuth` (managed identity, hashed passwords, signed JWTs) |
| Authorization | Every service method checks `row.user_id == caller_id` before a write — see `backend/services/*.py` |
| REST API | `backend/routes/*.py` — resource-oriented endpoints over HTTP, see `docs/api_reference.md` |
| Client-server architecture | React (client) never touches the DB/storage directly; FastAPI (server) mediates everything |
| Serverless computing | The backend, deployed as a container that scales to zero on idle, behaves serverlessly on free-tier PaaS hosts |
| Event-driven architecture | Logging a practice session triggers a chain of side effects (goal progress → milestone check → streak recompute) inside one request — see `PracticeService.log_session` |
| Scalability / elasticity | Stateless API + managed DB/storage that scale independently — see `docs/scalability_and_reliability.md` |
| Availability | Managed services provide uptime SLAs beyond what a single self-hosted server could offer |
| CDN | Static frontend assets are served through the hosting platform's CDN edge network |
| Load balancing | Handled transparently by the PaaS host in front of the FastAPI container |
| API Gateway | FastAPI itself acts as the single entry point/gateway for all client requests |
| Caching | Signed-URL caching in `SupabaseStorage`; browser HTTP caching for static assets |
| Environment variables | All secrets/config load from `.env` via `backend/config.py` — never hardcoded |
| Secrets management | Service-role keys live only in backend environment variables, never shipped to the frontend |
| Logging | Structured logging in `backend/app.py`; every unhandled error is logged server-side |
| Monitoring | `/api/health` endpoint for uptime checks; hosting-platform dashboards for CPU/memory/logs |
| Backup | Managed PostgreSQL (Supabase) includes automatic backups on its free/pro tiers |
| CI/CD | `.github/workflows/ci.yml` runs the automated test suite on every push |
| Cloud deployment | `docs/deployment_guide.md` — step-by-step deploy to Supabase + a free-tier PaaS host |

---

## 4. Technology stack options

### Option A — Beginner
**Frontend:** HTML/CSS/JS · **Backend:** Python Flask · **Database:** SQLite ·
**Storage:** local `uploads/` folder.
*Purpose:* complete local simulation before touching the cloud at all.
*Difficulty:* low. *Cost:* $0. *Limitations:* single device, no real auth,
no cloud storage, doesn't demonstrate managed cloud services.

### Option B — Recommended cloud version (**this repository**)
**Frontend:** React · **Backend:** Python FastAPI · **Authentication:**
Supabase Auth · **Database:** Supabase PostgreSQL · **Storage:** Supabase
Storage · **Deployment:** a free-tier, student-friendly host.
*Difficulty:* moderate. *Cost:* $0 on free tiers. *Advantages:* real managed
auth/DB/storage, a proper REST API, still deployable by a student with no
credit card. *Limitations:* single-region free tier, modest storage/row
limits, no CDN/API gateway of its own (the PaaS host provides basic
versions of both).
*Cloud concepts demonstrated:* every item in the table above.

---

## 5–16. Feature modules

Everything below is implemented and documented in code comments at the
listed path — this README summarizes; the code is the source of truth.

| Module | Where | Docs |
|---|---|---|
| 5. User profile | `backend/services/profile_service.py`, `backend/routes/profile_routes.py` | public vs. private view, profile picture via object storage |
| 6. Hobby & skill management | `backend/services/skill_service.py` | `createSkill/updateSkill/deleteSkill/getMySkills/getSkillDetails` |
| 7. Goal & milestone tracking | `backend/services/goal_service.py` | progress % formula + capping explained in the module docstring |
| 8. Practice session tracking | `backend/services/practice_service.py` | **streak calculation is explained in detail in the module docstring** |
| 9. Cloud database design | `cloud/database_service.py`, `docs/er_diagram.md`, `docs/schema.sql` | ER diagram, keys, indexes, relational-vs-NoSQL discussion |
| 10. Cloud object storage | `cloud/storage_service.py`, `backend/services/file_service.py` | storage path layout, signed URLs, public/private permissions |
| 11. Community sharing | `backend/services/post_service.py` | createPost / feed / deleteOwnPost |
| 12. Likes & comments | `backend/services/social_service.py` | duplicate-like prevention via composite primary key |
| 13. Optional follow system | `backend/services/social_service.py` | follow/unfollow/getFollowers/getFollowing |
| 14. User dashboard | `analytics/progress_service.py` | practice hours by skill, weekly trend, monthly trend, goal completion, skill distribution |
| 15. Community dashboard | `backend/routes/search_routes.py` (`/api/community/trending`) | trending categories this week |
| 16. REST API design | `backend/routes/*.py` | full endpoint table in `docs/api_reference.md` |

---

## Quick start

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Cloud mode only) a free [Supabase](https://supabase.com) project

### Run locally (no cloud account needed)
```bash
# 1. Backend
cd backend/..                     # repo root
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # defaults are already set to CLOUD_PROVIDER=local
uvicorn backend.app:app --reload  # http://localhost:8000

# 2. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env
npm run dev                       # http://localhost:5173
```
Register an account in the browser — everything is stored in
`sample_data/local_store/` as JSON, so you can delete that folder any time
to reset. See `docs/deployment_guide.md` to switch `CLOUD_PROVIDER=supabase`
and deploy for real.

### Run the automated tests
```bash
pip install -r requirements.txt
pytest tests/ -v
```
See `docs/testing.md` for the full 27-case test matrix and what each test
proves.

---

## Project folder structure

```
Cloud-Hobby-Skills-Tracker/
├── backend/                 # FastAPI app
│   ├── app.py                # entrypoint, wiring, error handlers
│   ├── config.py              # env-driven settings
│   ├── models/schemas.py      # row shapes + factory functions
│   ├── routes/                 # one file per resource (auth, skills, goals, ...)
│   ├── services/                # business logic + ownership checks
│   ├── middleware/               # auth dependency, rate limiting
│   └── utils/validation.py        # shared input validation
├── cloud/                   # provider-agnostic cloud abstraction
│   ├── auth_service.py        # SupabaseAuth / LocalAuth
│   ├── database_service.py    # SupabaseDatabase / LocalDatabase
│   ├── storage_service.py     # SupabaseStorage / LocalStorage
│   └── factory.py             # builds the right trio from CLOUD_PROVIDER
├── analytics/progress_service.py  # dashboard aggregation
├── frontend/                # React app (Vite)
│   └── src/{pages,components,services,context,utils,styles}
├── tests/                   # pytest suite (27 test-ID scenarios)
├── docs/                    # architecture, schema, API, security, report, ...
├── sample_data/              # seed script + local-mode JSON store (gitignored)
├── .github/workflows/ci.yml # automated tests on every push
├── requirements.txt
└── .env.example
```

---


## Further documentation

- `docs/architecture.md` — system architecture + diagrams
- `docs/er_diagram.md` / `docs/schema.sql` — database design
- `docs/api_reference.md` — full REST endpoint reference
- `docs/security_and_privacy.md` — auth, authorization, secure uploads, moderation
- `docs/scalability_and_reliability.md` — scaling limits, failure handling, cloud analytics
- `docs/deployment_guide.md` — local simulation + cloud deployment steps
- `docs/testing.md` — 27-case test matrix + automated tests
- `docs/github_and_proof.md` — commit strategy, proof-of-work, screenshot checklist
- `docs/project_report.md` — full written report
- `docs/resume_and_interview_prep.md` — resume bullets, LinkedIn copy, interview Q&A

## Known Limitations
- Follow/unfollow, viewing another user's public profile, and reporting a
  post are implemented on the backend (see `docs/api_reference.md`) but
  don't yet have buttons in the frontend UI.
- Marking a goal as "abandoned" is only possible via the API (`/docs`),
  not yet from the goal detail page.
- Free-tier hosting (Render) sleeps after inactivity — the first request
  after idle time can take 30–50 seconds to respond.

## License
This is a student coursework project built for learning purposes, using only
dummy/synthetic data. Use freely for your own learning.
