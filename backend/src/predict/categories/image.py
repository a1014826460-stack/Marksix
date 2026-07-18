from __future__ import annotations

from typing import Any, Callable

from domains.prediction import predict_repository


table_exists: Callable[[Any, str], bool] = lambda _conn, _table_name: False
table_columns: Callable[[Any, str], tuple[str, ...]] = lambda _conn, _table_name: ()


def latest_window_metadata(conn: Any, table_name: str) -> dict[str, Any]:
    if not table_exists(conn, table_name):
        return {}

    selected_columns = tuple(
        column for column in ("start", "end", "image_url") if column in set(table_columns(conn, table_name))
    )
    if not selected_columns:
        return {}

    row = predict_repository.load_latest_columns_by_issue(
        conn,
        table_name,
        columns=selected_columns,
    )
    if not row:
        return {}
    return {column: row[column] for column in selected_columns}


def format_window_content(base_formatter, table_name: str):
    def formatter(labels: tuple[str, ...], conn: Any) -> dict[str, Any]:
        metadata = latest_window_metadata(conn, table_name)
        return {
            "start": str(metadata.get("start") or ""),
            "end": str(metadata.get("end") or ""),
            "content": base_formatter(labels, conn),
            "image_url": metadata.get("image_url"),
        }

    return formatter
