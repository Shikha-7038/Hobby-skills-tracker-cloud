"""
backend/app.py
===============
The FastAPI application entrypoint. Run it with:

    uvicorn backend.app:app --reload

What happens at startup:
    1. Settings are loaded from the environment (backend/config.py).
    2. build_cloud() constructs the auth/db/storage trio for whichever
       CLOUD_PROVIDER is configured (see cloud/factory.py).
    3. Every service is instantiated once and attached to app.state, so
       route handlers never construct their own service objects.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from cloud.auth_service import AuthError
from cloud.database_service import DatabaseError
from cloud.factory import build_cloud
from cloud.storage_service import StorageError
from backend.config import settings
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.utils.validation import ValidationError

from analytics.progress_service import AnalyticsService
from backend.services.file_service import FileService
from backend.services.goal_service import GoalService
from backend.services.moderation_service import ModerationService
from backend.services.post_service import PostService
from backend.services.practice_service import PracticeService
from backend.services.profile_service import ProfileService
from backend.services.skill_service import SkillService
from backend.services.social_service import SocialService

from backend.routes import (
    analytics_routes, auth_routes, file_routes, goal_routes, post_routes,
    practice_routes, profile_routes, search_routes, skill_routes, social_routes,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("hobby_tracker")

settings.validate()

app = FastAPI(
    title="Online Hobby & Skills Tracker API",
    description="Cloud-backed REST API for tracking hobbies, practice, goals, and community sharing.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)


@app.on_event("startup")
def startup() -> None:
    cloud = build_cloud(settings)
    app.state.cloud = cloud
    app.state.profile_service = ProfileService(cloud.db, cloud.storage)
    app.state.skill_service = SkillService(cloud.db)
    app.state.goal_service = GoalService(cloud.db)
    app.state.practice_service = PracticeService(cloud.db, app.state.goal_service)
    app.state.post_service = PostService(cloud.db, cloud.storage)
    app.state.social_service = SocialService(cloud.db)
    app.state.file_service = FileService(cloud.db, cloud.storage, settings.allowed_image_types,
                                          settings.max_upload_mb)
    app.state.moderation_service = ModerationService(cloud.db, cloud.storage, cloud.auth)
    app.state.analytics_service = AnalyticsService(cloud.db)
    logger.info("Started with CLOUD_PROVIDER=%s", settings.cloud_provider)

    # Local simulation only: serve uploaded files back over HTTP so the
    # frontend can render them without needing real cloud storage.
    if settings.cloud_provider == "local":
        media_dir = Path(settings.local_data_dir) / "storage"
        media_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")


# --------------------------------------------------------------------------- #
# Centralized error handling (brief section 19 - "Error handling")
# --------------------------------------------------------------------------- #
@app.exception_handler(ValidationError)
def handle_validation_error(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"field": exc.field, "message": exc.message})


@app.exception_handler(AuthError)
def handle_auth_error(request: Request, exc: AuthError):
    return JSONResponse(status_code=exc.status_code, content={"message": exc.message})


@app.exception_handler(DatabaseError)
def handle_database_error(request: Request, exc: DatabaseError):
    logger.error("Database error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=503, content={
        "message": "We couldn't reach the database. Please try again in a moment."})


@app.exception_handler(StorageError)
def handle_storage_error(request: Request, exc: StorageError):
    logger.error("Storage error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=503, content={
        "message": "File storage is temporarily unavailable. Please try again in a moment."})


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={
        "message": "Something went wrong on our end. Please try again."})


@app.get("/api/health")
def health():
    """Used by the deployment platform's health check and by CI smoke tests."""
    return {"status": "ok", "cloud_provider": settings.cloud_provider}


for module in (auth_routes, profile_routes, skill_routes, goal_routes, practice_routes,
               post_routes, social_routes, file_routes, analytics_routes, search_routes):
    app.include_router(module.router)
