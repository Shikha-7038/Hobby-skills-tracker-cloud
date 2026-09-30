# Testing Strategy

## Automated tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

- `tests/conftest.py` builds a **fresh, in-memory local cloud** (`CLOUD_PROVIDER=local`,
  `LOCAL_PERSIST=false`) per test via FastAPI's `TestClient`, so tests never
  touch a real network or leak state into each other.
- `tests/test_unit_calculations.py` — pure functions (streak math, progress
  %), no HTTP layer involved.
- `tests/test_auth_and_profile.py`, `test_skills_goals_practice.py`,
  `test_community.py`, `test_analytics_and_failures.py` — full HTTP-level
  tests through FastAPI's `TestClient`, covering all 27 scenarios below.
- CI (`.github/workflows/ci.yml`) runs the full suite on every push to
  `main` and on every pull request.

**Verification performed while building this project:** `fastapi` could not
be installed in the offline sandbox used to write this code, so the 27
HTTP-level scenarios below were additionally verified by exercising the
exact same service-layer functions the routes call (`ProfileService`,
`SkillService`, `GoalService`, `PracticeService`, `PostService`,
`SocialService`, `FileService`, `ModerationService`) directly against
`LocalAuth`/`LocalDatabase`/`LocalStorage`, end-to-end, in one script. Every
one of those checks passed. Run `pytest tests/ -v` yourself after
`pip install -r requirements.txt` to get the HTTP-level pass/fail printed
for your own submission record.

## Test matrix (Test ID → Scenario → Input → Expected Result)

| ID | Scenario | Input | Expected Result | Verified via |
|----|----------|-------|------------------|---------------|
| 1 | User registration | Valid name/username/email/password | `201`, returns user + tokens | `test_01_user_registration` |
| 2 | Duplicate registration | Same email registered twice | `409` on the second call | `test_02_duplicate_registration_rejected` |
| 3 | Valid login | Correct email/password | `200`, returns tokens | `test_03_valid_login` |
| 4 | Invalid login | Wrong password | `401` | `test_04_invalid_login_rejected` |
| 5 | Profile update | New bio text | `200`, bio reflected in response | `test_05_profile_update` |
| 6 | Add skill | Valid skill payload | `201`, `status="ACTIVE"` | `test_06_add_skill` |
| 7 | Update skill | `{"status": "PAUSED"}` | `200`, status updated | `test_07_update_skill` |
| 8 | Delete skill | Owner deletes their skill | `204`, then `404` on re-fetch | `test_08_delete_skill` |
| 9 | Create goal | Goal + 2 milestones | `201`, milestones array length 2 | `test_09_create_goal_with_milestones` |
| 10 | Log practice session | 60 minutes on a skill | `201`, session recorded | `test_10_log_practice_session` |
| 11 | Progress calculation | 10h logged against a 20h goal | `progress_percent == 50.0` | `test_11_progress_calculation_via_api` |
| 12 | Milestone completion | Enough minutes to cross a milestone | Milestone appears in `milestones_achieved` | `test_12_milestone_completion` |
| 13 | File upload | Valid JPEG bytes | `201`, `storage_path` ends in `.jpg` | `test_13_file_upload` |
| 14 | Invalid file | A `.txt` file | `422` | `test_14_invalid_file_rejected` |
| 15 | Create community post | Text content | `201` | `test_15_create_community_post` |
| 16 | Retrieve feed | — | `200`, `total >= 1` | `test_16_retrieve_feed` |
| 17 | Like post | Second user likes a post | `201`, `like_count == 1` | `test_17_like_post` |
| 18 | Duplicate like prevention | Same user likes twice | Second call → `422` | `test_18_duplicate_like_prevented` |
| 19 | Unlike post | Liked, then unliked | `200`, `like_count == 0` | `test_19_unlike_post` |
| 20 | Add comment | Comment text | `201`, comment appears in list | `test_20_add_comment` |
| 21 | Unauthorized content deletion | Non-owner tries to delete a post | `403` | `test_21_unauthorized_post_deletion_rejected` |
| 22 | Analytics calculation | 120 minutes logged | `total_practice_minutes == 120` | `test_22_analytics_calculation` |
| 23 | User-data isolation | User B requests User A's private skill | `404` (not `403`) | `test_23_skill_details_isolated_between_users` |
| 24 | Cloud-storage failure | Storage dependency raises `StorageError` | `503`, friendly message | `test_24_storage_failure_returns_graceful_error` |
| 25 | Database failure | DB dependency raises `DatabaseError` | `503`, friendly message | `test_25_database_failure_returns_graceful_error` |
| 26 | Authentication-token expiry | Garbage/invalid bearer token | `401` | `test_26_garbage_token_rejected` |
| 27 | Logout | Logout, then reuse the old token | Reused token → `401` | `test_27_logout_revokes_token` |

Every row above has a corresponding automated test with the exact same
Test ID number in its function name, so `pytest tests/ -v` output maps
1:1 back to this table for a report or a screenshot.

## Manual/exploratory testing checklist

Beyond the automated matrix, manually click through before considering a
deploy "done":
- [ ] Register two separate dummy accounts in the actual browser UI
- [ ] Confirm account A cannot see account B's skills in the UI (not just the API)
- [ ] Upload a real photo as a profile picture and as a post image
- [ ] Log five consecutive days of practice and confirm the streak counter and growth-row both update correctly
- [ ] Refresh the page mid-session and confirm you're still logged in (token persisted)
- [ ] Log out, then use the browser back button — confirm protected pages don't leak stale data
- [ ] Resize the browser to a phone width and confirm the layout adapts
