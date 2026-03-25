"""Storage integration helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings


@dataclass
class StoredFile:
    storage_path: str
    size: int
    content_type: str | None = None
    original_name: str | None = None


class StorageAdapter(ABC):
    """Pluggable file storage contract."""

    @abstractmethod
    def save(
        self,
        file_obj: BinaryIO,
        *,
        storage_path: str,
        content_type: str | None = None,
        original_name: str | None = None,
    ) -> StoredFile:
        """Persist a file-like object and return normalized storage metadata."""

    @abstractmethod
    def delete(self, storage_path: str) -> None:
        """Delete a file if it exists."""

    @abstractmethod
    def exists(self, storage_path: str) -> bool:
        """Return True when the storage path exists."""

    @abstractmethod
    def open_read(self, storage_path: str) -> BinaryIO:
        """Open a stored file for binary reading."""


class LocalStorageAdapter(StorageAdapter):
    """Filesystem-backed adapter for local development and single-node deployments."""

    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_path: str) -> Path:
        normalized_relative = Path(storage_path)
        candidate = (self.root / normalized_relative).resolve()
        if os.path.commonpath([str(self.root), str(candidate)]) != str(self.root):
            raise ValueError("Invalid storage path")
        return candidate

    def _normalize_storage_path(self, storage_path: str) -> str:
        normalized = Path(storage_path).as_posix().strip("/")
        if not normalized:
            raise ValueError("storage_path cannot be empty")
        return normalized

    def save(
        self,
        file_obj: BinaryIO,
        *,
        storage_path: str,
        content_type: str | None = None,
        original_name: str | None = None,
    ) -> StoredFile:
        normalized_storage_path = self._normalize_storage_path(storage_path)
        destination = self._resolve_path(normalized_storage_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        with destination.open("wb") as target:
            shutil.copyfileobj(file_obj, target)
        return StoredFile(
            storage_path=normalized_storage_path,
            size=destination.stat().st_size,
            content_type=content_type,
            original_name=original_name,
        )

    def delete(self, storage_path: str) -> None:
        destination = self._resolve_path(self._normalize_storage_path(storage_path))
        if destination.exists():
            destination.unlink()

    def exists(self, storage_path: str) -> bool:
        return self._resolve_path(self._normalize_storage_path(storage_path)).exists()

    def open_read(self, storage_path: str) -> BinaryIO:
        destination = self._resolve_path(self._normalize_storage_path(storage_path))
        return destination.open("rb")


def get_storage_adapter() -> StorageAdapter:
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageAdapter(settings.LOCAL_STORAGE_ROOT)
    raise RuntimeError(f"Unsupported storage backend: {settings.STORAGE_BACKEND}")
