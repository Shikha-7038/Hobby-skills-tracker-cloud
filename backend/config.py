"""
backend/config.py
==================
PURPOSE
    Single source of truth for configuration. Every value is read from an
    environment variable (see .env.example) so that NOTHING secret is ever
    hardcoded in source control.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    # -- General ------------------------------------------------------- #
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    public_api_url: str = field(default_factory=lambda: os.getenv("PUBLIC_API_URL", "http://localhost:8000"))
    cors_origins: list[str] = field(default_factory=lambda: _list("CORS_ORIGINS", "http://localhost:5173"))

    # -- Cloud provider switch ------------------------------------------ #
    cloud_provider: str = field(default_factory=lambda: os.getenv("CLOUD_PROVIDER", "local"))

    # -- Supabase (used when CLOUD_PROVIDER=supabase) ------------------- #
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_anon_key: str = field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", ""))
    supabase_service_role_key: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    storage_bucket: str = field(default_factory=lambda: os.getenv("STORAGE_BUCKET", "hobby-tracker-media"))

    # -- Local simulation (used when CLOUD_PROVIDER=local) -------------- #
    local_data_dir: str = field(default_factory=lambda: os.getenv("LOCAL_DATA_DIR", "./sample_data/local_store"))
    local_persist: bool = field(default_factory=lambda: _bool("LOCAL_PERSIST", "true"))
    local_jwt_secret: str = field(default_factory=lambda: os.getenv("LOCAL_JWT_SECRET", "dev-only-change-me"))

    # -- Uploads --------------------------------------------------------- #
    max_upload_mb: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_MB", "5")))
    allowed_image_types: list[str] = field(
        default_factory=lambda: _list("ALLOWED_IMAGE_TYPES", "image/jpeg,image/png,image/webp,image/gif")
    )

    # -- Rate limiting ----------------------------------------------------#
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")))

    # -- Optional AI suggestion service ----------------------------------#
    ai_suggest_url: str = field(default_factory=lambda: os.getenv("AI_SUGGEST_URL", ""))

    def validate(self) -> None:
        if self.cloud_provider not in ("local", "supabase"):
            raise RuntimeError("CLOUD_PROVIDER must be 'local' or 'supabase'")
        if self.environment == "production" and self.local_jwt_secret == "dev-only-change-me":
            raise RuntimeError("Refusing to start in production with the default LOCAL_JWT_SECRET.")


settings = Settings()
