"""Pagination helpers."""

from __future__ import annotations

from math import floor
from typing import Any

from fastapi import Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class PaginationParams(BaseModel):
    page: int = 1
    limit: int = DEFAULT_PAGE_SIZE
    skip: int = 0


def get_pagination_params(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    skip: int | None = Query(default=None, ge=0),
) -> PaginationParams:
    if skip is not None:
        derived_page = floor(skip / limit) + 1
        if page != 1 and page != derived_page:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="page and skip cannot describe different slices",
            )
        return PaginationParams(page=derived_page, limit=limit, skip=skip)
    resolved_skip = (page - 1) * limit
    return PaginationParams(page=page, limit=limit, skip=resolved_skip)


def apply_pagination(query: Any, *, skip: int, limit: int):
    return query.offset(skip).limit(limit)


def build_paginated_response(*, items: list[Any], total: int, pagination: PaginationParams) -> dict[str, Any]:
    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "limit": pagination.limit,
    }


def paginate_query(query: Any, *, pagination: PaginationParams) -> dict[str, Any]:
    total = query.order_by(None).count()
    items = apply_pagination(query, skip=pagination.skip, limit=pagination.limit).all()
    return build_paginated_response(items=items, total=total, pagination=pagination)


def paginate_sequence(items: list[Any], *, pagination: PaginationParams) -> dict[str, Any]:
    total = len(items)
    paginated_items = items[pagination.skip : pagination.skip + pagination.limit]
    return build_paginated_response(items=paginated_items, total=total, pagination=pagination)


def validate_pagination_query_params(request: Request) -> None:
    raw_page = request.query_params.get("page")
    raw_skip = request.query_params.get("skip")
    raw_limit = request.query_params.get("limit")

    if raw_page is not None:
        try:
            page = int(raw_page)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="page must be an integer",
            ) from exc
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="page must be greater than or equal to 1",
            )

    if raw_skip is not None:
        try:
            skip = int(raw_skip)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="skip must be an integer",
            ) from exc
        if skip < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="skip must be greater than or equal to 0",
            )

    if raw_limit is not None:
        try:
            limit = int(raw_limit)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="limit must be an integer",
            ) from exc
        if limit < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="limit must be greater than or equal to 1",
            )
        if limit > MAX_PAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"limit must be less than or equal to {MAX_PAGE_SIZE}",
            )


PaginationDependency = Depends(get_pagination_params)
