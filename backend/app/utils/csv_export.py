"""CSV export helpers."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Iterable

from fastapi import Response


def build_csv_response(
    *,
    filename: str,
    headers: list[str],
    rows: Iterable[Iterable[object | None]],
) -> Response:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(list(row))

    return Response(
        content="\ufeff" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}.csv"',
        },
    )
