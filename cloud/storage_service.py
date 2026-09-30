"""
cloud/storage_service.py
========================
PURPOSE
    Cloud *object storage* abstraction. Files (profile pictures, achievement
    images, certificates) live in a bucket; the database only keeps the
    storage path + metadata.

    * SupabaseStorage - Supabase Storage (S3-compatible) with a PRIVATE bucket.
      Every file is served through short-lived SIGNED URLs.
    * LocalStorage    - writes into a local folder (simulation / tests).
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when the object store is unreachable or rejects an operation."""


class StorageService(ABC):
    @abstractmethod
    def upload(self, path: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    def delete(self, path: str) -> None: ...

    @abstractmethod
    def signed_url(self, path: str, expires_in: int = 3600) -> str: ...

    def signed_urls(self, paths: Iterable[str], expires_in: int = 3600) -> dict[str, str]:
        """Batch version. Subclasses may override with a single network call."""
        return {p: self.signed_url(p, expires_in) for p in set(paths)}


# --------------------------------------------------------------------------- #
class LocalStorage(StorageService):
    """Stores objects on disk and exposes them at ``<public_api_url>/media/<path>``."""

    def __init__(self, base_dir: str, public_api_url: str):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.public_api_url = public_api_url.rstrip("/")

    def _resolve(self, path: str) -> Path:
        target = (self.base_dir / path).resolve()
        if not target.is_relative_to(self.base_dir):  # blocks ../ path traversal
            raise StorageError("Invalid storage path")
        return target

    def upload(self, path, data, content_type):
        try:
            target = self._resolve(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        except OSError as exc:
            raise StorageError(str(exc)) from exc

    def delete(self, path):
        try:
            self._resolve(path).unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError(str(exc)) from exc

    def signed_url(self, path, expires_in=3600):
        # Local simulation: the folder is served statically, so the URL is not
        # truly signed. In Supabase mode this is a real, expiring signed URL.
        return f"{self.public_api_url}/media/{path}"


# --------------------------------------------------------------------------- #
class SupabaseStorage(StorageService):
    def __init__(self, client: Any, bucket: str, supabase_url: str):
        self.client = client
        self.bucket = bucket
        self.storage_base = supabase_url.rstrip("/") + "/storage/v1"
        self._cache: dict[str, tuple[str, float]] = {}  # path -> (url, expires_at)

    def _bucket(self):
        return self.client.storage.from_(self.bucket)

    def _absolute(self, url: str) -> str:
        if url.startswith("http"):
            return url
        return self.storage_base + ("" if url.startswith("/") else "/") + url

    def upload(self, path, data, content_type):
        try:
            self._bucket().upload(path, data, {"content-type": content_type, "upsert": "true"})
        except Exception as exc:
            logger.error("Supabase storage upload failed: %s", exc)
            raise StorageError(str(exc)) from exc

    def delete(self, path):
        try:
            self._bucket().remove([path])
            self._cache.pop(path, None)
        except Exception as exc:
            logger.error("Supabase storage delete failed: %s", exc)
            raise StorageError(str(exc)) from exc

    def _cached(self, path: str) -> str | None:
        hit = self._cache.get(path)
        if hit and hit[1] - time.time() > 300:  # keep if >5 min of validity left
            return hit[0]
        return None

    def signed_url(self, path, expires_in=3600):
        return self.signed_urls([path], expires_in)[path]

    def signed_urls(self, paths, expires_in=3600):
        result: dict[str, str] = {}
        missing = []
        for p in set(paths):
            cached = self._cached(p)
            if cached:
                result[p] = cached
            else:
                missing.append(p)
        if missing:
            try:
                items = self._bucket().create_signed_urls(missing, expires_in)
            except Exception as exc:
                logger.error("Supabase signed URL creation failed: %s", exc)
                raise StorageError(str(exc)) from exc
            for item in items:
                url = item.get("signedURL") or item.get("signedUrl")
                path = item.get("path")
                if url and path:
                    full = self._absolute(url)
                    self._cache[path] = (full, time.time() + expires_in)
                    result[path] = full
        return result
