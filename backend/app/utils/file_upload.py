"""File upload helpers."""

from __future__ import annotations

import mimetypes
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

_SAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class ValidatedUpload:
    file_name: str
    content_type: str
    size: int
    extension: str


def sanitize_filename(filename: str) -> str:
    raw_name = Path(filename or "").name.strip()
    if not raw_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid file name",
        )
    sanitized = _SAFE_FILENAME_CHARS.sub("_", raw_name).strip("._")
    if not sanitized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file name is invalid after sanitization",
        )
    return sanitized[:255]


def get_upload_size(upload: UploadFile) -> int:
    file_obj = upload.file
    current_position = file_obj.tell()
    file_obj.seek(0, 2)
    size = file_obj.tell()
    file_obj.seek(current_position)
    return size


def validate_document_upload(upload: UploadFile) -> ValidatedUpload:
    file_name = sanitize_filename(upload.filename or "")
    extension = Path(file_name).suffix.lower()
    if extension not in {item.lower() for item in settings.ALLOWED_DOCUMENT_EXTENSIONS}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {extension or 'none'}",
        )

    size = get_upload_size(upload)
    if size <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file cannot be empty",
        )

    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit",
        )

    content_type = (upload.content_type or "").strip().lower()
    if not content_type or content_type == "application/octet-stream":
        guessed_content_type, _ = mimetypes.guess_type(file_name)
        content_type = (guessed_content_type or "").lower()
    if content_type not in {item.lower() for item in settings.ALLOWED_DOCUMENT_MIME_TYPES}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {content_type or 'unknown'}",
        )

    upload.file.seek(0)
    return ValidatedUpload(
        file_name=file_name,
        content_type=content_type,
        size=size,
        extension=extension,
    )


def build_secure_storage_path(
    *,
    entity_type: str,
    entity_id: int,
    document_key: str,
    version_number: int,
    file_name: str,
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    unique_token = uuid4().hex
    extension = Path(file_name).suffix.lower()
    return (
        f"documents/{entity_type}/{entity_id}/{document_key}/"
        f"v{version_number}/{timestamp}_{unique_token}{extension}"
    )
