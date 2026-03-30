"""Material master endpoints."""

from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.material import (
    MaterialCreate,
    MaterialOut,
    MaterialStockSummaryOut,
    MaterialUpdate,
)
from app.services.material_service import (
    create_material,
    get_material_stock_summary,
    get_material_or_404,
    list_materials,
    list_materials_for_export,
    update_material,
)
from app.utils.csv_export import build_csv_response
from app.utils.pagination import PaginationParams, get_pagination_params
from app.utils.sorting import SortParams, get_sort_params

router = APIRouter(prefix="/materials", tags=["Materials"])


@router.get("", response_model=PaginatedResponse[MaterialOut])
@router.get("/", response_model=PaginatedResponse[MaterialOut], include_in_schema=False)
def list_all_materials(
    is_active: bool | None = None,
    category: str | None = None,
    company_id: int | None = None,
    project_id: int | None = None,
    search: str | None = None,
    attention: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("materials:read")),
):
    return list_materials(
        db,
        current_user=current_user,
        pagination=pagination,
        is_active=is_active,
        category=category,
        company_id=company_id,
        project_id=project_id,
        search=search,
        attention=attention,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )


@router.get("/export")
def export_materials(
    is_active: bool | None = None,
    category: str | None = None,
    company_id: int | None = None,
    project_id: int | None = None,
    search: str | None = None,
    attention: str | None = None,
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("materials:read")),
):
    materials = list_materials_for_export(
        db,
        current_user,
        is_active=is_active,
        category=category,
        company_id=company_id,
        project_id=project_id,
        search=search,
        attention=attention,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )
    return build_csv_response(
        filename="materials-export",
        headers=[
            "Item Code",
            "Material",
            "Category",
            "Project",
            "Company",
            "Unit",
            "Current Stock",
            "Reorder Level",
            "Default Rate",
            "Active",
        ],
        rows=[
            [
                material.item_code,
                material.item_name,
                material.category,
                material.project.name if material.project else None,
                material.company.name if material.company else None,
                material.unit,
                material.current_stock,
                material.reorder_level,
                material.default_rate,
                material.is_active,
            ]
            for material in materials
        ],
    )


@router.post("", response_model=MaterialOut, status_code=201)
@router.post("/", response_model=MaterialOut, status_code=201, include_in_schema=False)
def create_new_material(
    payload: MaterialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("materials:create")),
):
    return create_material(db, payload, current_user)


@router.get("/stock-summary", response_model=List[MaterialStockSummaryOut])
def get_material_stock_summary_by_scope(
    group_by: str = "project",
    company_id: int | None = None,
    project_id: int | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("stock_ledger:read")),
):
    return get_material_stock_summary(
        db,
        current_user=current_user,
        group_by=group_by,
        company_id=company_id,
        project_id=project_id,
        is_active=is_active,
    )


@router.get("/{material_id}", response_model=MaterialOut)
def get_single_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("materials:read")),
):
    return get_material_or_404(db, material_id, current_user=current_user)


@router.put("/{material_id}", response_model=MaterialOut)
def update_existing_material(
    material_id: int,
    payload: MaterialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("materials:update")),
):
    return update_material(db, material_id, payload, current_user)


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("materials:delete")),
):
    delete_material(db, material_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{material_id}", response_model=MaterialOut)
def patch_existing_material(
    material_id: int,
    payload: MaterialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("materials:update")),
):
    return update_material(db, material_id, payload, current_user)
