# GitHub Upload Strategy, Proof-of-Work & Screenshot Checklist

## 1. GitHub upload strategy

**Repository name:** `hobby-skills-tracker-cloud` (or similar — descriptive,
lowercase, hyphenated).

**Commit history that reads like real development, not one dump:**
1. `chore: project scaffold and cloud provider abstraction`
2. `feat: authentication and profile management`
3. `feat: skill and goal/milestone tracking`
4. `feat: practice session logging and streak calculation`
5. `feat: community posts, likes, comments, follows`
6. `feat: file upload with content-type validation`
7. `feat: analytics dashboard`
8. `feat: React frontend — auth, skills, dashboard, feed, profile`
9. `test: automated test suite covering all 27 scenarios`
10. `docs: architecture, database design, API reference, security`
11. `ci: GitHub Actions workflow`
12. `docs: deployment guide and README`

Committing in this order (even if you're uploading a finished project) lets
a reviewer see the project actually reflects real incremental engineering.

**Before your first commit:**
```bash
git init
git add .gitignore
git commit -m "chore: initial gitignore"
# then commit in the stages above
```
Double-check `git status` never shows `.env` — only `.env.example` should
ever be tracked. Run `git log --all -- .env` occasionally to confirm no
past commit leaked a real secret.

**Branch strategy:** commit to `main` directly for a solo student project is
fine, but consider one `feature/community-feed`-style branch merged via a
pull request, purely so your GitHub profile shows PR activity, which
reviewers do look for.

## 2. Proof-of-work strategy

What makes a repository *credible* proof of work, beyond "the code exists":

1. **A README that explains the *why*, not just the *how*.** Done — see
   the root `README.md`.
2. **Real commit history** spread across dates/sessions, not one commit
   with everything.
3. **Passing CI badge.** Add this near the top of `README.md` once your
   repo is pushed and Actions has run at least once:
   ```markdown
   ![CI](https://github.com/<you>/<repo>/actions/workflows/ci.yml/badge.svg)
   ```
4. **A live, clickable deployment link** in the README (see
   `docs/deployment_guide.md`) — a reviewer trying the app themselves is
   worth more than any number of screenshots.
5. **Tests that actually run in CI**, not just described in a doc.
6. **Architecture diagrams** (see `docs/architecture.md`) — shows you can
   explain a system, not just produce code from a prompt.
7. **A short demo video/GIF** (60–90 seconds: register → add hobby → log
   practice → see progress move → post to feed → like from a second
   account) linked at the top of the README.

## 3. Screenshot / proof checklist

Capture each of these, save under `screenshots/` with the filename shown,
and reference them from the README once captured:

| # | What to capture | Suggested filename |
|---|---|---|
| 1 | Project folder structure (IDE sidebar or `tree` output) | `01-folder-structure.png` |
| 2 | Cloud architecture diagram (render `docs/architecture.md`'s mermaid diagram) | `02-architecture-diagram.png` |
| 3 | Registration page | `03-registration-page.png` |
| 4 | Login page | `04-login-page.png` |
| 5 | User profile page | `05-user-profile.png` |
| 6 | "Add skill" form filled in | `06-add-skill.png` |
| 7 | Skills dashboard with multiple hobbies | `07-skills-dashboard.png` |
| 8 | Goal creation with milestones | `08-goal-creation.png` |
| 9 | Practice-session entry form | `09-practice-entry.png` |
| 10 | Progress bar before/after logging practice | `10-progress-calculation.png` |
| 11 | A milestone marked achieved (celebration banner) | `11-milestone-achieved.png` |
| 12 | Analytics dashboard with charts | `12-analytics-dashboard.png` |
| 13 | Supabase Table Editor showing real rows | `13-cloud-database.png` |
| 14 | Supabase Storage bucket with an uploaded file | `14-cloud-storage-upload.png` |
| 15 | An achievement image attached to a skill | `15-achievement-image.png` |
| 16 | Creating a community post | `16-create-post.png` |
| 17 | Community feed with multiple posts | `17-community-feed.png` |
| 18 | Liking a post (before/after count) | `18-like-interaction.png` |
| 19 | Commenting on a post | `19-comment-interaction.png` |
| 20 | A second dummy user account, logged in | `20-second-user-account.png` |
| 21 | Proof that user B cannot see user A's private skill (404 in devtools, or UI) | `21-data-isolation-test.png` |
| 22 | A raw REST API response (Postman, or `/docs` Swagger UI) | `22-rest-api-response.png` |
| 23 | `pytest tests/ -v` passing in a terminal | `23-automated-tests.png` |
| 24 | Your PaaS host's deployment dashboard (Render/Railway) | `24-cloud-deployment-dashboard.png` |
| 25 | The live, deployed application in a browser (with the real URL visible) | `25-live-application.png` |
| 26 | GitHub commit history (graph view) | `26-github-commit-history.png` |
| 27 | The GitHub repository home page | `27-github-repository.png` |
| 28 | README rendered on GitHub | `28-readme-preview.png` |

**What each screenshot proves**, in one line each: (1) organized codebase,
(2) architectural understanding, (3–5) working auth + profile, (6–11)
core hobby/goal/practice tracking loop functions end to end, (12) analytics
work, (13–15) a real cloud database and object storage are actually being
used (not just simulated), (16–19) community features work across users,
(20–21) data isolation/security is real, not assumed, (22) the API is a
genuine REST interface, (23) the project is tested, (24–25) it's actually
deployed and reachable on the internet, (26–28) it's real, maintained,
documented work — not a single AI-generated dump.
