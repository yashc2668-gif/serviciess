"""Document metadata endpoints."""

from typing import List

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import (
    DocumentCreate,
    DocumentEntityType,
    DocumentOut,
    DocumentUpdate,
    DocumentVersionCreate,
)
from app.services.document_service import (
    add_document_version,
    add_document_version_from_upload,
    create_document,
    create_document_from_upload,
    get_document_or_404,
    list_documents,
    open_document_download,
    update_document_metadata,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/", response_model=List[DocumentOut])
def list_all_documents(
    entity_type: str | None = None,
    entity_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("documents:read")),
):
    return list_documents(db, entity_type=entity_type, entity_id=entity_id)


@router.post("/", response_model=DocumentOut, status_code=201)
def create_new_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("documents:create")),
):
    return create_document(db, payload, current_user)


@router.post("/upload", response_model=DocumentOut, status_code=201)
def upload_new_document(
    entity_type: DocumentEntityType = Form(...),
    entity_id: int = Form(...),
    title: str = Form(...),
    document_type: str | None = Form(default=None),
    remarks: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("documents:create")),
):
    return create_document_from_upload(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        document_type=document_type,
        remarks=remarks,
        upload=file,
        current_user=current_user,
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_single_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("documents:read")),
):
    return get_document_or_404(db, document_id)


@router.get("/{document_id}/download")
def download_document_file(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("documents:read")),
):
    document, file_handle = open_document_download(db, document_id)

    def iter_file():
        try:
            while chunk := file_handle.read(1024 * 1024):
                yield chunk
        finally:
            file_handle.close()

    return StreamingResponse(
        iter_file(),
        media_type=document.latest_mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{document.latest_file_name}"',
        },
    )


@router.put("/{document_id}", response_model=DocumentOut)
def update_existing_document(
    document_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("documents:update")),
):
    return update_document_metadata(db, document_id, payload)


@router.post("/{document_id}/versions", response_model=DocumentOut)
def create_document_version(
    document_id: int,
    payload: DocumentVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("documents:create")),
):
    return add_document_version(db, document_id, payload, current_user)


@router.post("/{document_id}/versions/upload", response_model=DocumentOut)
def upload_document_version(
    document_id: int,
    remarks: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("documents:create")),
):
    return add_document_version_from_upload(
        db,
        document_id=document_id,
        remarks=remarks,
        upload=file,
        current_user=current_user,
    )
