"""Sorting helpers for list endpoints."""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import Query
from pydantic import BaseModel


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortParams(BaseModel):
    sort_by: str | None = None
    sort_dir: SortDirection = SortDirection.ASC


def get_sort_params(
    sort_by: str | None = Query(default=None),
    sort_dir: SortDirection = Query(default=SortDirection.ASC),
) -> SortParams:
    return SortParams(sort_by=sort_by, sort_dir=sort_dir)


def apply_sorting(
    query: Any,
    *,
    sort_by: str | None,
    sort_dir: SortDirection,
    sort_options: dict[str, Any],
    default_order: tuple[Any, ...],
):
    selected = sort_options.get(sort_by) if sort_by is not None else None
    if selected is None:
        return query.order_by(*default_order)

    columns = selected if isinstance(selected, (list, tuple)) else (selected,)
    ordered = [
        column.desc() if sort_dir == SortDirection.DESC else column.asc()
        for column in columns
    ]
    return query.order_by(*ordered)
