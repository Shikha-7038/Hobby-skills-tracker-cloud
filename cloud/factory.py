"""
cloud/factory.py
================
Builds the trio {auth, db, storage} for the configured provider.

    CLOUD_PROVIDER=supabase  -> Supabase Auth + PostgreSQL + Storage (cloud)
    CLOUD_PROVIDER=local     -> offline simulation with the same interfaces
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cloud.auth_service import AuthService, LocalAuth, SupabaseAuth
from cloud.database_service import DatabaseService, LocalDatabase, SupabaseDatabase
from cloud.storage_service import LocalStorage, StorageService, SupabaseStorage


@dataclass
class CloudServices:
    auth: AuthService
    db: DatabaseService
    storage: StorageService


def build_cloud(settings) -> CloudServices:
    provider = settings.cloud_provider.lower()

    if provider == "supabase":
        missing = [n for n, v in (
            ("SUPABASE_URL", settings.supabase_url),
            ("SUPABASE_ANON_KEY", settings.supabase_anon_key),
            ("SUPABASE_SERVICE_ROLE_KEY", settings.supabase_service_role_key),
        ) if not v]
        if missing:
            raise RuntimeError(
                "CLOUD_PROVIDER=supabase but these environment variables are missing: "
                + ", ".join(missing) + ". Copy .env.example to .env and fill them in."
            )
        from supabase import create_client

        admin = create_client(settings.supabase_url, settings.supabase_service_role_key)
        return CloudServices(
            auth=SupabaseAuth(settings.supabase_url, settings.supabase_anon_key,
                              settings.supabase_service_role_key),
            db=SupabaseDatabase(admin),
            storage=SupabaseStorage(admin, settings.storage_bucket, settings.supabase_url),
        )

    if provider == "local":
        data_dir = Path(settings.local_data_dir)
        persist = settings.local_persist
        return CloudServices(
            auth=LocalAuth(settings.local_jwt_secret,
                           path=str(data_dir / "auth.json") if persist else None),
            db=LocalDatabase(path=str(data_dir / "db.json") if persist else None),
            storage=LocalStorage(str(data_dir / "storage"), settings.public_api_url),
        )

    raise RuntimeError(f"Unknown CLOUD_PROVIDER '{settings.cloud_provider}' (use 'supabase' or 'local')")
