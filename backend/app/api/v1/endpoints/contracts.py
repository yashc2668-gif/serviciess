"""Contract endpoints."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.contract import ContractCreate, ContractDetailOut, ContractOut, ContractUpdate
from app.services.contract_service import (
    create_contract,
    get_contract_or_404,
    list_contracts,
    update_contract,
)

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.post("/", response_model=ContractOut, status_code=201)
def create_new_contract(
    payload: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("contracts:create")),
):
    return create_contract(db, payload, current_user)


@router.get("/", response_model=List[ContractOut])
def list_all_contracts(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("contracts:read")),
):
    return list_contracts(db, project_id=project_id)


@router.get("/{contract_id}", response_model=ContractDetailOut)
def get_single_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("contracts:read")),
):
    return get_contract_or_404(db, contract_id)


@router.put("/{contract_id}", response_model=ContractOut)
def update_existing_contract(
    contract_id: int,
    payload: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("contracts:update")),
):
    return update_contract(db, contract_id, payload, current_user)
