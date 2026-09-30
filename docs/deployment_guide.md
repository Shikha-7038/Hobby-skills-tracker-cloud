# Local Simulation & Cloud Deployment Guide

## Part 1 — Local simulation (no cloud account, no cost)

This is the recommended way to develop and grade the project.

```bash
# from the repository root
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # CLOUD_PROVIDER=local by default — no edits needed
uvicorn backend.app:app --reload
```
In a second terminal:
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Open `http://localhost:5173`. Everything you do is stored as JSON under
`sample_data/local_store/` (git-ignored) — delete that folder any time to
reset to a clean slate. `backend/app.py` also mounts `/media` so images
uploaded in local mode render in the browser exactly like a real signed URL
would in the cloud.

Optionally seed some dummy data first:
```bash
python sample_data/seed_local_data.py
```

## Part 2 — Set up the real cloud backend (Supabase, free tier)

1. Create a free project at [supabase.com](https://supabase.com).
2. In **Project Settings → API**, copy:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY` (⚠️ keep this secret;
     never put it in the frontend or commit it to git)
3. In **SQL Editor**, paste and run `docs/schema.sql` — this creates every
   table, index, and Row Level Security policy the app needs.
4. In **Storage**, create a new bucket named `hobby-tracker-media` and mark
   it **private** (not public) — the app serves files through signed URLs,
   never a public bucket URL.
5. In **Authentication → Settings**, you can turn off "Confirm email" for
   easier local testing with dummy accounts (re-enable for anything closer
   to production).

## Part 3 — Run the backend against real Supabase

```bash
cp .env.example .env
```
Edit `.env`:
```env
CLOUD_PROVIDER=supabase
SUPABASE_URL=https://xxxxxxxx.supabase.co
SUPABASE_ANON_KEY=ey...
SUPABASE_SERVICE_ROLE_KEY=ey...
STORAGE_BUCKET=hobby-tracker-media
ENVIRONMENT=development
```
```bash
pip install -r requirements.txt   # now also installs the supabase client
uvicorn backend.app:app --reload
```
Register a new (dummy) account in the frontend and confirm the row appears
in Supabase's **Table Editor → users**.

## Part 4 — Deploy the backend (free-tier PaaS)

Any container-friendly free host works; steps below use **Render** as the
concrete example (Railway/Fly.io are very similar).

1. Push this repository to GitHub (see `docs/github_and_proof.md`).
2. On Render: **New → Web Service**, connect the GitHub repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
5. Add the same environment variables as your local `.env`
   (`CLOUD_PROVIDER=supabase`, the three `SUPABASE_*` keys,
   `STORAGE_BUCKET`, and set `ENVIRONMENT=production`, `PUBLIC_API_URL` to
   the Render URL you're given, and `CORS_ORIGINS` to your frontend's URL
   once you have it from Part 5).
6. Deploy. Confirm `https://<your-service>.onrender.com/api/health` returns
   `{"status": "ok", "cloud_provider": "supabase"}`.

A minimal `Dockerfile` is included if your host prefers a container build
over buildpacks:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY cloud/ cloud/
COPY analytics/ analytics/
EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Part 5 — Deploy the frontend (free static hosting)

Using **Vercel** as the concrete example (Netlify is nearly identical):

1. Import the repo on [vercel.com](https://vercel.com), set the project
   root to `frontend/`.
2. Build command: `npm run build`  ·  Output directory: `dist`
3. Set the rewrite so `/api/*` and `/media/*` forward to your deployed
   backend (in `frontend/vercel.json`, already included) — update the
   `destination` host to your Render URL.
4. Deploy. Update the backend's `CORS_ORIGINS` env var to this Vercel URL
   and redeploy the backend so the browser is allowed to call it.

## Part 6 — Confirm the deployed app end-to-end

1. Open the Vercel URL, register a (dummy) account.
2. Add a hobby, log a practice session, confirm the goal's progress bar
   moves.
3. Upload a profile picture; confirm it appears (this proves the object
   storage + signed-URL path works in the cloud).
4. Post to the community feed from one account, like/comment from a
   second account (proves cross-user data + community sharing work in the
   cloud, not just locally).
5. Screenshot the Supabase **Table Editor** and **Storage** bucket showing
   this data — see `docs/github_and_proof.md` for the full screenshot
   checklist.

## Rollback / troubleshooting

- **`CLOUD_PROVIDER=supabase but ... environment variables are missing`** —
  `cloud/factory.py` refuses to start rather than silently falling back;
  double-check all three `SUPABASE_*` variables are set.
- **CORS errors in the browser console** — `CORS_ORIGINS` on the backend
  must exactly match the frontend's deployed origin (scheme + host, no
  trailing slash).
- **Uploaded images don't render** — confirm the Storage bucket exists and
  is named exactly `STORAGE_BUCKET`; check the backend logs for a
  `StorageError`.
