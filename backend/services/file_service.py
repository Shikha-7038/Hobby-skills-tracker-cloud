"""
backend/services/file_service.py
=================================
PURPOSE
    Every upload (profile picture, achievement proof, post image) passes
    through here first. This is where FILE-TYPE and FILE-SIZE validation
    happen (docs/security.md - "secure uploads"), before a single byte
    reaches cloud storage.

STORAGE LAYOUT (brief section 10)
    users/<user_id>/profile/<file_id>.<ext>
    users/<user_id>/skills/<skill_id>/<file_id>.<ext>
    users/<user_id>/posts/<file_id>.<ext>
"""
from __future__ import annotations

from typing import Optional

from cloud.database_service import DatabaseService
from cloud.storage_service import StorageService
from backend.models.schemas import FILE_KINDS, new_file
from backend.utils.validation import ValidationError, clean_choice

_EXT_BY_TYPE = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}


def _sniff_image_type(data: bytes) -> Optional[str]:
    """Identifies an image format from its magic bytes. Deliberately written
    by hand instead of using the standard-library ``imghdr`` module, which is
    deprecated (removed in Python 3.13) and only recognizes JPEGs that carry
    a JFIF/Exif marker or the raw \\xff\\xd8\\xff\\xdb prefix - missing many
    otherwise-valid JPEGs a browser or phone camera can produce."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


class FileService:
    def __init__(self, db: DatabaseService, storage: StorageService,
                 allowed_types: list[str], max_upload_mb: int):
        self.db = db
        self.storage = storage
        self.allowed_types = allowed_types
        self.max_bytes = max_upload_mb * 1024 * 1024

    def upload(self, *, owner_id: str, kind: str, data: bytes, declared_content_type: str,
               skill_id: Optional[str] = None) -> dict:
        kind = clean_choice(kind, "kind", FILE_KINDS)

        if len(data) == 0:
            raise ValidationError("file", "the uploaded file is empty")
        if len(data) > self.max_bytes:
            raise ValidationError("file", f"must be smaller than {self.max_bytes // (1024 * 1024)} MB")

        # Trust the BYTES, not the filename or the browser-supplied Content-Type header,
        # both of which are trivial for a client to spoof.
        real_type = _sniff_image_type(data)
        if not real_type or real_type not in self.allowed_types:
            raise ValidationError("file", "must be a valid JPEG, PNG, WEBP, or GIF image")

        ext = _EXT_BY_TYPE[real_type]
        placeholder = new_file(owner_id=owner_id, kind=kind, storage_path="", content_type=real_type,
                                size_bytes=len(data))
        file_id = placeholder["file_id"]

        if kind == "PROFILE_IMAGE":
            path = f"users/{owner_id}/profile/{file_id}.{ext}"
        elif kind == "ACHIEVEMENT_IMAGE":
            if not skill_id:
                raise ValidationError("skill_id", "achievement images must reference a skill")
            path = f"users/{owner_id}/skills/{skill_id}/{file_id}.{ext}"
        else:  # POST_MEDIA
            path = f"users/{owner_id}/posts/{file_id}.{ext}"

        self.storage.upload(path, data, real_type)
        placeholder["storage_path"] = path
        return self.db.insert("files", placeholder)

    def delete_file(self, owner_id: str, file_id: str) -> None:
        record = self.db.get("files", file_id)
        if not record:
            raise ValidationError("file_id", "file not found")
        if record["owner_id"] != owner_id:
            raise ValidationError("file_id", "you can only delete your own files")
        self.storage.delete(record["storage_path"])
        self.db.delete("files", file_id)
