"""Document service helpers."""

from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException, status
from fastapi import UploadFile
from sqlalchemy.orm import Session, selectinload

from app.core.logging import log_business_event
from app.integrations.storage import get_storage_adapter
from app.models.contract import Contract
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.measurement import Measurement
from app.models.payment import Payment
from app.models.ra_bill import RABill
from app.models.user import User
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentVersionCreate,
)
from app.services.audit_service import log_audit_event, serialize_model
from app.utils.file_upload import build_secure_storage_path, validate_document_upload


SUPPORTED_DOCUMENT_ENTITY_MODELS = {
    "contract": Contract,
    "measurement": Measurement,
    "ra_bill": RABill,
    "payment": Payment,
}


def _validate_entity_linkage(db: Session, entity_type: str, entity_id: int) -> None:
    model = SUPPORTED_DOCUMENT_ENTITY_MODELS.get(entity_type)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported document entity type: {entity_type}",
        )
    exists = db.query(model.id).filter(model.id == entity_id).first()
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_type} not found",
        )


def _document_query(db: Session):
    return db.query(Document).options(selectinload(Document.versions))


def _document_audit_payload(document: Document) -> dict:
    latest_version = document.versions[-1] if document.versions else None
    return {
        "document": serialize_model(document),
        "latest_version": serialize_model(latest_version) if latest_version is not None else None,
    }


def _persist_new_document(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    storage_key: str,
    title: str,
    document_type: str | None,
    file_name: str,
    file_path: str,
    mime_type: str | None,
    file_size: int | None,
    remarks: str | None,
    created_by: int | None,
) -> Document:
    document = Document(
        entity_type=entity_type,
        entity_id=entity_id,
        storage_key=storage_key,
        title=title,
        document_type=document_type,
        current_version_number=1,
        latest_file_name=file_name,
        latest_file_path=file_path,
        latest_mime_type=mime_type,
        latest_file_size=file_size,
        remarks=remarks,
        created_by=created_by,
    )
    db.add(document)
    db.flush()
    document.versions.append(
        DocumentVersion(
            document_id=document.id,
            version_number=1,
            file_name=file_name,
            file_path=file_path,
            mime_type=mime_type,
            file_size=file_size,
            remarks=remarks,
            uploaded_by=created_by,
        )
    )
    return document


def _persist_document_version(
    db: Session,
    *,
    document: Document,
    version_number: int,
    file_name: str,
    file_path: str,
    mime_type: str | None,
    file_size: int | None,
    remarks: str | None,
    uploaded_by: int | None,
) -> None:
    document.current_version_number = version_number
    document.latest_file_name = file_name
    document.latest_file_path = file_path
    document.latest_mime_type = mime_type
    document.latest_file_size = file_size
    if remarks is not None:
        document.remarks = remarks
    document.versions.append(
        DocumentVersion(
            document_id=document.id,
            version_number=version_number,
            file_name=file_name,
            file_path=file_path,
            mime_type=mime_type,
            file_size=file_size,
            remarks=remarks,
            uploaded_by=uploaded_by,
        )
    )


def get_document_or_404(db: Session, document_id: int) -> Document:
    document = _document_query(db).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


def list_documents(
    db: Session,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> list[Document]:
    query = _document_query(db)
    if entity_type is not None:
        query = query.filter(Document.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(Document.entity_id == entity_id)
    return query.order_by(Document.updated_at.desc(), Document.id.desc()).all()


def create_document(
    db: Session,
    payload: DocumentCreate,
    current_user: User,
) -> Document:
    _validate_entity_linkage(db, payload.entity_type, payload.entity_id)
    document = _persist_new_document(
        db,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        storage_key=str(uuid4()),
        title=payload.title,
        document_type=payload.document_type,
        file_name=payload.file_name,
        file_path=payload.file_path,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
        remarks=payload.remarks,
        created_by=current_user.id,
    )
    db.commit()
    db.refresh(document)
    return get_document_or_404(db, document.id)


def add_document_version(
    db: Session,
    document_id: int,
    payload: DocumentVersionCreate,
    current_user: User,
) -> Document:
    document = get_document_or_404(db, document_id)
    _validate_entity_linkage(db, document.entity_type, document.entity_id)
    next_version = int(document.current_version_number or 0) + 1
    _persist_document_version(
        db,
        document=document,
        version_number=next_version,
        file_name=payload.file_name,
        file_path=payload.file_path,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
        remarks=payload.remarks,
        uploaded_by=current_user.id,
    )
    db.commit()
    db.refresh(document)
    return get_document_or_404(db, document.id)


def create_document_from_upload(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    title: str,
    document_type: str | None,
    remarks: str | None,
    upload: UploadFile,
    current_user: User,
) -> Document:
    _validate_entity_linkage(db, entity_type, entity_id)
    validated_upload = validate_document_upload(upload)
    document_key = str(uuid4())
    storage_path = build_secure_storage_path(
        entity_type=entity_type,
        entity_id=entity_id,
        document_key=document_key,
        version_number=1,
        file_name=validated_upload.file_name,
    )
    storage = get_storage_adapter()
    stored_file = storage.save(
        upload.file,
        storage_path=storage_path,
        content_type=validated_upload.content_type,
    )

    try:
        document = _persist_new_document(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            storage_key=document_key,
            title=title,
            document_type=document_type,
            file_name=validated_upload.file_name,
            file_path=stored_file.storage_path,
            mime_type=stored_file.content_type,
            file_size=stored_file.size,
            remarks=remarks,
            created_by=current_user.id,
        )
        db.flush()
        log_audit_event(
            db,
            entity_type="document",
            entity_id=document.id,
            action="create",
            performed_by=current_user,
            after_data=_document_audit_payload(document),
            remarks=remarks or title,
        )
        db.commit()
        db.refresh(document)
        log_business_event(
            "document.uploaded",
            document_id=document.id,
            entity_type=entity_type,
            entity_id=entity_id,
            version_number=1,
            storage_path=document.latest_file_path,
            file_size=document.latest_file_size,
        )
        return get_document_or_404(db, document.id)
    except Exception:
        db.rollback()
        storage.delete(stored_file.storage_path)
        raise


def add_document_version_from_upload(
    db: Session,
    *,
    document_id: int,
    remarks: str | None,
    upload: UploadFile,
    current_user: User,
) -> Document:
    document = get_document_or_404(db, document_id)
    _validate_entity_linkage(db, document.entity_type, document.entity_id)
    before_data = _document_audit_payload(document)
    validated_upload = validate_document_upload(upload)
    next_version = int(document.current_version_number or 0) + 1
    storage_path = build_secure_storage_path(
        entity_type=document.entity_type,
        entity_id=document.entity_id,
        document_key=document.storage_key,
        version_number=next_version,
        file_name=validated_upload.file_name,
    )
    storage = get_storage_adapter()
    stored_file = storage.save(
        upload.file,
        storage_path=storage_path,
        content_type=validated_upload.content_type,
    )

    try:
        _persist_document_version(
            db,
            document=document,
            version_number=next_version,
            file_name=validated_upload.file_name,
            file_path=stored_file.storage_path,
            mime_type=stored_file.content_type,
            file_size=stored_file.size,
            remarks=remarks,
            uploaded_by=current_user.id,
        )
        db.flush()
        log_audit_event(
            db,
            entity_type="document",
            entity_id=document.id,
            action="version_upload",
            performed_by=current_user,
            before_data=before_data,
            after_data=_document_audit_payload(document),
            remarks=remarks or f"Uploaded version {next_version}",
        )
        db.commit()
        db.refresh(document)
        log_business_event(
            "document.version_uploaded",
            document_id=document.id,
            entity_type=document.entity_type,
            entity_id=document.entity_id,
            version_number=next_version,
            storage_path=document.latest_file_path,
            file_size=document.latest_file_size,
        )
        return get_document_or_404(db, document.id)
    except Exception:
        db.rollback()
        storage.delete(stored_file.storage_path)
        raise


def update_document_metadata(
    db: Session,
    document_id: int,
    payload: DocumentUpdate,
) -> Document:
    document = get_document_or_404(db, document_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(document, field, value)
    db.commit()
    db.refresh(document)
    return get_document_or_404(db, document.id)


def open_document_download(
    db: Session,
    document_id: int,
):
    document = get_document_or_404(db, document_id)
    storage = get_storage_adapter()
    if not storage.exists(document.latest_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found in storage",
        )
    return document, storage.open_read(document.latest_file_path)
