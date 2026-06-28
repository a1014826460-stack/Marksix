"""Compatibility facade for admin mode_payload CRUD helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from domains.prediction import mode_payload_service
from domains.prediction.mode_payload_repository import (
    mode_payload_table_columns as _mode_payload_table_columns,
    mode_payload_table_exists as _mode_payload_table_exists,
)


def validate_mode_payload_table(table_name: str) -> str:
    return mode_payload_service.validate_mode_payload_table(table_name)


def normalize_mode_payload_source(source: str) -> str:
    return mode_payload_service.normalize_mode_payload_source(source)


def normalize_mode_payload_row_id(row_id: Any, source: str = "public") -> Any:
    return mode_payload_service.normalize_mode_payload_row_id(row_id, source)


def mode_payload_table_exists(conn: Any, table_name: str, source: str) -> bool:
    return _mode_payload_table_exists(conn, table_name, source)


def mode_payload_table_columns(conn: Any, table_name: str, source: str) -> tuple[str, ...]:
    return _mode_payload_table_columns(conn, table_name, source)


def list_mode_payload_rows(
    db_path: str | Path,
    table_name: str,
    type_filter: str = "",
    web_filter: str = "",
    page: int = 1,
    page_size: int = 50,
    search: str = "",
    source: str = "public",
) -> dict[str, Any]:
    return mode_payload_service.list_mode_payload_rows(
        db_path,
        table_name,
        type_filter=type_filter,
        web_filter=web_filter,
        page=page,
        page_size=page_size,
        search=search,
        source=source,
    )


def update_mode_payload_row(
    db_path: str | Path,
    table_name: str,
    row_id: Any,
    data: dict[str, Any],
    source: str = "public",
) -> dict[str, Any]:
    return mode_payload_service.update_mode_payload_row(
        db_path,
        table_name,
        row_id,
        data,
        source=source,
    )


def delete_mode_payload_row(
    db_path: str | Path,
    table_name: str,
    row_id: Any,
    source: str = "public",
) -> None:
    mode_payload_service.delete_mode_payload_row(
        db_path,
        table_name,
        row_id,
        source=source,
    )
