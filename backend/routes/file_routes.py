"""
backend/routes/file_routes.py
==============================
POST   /api/files/upload   - upload a profile picture / achievement image / post image
DELETE /api/files/{id}     - delete a file you own

The response includes a ready-to-use ``storage_path`` the client then passes
back in PUT /api/profile (as profile_picture) or POST /api/posts (media_path).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from backend.middleware.auth_middleware import get_current_user
from backend.utils.validation import ValidationError

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload", status_code=201)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    kind: str = Form(...),
    skill_id: str | None = Form(None),
    user_id: str = Depends(get_current_user),
):
    data = await file.read()
    try:
        record = request.app.state.file_service.upload(
            owner_id=user_id, kind=kind, data=data,
            declared_content_type=file.content_type or "", skill_id=skill_id)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})

    storage = request.app.state.cloud.storage
    if kind == "PROFILE_IMAGE":
        request.app.state.profile_service.set_profile_picture(user_id, record["storage_path"])

    return {**record, "url": storage.signed_url(record["storage_path"])}


@router.delete("/{file_id}", status_code=204)
def delete_file(file_id: str, request: Request, user_id: str = Depends(get_current_user)):
    try:
        request.app.state.file_service.delete_file(user_id, file_id)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "message": exc.message})
