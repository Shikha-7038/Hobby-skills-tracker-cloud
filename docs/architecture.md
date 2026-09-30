# System Architecture

## 1. High-level architecture

```mermaid
flowchart TB
    subgraph Client["Client (browser / mobile browser)"]
        FE["React SPA (Vite)"]
    end

    subgraph API["Backend — FastAPI (deployed on a PaaS host)"]
        Routes["REST routes\n/api/*"]
        MW["Middleware\nJWT auth · rate limiting"]
        Services["Service layer\nownership checks · validation"]
    end

    subgraph Cloud["Managed cloud services (Supabase)"]
        Auth["Supabase Auth\n(identity, JWT issuance)"]
        DB[("Supabase PostgreSQL\n(structured data)")]
        Storage[("Supabase Storage\n(files/images, S3-compatible)")]
    end

    FE -- "HTTPS / JSON + Bearer token" --> Routes
    Routes --> MW --> Services
    Services -- "verify token" --> Auth
    Services -- "SQL via client library" --> DB
    Services -- "upload / signed URL" --> Storage
    Storage -- "signed URL response" --> FE
```

**Why the frontend never talks to Supabase directly in this project:** the
service-role key needed for some operations (e.g. deleting another table's
rows on cascade) must never reach the browser. Routing every request through
FastAPI keeps that key server-side only, and lets the backend enforce
ownership rules (`docs/security_and_privacy.md`) that a client-only app
cannot be trusted to enforce.

## 2. Request lifecycle (example: logging a practice session)

```mermaid
sequenceDiagram
    participant U as User (browser)
    participant R as FastAPI route
    participant M as Auth middleware
    participant S as PracticeService
    participant G as GoalService
    participant D as Supabase PostgreSQL

    U->>R: POST /api/practice {skill_id, duration_minutes, ...}
    R->>M: verify bearer token
    M-->>R: user_id
    R->>S: log_session(user_id, payload)
    S->>D: insert practice_sessions row
    S->>G: apply_progress(skill_id, hours)
    G->>D: update goals.current_value
    G->>D: check + update milestones.achieved
    G-->>S: newly achieved milestones
    S->>D: read all sessions for streak calc
    S-->>R: {session, milestones_achieved, streaks}
    R-->>U: 201 Created (JSON)
```

## 3. Cloud provider abstraction

The single biggest architectural decision in this project: **every cloud
capability is behind an interface**, with two implementations.

```mermaid
classDiagram
    class AuthService {
        <<abstract>>
        +register()
        +login()
        +verify_token()
    }
    class DatabaseService {
        <<abstract>>
        +insert()
        +select()
        +update()
        +delete()
    }
    class StorageService {
        <<abstract>>
        +upload()
        +delete()
        +signed_url()
    }

    AuthService <|-- SupabaseAuth
    AuthService <|-- LocalAuth
    DatabaseService <|-- SupabaseDatabase
    DatabaseService <|-- LocalDatabase
    StorageService <|-- SupabaseStorage
    StorageService <|-- LocalStorage
```

`cloud/factory.py` reads `CLOUD_PROVIDER` from the environment and builds
the matching trio. Every route and service is written against the abstract
interface, so **the exact same `backend/` code is what runs in local
simulation and in the deployed cloud version** — nothing is mocked out or
reimplemented for "demo mode."

## 4. Cloud computing concepts, mapped to code

See the table in the main `README.md` §3 for the full list. The two most
important ones to be able to explain out loud:

- **Authentication vs. authorization.** Authentication ("who are you?")
  happens once, in `backend/middleware/auth_middleware.py`, by verifying the
  JWT. Authorization ("are you allowed to touch *this* row?") happens
  separately, per-write, next to the data it protects — e.g.
  `SkillService._owned_skill()` checks `skill.user_id == caller_id` before
  any update or delete.
- **Serverless / elastic scaling.** The FastAPI process keeps no
  request-to-request state in memory (all state lives in the managed
  database), so a PaaS host can run zero, one, or many copies of it behind
  a load balancer without any code change — see
  `docs/scalability_and_reliability.md`.

## 5. Deployment topology

```mermaid
flowchart LR
    subgraph Internet
        User((Browser))
    end
    subgraph Hosting["Free-tier PaaS (e.g. Render / Railway / Fly.io)"]
        API["FastAPI container"]
    end
    subgraph StaticHost["Static hosting (e.g. Vercel / Netlify)"]
        SPA["React build (static files, served via CDN)"]
    end
    subgraph Supabase
        SAuth[Auth]
        SDB[(PostgreSQL)]
        SStorage[(Storage)]
    end

    User -->|HTTPS| SPA
    SPA -->|HTTPS fetch /api/*| API
    API --> SAuth
    API --> SDB
    API --> SStorage
```
