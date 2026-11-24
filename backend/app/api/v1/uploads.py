from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status

from ...config import get_settings
from ...deps import CurrentUser
from ...schemas import CoverUploadOut

router = APIRouter(prefix="/uploads", tags=["uploads"])

CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.post("/cover", response_model=CoverUploadOut, status_code=201)
async def upload_cover(_: CurrentUser, file: UploadFile) -> CoverUploadOut:
    settings = get_settings()
    data = await file.read(settings.max_cover_bytes + 1)

    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Файл пустой")
    if len(data) > settings.max_cover_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Максимум {settings.max_cover_mb} МБ",
        )

    extension = CONTENT_TYPES.get(file.content_type or "")
    if extension is None:
        extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Поддерживаются только JPG, PNG, WEBP и GIF",
        )

    directory = settings.upload_dir_path
    await asyncio.to_thread(directory.mkdir, parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{extension}"
    await asyncio.to_thread((directory / filename).write_bytes, data)

    return CoverUploadOut(url=f"/uploads/{filename}")
