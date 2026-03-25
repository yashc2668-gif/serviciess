"""Measurement endpoints."""

from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.measurement import (
    MeasurementCreate,
    MeasurementOut,
    MeasurementStatus,
    MeasurementUpdate,
)
from app.services.measurement_service import (
    approve_measurement,
    create_measurement,
    delete_measurement,
    get_measurement_or_404,
    list_measurements,
    submit_measurement,
    update_measurement,
)

router = APIRouter(prefix="/measurements", tags=["Measurements"])


@router.post("/", response_model=MeasurementOut, status_code=201)
def create_new_measurement(
    payload: MeasurementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("measurements:create")),
):
    return create_measurement(db, payload, current_user)


@router.get("/", response_model=List[MeasurementOut])
def list_all_measurements(
    contract_id: int | None = None,
    status_filter: MeasurementStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("measurements:read")),
):
    return list_measurements(db, contract_id=contract_id, status_filter=status_filter)


@router.get("/{measurement_id}", response_model=MeasurementOut)
def get_single_measurement(
    measurement_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("measurements:read")),
):
    return get_measurement_or_404(db, measurement_id)


@router.put("/{measurement_id}", response_model=MeasurementOut)
def update_existing_measurement(
    measurement_id: int,
    payload: MeasurementUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("measurements:update")),
):
    return update_measurement(db, measurement_id, payload)


@router.delete("/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_measurement(
    measurement_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("measurements:update")),
):
    delete_measurement(db, measurement_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{measurement_id}/submit", response_model=MeasurementOut)
def submit_existing_measurement(
    measurement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("measurements:submit")),
):
    return submit_measurement(db, measurement_id, current_user)


@router.post("/{measurement_id}/approve", response_model=MeasurementOut)
def approve_existing_measurement(
    measurement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("measurements:approve")),
):
    return approve_measurement(db, measurement_id, current_user)
