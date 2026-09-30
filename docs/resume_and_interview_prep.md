# Resume, LinkedIn & Interview Preparation

## A. Resume bullet points

- Designed and built a cloud-native hobby/skills-tracking platform on
  **FastAPI + React**, with a provider-agnostic cloud layer (auth, database,
  object storage) that runs identically against **Supabase** in production
  and a local simulation offline, enabling zero-cost development and grading.
- Implemented **JWT-based authentication with refresh-token rotation**,
  per-request **authorization checks** enforcing row-level data ownership,
  and **content-based file validation** for secure image uploads to cloud
  object storage with time-limited signed URLs.
- Built a **REST API with 30+ endpoints** covering skill/goal tracking,
  automatic progress and streak calculation, a community feed with
  database-enforced duplicate-like prevention, and an analytics dashboard —
  covered by an **automated test suite of 27 scenarios** running in CI.

## B. Two-line project description

Built a cloud-backed hobby and skills tracker (React + FastAPI + Supabase)
where users log practice, track goal progress and streaks, and share
achievements in a community feed — with full authentication, authorization,
object storage, and a REST API, deployed on free-tier cloud infrastructure.

## C. Professional LinkedIn project description

> **Online Hobby & Skills Tracker — Cloud Computing Project**
>
> I designed and built a full-stack, cloud-native application for tracking
> hobby and skill practice, from the ground up: a React frontend, a FastAPI
> REST backend, and a provider-agnostic cloud services layer supporting
> Supabase (managed authentication, PostgreSQL, and object storage) with a
> fully-featured local simulation mode for offline development.
>
> The project covers the full loop of a modern cloud application:
> authenticated, authorized, user-specific data; a normalized relational
> schema with composite-key constraints enforcing business rules at the
> database level; secure file uploads validated by content rather than
> filename, served through private, time-limited signed URLs; a community
> feed with likes, comments, and moderation; a personal analytics dashboard;
> and a codebase covered by 27 automated test scenarios running in CI,
> deployed on free-tier cloud infrastructure.
>
> Tech: React, FastAPI, Python, PostgreSQL (Supabase), Supabase
> Auth/Storage, pytest, GitHub Actions.

## D. Technical skills demonstrated

Cloud architecture design · REST API design · relational database design
(PostgreSQL) · authentication & authorization · secure file upload handling
· object storage & signed URLs · React (hooks, context, component design) ·
Python (FastAPI, Pydantic) · automated testing (pytest) · CI/CD (GitHub
Actions) · Git/GitHub workflow · technical documentation & system-diagramming.

## E. GitHub repository description (short, for the repo's "About" field)

> Cloud-backed hobby & skills tracker — React + FastAPI + Supabase. Log
> practice, track goals/streaks, share progress in a community feed. Full
> local-simulation mode, 27-scenario test suite, CI, and deployment guide.

---

## Interview Preparation — 10 questions & answers

### 1. Explain your project.
"It's a cloud-backed app for tracking hobbies and skills — you create a
hobby, set a goal like 'practice 30 hours,' log practice sessions against
it, and the app calculates your progress percentage and a daily streak
automatically. You can also share updates to a community feed that other
users can like and comment on. Architecturally, the point of the project
wasn't just 'build a tracker' — it was to demonstrate a real cloud stack:
a React frontend that only talks to a REST API, a FastAPI backend that
owns all the business logic and authorization, and a Supabase-backed cloud
layer for authentication, the database, and file storage. I also built a
local-simulation mode so the exact same backend code runs fully offline,
which is what I used for development and testing before deploying it for
real."

### 2. Why did you choose Supabase over Firebase/AWS for this project?
"Firebase's Firestore is a great NoSQL option, but my data is heavily
relational — goals belong to skills, which belong to users, milestones
belong to goals — and I wanted to practice SQL and relational schema
design, including using database-level constraints (like a composite
primary key) to enforce business rules, which is harder to express cleanly
in a document database. AWS/Azure/GCP would demonstrate more
industry-standard services, but usually needs a credit card and more
networking/IAM knowledge than a student project needs to prove the same
underlying concepts. Supabase gave me a managed Postgres database, managed
auth, and object storage, all on a free tier with no card required — and I
specifically wrote the `cloud/` layer as an interface, so swapping in AWS
later wouldn't require touching any business logic."

### 3. How does your cloud database design work? Walk me through the schema.
"There are eleven tables. `users`, `skills`, `goals`, and
`practice_sessions` are the core tracking tables — a user has many skills,
a skill has many goals, a goal has many milestones. On the community side,
`posts`, `comments`, `likes`, and `follows` handle sharing. One design
decision I'm proud of: `likes` uses a composite primary key,
`"<post_id>:<user_id>"`, instead of an auto-increment ID. That means 'a
user can only like a post once' isn't just an application-level check I
have to remember to write everywhere — it's enforced by the database
itself. A second insert attempt just fails with a duplicate-key error,
even under a race condition."

### 4. How does object storage work in your app, and why not just store images in the database?
"The database only ever stores a storage *path* as a string — the actual
image bytes live in a Supabase Storage bucket, which is private, not
public. Whenever the frontend needs to display an image, the backend
generates a signed URL — a time-limited link, an hour by default — rather
than a permanent public URL. That's both more secure and cheaper at scale:
databases are expensive to store large binary blobs in and don't scale for
that the way object storage does. I also validate every upload by
inspecting the actual file bytes — the magic number at the start of the
file — instead of trusting the browser's Content-Type header or the file
extension, both of which a client can spoof."

### 5. How does authentication differ from authorization in your implementation?
"Authentication happens once per request, in a FastAPI dependency that
verifies the bearer token and extracts a user ID — that answers 'who is
calling?' Authorization is separate and happens inside each service method,
right next to the data — for example, before updating a skill, I check
`skill.user_id == caller_id` and raise a 403 if it doesn't match. I keep
these separate on purpose: authentication is generic and reusable across
every endpoint, but authorization rules are specific to each resource, so
they live with that resource's service code, not in a single global
'permissions' file that would get harder to reason about as the app grows."

### 6. What does your REST API look like, and why REST instead of GraphQL?
"It's resource-oriented — `/api/skills`, `/api/goals`, `/api/posts`, and so
on, with standard HTTP verbs for create/read/update/delete. I chose REST
because the data-access patterns are simple and well-known upfront (get my
skills, get a post's comments) rather than needing GraphQL's flexible
querying for deeply nested, client-driven shapes. REST also made it
straightforward to document with FastAPI's automatic OpenAPI/Swagger docs,
which I used constantly while building the frontend against the API."

### 7. How would this app handle community feed features at a much larger scale — say, a million users?
"A few things would need to change. First, my feed pagination currently
uses `OFFSET`, which gets slow on a huge table — I'd switch to
keyset/cursor pagination, filtering on `created_at < last_seen_timestamp`
instead. Second, my rate limiter currently lives in each backend process's
memory, which doesn't work once you're running multiple instances behind a
load balancer — that would move to a shared store like Redis. Third, my
analytics dashboard currently recomputes everything from raw rows on every
request; at scale I'd precompute daily rollups on a schedule instead. The
backend itself is already stateless, so horizontally scaling the number of
API instances wouldn't require any code change — that part was a deliberate
design choice from the start."

### 8. What security measures did you implement?
"A few layers: passwords are hashed by the auth provider, never handled in
plaintext by my code; sessions use short-lived JWTs with a separate
refresh token; every write checks resource ownership before proceeding;
file uploads are validated by actual byte content, not just filename or
declared MIME type, with a size cap enforced before the file even reaches
storage; all files are private and only ever accessed via signed URLs; and
every secret — API keys, JWT secrets — is loaded from environment
variables and never committed to source control, which I enforced with
`.gitignore` and a documented `.env.example`."

### 9. How did you test this project?
"Two layers. Pure business logic — streak calculation, progress
percentage — has unit tests with no network or database involved at all,
since those are just functions of dates and numbers. Then I have
HTTP-level tests using FastAPI's TestClient that exercise the full request
path — register a user, hit a protected endpoint, assert the right status
code — covering 27 defined scenarios: normal cases like creating a goal,
but also failure cases like a second user trying to delete someone else's
post, or the database itself being simulated as unreachable to confirm the
API degrades to a clean 503 instead of crashing. Those tests run
automatically in GitHub Actions on every push."

### 10. What would you do differently, or what's the biggest limitation of your current design?
"The honest answer: analytics are computed live on every dashboard
request by scanning a user's raw session rows. That's completely fine at
the scale this project runs at, but it's the first thing that would need
to change for a large user base — I'd move to precomputed, periodically
refreshed summary rows instead of recomputing from scratch every time.
I also don't have real-time updates — if someone likes your post, you
don't see it until you refresh the feed. Given more time I'd add that via
WebSockets or Supabase's realtime subscriptions, since the data model
already supports it; it just wasn't necessary to prove the core cloud
concepts this project was built to demonstrate."
